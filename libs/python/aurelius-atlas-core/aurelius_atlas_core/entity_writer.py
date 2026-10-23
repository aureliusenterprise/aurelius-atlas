"""``EntityWriter``: creating, updating and deleting entities as ``AtlasEntityStoreV2`` does (EWR-02 to EWR-16).

``createOrUpdate``, ``preCreateOrUpdate``, ``updateByUniqueAttributes`` and ``updateEntityAttributeByGuid``, with
the ``EntityMutationContext`` they fill: a request is discovered, mapped in memory, its relationship attributes
too (REL-11, DD-066), and written in one write (DD-052). ``deleteById``, ``deleteByIds``,
``deleteByUniqueAttributes`` and ``purgeByIds`` through the delete handlers (EDL-02 to EDL-09).
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
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
)
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.builtin.object_id_type import is_assigned_guid
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.values import relationship_type_of

from aurelius_atlas_core.delete_handler import DeleteHandler
from aurelius_atlas_core.delete_type import DeleteType
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
    EntityStore,
    EntityVersionConflictError,
    EntityWriteError,
    RelationshipChange,
    TaskChange,
    UniqueValueTakenError,
)
from aurelius_atlas_core.hard_delete_handler import HardDeleteHandler
from aurelius_atlas_core.relationship_mapper import RelationshipMapper
from aurelius_atlas_core.soft_delete_handler import SoftDeleteHandler
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.tag_propagation import Deferral, TagPropagation
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
    guid_assignments: dict[str, str] = field(default_factory=dict)
    guids: dict[str | None, str] = field(default_factory=dict)

    def add_created(self, request_guid: str | None, entity: AtlasEntity, entity_type: EntityType) -> None:
        guid = str(entity.guid)
        self.created.append((entity, entity_type))
        self._assign(request_guid, guid)

    def add_updated(
        self, request_guid: str | None, entity: AtlasEntity, entity_type: EntityType, stored: VersionedEntity
    ) -> None:
        guid = str(entity.guid)
        if request_guid in self.guids or guid in self.guids:
            return
        self.updated.append((entity, entity_type, stored))
        self._assign(request_guid, guid)

    def _assign(self, request_guid: str | None, guid: str) -> None:
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


class EntityWriter:
    """Writes entities of a request into ``store``, as ``user``; ``delete_type`` is the default delete (EDL-04).

    ``tasks`` defers propagation to tasks (TSK-02); ``notifier`` is told what each request changed (DD-084).
    """

    def __init__(
        self,
        store: EntityStore,
        *,
        user: str | None = None,
        delete_type: DeleteType = DeleteType.SOFT,
        tasks: bool = False,
        notifier: EntityChangeNotifier | None = None,
    ) -> None:
        self._store = store
        self._user = user
        self._delete_type = DeleteType.SOFT if delete_type is DeleteType.DEFAULT else delete_type
        self._tasks = tasks
        self._notifier = notifier
        self._record = RequestRecord()

    async def delete_by_id(self, guid: str, delete_type: DeleteType = DeleteType.DEFAULT) -> EntityMutationResponse:
        """``deleteById``: the entity with ``guid`` and what it owns; an unknown GUID deletes nothing (EDL-03).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` for an empty GUID.
        """
        if not guid:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        return await self._delete(lambda: self._stored([guid]), delete_type)

    async def delete_by_ids(
        self, guids: Sequence[str], delete_type: DeleteType = DeleteType.DEFAULT
    ) -> EntityMutationResponse:
        """``deleteByIds``: the entities with these GUIDs and what they own (EDL-02, EDL-03).

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` when no GUID is given.
        """
        if not guids:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUIDS)
        return await self._delete(lambda: self._stored(guids), delete_type)

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
            return [] if found is None else [found]

        return await self._delete(holder, delete_type)

    async def purge_by_ids(self, guids: Sequence[str]) -> EntityMutationResponse:
        """``purgeByIds``: remove the ``DELETED`` entities with these GUIDs and what they own (EDL-02 to EDL-08).

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` when no GUID is given.
        """
        if not guids:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUIDS)

        async def deleted() -> list[VersionedEntity]:
            return [found for found in await self._stored(guids) if found.entity.state is EntityStatus.DELETED]

        return await self._delete(deleted, DeleteType.HARD, purge=True)

    async def _stored(self, guids: Sequence[str]) -> list[VersionedEntity]:
        found = await self._store.get_many(guids)
        return [found[guid] for guid in dict.fromkeys(guids) if guid in found]

    async def _delete(
        self, candidates: Candidates, delete_type: DeleteType, *, purge: bool = False
    ) -> EntityMutationResponse:
        """``deleteVertices`` and ``purgeVertices``, run again once after a lost race (EDL-08, EDL-09)."""
        hard = (self._delete_type if delete_type is DeleteType.DEFAULT else delete_type) is DeleteType.HARD
        for attempt in range(1, ATTEMPTS + 1):
            handler: DeleteHandler = (HardDeleteHandler if hard else SoftDeleteHandler)(
                self._store, now=self._store.now(), user=self._user, purge=purge, deferral=self._deferral()
            )
            try:
                return await self._mutated(await self._deleted(handler, await candidates(), purge=purge))
            except EntityVersionConflictError as conflict:
                if attempt == ATTEMPTS:
                    raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(conflict)) from conflict
            except (UniqueValueTakenError, EntityWriteError) as failure:
                raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(failure)) from failure
        raise AssertionError  # pragma: no cover - the loop returns or raises

    async def _mutated(self, response: EntityMutationResponse) -> EntityMutationResponse:
        """``onEntitiesMutated``: the response pruned, as Atlas answers it, and told to the notifier (AUD-02).

        The classifications created entities were given come first, the propagations after (CAU-02, CAU-05).
        """
        prune_response(response)
        record, self._record = self._record, RequestRecord()
        notifier = self._notifier
        if notifier is not None:
            for guids, instance in record.added_classifications:
                await notifier.on_classifications_added(guids, [instance], user=self._user)
            await notifier.on_entities_mutated(response, user=self._user)
            gone = [
                str(header.guid)
                for operation in (EntityOperation.DELETE, EntityOperation.PURGE)
                for header in response.get_entities_by_operation(operation) or []
            ]
            await notifier.notify_propagated_entities(record.added, record.removed, user=self._user, deleted=gone)
        return response

    async def _deleted(
        self, handler: DeleteHandler, candidates: list[VersionedEntity], *, purge: bool
    ) -> EntityMutationResponse:
        deletion = await handler.delete_entities(candidates)
        self._record = RequestRecord()
        self._record.merge(deletion.added, deletion.removed)
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

    async def create_or_update(
        self, entities: AtlasEntityWithExtInfo | AtlasEntitiesWithExtInfo | None
    ) -> EntityMutationResponse:
        """``createOrUpdate``: create the request's entities or update those already stored (EWR-02 to EWR-13)."""
        return await self._run(_stream(entities), partial=False)

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
        return await self._run(_stream(entity_info), partial=True)

    async def update_attribute_by_guid(self, guid: str, name: str | None, value: object) -> EntityMutationResponse:
        """``updateEntityAttributeByGuid``: set one primitive or reference attribute of an entity (EWR-15).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND``, ``UNKNOWN_ATTRIBUTE`` or ``ATTRIBUTE_UPDATE_NOT_SUPPORTED``.
        """
        found = await self._store.get(guid)
        if found is None:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
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
        return await self._run(EntityStream([entity], AtlasEntityExtInfo()), partial=True)

    async def _run(self, stream: EntityStream, *, partial: bool) -> EntityMutationResponse:
        """Run the request, once more when its write loses a race (EWR-16, DD-052).

        Raises:
            AtlasError: ``INTERNAL_ERROR`` for a second lost race, a unique value held by another entity, or a
                write that failed.
        """
        for attempt in range(1, ATTEMPTS + 1):
            try:
                return await self._mutated(await self._create_or_update(_copy(stream), partial=partial))
            except EntityVersionConflictError as conflict:
                if attempt == ATTEMPTS:
                    raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(conflict)) from conflict
            except (UniqueValueTakenError, EntityWriteError) as failure:
                raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(failure)) from failure
        raise AssertionError  # pragma: no cover - the loop returns or raises

    async def _create_or_update(self, stream: EntityStream, *, partial: bool) -> EntityMutationResponse:
        self._record = RequestRecord()
        discovery = EntityDiscovery(self._store, stream)
        context = await discovery.discover()
        mutation = await self._prepare(discovery, context, partial=partial)
        skipped = await self._unchanged(mutation)
        now = self._store.now()
        mapper = EntityMapper(
            self._store.registry,
            resolve=lambda value: self._resolve(context, mutation, value),
            guid_assignments=mutation.guid_assignments,
            now=now,
            user=self._user,
            is_deleted=lambda guid: (
                guid in context.stored and context.stored[guid].entity.state is EntityStatus.DELETED
            ),
        )
        relationships = RelationshipMapper(
            self._store,
            resolve=lambda value: self._resolve(context, mutation, value),
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
        )
        written: dict[str, StoredEntity] = {}
        classified: list[ClassificationChange] = []
        for entity, entity_type in mutation.created:
            await relationships.map(entity, entity_type, str(entity.guid), EntityOperation.CREATE)
            written[str(entity.guid)] = mapper.create(entity, entity_type, str(entity.guid))
            if entity.classifications:
                written[str(entity.guid)], added = self._classified(written[str(entity.guid)], entity.classifications)
                classified += [ClassificationChange(instance) for instance in added]
        operation = EntityOperation.PARTIAL_UPDATE if partial else EntityOperation.UPDATE
        for entity, entity_type, stored in mutation.updated:
            if entity.guid not in skipped:
                await relationships.map(entity, entity_type, str(entity.guid), operation)
                new = mapper.update(entity, entity_type, stored.entity, partial=partial)
                if not partial and stored.entity.is_incomplete:
                    new = new.model_copy(update={"is_incomplete": False})
                written[str(entity.guid)] = new
        reported = await self._touch(mapper, context, written, skipped)
        for guid, listed in relationships.listings().items():
            current = written[guid] if guid in written else context.stored[guid].entity
            written[guid] = current.model_copy(update={"relationship_guids": listed or None})
        for guid in mapper.revived:
            current = written[guid] if guid in written else context.stored[guid].entity
            written[guid] = current.model_copy(update={"state": EntityStatus.ACTIVE})  # OWN-04
        changes: dict[str, EntityChange] = {}
        for guid, new in written.items():
            stored = context.stored.get(guid)
            changes[guid] = EntityChange(new, None if stored is None else stored.version)
        tasks = await self._propagate(relationships, changes, classified)
        relationship_changes = {change.relationship.guid: change for change in relationships.relationship_changes()}
        deleted = await self._drop_owned(
            mapper.dropped,
            relationships,
            changes,
            relationship_changes,
            now,
        )
        classified += deleted.classification_changes
        tasks += deleted.task_changes
        if changes or relationship_changes or classified:
            await self._store.write(list(changes.values()), list(relationship_changes.values()), classified, tasks)
        return await self._response(mutation, skipped, reported + deleted.updated, partial=partial, deleted=deleted)

    async def _propagate(
        self,
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
            deferral=self._deferral(),
        )
        for relationship in relationships.created():
            await propagation.relationship_created(relationship)
        for relationship in relationships.removed():
            await propagation.relationship_removed(relationship)
        for instance in instances.values():
            if instance.entity_guid:
                reached = await propagation.propagate(instance, instance.entity_guid) if instance.propagate else []
                self._record.added_classifications.append(([instance.entity_guid, *reached], instance))
        for change in propagation.entity_changes(changes):
            changes[change.entity.guid] = change
        self._record.merge(propagation.added, propagation.removed)
        return [TaskChange(task) for task in propagation.tasks()]

    def _deferral(self) -> Deferral | None:
        """Tasks for propagation, recorded by the writer's user now, when they are enabled (TSK-02, TSK-08)."""
        return Deferral(self._user, self._store.now(), self._store.new_guid) if self._tasks else None

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

    async def _drop_owned(
        self,
        dropped: list[str],
        relationships: RelationshipMapper,
        changes: dict[str, EntityChange],
        relationship_changes: dict[str, RelationshipChange],
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
            view, now=now, user=self._user, deferral=self._deferral()
        )
        found = await view.get_many(dropped)
        deletion = await handler.delete_entities([found[guid] for guid in dropped if guid in found])
        self._record.merge(deletion.added, deletion.removed)
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

    async def _prepare(self, discovery: EntityDiscovery, context: DiscoveryContext, *, partial: bool) -> _Mutation:
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
                discovery.validate_and_normalize(entity, for_update=partial)
                entity.guid = found
                if partial and stored.entity.is_incomplete:
                    continue  # Atlas leaves an incomplete entity out of a partial update
                if stored.entity.is_incomplete:
                    entity.is_incomplete = False
                mutation.add_updated(request_guid, entity, entity_type, stored)
            else:
                discovery.validate_and_normalize(entity, for_update=False)
                guid = self._store.new_guid()
                context.resolved_guids[request_guid] = guid
                context.add_resolved_by_unique(_object_id(entity, entity_type), guid)
                entity.guid = guid
                mutation.add_created(request_guid, entity, entity_type)
        return mutation

    def _resolved_entity(self, context: DiscoveryContext, entity: AtlasEntity, entity_type: EntityType) -> str | None:
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

    async def _unchanged(self, mutation: _Mutation) -> set[str]:
        """The updated entities the comparator finds unchanged; they are neither written nor reported (EWR-08)."""
        comparator = EntityComparator(EntityRetriever(self._store), mutation.guid_assignments)
        skipped: set[str] = set()
        for entity, entity_type, stored in mutation.updated:
            if entity.status is EntityStatus.DELETED:
                continue
            if not await comparator.has_difference(entity, entity_type, stored.entity):
                skipped.add(str(entity.guid))
        return skipped

    def _resolve(self, context: DiscoveryContext, mutation: _Mutation, value: object) -> str:
        """``getInstanceType`` and ``mapObjectIdValue``: the GUID of the entity a reference names (EWR-11).

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
        if entity_type is None:
            raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, value)
        if found is None:
            found = context.resolved_object_id(object_id, list(entity_type.all_sub_types))
        if found is None:
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
            if entity.guid not in skipped:
                response.add_entity(operation, await retriever.header(str(entity.guid)))
        taken = {str(header.guid): header for header in deleted.headers}
        for header in deleted.headers:
            response.add_entity(EntityOperation.DELETE, header)
        for guid in dict.fromkeys(reported):
            header = taken.get(guid) or await retriever.header(guid, classifications=False)  # as recorded before
            response.add_entity(operation, header)
        response.guid_assignments = mutation.guid_assignments
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


def _stream(entities: AtlasEntityWithExtInfo | AtlasEntitiesWithExtInfo | None) -> EntityStream:
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
