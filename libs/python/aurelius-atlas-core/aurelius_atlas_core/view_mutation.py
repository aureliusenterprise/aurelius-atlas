"""``ViewMutationDoor``: the mutation door of the view family (AVW-01 to AVW-12, ADR 064, DD-589 to DD-594).

A view is given back as the _desired state_ of one entity: its ``attributes``, and, when named, the complete
desired ``classifications``, ``labels``, ``meanings`` and ``sections``. The door reads what the entity carries
now, diffs each set, and applies the difference through the same internals 2.4, 3.3a, 5.3a, 5.2c and 3.1a use —
one request, no client sequence (DD-589). The store has no transactions (ADR 047), so the door records each
written document's before-image as it applies and rewinds them when a later step fails, answering its refusal
having applied nothing (DD-590). An update names the ``updateTime`` of the view it edited; a stored entity
changed since is answered with the conflict and the stored view (DD-591). The change records (audits) ride the
notifier only after the whole apply has succeeded, so a refused request leaves none (AVW-10).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NoReturn, cast

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, validate_guid
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntityWithExtInfo,
    AtlasRelatedObjectId,
    AtlasRelationship,
    EntityMutationResponse,
    EntityOperation,
    RelationshipStatus,
)
from aurelius_atlas_model.views import EntityView
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.edge_direction import EdgeDirection
from aurelius_atlas_typesystem.entity_type import EntityType

from aurelius_atlas_core.authorization import ALLOW_ALL, Authorizer
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_documents import DocumentVersion, LinkedKind, VersionedEntity
from aurelius_atlas_core.entity_labels import EntityLabels
from aurelius_atlas_core.entity_store import (
    ClassificationChange,
    EntityChange,
    EntityStore,
    RelationshipChange,
    TaskChange,
)
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.glossary_service import GlossaryService
from aurelius_atlas_core.glossary_term_utils import TERM_ASSIGNMENT
from aurelius_atlas_core.graph_helper import collection_elements, referenced_end, relationship_type_name
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.view_derivation import view_of

PLACEHOLDER = "-1"
"""The request GUID a create names its own entity by, before the server mints the real one (DV-162, AVW-06)."""


class ViewVersionConflictError(Exception):
    """The stored entity changed since the edited view was read (AVW-04, DD-591).

    The door raises it with the stored view; the route answers the conflict code beside that view.
    """

    def __init__(self, view: EntityView) -> None:
        super().__init__(f"entity {view.guid} changed since the view of it was read")
        self.view = view


@dataclass
class _End:
    """One end a sections entry names: its GUID and whether the entry asks for its removal (AVW-09)."""

    guid: str
    deleted: bool = False


@dataclass
class _Section:
    """One sections entry: the relationship attribute and the ends it names."""

    attribute: str
    ends: list[_End] = field(default_factory=list)


@dataclass
class _Write:
    """The request as the door read it: the fields it acts on, the rest of the view ignored (AVW-02)."""

    type_name: str
    attributes: dict[str, Any]
    guid: str | None = None
    update_time: int | None = None
    labels: list[str] | None = None
    classifications: list[str] | None = None
    meanings: list[str] | None = None
    sections: list[_Section] | None = None


class RewindStore(EntityStore):
    """An ``EntityStore`` that records, for each document its writes changed, the state before the first (DD-590).

    ``undo`` writes those recorded states back over the current ones in one write of the real store: entities and
    linked documents a step created are removed, ones it changed are put back, ones it removed are restored.
    A concurrent change to a recorded document answers a conflict of that undo, as of any other write.
    """

    def __init__(self, real: EntityStore) -> None:
        super().__init__(real.registry, real._documents, clock=real._clock, new_id=real._new_id)  # noqa: SLF001
        self._real = real
        self._entities: dict[str, StoredEntity | None] = {}
        self._linked: dict[LinkedKind, dict[str, Any]] = {kind: {} for kind in LinkedKind}

    async def write(
        self,
        changes: Sequence[EntityChange],
        relationship_changes: Sequence[RelationshipChange] = (),
        classification_changes: Sequence[ClassificationChange] = (),
        task_changes: Sequence[TaskChange] = (),
    ) -> None:
        """Record what is about to change, then write as the store does (DD-590)."""
        await self._record_entities([change.entity.guid for change in changes])
        await self._record_linked(
            LinkedKind.RELATIONSHIP, [change.relationship.guid for change in relationship_changes]
        )
        await self._record_linked(
            LinkedKind.CLASSIFICATION, [change.classification.guid for change in classification_changes]
        )
        await self._record_linked(LinkedKind.TASK, [change.task.guid for change in task_changes])
        await super().write(changes, relationship_changes, classification_changes, task_changes)

    async def undo(self) -> None:
        """Write the recorded states back over the current ones through the real store, once (DD-590)."""
        entities = await self._restore_entities()
        relationships = await self._restore_linked(LinkedKind.RELATIONSHIP)
        classifications = await self._restore_linked(LinkedKind.CLASSIFICATION)
        tasks = await self._restore_linked(LinkedKind.TASK)
        if entities or relationships or classifications or tasks:
            await self._real.write(entities, relationships, classifications, tasks)
        self._entities.clear()
        for kind in self._linked:
            self._linked[kind].clear()

    async def _record_entities(self, guids: Sequence[str]) -> None:
        unread = [guid for guid in dict.fromkeys(guids) if guid not in self._entities]
        if not unread:
            return
        for guid, found in (await self._documents.get(unread)).items():
            self._entities[guid] = found.entity
        for guid in unread:
            self._entities.setdefault(guid, None)

    async def _record_linked(self, kind: LinkedKind, guids: Sequence[str]) -> None:
        recorded = self._linked[kind]
        unread = [guid for guid in dict.fromkeys(guids) if guid not in recorded]
        if not unread:
            return
        for guid, (document, _) in (await self._documents.get_linked(kind, unread)).items():
            recorded[guid] = document
        for guid in unread:
            recorded.setdefault(guid, None)

    async def _restore_entities(self) -> list[EntityChange]:
        current = await self._documents.get(list(self._entities))
        changes = []
        for guid, before in self._entities.items():
            found = current.get(guid)
            if before is None:
                if found is not None:
                    changes.append(EntityChange(found.entity, found.version, remove=True))
            elif found is not None:
                changes.append(EntityChange(before, found.version))
        return changes

    async def _restore_linked(self, kind: LinkedKind) -> list[Any]:
        recorded = self._linked[kind]
        current = await self._documents.get_linked(kind, list(recorded))

        def change(
            before: Any,  # noqa: ANN401 - the kind's stored document, or none when it did not exist
            found: tuple[Any, DocumentVersion] | None,
        ) -> Any:  # noqa: ANN401 - one kind's change, or none when there is nothing to undo
            if before is None:
                return None if found is None else _linked_change(kind, found[0], found[1], remove=True)
            if found is None:
                return _linked_change(kind, before, None)
            return _linked_change(kind, before, found[1])

        return [found for guid in recorded if (found := change(recorded[guid], current.get(guid))) is not None]


def _linked_change(
    kind: LinkedKind,
    document: Any,  # noqa: ANN401 - the kind's stored document
    expected: DocumentVersion | None,
    *,
    remove: bool = False,
) -> Any:  # noqa: ANN401 - one kind's change class
    """The ``EntityStore`` change of one linked document: its kind's change class over the new state."""
    if kind is LinkedKind.RELATIONSHIP:
        return RelationshipChange(cast("StoredRelationship", document), expected, remove)
    if kind is LinkedKind.CLASSIFICATION:
        return ClassificationChange(cast("StoredClassification", document), expected, remove)
    return TaskChange(cast("StoredTask", document), expected, remove)


def _created_guid(response: EntityMutationResponse) -> str:
    """The GUID the writer minted for its one create (AVW-06)."""
    headers = response.get_entities_by_operation(EntityOperation.CREATE) or []
    if not headers or not headers[0].guid:  # pragma: no cover - the writer mints one GUID per create
        raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, "the door's create answered no entity")
    return str(headers[0].guid)


class _BufferedNotifier:
    """A notifier that records what it is told; ``replay`` tells it to the real one, in order (AVW-10, DD-590).

    A refused request leaves its change records unheard: the door replays only after the whole apply succeeded.
    """

    def __init__(self, real: EntityChangeNotifier | None) -> None:
        self._real = real
        self._calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 - the recorded call, replayable later

        async def record(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401 - any notifier call, replayed unchanged
            self._calls.append((name, args, kwargs))

        return record

    async def replay(self) -> None:
        """Tell the real notifier everything the apply changed, in the order it happened."""
        if self._real is None:
            return
        for name, args, kwargs in self._calls:
            await getattr(self._real, name)(*args, **kwargs)


class ViewMutationDoor:
    """Writes one entity from a view's desired state, as ``user``, through the Atlas internals (AVW-05).

    The door is the Aurelius surface over the internals of 2.4 (attributes, EVL validation), 3.3a (own tags),
    5.3a (labels), 5.2c (term assignments) and 3.1a (relationship ends); Atlas's own endpoints behave as before
    (AVW-12). ``authorizer`` is what those internals check with, ``notifier`` records what a finished apply
    changed (AVW-10), and ``tasks`` defers propagation as the server's setting says.
    """

    def __init__(
        self,
        store: EntityStore,
        *,
        user: str | None = None,
        authorizer: Authorizer = ALLOW_ALL,
        notifier: EntityChangeNotifier | None = None,
        tasks: bool = False,
    ) -> None:
        self._store = store
        self._user = user
        self._authorizer = authorizer
        self._notifier = notifier
        self._tasks = tasks

    async def apply(self, body: object) -> EntityView:
        """Apply the view and answer the entity's live view: derived fresh, ``updateTime`` new (AVW-07).

        Raises:
            AtlasError: ``VIEW_REFUSED`` for a body the door cannot act on (AVW-02, AVW-08, AVR-13),
                ``ENTITY_NAME_TAKEN`` when a create's unique values are held (AVW-06),
                ``ENTITY_VERSION_CONFLICT`` for a lost update (AVW-04), and what the internals answer —
                their validation and constraint codes unchanged (AVW-03, AVW-09).
            ViewVersionConflictError: the stored entity changed since the view was read (AVW-04).
        """
        write = _parse_view(body)
        registry = self._store.registry
        entity_type = registry.entity_type(write.type_name)
        if entity_type is None:
            _refuse([f"Unknown entity type: {write.type_name}"])
        if write.guid is None:
            return await self._create(write, entity_type)
        return await self._update(write, str(write.guid))

    async def _create(self, write: _Write, entity_type: EntityType) -> EntityView:
        """Create one entity: its unique values free, the server's GUID, its own fields as given (AVW-06)."""
        await self._check_taken(write, entity_type)
        rewind = RewindStore(self._store)
        buffer = _BufferedNotifier(self._notifier)
        try:
            response = await self._writer(rewind, buffer).create_or_update(_entity_for_create(write))
            guid = _created_guid(response)
            await self._write_sets(rewind, buffer, guid, write, create=True)
        except Exception:
            await rewind.undo()
            raise
        await buffer.replay()
        return await self._view(guid)

    async def _update(self, write: _Write, guid: str) -> EntityView:
        """Update one entity from the view its reader holds, its sets replaced as desired (AVW-04, AVW-05)."""
        found = await self._store.get(guid)
        if found is None:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        if found.entity.type_name != write.type_name:
            _refuse([f"The door cannot change an entity's type: it is {found.entity.type_name}, not {write.type_name}"])
        if write.update_time is None:
            _refuse(["An update through the view door names the updateTime of the view it edited"])
        if write.update_time != found.entity.update_time:
            stored_type = self._store.registry.entity_type(found.entity.type_name)
            view = view_of(found.entity, stored_type) if stored_type else _bare_view(found.entity)
            raise ViewVersionConflictError(view.model_copy(update={"stale": False}))
        rewind = RewindStore(self._store)
        buffer = _BufferedNotifier(self._notifier)
        try:
            await self._writer(rewind, buffer).create_or_update(_entity_for_update(write))
            await self._write_sets(rewind, buffer, guid, write, create=False)
        except Exception:
            await rewind.undo()
            raise
        await buffer.replay()
        return await self._view(guid)

    async def _write_sets(
        self, rewind: RewindStore, buffer: _BufferedNotifier, guid: str, write: _Write, *, create: bool
    ) -> None:
        """Apply the desired sets through the internals, in the order AVW-05 names them.

        A create's attributes step already carried its labels and own tags (CLS-10, LBL-05), so those two
        steps run for updates alone; the tags and labels a step replaces are read as the entity holds them
        now, before its own writes (DD-589).
        """
        if write.classifications is not None and not create:
            await self._classifications(rewind, buffer, guid, write.classifications)
        if write.labels is not None and not create:
            current = await self._store.get(guid)
            now = list(current.entity.labels or []) if current else []
            if sorted(now) != sorted(dict.fromkeys(write.labels)):
                await self._labels(rewind, buffer).set_labels(guid, write.labels)
        if write.meanings is not None:
            await self._meanings(rewind, buffer, guid, write.meanings)
        if write.sections is not None:
            await self._sections(rewind, buffer, guid, write.sections)

    async def _classifications(
        self, rewind: RewindStore, buffer: _BufferedNotifier, guid: str, desired: list[str]
    ) -> None:
        """Replace the entity's own tags, leaving what propagation brought in place (AVW-08, DD-589).

        A desired name the entity carries only through propagation is refused naming its source: the door
        writes own tags, and an own copy of a propagated name would half-remove on the next save.
        """
        own, propagated = await self._tags(guid)
        desired_names = [str(name).lower() for name in desired]
        for name in desired_names:
            source = propagated.get(name)
            if source is not None and name not in own:
                _refuse(
                    [
                        (
                            f"The classification {source[0]} reaches this entity from entity {source[1]}: "
                            "a propagated tag is not the door's to write"
                        )
                    ]
                )
        added = [name for name in desired if name.lower() not in own]
        removed = [name for name, _ in own.items() if name not in desired_names]
        service = self._classifications_service(rewind, buffer)
        if added:
            await service.add_classifications(
                guid, [AtlasClassification.model_validate({"typeName": name}) for name in added]
            )
        for name in removed:
            await service.delete_classification(guid, own[name])

    async def _tags(self, guid: str) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
        """The entity's own tags by name, and the propagated ones by name with their display name and source."""
        found = await self._store.get(guid)
        listed = (found.entity.classification_guids or []) if found else []
        own: dict[str, str] = {}
        propagated: dict[str, tuple[str, str]] = {}
        for versioned in (await self._store.get_classifications(listed)).values():
            name = str(versioned.classification.type_name)
            attached = versioned.classification.entity_guid
            if attached and attached != guid:
                propagated[name.lower()] = (name, str(attached))
            else:
                own[name.lower()] = name
        return own, propagated

    def _labels(self, rewind: RewindStore, buffer: _BufferedNotifier) -> EntityLabels:
        return EntityLabels(
            rewind, user=self._user, notifier=cast("EntityChangeNotifier", buffer), authorizer=self._authorizer
        )

    def _classifications_service(self, rewind: RewindStore, buffer: _BufferedNotifier) -> EntityClassifications:
        return EntityClassifications(
            rewind,
            user=self._user,
            tasks=self._tasks,
            notifier=cast("EntityChangeNotifier", buffer),
            authorizer=self._authorizer,
        )

    async def _meanings(self, rewind: RewindStore, buffer: _BufferedNotifier, guid: str, desired: list[str]) -> None:
        """Replace the term assignments, adding and removing them through 5.2c's internals (AVW-05)."""
        found = await self._store.get(guid)
        current = _assignments(((await self._relationships(found)).values()) if found else [], guid)
        terms = [str(term) for term in dict.fromkeys(desired)]
        service = GlossaryService(
            rewind,
            user=self._user,
            tasks=self._tasks,
            notifier=cast("EntityChangeNotifier", buffer),
            authorizer=self._authorizer,
        )
        for term in terms:
            if term.lower() not in current:
                await service.assign_term_to_entities(term, [AtlasRelatedObjectId.model_validate({"guid": guid})])
        for term, relationship_guid in current.items():
            if term not in [str(name).lower() for name in terms]:
                await service.remove_term_from_entities(
                    term,
                    [AtlasRelatedObjectId.model_validate({"guid": guid, "relationshipGuid": relationship_guid})],
                )

    async def _sections(
        self, rewind: RewindStore, buffer: _BufferedNotifier, guid: str, sections: list[_Section]
    ) -> None:
        """Replace the ends of the named relationship attributes through 3.1a's internals (AVW-05, AVW-09)."""
        found = await self._store.get(guid)
        if found is None:  # pragma: no cover - the attributes step of this request just wrote the entity
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        entity_type = self._store.registry.entity_type(found.entity.type_name)
        relationships = [found.relationship for found in (await self._relationships(found)).values()]
        store = RelationshipStore(
            rewind,
            user=self._user,
            delete_type=DeleteType.HARD,
            tasks=self._tasks,
            notifier=cast("EntityChangeNotifier", buffer),
            authorizer=self._authorizer,
        )
        for section in sections:
            await self._section(store, guid, entity_type, section, relationships)

    async def _section(
        self,
        store: RelationshipStore,
        guid: str,
        entity_type: EntityType | None,
        section: _Section,
        relationships: list[StoredRelationship],
    ) -> None:
        attribute = _section_attribute(entity_type, section.attribute)
        type_name = _relationship_type_name(guid, relationships, entity_type, section.attribute)
        ends = {end.guid: end for end in section.ends}
        current = {
            referenced_end(relationship, attribute.relationship_edge_direction, guid): relationship
            for relationship in collection_elements(guid, relationships, attribute)
            if relationship.state is RelationshipStatus.ACTIVE
        }
        for end, wanted in ends.items():
            if wanted.deleted:
                if end in current:
                    await store.delete_by_id(current[end].guid, DeleteType.HARD)
                continue
            if end in current:
                continue
            await self._create_end(store, guid, type_name, end, attribute, relationships)
        for end, relationship in current.items():
            if end not in ends:
                await store.delete_by_id(relationship.guid, DeleteType.HARD)

    async def _create_end(  # noqa: PLR0913, PLR0917 - the edge's parts, as one create needs them
        self,
        store: RelationshipStore,
        guid: str,
        type_name: str,
        end: str,
        attribute: AtlasAttribute,
        relationships: list[StoredRelationship],
    ) -> None:
        """Create the edge the entry asks for, clearing a soft-deleted one of the same pair first (AVW-09)."""
        for relationship in relationships:
            if _is_pair(
                relationship, guid, end, attribute.relationship_edge_direction, attribute.relationship_edge_label
            ):
                await store.delete_by_id(relationship.guid, DeleteType.HARD)
        end1, end2 = (end, guid) if attribute.relationship_edge_direction is EdgeDirection.IN else (guid, end)
        await store.create(
            AtlasRelationship.model_validate(
                {
                    "typeName": type_name,
                    "end1": {"guid": end1},
                    "end2": {"guid": end2},
                    "attributes": {},
                }
            )
        )

    def _writer(self, rewind: RewindStore, buffer: _BufferedNotifier) -> EntityWriter:
        return EntityWriter(
            rewind,
            user=self._user,
            tasks=self._tasks,
            notifier=cast("EntityChangeNotifier", buffer),
            authorizer=self._authorizer,
        )

    async def _check_taken(self, write: _Write, entity_type: EntityType) -> None:
        """A create's unique values must be free: a held one answers the conflict naming its holder (AVW-06)."""
        values = {
            name: write.attributes.get(str(attribute.name))
            for name, attribute in entity_type.unique_attributes.items()
            if write.attributes.get(str(attribute.name)) is not None
        }
        if not values:
            return
        holder = await self._store.find_by_unique_attributes(entity_type, values)
        if holder is not None:
            taken = "/".join(str(value) for value in values.values())
            raise AtlasError(AtlasErrorCode.ENTITY_NAME_TAKEN, taken, holder.entity.guid)

    async def _relationships(self, found: VersionedEntity) -> Mapping[str, Any]:
        return await self._store.get_relationships(found.entity.relationship_guids or [])

    async def _view(self, guid: str) -> EntityView:
        """The live view of the written entity, ``stale`` false: the door's write is the freshness (AVW-07, DD-594)."""
        found = await self._store.get(guid)
        if found is None:  # pragma: no cover - the door just wrote the entity through this store
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        entity_type = self._store.registry.entity_type(found.entity.type_name)
        if entity_type is None:  # pragma: no cover - the store only holds entities of known types
            raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, f"the type {found.entity.type_name} of entity {guid}")
        return view_of(found.entity, entity_type).model_copy(update={"stale": False})


def _is_pair(
    relationship: StoredRelationship, guid: str, end: str, direction: EdgeDirection, label: str | None
) -> bool:
    """Whether the relationship is any-state edge between ``guid`` and ``end`` under ``label``."""
    if relationship.label != label:
        return False
    ends = set(relationship.ends())
    return (
        {guid, end} == ends
        and not (direction is EdgeDirection.IN and relationship.end2_guid != end)
        and not (direction is EdgeDirection.OUT and relationship.end1_guid != guid)
    )


def _assignments(versioned: Any, guid: str) -> dict[str, str]:  # noqa: ANN401 - the store's VersionedRelationship values
    """The entity's active term assignments: the term GUID to the assignment's GUID (GTA-01)."""
    return {
        edge.end1_guid.lower(): edge.guid
        for edge in (found.relationship for found in versioned)
        if edge.type_name == TERM_ASSIGNMENT and edge.end2_guid == guid and edge.state is RelationshipStatus.ACTIVE
    }


def _section_attribute(entity_type: EntityType | None, name: str) -> AtlasAttribute:
    """The relationship attribute a sections entry names, refused when the type has none (AVW-09)."""
    by_type = entity_type.relationship_attributes.get(name) if entity_type else None
    if not by_type:
        _refuse([f"The sections entry names an unknown relationship attribute: {name}"])
    return next(iter(by_type.values()))


def _relationship_type_name(
    guid: str,
    relationships: list[StoredRelationship],
    entity_type: EntityType | None,
    name: str,
) -> str:
    """The relationship type of the attribute: its only one, or the one an edge of the entity already is."""
    if entity_type is None:  # pragma: no cover - the door checked the type before its steps
        _refuse([f"The sections entry names an attribute of no known type: {name}"])
    found = relationship_type_name(guid, relationships, entity_type, name)
    if found is None:  # pragma: no cover - _section_attribute refused an attribute with no type
        _refuse([f"The sections entry names an attribute with no relationship type: {name}"])
    return found


def _entity_for_create(write: _Write) -> AtlasEntityWithExtInfo:
    """The create body: the view's own fields, its read-only parts left out, the placeholder GUID (AVW-02, EWR-09)."""
    given: dict[str, Any] = {
        "guid": PLACEHOLDER,
        "typeName": write.type_name,
        "attributes": write.attributes,
    }
    if write.labels is not None:
        given["labels"] = write.labels
    if write.classifications is not None:
        given["classifications"] = [{"typeName": name} for name in write.classifications]
    return AtlasEntityWithExtInfo.model_validate({"entity": given})


def _entity_for_update(write: _Write) -> AtlasEntityWithExtInfo:
    """The update body: the entity's GUID and the given attributes; 2.4's update keeps the rest (EWR-10)."""
    return AtlasEntityWithExtInfo.model_validate(
        {"entity": {"guid": write.guid, "typeName": write.type_name, "attributes": write.attributes}}
    )


def _bare_view(stored: StoredEntity) -> EntityView:
    """A view of an entity whose type is gone from the registry: what its document names (AVW-04's material)."""
    return EntityView.model_validate(
        {
            "guid": stored.guid,
            "typeName": stored.type_name,
            "name": None,
            "status": stored.state,
            "createTime": stored.create_time,
            "updateTime": stored.update_time,
            "createdBy": stored.created_by,
            "updatedBy": stored.updated_by,
            "labels": list(stored.labels or []),
        }
    )


def _parse_view(body: object) -> _Write:
    """The request as the door reads it: the view's own fields, one message per refusal (AVW-02, AVR-13).

    ``typeName`` and ``attributes`` are required; ``guid`` makes it an update and must name an entity; an
    update names the ``updateTime`` of the view it edited (AVW-04). The sets are lists of names, term GUIDs,
    or sections entries; anything else the view carries — ``quality``, ``stale``, the breadcrumb — is ignored.

    Raises:
        AtlasError: ``VIEW_REFUSED`` with every problem found.
    """
    if not isinstance(body, dict):
        _refuse(["The request body must be a view as a JSON object"])
    errors: list[str] = []
    write = _parse_fields(body, errors)
    _parse_sets(body, write, errors)
    sections = body.get("sections")
    if sections is not None:
        parsed = _parse_sections(sections, errors)
        if parsed is not None:
            write.sections = parsed
    if errors:
        _refuse(errors)
    return write


def _parse_fields(body: dict[str, Any], errors: list[str]) -> _Write:
    """The door's required fields: typeName, attributes, the optional guid, and an update's updateTime."""
    type_name = body.get("typeName")
    if not isinstance(type_name, str) or not type_name:
        errors.append("A view through the door names its typeName")
        type_name = ""
    attributes = body.get("attributes")
    if not isinstance(attributes, dict):
        errors.append("A view through the door carries its attributes")
        attributes = {}
    guid = body.get("guid")
    if guid is not None:
        validate_guid("guid", str(guid))
    return _Write(
        type_name=str(type_name),
        attributes=dict(attributes),
        guid=None if guid is None else str(guid),
        update_time=_update_time(body, updating=guid is not None, errors=errors),
    )


def _parse_sets(body: dict[str, Any], write: _Write, errors: list[str]) -> None:
    """The named set fields, each a list of non-empty names, deduplicated (AVW-02)."""
    for name in ("labels", "classifications", "meanings"):
        given = body.get(name)
        if given is None:
            continue
        if not isinstance(given, list) or not all(isinstance(item, str) and item for item in given):
            errors.append(f"The {name} must be a list of names")
            continue
        setattr(write, name, [str(item) for item in dict.fromkeys(given)])


def _update_time(body: dict[str, Any], *, updating: bool, errors: list[str]) -> int | None:
    """The ``updateTime`` of the view the update edits; required of an update, ignored by a create (AVW-04)."""
    given = body.get("updateTime")
    if not updating:
        return None
    if given is None:
        errors.append("An update through the view door names the updateTime of the view it edited")
        return None
    if isinstance(given, bool) or not isinstance(given, (int, float)):
        errors.append("The updateTime must be the milliseconds the edited view carried")
        return None
    return int(given)


def _parse_sections(sections: object, errors: list[str]) -> list[_Section] | None:
    """The sections entries: each names an attribute and its ends by GUID, ACTIVE or a delete intent (AVW-09)."""
    if not isinstance(sections, list):
        errors.append("The sections must be a list of entries")
        return None
    parsed: list[_Section] = []
    for entry in sections:
        if not isinstance(entry, dict) or not isinstance(entry.get("attribute"), str) or not entry["attribute"]:
            errors.append("Each sections entry names an attribute and its ends")
            continue
        ends: list[_End] = []
        wanted = entry.get("entities") or []
        if not isinstance(wanted, list):
            errors.append(f"The sections entry {entry['attribute']} names its ends as a list")
            continue
        for end in wanted:
            guid = end.get("guid") if isinstance(end, dict) else end if isinstance(end, str) else None
            if not isinstance(guid, str) or not guid:
                errors.append(f"The sections entry {entry['attribute']} names an end by its GUID")
                continue
            deleted = isinstance(end, dict) and str(end.get("status") or "").upper() == "DELETED"
            ends.append(_End(guid=guid, deleted=deleted))
        parsed.append(_Section(attribute=str(entry["attribute"]), ends=ends))
    return parsed


def _refuse(messages: list[str]) -> NoReturn:
    """Refuse the request in the door's own shape: one ``VIEW_REFUSED``, ``messages`` one per problem (AVR-13)."""
    raise AtlasError(AtlasErrorCode.VIEW_REFUSED, "; ".join(messages), messages=messages)
