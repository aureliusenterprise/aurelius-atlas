"""``EntityClassifications``: classifications attached directly to entities (CLS-03 to CLS-09).

The classification methods of ``AtlasEntityStoreV2`` (``getClassifications``, ``addClassifications``,
``addClassification``, ``updateClassifications``, ``deleteClassification``) and the mapping ``EntityGraphMapper``
does for them, on classification instances of their own index (DD-070), each request one write (DD-071), run again
once after a lost race (DD-052).
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasClassification, EntityOperation, EntityStatus
from aurelius_atlas_model.tasks import TaskStatus
from aurelius_atlas_typesystem.classification_type import ClassificationType
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.entity_documents import VersionedEntity
from aurelius_atlas_core.entity_mapper import EntityMapper
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import (
    ClassificationChange,
    EntityChange,
    EntityStore,
    EntityVersionConflictError,
    EntityWriteError,
    TaskChange,
    UniqueValueTakenError,
)
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.tag_propagation import Deferral, TagPropagation
from aurelius_atlas_core.typedef_document import DocumentVersion

ATTEMPTS = 2
"""A request that loses a race is run once more (DD-052)."""

PROPAGATE_DEFAULT = True
"""``atlas.classification.propagation.default`` (DD-072)."""
REMOVE_PROPAGATIONS_DEFAULT = False
"""``atlas.classification.propagation.remove.on.entity.delete`` (DD-072)."""

NO_GUID = "Guid(s) not specified"
NO_GUID_FOR_UPDATE = "Guid not specified"
NO_CLASSIFICATIONS = "classifications(s) not specified"
NO_CLASSIFICATION_NAME = "classifications not specified"
NO_CLASSIFICATION = "classification not specified"
ALREADY_ASSOCIATED = "entity: {guid}, already associated with classification: {name}"


class EntityClassifications:
    """Classifications of the entities of ``store``, changed as ``user``; ``tasks`` defers propagation (TSK-02)."""

    def __init__(self, store: EntityStore, *, user: str | None = None, tasks: bool = False) -> None:
        self._store = store
        self._user = user
        self._tasks = tasks

    async def get_classifications(self, guid: str) -> list[AtlasClassification]:
        """``getClassifications``: the entity's classifications (CLS-03).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND``.
        """
        return await EntityRetriever(self._store).classifications(guid)

    async def get_classification(self, guid: str, name: str) -> AtlasClassification:
        """``getClassification``: the first of the name attached directly, else the first of the name (CLS-03).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND``, ``CLASSIFICATION_NOT_FOUND``.
        """
        found = None
        for classification in await self.get_classifications(guid):
            if (classification.type_name or "").lower() != name.lower():
                continue
            if not classification.entity_guid or classification.entity_guid.lower() == guid.lower():
                return classification
            found = found or classification
        if found is None:
            raise AtlasError(AtlasErrorCode.CLASSIFICATION_NOT_FOUND, name)
        return found

    async def add_classifications(self, guid: str, classifications: Sequence[AtlasClassification] | None) -> None:
        """``addClassifications``: attach them to the entity, after checking them all (CLS-04, CLS-05).

        Raises:
            AtlasError: ``INVALID_PARAMETERS``, ``INSTANCE_GUID_NOT_FOUND``, ``CLASSIFICATION_NOT_FOUND``,
                ``INVALID_ENTITY_FOR_CLASSIFICATION``.
        """
        if not guid:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID)
        if not classifications:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_CLASSIFICATIONS)

        async def attempt() -> None:
            found = await self._entity(guid)
            given = [classification.model_copy(deep=True) for classification in classifications]
            for classification in given:
                self._validate(classification)
            await self._check_associations(found.entity, given)
            await self._write_added([(found, given)])

        await self._run(attempt)

    async def add_classification(self, guids: Sequence[str] | None, classification: AtlasClassification | None) -> None:
        """``addClassification``: attach one classification to each entity, after checking each (CLS-07).

        Raises:
            AtlasError: as ``add_classifications``.
        """
        if not guids:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID)
        if classification is None:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_CLASSIFICATION)
        checked = classification.model_copy(deep=True)
        self._validate(checked)

        async def attempt() -> None:
            targets: list[tuple[VersionedEntity, list[AtlasClassification]]] = []
            for guid in guids:
                found = await self._entity(guid)
                await self._check_associations(found.entity, [checked])
                targets.append((found, [checked.model_copy(deep=True)]))
            await self._write_added(targets)

        await self._run(attempt)

    async def update_classifications(self, guid: str, classifications: Sequence[AtlasClassification] | None) -> None:
        """``updateClassifications``: change classifications the entity has attached directly (CLS-08).

        Raises:
            AtlasError: ``INVALID_PARAMETERS``, ``INSTANCE_GUID_NOT_FOUND``, ``CLASSIFICATION_NOT_FOUND``,
                ``CLASSIFICATION_UPDATE_FROM_PROPAGATED_ENTITY``, ``CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY``.
        """
        if not guid:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID_FOR_UPDATE)
        if not classifications:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_CLASSIFICATIONS)

        async def attempt() -> None:
            found = await self._entity(guid)
            given = [classification.model_copy(deep=True) for classification in classifications]
            for classification in given:
                self._validate(classification)
            instances = await self._instances(found.entity)
            mapper = self._mapper()
            changes: dict[str, ClassificationChange] = {}
            entity = found.entity.touched(now=self._store.now(), user=self._user)
            propagation = self._propagation({guid: (entity, found.version)})
            for classification in given:
                name = str(classification.type_name)
                if not classification.entity_guid:
                    classification.entity_guid = guid
                elif classification.entity_guid.lower() != guid.lower():
                    raise AtlasError(AtlasErrorCode.CLASSIFICATION_UPDATE_FROM_PROPAGATED_ENTITY, name)
                current = next((c for c in instances if c.classification.type_name == name and _direct(c, guid)), None)
                if current is None:
                    raise AtlasError(AtlasErrorCode.CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY, name)
                classification_type = self._validate(classification, update=True)
                stored = changes[current.guid].classification if current.guid in changes else current.classification
                updated = _updated(mapper, classification_type, classification, stored)
                changes[current.guid] = ClassificationChange(updated, current.version)
                await _propagate_change(propagation, guid, stored, updated, given=classification.propagate)
            await self._write_propagated(propagation, [(guid, found.version)], [], list(changes.values()))

        await self._run(attempt)

    async def delete_classification(self, guid: str, name: str, associated_entity_guid: str | None = None) -> None:
        """``deleteClassification``: remove a classification the entity has attached directly (CLS-09).

        Raises:
            AtlasError: ``INVALID_PARAMETERS``, ``INSTANCE_GUID_NOT_FOUND``, ``NO_CLASSIFICATIONS_FOUND_FOR_ENTITY``,
                ``CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY``, ``PROPAGATED_CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY``.
        """
        if not guid:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID)
        if not name:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_CLASSIFICATION_NAME)

        async def attempt() -> None:
            found = await self._entity(guid)
            if associated_entity_guid and associated_entity_guid != guid:
                await self._delete_propagated(found, name, associated_entity_guid)
                return
            direct = [instance for instance in await self._instances(found.entity) if _direct(instance, guid)]
            if not direct:
                raise AtlasError(AtlasErrorCode.NO_CLASSIFICATIONS_FOUND_FOR_ENTITY, guid)
            current = next((c for c in direct if c.classification.type_name == name), None)
            if current is None:
                raise AtlasError(AtlasErrorCode.CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY, name)
            propagation = self._propagation({guid: (found.entity, found.version)})
            if current.classification.propagate is not False:
                if propagation.deferred:
                    await self._check_no_pending(current.guid, guid)
                await propagation.withdraw(current.classification, guid)
            entity = propagation.entity(guid) or found.entity
            listed = [listed for listed in entity.classification_guids or [] if listed != current.guid]
            entity = entity.model_copy(update={"classification_guids": listed or None})
            propagation.put_entity(entity.touched(now=self._store.now(), user=self._user))
            kept = bool(await propagation.listed_by(current.classification))
            removal = ClassificationChange(current.classification, current.version, remove=not kept)
            await self._write_propagated(propagation, [(guid, found.version)], [], [] if kept else [removal])

        await self._run(attempt)

    async def _delete_propagated(self, found: VersionedEntity, name: str, associated: str) -> None:
        """``deletePropagatedClassification``: one propagated from a deleted entity stops being listed (PRO-08).

        Raises:
            AtlasError: ``PROPAGATED_CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY``,
                ``PROPAGATED_CLASSIFICATION_REMOVAL_NOT_SUPPORTED``.
        """
        guid = found.entity.guid
        current = next(
            (
                c
                for c in await self._instances(found.entity)
                if c.classification.type_name == name
                and c.classification.entity_guid == associated
                and not _direct(c, guid)
            ),
            None,
        )
        if current is None:
            raise AtlasError(
                AtlasErrorCode.PROPAGATED_CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY, name, associated, guid
            )
        if current.classification.entity_status is EntityStatus.ACTIVE:
            raise AtlasError(AtlasErrorCode.PROPAGATED_CLASSIFICATION_REMOVAL_NOT_SUPPORTED, name, associated)
        listed = [listed for listed in found.entity.classification_guids or [] if listed != current.guid]
        entity = found.entity.model_copy(update={"classification_guids": listed or None})
        propagation = TagPropagation(self._store, entities={guid: (entity, found.version)})
        kept = bool(await propagation.listed_by(current.classification))
        removal = ClassificationChange(current.classification, current.version, remove=True)
        await self._store.write([EntityChange(entity, found.version)], [], [] if kept else [removal])

    def attached(
        self, entity: StoredEntity, classifications: Sequence[AtlasClassification]
    ) -> tuple[StoredEntity, list[StoredClassification]]:
        """``EntityGraphMapper.addClassifications``: the new instances, and the entity listing them (CLS-05).

        A classification that says ``propagate`` and names another entity is left out. The entity is not touched.
        """
        mapper = self._mapper()
        instances = []
        for classification in classifications:
            if classification.propagate and classification.entity_guid and classification.entity_guid != entity.guid:
                continue
            classification_type = self._store.registry.classification_type(classification.type_name)
            if classification_type is None:  # pragma: no cover - checked before
                raise AtlasError(AtlasErrorCode.CLASSIFICATION_NOT_FOUND, classification.type_name)
            instances.append(_created(mapper, classification_type, classification, entity.guid, self._store.new_guid()))
        listed = [*(entity.classification_guids or []), *(instance.guid for instance in instances)]
        return entity.model_copy(update={"classification_guids": listed or None}), instances

    def _validate(self, classification: AtlasClassification, *, update: bool = False) -> ClassificationType:
        """``validateAndNormalize`` (``ForUpdate``): the classification's type checks and normalises it (CLS-04).

        Raises:
            AtlasError: ``CLASSIFICATION_NOT_FOUND`` for an unknown type, ``INVALID_PARAMETERS`` with the messages.
        """
        classification_type = self._store.registry.classification_type(classification.type_name)
        if classification_type is None:
            raise AtlasError(AtlasErrorCode.CLASSIFICATION_NOT_FOUND, classification.type_name)
        messages: list[str] = []
        name = str(classification.type_name)
        if update:
            classification_type.validate_value_for_update(classification, name, messages)
        else:
            classification_type.validate_value(classification, name, messages)
        if messages:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, messages)
        if update:
            classification_type.get_normalized_value_for_update(classification)
        else:
            classification_type.get_normalized_value(classification)
        return classification_type

    async def _check_associations(self, entity: StoredEntity, classifications: Sequence[AtlasClassification]) -> None:
        """``validateEntityAssociations``: not attached directly yet, and allowed for the entity's type (CLS-04)."""
        names = [
            instance.classification.type_name
            for instance in await self._instances(entity)
            if _direct(instance, entity.guid)
        ]
        entity_type = _entity_type(self._store.registry, entity)
        for classification in classifications:
            name = str(classification.type_name)
            if name in names:
                raise AtlasError(
                    AtlasErrorCode.INVALID_PARAMETERS, ALREADY_ASSOCIATED.format(guid=entity.guid, name=name)
                )
            classification_type = self._store.registry.classification_type(name)
            if classification_type is not None and not classification_type.can_apply_to_entity_type(entity_type):
                raise AtlasError(AtlasErrorCode.INVALID_ENTITY_FOR_CLASSIFICATION, entity.guid, entity.type_name, name)

    async def _write_added(self, targets: Sequence[tuple[VersionedEntity, list[AtlasClassification]]]) -> None:
        """Attach and propagate, entity after entity, as ``addClassifications`` per GUID does (CLS-05, PRO-03)."""
        instances: list[ClassificationChange] = []
        now = self._store.now()
        propagation = self._propagation()
        own: list[tuple[str, DocumentVersion | None]] = []
        for found, classifications in targets:
            guid = found.entity.guid
            current = propagation.entity(guid) or found.entity
            entity, added = self.attached(current, classifications)
            propagation.put_entity(entity.touched(now=now, user=self._user), found.version)
            own.append((guid, found.version))
            instances += [ClassificationChange(instance) for instance in added]
            propagation.add_instances(added)
            for instance in added:
                if instance.propagate:
                    await propagation.propagate(instance, guid)
        await self._write_propagated(propagation, own, [], instances)

    async def _write_propagated(
        self,
        propagation: TagPropagation,
        own: Sequence[tuple[str, DocumentVersion | None]],
        relationships: Sequence[Any],
        instances: Sequence[ClassificationChange],
    ) -> None:
        """Write the request's own entities as propagation left them, the others it changed and its tasks (PRO-10)."""
        await self._store.write(
            propagation.entity_changes(guid for guid, _ in own),
            relationships,
            instances,
            [TaskChange(task) for task in propagation.tasks()],
        )

    def _propagation(
        self, entities: Mapping[str, tuple[StoredEntity, DocumentVersion | None]] | None = None
    ) -> TagPropagation:
        """Propagation over the request's entities, deferred to tasks when they are enabled (TSK-02, TSK-08)."""
        deferral = Deferral(self._user, self._store.now(), self._store.new_guid) if self._tasks else None
        return TagPropagation(self._store, entities=entities, deferral=deferral)

    async def _check_no_pending(self, instance_guid: str, guid: str) -> None:
        """No ``PENDING`` task names the classification instance and the entity (TSK-03).

        Raises:
            AtlasError: ``DELETE_TAG_PROPAGATION_NOT_ALLOWED``.
        """
        for task, _ in await self._store.list_tasks(open_only=True):
            parameters = task.parameters or {}
            if (
                task.status is TaskStatus.PENDING
                and parameters.get("classificationVertexId") == instance_guid
                and parameters.get("entityGuid") == guid
            ):
                raise AtlasError(AtlasErrorCode.DELETE_TAG_PROPAGATION_NOT_ALLOWED, instance_guid, guid)

    async def _entity(self, guid: str) -> VersionedEntity:
        found = await self._store.get(guid)
        if found is None:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        return found

    async def _instances(self, entity: StoredEntity) -> list[_Instance]:
        """The entity's classification instances, in the order it lists them, with their versions."""
        listed = entity.classification_guids or []
        found = await self._store.get_classifications(listed)
        return [_Instance(guid, found[guid].classification, found[guid].version) for guid in listed if guid in found]

    def _mapper(self) -> EntityMapper:
        return EntityMapper(
            self._store.registry, resolve=_unresolved, guid_assignments={}, now=self._store.now(), user=self._user
        )

    async def _run(self, attempt: Callable[[], Awaitable[None]]) -> None:
        """Run once more after a lost race; a second loss or a failed write is ``INTERNAL_ERROR`` (DD-052)."""
        for number in range(1, ATTEMPTS + 1):
            try:
                await attempt()
            except EntityVersionConflictError as conflict:
                if number == ATTEMPTS:
                    raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(conflict)) from conflict
            except (UniqueValueTakenError, EntityWriteError) as failure:
                raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(failure)) from failure
            else:
                return


@dataclass(frozen=True)
class _Instance:
    """A stored classification instance, its GUID and the version it was read in."""

    guid: str
    classification: StoredClassification
    version: DocumentVersion


async def _propagate_change(
    propagation: TagPropagation,
    guid: str,
    stored: StoredClassification,
    updated: StoredClassification,
    *,
    given: bool | None,
) -> None:
    """``updateClassifications`` on ``propagate``: false to true propagates, true to false removes (PRO-03).

    Deferred, any ``propagate`` given records a task, ``ADD`` for true, ``DELETE`` for false (TSK-02).
    """
    propagation.add_instances([updated])
    if propagation.deferred:
        if given is not None:
            await (propagation.propagate(updated, guid) if given else propagation.withdraw(updated, guid))
        return
    was, now = stored.propagate is not False, updated.propagate is not False
    if now and not was:
        await propagation.propagate(updated, guid, blocks=True)
    elif was and not now:
        await propagation.withdraw(updated, guid)


def _direct(instance: _Instance, guid: str) -> bool:
    """Attached to entity ``guid`` itself: no entity GUID, or the entity's, ignoring case."""
    entity_guid = instance.classification.entity_guid
    return not entity_guid or entity_guid.lower() == guid.lower()


def _created(
    mapper: EntityMapper,
    classification_type: ClassificationType,
    classification: AtlasClassification,
    guid: str,
    instance_guid: str,
) -> StoredClassification:
    """``createClassificationVertex`` and ``mapClassification(CREATE)``: a new instance with Atlas's defaults."""
    attributes: dict[str, Any] = {}
    mapper.struct_attributes(classification_type, classification.attributes or {}, attributes, EntityOperation.CREATE)
    return StoredClassification(
        guid=instance_guid,
        type_name=str(classification_type.type_name),
        super_type_names=list(classification_type.all_super_types),
        entity_guid=classification.entity_guid or guid,
        entity_status=classification.entity_status or EntityStatus.ACTIVE,
        propagate=PROPAGATE_DEFAULT if classification.propagate is None else classification.propagate,
        remove_propagations_on_entity_delete=(
            REMOVE_PROPAGATIONS_DEFAULT
            if classification.remove_propagations_on_entity_delete is None
            else classification.remove_propagations_on_entity_delete
        ),
        validity_periods=classification.validity_periods,
        attributes=attributes,
    )


def _updated(
    mapper: EntityMapper,
    classification_type: ClassificationType,
    classification: AtlasClassification,
    stored: StoredClassification,
) -> StoredClassification:
    """``mapClassification(UPDATE)``: given attributes, and given validity periods and flags, over the stored."""
    attributes = dict(stored.attributes)
    mapper.struct_attributes(classification_type, classification.attributes or {}, attributes, EntityOperation.UPDATE)
    update: dict[str, Any] = {"attributes": attributes}
    if classification.validity_periods is not None:
        update["validity_periods"] = classification.validity_periods
    if classification.propagate is not None:
        update["propagate"] = classification.propagate
    if classification.remove_propagations_on_entity_delete is not None:
        update["remove_propagations_on_entity_delete"] = classification.remove_propagations_on_entity_delete
    return stored.model_copy(update=update)


def _entity_type(registry: TypeRegistry, entity: StoredEntity) -> EntityType:
    entity_type = registry.entity_type(entity.type_name)
    if entity_type is None:  # pragma: no cover - stored entities are of registered types
        raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, entity.type_name)
    return entity_type


def _unresolved(value: object) -> str:
    """References in a classification name no entity of the request (``mapObjectIdValue`` without a context)."""
    raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, value)
