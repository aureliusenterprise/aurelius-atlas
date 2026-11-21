"""``EntityWriter``: creating, updating and deleting entities as ``AtlasEntityStoreV2`` does (EWR-02 to EWR-16).

``createOrUpdate``, ``preCreateOrUpdate``, ``updateByUniqueAttributes`` and ``updateEntityAttributeByGuid``, with
the ``EntityMutationContext`` they fill: a request is discovered, mapped in memory, its relationship attributes
too (REL-11, DD-066), and written in one write (DD-052). ``deleteById``, ``deleteByIds``,
``deleteByUniqueAttributes`` and ``purgeByIds`` through the delete handlers (EDL-02 to EDL-09).

``WritePipeline`` is that mechanism on its own: the discovery, mapping and commit steps every write runs, with
the per-attempt ``WriteTransaction`` they share. ``EntityWriter`` is the request-facing writer built on it (this
module), and ``ImportWriter`` in ``import_writer.py`` is the import's, which shares the same steps and the same
transaction object without subclassing ``EntityWriter`` (WRS-07, DD-780).
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasEntityExtInfo,
    AtlasEntityHeader,
    AtlasEntityWithExtInfo,
    AtlasObjectId,
    EntityMutationResponse,
    EntityOperation,
    EntityStatus,
    RelationshipStatus,
)
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.builtin.object_id_type import is_assigned_guid
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.values import relationship_type_of

from aurelius_atlas_core.authorization import ALLOW_ALL, AtlasPrivilege, Authorizer
from aurelius_atlas_core.delete_handler import DeleteHandler
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_business_metadata import add_or_update_business_attributes, set_business_attributes
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier, RequestRecord, prune_response
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_comparator import EntityComparator
from aurelius_atlas_core.entity_discovery import DiscoveryContext, EntityDiscovery, EntityStream, object_id_of
from aurelius_atlas_core.entity_documents import VersionedEntity
from aurelius_atlas_core.entity_mapper import EntityMapper
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import (
    ClassificationChange,
    EntityChange,
    EntityVersionConflictError,
    EntityWriteError,
    RelationshipChange,
    TaskChange,
    UniqueValueTakenError,
    WriteStore,
)
from aurelius_atlas_core.guids import AssignedGuid, as_assigned_guid
from aurelius_atlas_core.hard_delete_handler import HardDeleteHandler
from aurelius_atlas_core.relationship_mapper import RelationshipMapper
from aurelius_atlas_core.soft_delete_handler import SoftDeleteHandler
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.tag_propagation import Deferral, TagPropagation
from aurelius_atlas_core.task_hold import TaskHold
from aurelius_atlas_core.transaction_view import TransactionView

NO_ENTITY_TO_UPDATE = "no entity to update."
NO_GUIDS = "Guid(s) not specified"
ATTEMPTS = 2
"""A request that loses a race is run once more (DD-052)."""


@dataclass
class _Mutation:
    """``EntityMutationContext``: the entities to create and to update, and the GUIDs given to them."""

    created: list[tuple[AtlasEntity, EntityType]] = field(default_factory=list)
    updated: list[tuple[AtlasEntity, EntityType, VersionedEntity]] = field(default_factory=list)
    guid_assignments: dict[str, AssignedGuid] = field(default_factory=dict)
    """What each placeholder GUID of the request became (ENT-17); assigned values only (DV-162)."""
    guids: dict[str | None, AssignedGuid] = field(default_factory=dict)
    to_delete: list[str] = field(default_factory=list)
    """The entities an import gives ``DELETED`` that are ``ACTIVE`` (IMP-04)."""
    reactivated: set[str] = field(default_factory=set)
    """The ``DELETED`` entities an import gives ``ACTIVE`` (IMP-04)."""

    def add_created(self, request_guid: str | None, entity: AtlasEntity, entity_type: EntityType) -> None:
        guid = as_assigned_guid(str(entity.guid))
        self.created.append((entity, entity_type))
        self._assign(request_guid, guid)

    def add_updated(
        self, request_guid: str | None, entity: AtlasEntity, entity_type: EntityType, stored: VersionedEntity
    ) -> None:
        guid = as_assigned_guid(str(entity.guid))
        if request_guid in self.guids or guid in self.guids:
            return
        self.updated.append((entity, entity_type, stored))
        self._assign(request_guid, guid)

    def _assign(self, request_guid: str | None, guid: AssignedGuid) -> None:
        self.guids[guid] = guid
        if request_guid != guid:
            self.guid_assignments[str(request_guid)] = guid
            self.guids[request_guid] = guid


@dataclass
class _Dropped:
    """The owned entities an update deleted (their headers), and the entities those deletes changed (OWN-03)."""

    headers: list[AtlasEntityHeader] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    classification_changes: list[ClassificationChange] = field(default_factory=list)
    task_changes: list[TaskChange] = field(default_factory=list)


type Candidates = Callable[[], Awaitable[list[VersionedEntity]]]
"""Reads the entities a delete names, again for each attempt."""


@dataclass
class WriteTransaction:
    """The state one write attempt carries between its steps (WRS-05, WRS-06, DD-776, DD-779).

    ``importing`` and ``hold`` are the attempt's options, fixed when it is built; ``record``, ``deletions`` and
    ``guids`` are what a step writes and a later step reads. Each writer builds one at the top of each attempt
    and passes it to every step, so a retry starts clean: no write's state survives on the writer into the next
    attempt. The order-sensitive reads (``deletions``, ``guids``) are set by ``_create_or_update`` and read only
    after the run has returned, so the sequence rides the object's lifetime rather than a mutable writer field.
    """

    importing: bool = False
    """True for ``createOrUpdateForImport`` alone (IMP-01); it changes discovery, mapping and the change check."""
    hold: TaskHold | None = None
    """The import's task hold, or None (IMT-01); the deferral records propagation tasks with it."""
    record: RequestRecord = field(default_factory=RequestRecord)
    """What the write changed, told to the notifier once it is written (DD-084)."""
    deletions: list[str] = field(default_factory=list)
    """The GUIDs an import gives ``DELETED`` that are ``ACTIVE``; deleted after the entities land (IMP-04)."""
    guids: dict[str, str] = field(default_factory=dict)
    """The GUID each request GUID became, for an import's classification replace (IMP-06)."""


class WritePipeline:
    """The write mechanism every writer runs: discovery, mapping and commit, over one transaction per attempt.

    Writes entities of a request into ``store``, as ``user``; ``delete_type`` is the default delete (EDL-04).
    ``tasks`` defers propagation to tasks (TSK-02); ``notifier`` is told what each request changed (DD-084);
    ``authorizer`` checks each entity created, updated or deleted (AUZ-07). ``unsafe_reparent`` lets a
    parent-side save move a child it does not own, and skips the refusal RPS-01 makes (DD-755, DD-757).

    It holds no state of one write: the ``WriteTransaction`` a step builds carries it (WRS-05, WRS-06), and the
    import path's flag and task hold ride that transaction too, so the shared pipeline carries no import-only
    field (WRS-07, DD-778).
    """

    def __init__(  # noqa: PLR0913 - the request's options, each a keyword
        self,
        store: WriteStore,
        *,
        user: str | None = None,
        delete_type: DeleteType = DeleteType.SOFT,
        tasks: bool = False,
        notifier: EntityChangeNotifier | None = None,
        authorizer: Authorizer = ALLOW_ALL,
        unsafe_reparent: bool = False,
    ) -> None:
        self._store = store
        self._user = user
        self._authorizer = authorizer
        self._delete_type = DeleteType.SOFT if delete_type is DeleteType.DEFAULT else delete_type
        self._tasks = tasks
        self._notifier = notifier
        self._unsafe_reparent = unsafe_reparent

    async def _deletable(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The stored entities of the GUIDs, each needing ``ENTITY_DELETE`` (AUZ-07)."""
        found = await self._stored(guids)
        for candidate in found:
            self._authorizer.verify_access(AtlasPrivilege.ENTITY_DELETE, "delete entity: guid=", candidate.entity.guid)
        return found

    async def _stored(self, guids: Sequence[str]) -> list[VersionedEntity]:
        found = await self._store.get_many(guids)
        return [found[guid] for guid in dict.fromkeys(guids) if guid in found]

    async def _delete(
        self, candidates: Candidates, txn: WriteTransaction, delete_type: DeleteType, *, purge: bool = False
    ) -> EntityMutationResponse:
        """``deleteVertices`` and ``purgeVertices``, run again once after a lost race (EDL-08, EDL-09)."""
        hard = (self._delete_type if delete_type is DeleteType.DEFAULT else delete_type) is DeleteType.HARD
        for attempt in range(1, ATTEMPTS + 1):
            handler: DeleteHandler = (HardDeleteHandler if hard else SoftDeleteHandler)(
                self._store, now=self._store.now(), user=self._user, purge=purge, deferral=self._deferral(txn)
            )
            try:
                return await self._mutated(await self._deleted(handler, txn, await candidates(), purge=purge), txn)
            except EntityVersionConflictError as conflict:
                if attempt == ATTEMPTS:
                    raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(conflict)) from conflict
            except (UniqueValueTakenError, EntityWriteError) as failure:
                raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(failure)) from failure
        raise AssertionError  # pragma: no cover - the loop returns or raises

    def _record_labels(self, txn: WriteTransaction, created: StoredEntity) -> None:
        """``setLabels`` of a created entity: its labels told as added once it is written (LBL-05)."""
        if created.labels:
            txn.record.added_labels.append((created.guid, list(created.labels)))

    def _business_attributes(
        self,
        txn: WriteTransaction,
        mapper: EntityMapper,
        created: StoredEntity,
        entity: AtlasEntity,
        entity_type: EntityType,
    ) -> StoredEntity:
        """``addOrUpdateBusinessAttributes`` of a created entity: those set told once it is written (BMD-02, BMD-06)."""
        stored, updated = add_or_update_business_attributes(mapper, created, entity_type, entity.business_attributes)
        if updated:
            txn.record.business_attributes[created.guid] = updated
        return stored

    async def _mutated(self, response: EntityMutationResponse, txn: WriteTransaction) -> EntityMutationResponse:
        """``onEntitiesMutated``: the response pruned, as Atlas answers it, and told to the notifier (AUD-02).

        The labels created entities were given come first, then each one's classifications and business attributes,
        the propagations after (LBL-05, CAU-02, BMD-06, CAU-05).
        """
        prune_response(response)
        record, txn.record = txn.record, RequestRecord()
        notifier = self._notifier
        if notifier is not None:
            for guid, labels in record.added_labels:
                await notifier.on_labels_updated(guid, labels, [], user=self._user)
            for guid, added, removed in record.updated_labels:
                await notifier.on_labels_updated(guid, added, removed, user=self._user)
            business = dict(record.business_attributes)
            for guids, instance in record.added_classifications:
                await self._notify_business_attributes(notifier, business, before=guids[0])
                await notifier.on_classifications_added(guids, [instance], user=self._user)
            await self._notify_business_attributes(notifier, business, before=None)
            await notifier.on_entities_mutated(response, user=self._user, importing=txn.importing)
            gone = [
                str(header.guid)
                for operation in (EntityOperation.DELETE, EntityOperation.PURGE)
                for header in response.get_entities_by_operation(operation) or []
            ]
            await notifier.notify_propagated_entities(record.added, record.removed, user=self._user, deleted=gone)
        return response

    async def _notify_business_attributes(
        self, notifier: EntityChangeNotifier, pending: dict[str, dict[str, dict[str, Any]]], *, before: str | None
    ) -> None:
        """The business attributes of the created entities ahead of ``before``, or of all, in creation order."""
        for guid in list(pending):
            if guid == before:
                return
            await notifier.on_business_attributes_updated(guid, pending.pop(guid), user=self._user)

    async def _deleted(
        self, handler: DeleteHandler, txn: WriteTransaction, candidates: list[VersionedEntity], *, purge: bool
    ) -> EntityMutationResponse:
        deletion = await handler.delete_entities(candidates)
        txn.record = RequestRecord()
        txn.record.merge(deletion.added, deletion.removed)
        retriever = EntityRetriever(self._store)
        headers = [await retriever.header(guid, classifications=purge) for guid in deletion.deleted]
        if deletion.changes or deletion.relationship_changes or deletion.classification_changes:
            await self._store.write(
                deletion.changes, deletion.relationship_changes, deletion.classification_changes, deletion.task_changes
            )
        response = EntityMutationResponse()
        for header in headers:
            response.add_entity(EntityOperation.PURGE if purge else EntityOperation.DELETE, header)
        for guid in [] if purge else deletion.updated:
            response.add_entity(EntityOperation.UPDATE, await retriever.header(guid, classifications=False))
        return response

    async def _run(
        self,
        stream: EntityStream,
        *,
        partial: bool,
        importing: bool = False,
        hold: TaskHold | None = None,
    ) -> tuple[EntityMutationResponse, WriteTransaction]:
        """Run the request, once more when its write loses a race (EWR-16, DD-052).

        Answers the response and the ``WriteTransaction`` the attempt ended on: the import path reads the
        deletions and the GUID assignments the attempt recorded (IMP-04, IMP-06). Each attempt builds its own
        transaction, so a retry never reads what the lost attempt left behind (WRS-05, WRS-06). The import's
        ``importing`` flag and task ``hold`` ride that transaction, so no writer field holds them (WRS-07).

        Raises:
            AtlasError: ``INTERNAL_ERROR`` for a second lost race, a unique value held by another entity, or a
                write that failed.
        """
        for attempt in range(1, ATTEMPTS + 1):
            try:
                response, txn = await self._create_or_update(
                    _copy(stream), partial=partial, importing=importing, hold=hold
                )
                return await self._mutated(response, txn), txn
            except EntityVersionConflictError as conflict:
                if attempt == ATTEMPTS:
                    raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(conflict)) from conflict
            except (UniqueValueTakenError, EntityWriteError) as failure:
                raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(failure)) from failure
        raise AssertionError  # pragma: no cover - the loop returns or raises

    async def _create_or_update(
        self, stream: EntityStream, *, partial: bool, importing: bool, hold: TaskHold | None
    ) -> tuple[EntityMutationResponse, WriteTransaction]:
        txn = WriteTransaction(importing=importing, hold=hold)
        discovery = EntityDiscovery(self._store, stream, importing=importing)
        context = await discovery.discover()
        mutation = await self._prepare(discovery, context, txn, partial=partial)
        txn.deletions = mutation.to_delete
        txn.guids = {str(key): str(guid) for key, guid in mutation.guids.items()}
        skipped = await self._unchanged(mutation, txn)
        self._verify_changes(mutation, skipped, txn)
        now = self._store.now()
        mapper = EntityMapper(
            self._store.registry,
            resolve=lambda value: self._resolve(context, mutation, txn, value),
            guid_assignments=mutation.guid_assignments,
            now=now,
            user=self._user,
            is_deleted=lambda guid: (
                guid in context.stored and context.stored[guid].entity.state is EntityStatus.DELETED
            ),
        )
        relationships = RelationshipMapper(
            self._store,
            resolve=lambda value: self._resolve(context, mutation, txn, value),
            known=context.stored,
            created={
                str(entity.guid): StoredEntity(
                    guid=str(entity.guid),
                    type_name=str(entity_type.type_name),
                    super_type_names=list(entity_type.all_super_types),
                )
                for entity, entity_type in mutation.created
            },
            now=now,
            user=self._user,
            hard=self._delete_type is DeleteType.HARD,
            touched=mapper.touched,
            dropped=mapper.dropped,
            importing=txn.importing,
            unsafe_reparent=self._unsafe_reparent,
        )
        written: dict[str, StoredEntity] = {}
        classified: list[ClassificationChange] = []
        for entity, entity_type in mutation.created:
            await relationships.map(entity, entity_type, str(entity.guid), EntityOperation.CREATE)
            written[str(entity.guid)], added = self._created(txn, mapper, entity, entity_type)
            classified += [ClassificationChange(instance) for instance in added]
        operation = EntityOperation.PARTIAL_UPDATE if partial else EntityOperation.UPDATE
        for entity, entity_type, stored in mutation.updated:
            if entity.guid not in skipped:
                await relationships.map(entity, entity_type, str(entity.guid), operation)
                new = mapper.update(entity, entity_type, stored.entity, partial=partial)
                if not partial and stored.entity.is_incomplete:
                    new = new.model_copy(update={"is_incomplete": False})
                written[str(entity.guid)] = self._imported_update(
                    txn, mapper, new=new, entity=entity, entity_type=entity_type, stored=stored.entity
                )
        reported = await self._touch(mapper, context, written, skipped)
        for guid, listed in relationships.listings().items():
            current = written[guid] if guid in written else context.stored[guid].entity
            written[guid] = current.model_copy(update={"relationship_guids": listed or None})
        for guid in [*mapper.revived, *mutation.reactivated]:
            current = written[guid] if guid in written else context.stored[guid].entity
            written[guid] = current.model_copy(update={"state": EntityStatus.ACTIVE})  # OWN-04, IMP-04
        changes: dict[str, EntityChange] = {}
        for guid, new in written.items():
            stored = context.stored.get(guid)
            changes[guid] = EntityChange(new, None if stored is None else stored.version)
        tasks = await self._propagate(txn, relationships, changes, classified)
        relationship_changes = {change.relationship.guid: change for change in relationships.relationship_changes()}
        relationship_changes.update(await self._reactivated_relationships(mutation, relationship_changes))
        deleted = await self._drop_owned(txn, mapper.dropped, relationships, changes, relationship_changes, now=now)
        classified += deleted.classification_changes
        tasks += deleted.task_changes
        if changes or relationship_changes or classified:
            await self._store.write(list(changes.values()), list(relationship_changes.values()), classified, tasks)
        response = await self._response(mutation, skipped, reported + deleted.updated, partial=partial, deleted=deleted)
        return response, txn

    async def _propagate(
        self,
        txn: WriteTransaction,
        relationships: RelationshipMapper,
        changes: dict[str, EntityChange],
        classified: list[ClassificationChange],
    ) -> list[TaskChange]:
        """Propagation by the relationships the request created or removed, and by its new entities' classifications.

        PRO-04, PRO-06, PRO-03; written with the request (PRO-10). Answers the tasks recorded (TSK-02).
        """
        pending, removed = relationships.pending()
        instances = {change.classification.guid: change.classification for change in classified}
        propagation = TagPropagation(
            self._store,
            entities={guid: (change.entity, change.expected) for guid, change in changes.items()},
            relationships={guid: found.relationship for guid, found in pending.items()},
            removed=removed,
            classifications=instances,
            deferral=self._deferral(txn),
        )
        for relationship in relationships.created():
            await propagation.relationship_created(relationship)
        for relationship in relationships.removed():
            await propagation.relationship_removed(relationship)
        for instance in instances.values():
            if instance.entity_guid:
                reached = await propagation.propagate(instance, instance.entity_guid) if instance.propagate else []
                txn.record.added_classifications.append(([instance.entity_guid, *reached], instance))
        for change in propagation.entity_changes(changes):
            changes[change.entity.guid] = change
        txn.record.merge(propagation.added, propagation.removed)
        return [TaskChange(task) for task in propagation.tasks()]

    def _deferral(self, txn: WriteTransaction) -> Deferral | None:
        """Tasks for propagation, recorded by the writer's user now, when they are enabled (TSK-02, TSK-08).

        The transaction's task hold, if any, holds the tasks it records (IMT-01); the import's writer sets it,
        and no other write has one.
        """
        return Deferral(self._user, self._store.now(), self._store.new_guid, txn.hold) if self._tasks else None

    def _classified(
        self, entity: StoredEntity, classifications: list[AtlasClassification]
    ) -> tuple[StoredEntity, list[StoredClassification]]:
        """``addClassifications`` of a created entity: no association checks, an unknown type fails (CLS-10).

        Raises:
            AtlasError: ``CLASSIFICATION_NOT_FOUND`` (DV-35).
        """
        for classification in classifications:
            if self._store.registry.classification_type(classification.type_name) is None:
                raise AtlasError(AtlasErrorCode.CLASSIFICATION_NOT_FOUND, classification.type_name)
        return EntityClassifications(self._store, user=self._user).attached(entity, classifications)

    async def _drop_owned(  # noqa: PLR0913 - the request's write set, each part needed to delete what it dropped
        self,
        txn: WriteTransaction,
        dropped: list[str],
        relationships: RelationshipMapper,
        changes: dict[str, EntityChange],
        relationship_changes: dict[str, RelationshipChange],
        *,
        now: int,
    ) -> _Dropped:
        """``deleteEdgeReference``'s ``deleteTypeVertex``: delete the owned entities the request dropped (OWN-02).

        The delete handler reads through a view of the request's changes; its changes replace the request's own for
        the same documents (DD-068). Answers the deleted entities' headers and the entities the deletes changed.
        """
        if not dropped:
            return _Dropped()
        pending, removed = relationships.pending()
        view = TransactionView(
            self._store,
            entities={
                guid: VersionedEntity(change.entity, change.expected)
                for guid, change in changes.items()
                if change.expected is not None
            },
            relationships=pending,
            removed=removed,
        )
        handler: DeleteHandler = (HardDeleteHandler if self._delete_type is DeleteType.HARD else SoftDeleteHandler)(
            view, now=now, user=self._user, deferral=self._deferral(txn)
        )
        found = await view.get_many(dropped)
        deletion = await handler.delete_entities([found[guid] for guid in dropped if guid in found])
        txn.record.merge(deletion.added, deletion.removed)
        retriever = EntityRetriever(self._store)
        headers = [await retriever.header(guid, classifications=False) for guid in deletion.deleted]
        for change in deletion.changes:
            changes[change.entity.guid] = change
        for change in deletion.relationship_changes:
            guid = change.relationship.guid
            if not relationships.is_new(guid):
                relationship_changes[guid] = change
            elif change.remove:
                relationship_changes.pop(guid, None)
            else:
                relationship_changes[guid] = RelationshipChange(change.relationship)
        return _Dropped(
            headers,
            [guid for guid in deletion.updated if guid not in deletion.deleted],
            deletion.classification_changes,
            deletion.task_changes,
        )

    async def _prepare(
        self, discovery: EntityDiscovery, context: DiscoveryContext, txn: WriteTransaction, *, partial: bool
    ) -> _Mutation:
        """``preCreateOrUpdate``: each request entity among the references, to update or to create (EWR-06)."""
        mutation = _Mutation()
        for request_guid in context.referenced_guids:
            entity = discovery.stream.get_by_guid(request_guid)
            if entity is None or request_guid in mutation.guids:
                continue
            entity_type = discovery.entity_type(entity.type_name)
            compact_attributes(entity, entity_type)
            found = self._resolved_entity(context, entity, entity_type)
            if found is not None:
                stored = context.stored[found]
                if txn.importing and stored.entity.is_incomplete and entity.is_incomplete:
                    continue  # an import leaves a shell entity it gives as a shell (IMP-04)
                discovery.validate_and_normalize(entity, for_update=partial)
                await discovery.validate_parent_groups(entity, entity_type, stored)
                entity.guid = found
                await self._refuse_held(discovery, entity, entity_type, found, txn)
                if partial and stored.entity.is_incomplete:
                    continue  # Atlas leaves an incomplete entity out of a partial update
                if stored.entity.is_incomplete:
                    entity.is_incomplete = False
                mutation.add_updated(request_guid, entity, entity_type, stored)
                if txn.importing:
                    _import_status(mutation, entity, stored.entity)
            else:
                discovery.validate_and_normalize(entity, for_update=False)
                await discovery.validate_parent_groups(entity, entity_type, None)
                kept = txn.importing and entity.guid is not None and is_assigned_guid(entity.guid)
                guid = as_assigned_guid(str(entity.guid)) if kept else self._store.new_guid()
                context.resolved_guids[request_guid] = guid
                context.add_resolved_by_unique(_object_id(entity, entity_type), guid)
                entity.guid = guid
                await self._refuse_held(discovery, entity, entity_type, guid, txn)
                mutation.add_created(request_guid, entity, entity_type)
        return mutation

    async def _refuse_held(
        self, discovery: EntityDiscovery, entity: AtlasEntity, entity_type: EntityType, guid: str, txn: WriteTransaction
    ) -> None:
        """The parent-safe check (RPS-01): an import is exempt, and so is a request that opted in (RPS-08, RPS-04)."""
        if txn.importing or self._unsafe_reparent:
            return
        await discovery.validate_parent_safe(entity, entity_type, guid)

    def _resolved_entity(
        self, context: DiscoveryContext, entity: AtlasEntity, entity_type: EntityType
    ) -> AssignedGuid | None:
        """``getResolvedEntityVertex``: the stored entity the request's entity resolved to, by GUID or values."""
        object_id = _object_id(entity, entity_type)
        found = context.resolved_guids.get(entity.guid)
        if found is not None:
            context.add_resolved_by_unique(object_id, found)
            return found
        found = context.resolved_object_id(object_id, list(entity_type.all_sub_types))
        if found is not None and found in context.stored:
            context.resolved_guids[entity.guid] = found
            return found
        return None

    def _created(
        self, txn: WriteTransaction, mapper: EntityMapper, entity: AtlasEntity, entity_type: EntityType
    ) -> tuple[StoredEntity, list[StoredClassification]]:
        """``createVertex`` and ``mapAttributesAndClassifications`` of a created entity: its attributes, labels,
        classifications and business attributes; an import's with its system attributes (EWR-09, IMP-02).
        """  # noqa: D205 - one sentence
        created = mapper.create(entity, entity_type, str(entity.guid))
        self._record_labels(txn, created)
        added: list[StoredClassification] = []
        if entity.classifications:
            given = [imported_classification(c) for c in entity.classifications] if txn.importing else None
            created, added = self._classified(created, given or entity.classifications)
        created = self._business_attributes(txn, mapper, created, entity, entity_type)
        return (with_system_attributes(created, entity) if txn.importing else created), added

    def _imported_update(  # noqa: PLR0913 - the entity before and after an import's update, with its type
        self,
        txn: WriteTransaction,
        mapper: EntityMapper,
        *,
        new: StoredEntity,
        entity: AtlasEntity,
        entity_type: EntityType,
        stored: StoredEntity,
    ) -> StoredEntity:
        """An import's update: business attributes overwritten, its system attributes and labels kept (IMP-02, IMP-06).

        The labels it changes are told, as ``updateSystemAttributes`` sets them.
        """
        if not txn.importing:
            return new
        new, updated = set_business_attributes(mapper, new, entity_type, entity.business_attributes)
        if updated:
            txn.record.business_attributes[new.guid] = updated
        new = with_system_attributes(new, entity)
        added = [label for label in new.labels or [] if label not in (stored.labels or [])]
        removed = [label for label in stored.labels or [] if label not in (new.labels or [])]
        if added or removed:
            txn.record.updated_labels.append((new.guid, added, removed))
        return new

    async def _reactivated_relationships(
        self, mutation: _Mutation, changes: Mapping[str, RelationshipChange]
    ) -> dict[str, RelationshipChange]:
        """``activateEntityRelationships``: a reactivated entity's ``DELETED`` relationships to the entities its
        relationship attributes name, ``ACTIVE`` again (IMP-04).
        """  # noqa: D205 - one sentence
        found: dict[str, RelationshipChange] = {}
        for entity, _, stored in mutation.updated:
            if entity.guid not in mutation.reactivated:
                continue
            related = _related_guids(entity)
            listed = await self._store.get_relationships(stored.entity.relationship_guids or [])
            for guid, relationship in listed.items():
                current = relationship.relationship
                other = current.end2_guid if current.end1_guid == entity.guid else current.end1_guid
                if guid in changes or current.state is not RelationshipStatus.DELETED or other not in related:
                    continue
                active = current.model_copy(update={"state": RelationshipStatus.ACTIVE})
                found[guid] = RelationshipChange(active, relationship.version)
        return found

    def _verify_changes(self, mutation: _Mutation, skipped: set[str], txn: WriteTransaction) -> None:
        """Each entity created needs ``ENTITY_CREATE``, then each changed one ``ENTITY_UPDATE``; an import's none.

        AUZ-07, IMP-07.
        """
        if txn.importing:
            return
        for entity, _ in mutation.created:
            self._authorizer.verify_access(AtlasPrivilege.ENTITY_CREATE, "create entity: type=", entity.type_name)
        for entity, _, _ in mutation.updated:
            if entity.guid not in skipped:
                self._authorizer.verify_access(AtlasPrivilege.ENTITY_UPDATE, "update entity: type=", entity.type_name)

    async def _unchanged(self, mutation: _Mutation, txn: WriteTransaction) -> set[str]:
        """The updated entities the comparator finds unchanged; they are neither written nor reported (EWR-08)."""
        comparator = EntityComparator(EntityRetriever(self._store), mutation.guid_assignments, importing=txn.importing)
        skipped: set[str] = set()
        for entity, entity_type, stored in mutation.updated:
            if entity.status is EntityStatus.DELETED:
                continue
            if not await comparator.has_difference(entity, entity_type, stored.entity):
                skipped.add(str(entity.guid))
        return skipped

    def _resolve(
        self, context: DiscoveryContext, mutation: _Mutation, txn: WriteTransaction, value: object
    ) -> str | None:
        """``getInstanceType`` and ``mapObjectIdValue``: the GUID of the entity a reference names (EWR-11).

        None for one an import names that is not there (IMP-05).

        Raises:
            AtlasError: ``INVALID_OBJECT_ID`` when the reference names no entity of a known type.
        """
        object_id = object_id_of(value)
        if object_id is None:
            raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, None)
        guid = object_id.guid
        found = context.resolved_guids.get(guid) if guid is not None else None
        if found is None and guid is not None and is_assigned_guid(guid):
            found = mutation.guids.get(guid)
        type_name = object_id.type_name
        if type_name is None and found is not None:
            known = context.stored.get(found)
            created = next((e.type_name for e, _ in mutation.created if e.guid == found), None)
            type_name = known.entity.type_name if known is not None else created
        entity_type = None if type_name is None else self._store.registry.entity_type(type_name)
        if entity_type is None and not txn.importing:
            raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, value)
        if found is None and entity_type is not None:
            found = context.resolved_object_id(object_id, list(entity_type.all_sub_types))
        if found is None and not txn.importing:
            raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, value)
        return found

    async def _touch(
        self, mapper: EntityMapper, context: DiscoveryContext, written: dict[str, StoredEntity], skipped: set[str]
    ) -> list[str]:
        """``recordEntityUpdate``: entities a new single reference reached are changed now (EWR-12).

        Answers those to report: not the skipped ones.
        """
        missing = [guid for guid in mapper.touched if guid not in written and guid not in context.stored]
        if missing:
            context.stored.update(await self._store.get_many(missing))
        for guid in mapper.touched:
            current = written.get(guid) or (context.stored[guid].entity if guid in context.stored else None)
            if current is not None:
                written[guid] = mapper.touch(current)
        return [guid for guid in mapper.touched if guid not in skipped and guid in written]

    async def _response(
        self, mutation: _Mutation, skipped: set[str], reported: list[str], *, partial: bool, deleted: _Dropped
    ) -> EntityMutationResponse:
        """``mapAttributesAndClassifications``' response: headers by operation, and the GUID assignments.

        Created and updated entities, then deleted ones, then those the request made updated (EWR-13, OWN-03).
        """
        retriever = EntityRetriever(self._store)
        response = EntityMutationResponse()
        operation = EntityOperation.PARTIAL_UPDATE if partial else EntityOperation.UPDATE
        for entity, _ in mutation.created:
            header = await retriever.header(str(entity.guid))
            header.classifications, header.classification_names = [], []  # constructHeader runs before they attach
            response.add_entity(EntityOperation.CREATE, header)
        for entity, _, _ in mutation.updated:
            if entity.guid in mutation.reactivated:
                response.add_entity(EntityOperation.CREATE, await retriever.header(str(entity.guid)))
            if entity.guid not in skipped:
                response.add_entity(operation, await retriever.header(str(entity.guid)))
        taken = {str(header.guid): header for header in deleted.headers}
        for header in deleted.headers:
            response.add_entity(EntityOperation.DELETE, header)
        for guid in dict.fromkeys(reported):
            header = taken.get(guid) or await retriever.header(guid, classifications=False)  # as recorded before
            response.add_entity(operation, header)
        response.guid_assignments = {key: str(guid) for key, guid in mutation.guid_assignments.items()}
        return response


class EntityWriter(WritePipeline):
    """The request-facing writer: the non-import create, update and delete paths an Atlas request takes.

    Import semantics answer from ``ImportWriter`` (``import_writer.py``), which shares this writer's steps and
    the ``WriteTransaction`` they fill; this writer carries no import-only flag, and each write it runs builds
    a fresh transaction with no hold (WRS-07, DD-778, DD-780).
    """

    async def delete_by_id(self, guid: str, delete_type: DeleteType = DeleteType.DEFAULT) -> EntityMutationResponse:
        """``deleteById``: the entity with ``guid`` and what it owns; an unknown GUID deletes nothing (EDL-03).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` for an empty GUID.
        """
        if not guid:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        return await self._delete(lambda: self._deletable([guid]), WriteTransaction(), delete_type)

    async def delete_by_ids(
        self, guids: Sequence[str], delete_type: DeleteType = DeleteType.DEFAULT
    ) -> EntityMutationResponse:
        """``deleteByIds``: the entities with these GUIDs and what they own (EDL-02, EDL-03).

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` when no GUID is given.
        """
        if not guids:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUIDS)
        return await self._delete(lambda: self._deletable(guids), WriteTransaction(), delete_type)

    async def delete_by_unique_attributes(
        self, entity_type: EntityType, values: Mapping[str, Any], delete_type: DeleteType = DeleteType.DEFAULT
    ) -> EntityMutationResponse:
        """``deleteByUniqueAttributes``: the ``ACTIVE`` entity holding the values, if any (EDL-02, EDL-03).

        Raises:
            AtlasError: ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` naming ``{}`` alone when no value is given.
        """
        if not values:
            raise AtlasError(AtlasErrorCode.INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND, java_string(dict(values)))

        async def holder() -> list[VersionedEntity]:
            found = await self._store.find_by_unique_attributes(entity_type, values)
            if found is None:
                return []
            self._authorizer.verify_access(
                AtlasPrivilege.ENTITY_DELETE,
                "delete entity: typeName=",
                entity_type.type_name,
                ", uniqueAttributes=",
                dict(values),
            )
            return [found]

        return await self._delete(holder, WriteTransaction(), delete_type)

    async def purge_by_ids(self, guids: Sequence[str]) -> EntityMutationResponse:
        """``purgeByIds``: remove the ``DELETED`` entities with these GUIDs and what they own (EDL-02 to EDL-08).

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` when no GUID is given.
        """
        if not guids:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUIDS)

        async def deleted() -> list[VersionedEntity]:
            return [found for found in await self._stored(guids) if found.entity.state is EntityStatus.DELETED]

        return await self._delete(deleted, WriteTransaction(), DeleteType.HARD, purge=True)

    async def create_or_update(
        self, entities: AtlasEntityWithExtInfo | AtlasEntitiesWithExtInfo | None
    ) -> EntityMutationResponse:
        """``createOrUpdate``: create the request's entities or update those already stored (EWR-02 to EWR-13)."""
        response, _ = await self._run(entity_stream(entities), partial=False)
        return response

    async def update_by_unique_attributes(
        self, entity_type: EntityType, values: Mapping[str, Any], entity_info: AtlasEntityWithExtInfo | None
    ) -> EntityMutationResponse:
        """``updateByUniqueAttributes``: partially update the entity holding the unique values (EWR-14).

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` without an entity, ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND``.
        """
        if entity_info is None or entity_info.entity is None:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_ENTITY_TO_UPDATE)
        found = await self._store.find_by_unique_attributes(entity_type, values)
        if found is None:
            raise AtlasError(
                AtlasErrorCode.INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND, entity_type.type_name, java_string(dict(values))
            )
        entity_info.entity.guid = found.entity.guid
        self._authorizer.verify_access(AtlasPrivilege.ENTITY_UPDATE, "update entity ByUniqueAttributes")
        response, _ = await self._run(entity_stream(entity_info), partial=True)
        return response

    async def update_attribute_by_guid(self, guid: str, name: str | None, value: object) -> EntityMutationResponse:
        """``updateEntityAttributeByGuid``: set one primitive or reference attribute of an entity (EWR-15).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND``, ``UNKNOWN_ATTRIBUTE`` or ``ATTRIBUTE_UPDATE_NOT_SUPPORTED``.
        """
        found = await self._store.get(guid)
        if found is None:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        self._authorizer.verify_access(AtlasPrivilege.ENTITY_UPDATE, "update entity ByUniqueAttributes : guid=", guid)
        type_name = found.entity.type_name
        entity_type = self._store.registry.entity_type(type_name)
        attribute = None
        if entity_type is not None and name is not None:
            attribute = entity_type.attribute(name) or entity_type.relationship_attribute(
                name, relationship_type_of(value)
            )
        if attribute is None:
            raise AtlasError(AtlasErrorCode.UNKNOWN_ATTRIBUTE, name, type_name)
        match attribute.attribute_type.category:
            case TypeCategory.PRIMITIVE:
                pass
            case TypeCategory.OBJECT_ID_TYPE if isinstance(value, str):
                value = AtlasObjectId(guid=value, type_name=attribute.attribute_def.type_name)
            case TypeCategory.OBJECT_ID_TYPE:
                value = attribute.attribute_type.get_normalized_value(value)
            case _:
                raise AtlasError(
                    AtlasErrorCode.ATTRIBUTE_UPDATE_NOT_SUPPORTED, name, attribute.attribute_type.type_name
                )
        entity = AtlasEntity(guid=guid, type_name=type_name, attributes={str(name): value})
        response, _ = await self._run(EntityStream([entity], AtlasEntityExtInfo()), partial=True)
        return response


def compact_attributes(entity: AtlasEntity, entity_type: EntityType) -> None:
    """``compactAttributes``: a relationship attribute given in ``attributes`` moves to ``relationshipAttributes``.

    It is dropped when ``relationshipAttributes`` already holds it (EWR-06).
    """
    for name in entity_type.relationship_attributes:
        if entity.has_attribute(name):
            value = entity.remove_attribute(name)
            if value is not None and entity.get_relationship_attribute(name) is None:
                entity.set_relationship_attribute(name, value)


def _object_id(entity: AtlasEntity, entity_type: EntityType) -> AtlasObjectId:
    """``getAtlasObjectId``: the entity's unique values, its GUID only when it has none."""
    unique = {
        name: value for name in entity_type.unique_attributes if (value := entity.get_attribute(name)) is not None
    }
    return AtlasObjectId(guid=None if unique else entity.guid, type_name=entity.type_name, unique_attributes=unique)


def entity_stream(entities: AtlasEntityWithExtInfo | AtlasEntitiesWithExtInfo | None) -> EntityStream:
    """``AtlasEntityStream``: one entity, possibly null, or the list of a bulk request."""
    if isinstance(entities, AtlasEntityWithExtInfo):
        return EntityStream([entities.entity], entities)
    if entities is None:
        return EntityStream([], AtlasEntityExtInfo())
    return EntityStream(list(entities.entities or []), entities)


def _copy(stream: EntityStream) -> EntityStream:
    """A copy of the request to change: discovery and mapping change its entities as Java's do."""
    ext_info = stream.ext_info.model_copy(deep=True)
    copies = {id(entity): entity.model_copy(deep=True) for entity in stream.entities if entity is not None}
    if isinstance(ext_info, AtlasEntityWithExtInfo) and ext_info.entity is not None:
        copies[id(stream.entities[0])] = ext_info.entity
    elif isinstance(ext_info, AtlasEntitiesWithExtInfo):
        ext_info.entities = [copies[id(entity)] for entity in stream.entities if entity is not None]
    return EntityStream([None if entity is None else copies[id(entity)] for entity in stream.entities], ext_info)


def with_system_attributes(stored: StoredEntity, entity: AtlasEntity) -> StoredEntity:
    """``updateSystemAttributes``: an imported entity's version, times, users, home, proxy flag, provenance, custom
    attributes and labels kept; its update time and user only when it gives no attribute, as ``mapAttributes``
    then changes them (IMP-02).
    """  # noqa: D205 - one sentence
    given: dict[str, Any] = {
        "version": entity.version,
        "create_time": _epoch_millis(entity.create_time),
        "created_by": entity.created_by or None,
        "home_id": entity.home_id or None,
        "is_proxy": entity.is_proxy,
        "provenance_type": entity.provenance_type,
        "custom_attributes": entity.custom_attributes,
    }
    if not entity.attributes:
        given.update(update_time=_epoch_millis(entity.update_time), updated_by=entity.updated_by or None)
    update = {name: value for name, value in given.items() if value is not None}
    if entity.labels is not None:
        update["labels"] = list(dict.fromkeys(entity.labels)) or None
    return stored.model_copy(update=update)


def _import_status(mutation: _Mutation, entity: AtlasEntity, stored: StoredEntity) -> None:
    """An import's status: ``DELETED`` deletes an ``ACTIVE`` entity, ``ACTIVE`` revives a ``DELETED`` one (IMP-04)."""
    if entity.status is EntityStatus.DELETED and stored.state is EntityStatus.ACTIVE:
        mutation.to_delete.append(stored.guid)
    elif entity.status is EntityStatus.ACTIVE and stored.state is EntityStatus.DELETED:
        mutation.reactivated.add(stored.guid)


def imported_classification(classification: AtlasClassification) -> AtlasClassification:
    """``addClassifications`` of an import: a classification that says nothing does not propagate (IMP-06)."""
    if classification.propagate is not None:
        return classification
    return classification.model_copy(update={"propagate": False})


def _related_guids(entity: AtlasEntity) -> set[str]:
    """``getRelatedEntitiesGuids``: the GUIDs the entity's relationship attributes name."""
    found: set[str] = set()
    for value in (entity.relationship_attributes or {}).values():
        for item in value if isinstance(value, list) else [value]:
            guid = getattr(item, "guid", None)
            if guid:
                found.add(str(guid))
    return found


def _epoch_millis(value: datetime | int | None) -> int | None:
    """A timestamp as epoch milliseconds, or None."""
    if value is None or isinstance(value, int):
        return value
    return int(value.timestamp() * 1000)
