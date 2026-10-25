"""``EntityStore``: entities by GUID and unique attributes, written all or nothing (ENS-02 to ENS-09).

The storage side of ``AtlasEntityStoreV2`` and ``EntityGraphMapper``: what a graph transaction gave Atlas, rebuilt on
Elasticsearch with reserved unique values, conditional writes and a journal (DD-044 to DD-048).
"""

import time
import uuid
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.entity_documents import (
    EntityDocuments,
    JournalEntry,
    Linked,
    LinkedKind,
    LinkedWrite,
    Reservation,
    VersionedClassification,
    VersionedEntity,
    VersionedRelationship,
    WriteResult,
)
from aurelius_atlas_core.search_fields import search_fields
from aurelius_atlas_core.search_query import SearchHits, SearchQuery
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.typedef_document import DocumentVersion
from aurelius_atlas_core.unique_key import UniqueKey

LEASE_MILLISECONDS = 60_000
"""How long a write may take before recovery may undo it (DD-046)."""

UNKNOWN_ENTITY_TYPE_ERROR = "{type} is not an entity type"
UNIQUE_VALUE_TAKEN_ERROR = "unique value {attribute}={value} of type {type} is held by entity {holder}"
VERSION_CONFLICT_ERROR = "entity {guid} was changed by another write"
WRITE_FAILED_ERROR = "entity {guid} could not be written"
LEASE_PASSED_ERROR = "write {write_id} took longer than its lease"
REMOVE_UNREAD_ERROR = "entity {guid} cannot be removed without the version it was read in"


class UniqueValueTakenError(Exception):
    """A write needs a unique value another entity holds (ENS-05); nothing was written."""

    def __init__(self, key: UniqueKey, holder: str) -> None:
        super().__init__(
            UNIQUE_VALUE_TAKEN_ERROR.format(type=key.type_name, attribute=key.attribute, value=key.value, holder=holder)
        )
        self.key = key
        self.holder = holder


class EntityVersionConflictError(Exception):
    """Another write changed an entity after it was read (ENS-08); nothing was written."""

    def __init__(self, guid: str) -> None:
        super().__init__(VERSION_CONFLICT_ERROR.format(guid=guid))
        self.guid = guid


class EntityWriteError(Exception):
    """An entity could not be written for another reason; the write was undone (ENS-07)."""


@dataclass(frozen=True)
class EntityChange:
    """One entity of a write: its new state, and the version it was read in, or None for a new entity.

    With ``remove``, the write removes the entity, which must have been read: ``entity`` is its state then (DD-056).
    """

    entity: StoredEntity
    expected: DocumentVersion | None = None
    remove: bool = False


@dataclass(frozen=True)
class RelationshipChange:
    """One relationship of a write: its new state and the version it was read in, or None for a new one.

    With ``remove``, the write removes the relationship, which must have been read (DD-062).
    """

    relationship: StoredRelationship
    expected: DocumentVersion | None = None
    remove: bool = False


@dataclass(frozen=True)
class ClassificationChange:
    """One classification instance of a write: its new state and the version it was read in, or None for a new one.

    With ``remove``, the write removes the instance, which must have been read (DD-071).
    """

    classification: StoredClassification
    expected: DocumentVersion | None = None
    remove: bool = False


@dataclass(frozen=True)
class TaskChange:
    """One task of a write: its new state and the version it was read in, or None for a new one (DD-079).

    With ``remove``, the write removes the task, which must have been read.
    """

    task: StoredTask
    expected: DocumentVersion | None = None
    remove: bool = False


type _LinkedChanges = dict[LinkedKind, list[tuple[Linked, DocumentVersion | None, bool]]]
"""A write's linked documents by kind: each one's new state, the version it was read in, and whether it goes."""


class EntityStore:
    """Entities of the registry's entity types, and the relationships between them, in ``EntityDocuments``."""

    def __init__(
        self,
        registry: TypeRegistry,
        documents: EntityDocuments,
        *,
        clock: Callable[[], float] = time.time,
        new_id: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self.registry = registry
        self._documents = documents
        self._clock = clock
        self._new_id = new_id
        self.task_listeners: list[Callable[[], None]] = []
        """Called after a write that recorded tasks, to wake a worker (DD-080)."""

    async def prepare(self) -> None:
        """Create the indices that are missing (ENS-01)."""
        await self._documents.prepare()

    def new_guid(self) -> str:
        """A new entity's GUID: a random UUID in canonical lower-case text (ENS-02, DD-044)."""
        return self._new_id()

    def now(self) -> int:
        """The current time in epoch milliseconds, as Atlas stores times."""
        return int(self._clock() * 1000)

    async def get(self, guid: str) -> VersionedEntity | None:
        """The entity with ``guid`` as last written, or None (ENS-04)."""
        return (await self._documents.get([guid])).get(guid)

    async def get_many(self, guids: Sequence[str]) -> dict[str, VersionedEntity]:
        """The entities with these GUIDs that exist (ENS-04)."""
        return await self._documents.get(list(dict.fromkeys(guids)))

    async def find_by_unique_attributes(
        self, entity_type: EntityType, values: Mapping[str, Any]
    ) -> VersionedEntity | None:
        """The ``ACTIVE`` entity of the type, else of its first sub type, holding every given unique value (ENS-06).

        Values are normalised by the attribute's type; values of other attributes and nulls are ignored.
        """
        unique = {
            attribute.qualified_name: attribute.attribute_type.get_normalized_value(values[name])
            for name, attribute in entity_type.unique_attributes.items()
            if values.get(name) is not None
        }
        unique = {name: value for name, value in unique.items() if value is not None}
        if not unique:
            return None
        candidates = [str(entity_type.type_name), *entity_type.all_sub_types]
        keys = {
            type_name: [UniqueKey(type_name, attribute, value) for attribute, value in unique.items()]
            for type_name in candidates
        }
        held = await self._documents.reservations([key.id for type_keys in keys.values() for key in type_keys])
        for type_name in candidates:
            holders = {held[key.id].guid if key.id in held else None for key in keys[type_name]}
            if len(holders) == 1 and (guid := holders.pop()) is not None:
                return await self.get(guid)
        return None

    async def referring(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities whose references name any of these GUIDs (EDL-10, DD-057)."""
        return await self._documents.referring(list(dict.fromkeys(guids)))

    async def classified(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities listing any of these classification instances, attached or propagated (DD-075, DD-076)."""
        return await self._documents.classified(list(dict.fromkeys(guids)))

    async def get_relationships(self, guids: Sequence[str]) -> dict[str, VersionedRelationship]:
        """The relationships with these GUIDs that exist, as last written (REL-06, DD-061)."""
        found = await self._documents.get_linked(LinkedKind.RELATIONSHIP, list(dict.fromkeys(guids)))
        return {
            guid: VersionedRelationship(document, version)
            for guid, (document, version) in found.items()
            if isinstance(document, StoredRelationship)
        }

    async def classifications_of_types(self, type_names: Collection[str] | None) -> list[StoredClassification]:
        """The classification instances of these types, or of every type for None (DD-090)."""
        return await self._documents.classifications_of_types(type_names)

    async def search(self, query: SearchQuery) -> SearchHits:
        """The entities of a search query's page, how many match it in all, their scores and facets (DD-089)."""
        return await self._documents.search(query)

    async def terms(self, fields: Sequence[str], prefix: str) -> dict[str, list[tuple[str, int]]]:
        """Per search field, its most frequent words beginning with ``prefix`` (DD-094)."""
        return await self._documents.terms(fields, prefix)

    async def get_tasks(self, guids: Sequence[str]) -> dict[str, tuple[StoredTask, DocumentVersion]]:
        """The tasks with these GUIDs that exist, as last written (TSK-06, DD-079)."""
        found = await self._documents.get_linked(LinkedKind.TASK, list(dict.fromkeys(guids)))
        return {guid: (task, version) for guid, (task, version) in found.items() if isinstance(task, StoredTask)}

    async def list_tasks(self, *, open_only: bool = False) -> list[tuple[StoredTask, DocumentVersion]]:
        """Every task, or those ``PENDING`` or ``IN_PROGRESS``, oldest first (TSK-04, TSK-06)."""
        return await self._documents.list_tasks(open_only=open_only)

    async def get_classifications(self, guids: Sequence[str]) -> dict[str, VersionedClassification]:
        """The classification instances with these GUIDs that exist, as last written (CLS-02, DD-070)."""
        found = await self._documents.get_linked(LinkedKind.CLASSIFICATION, list(dict.fromkeys(guids)))
        return {
            guid: VersionedClassification(document, version)
            for guid, (document, version) in found.items()
            if isinstance(document, StoredClassification)
        }

    async def write(
        self,
        changes: Sequence[EntityChange],
        relationship_changes: Sequence[RelationshipChange] = (),
        classification_changes: Sequence[ClassificationChange] = (),
        task_changes: Sequence[TaskChange] = (),
    ) -> None:
        """Write new, changed and removed entities and the documents they list, all or nothing, through the journal.

        ENS-05, ENS-07, ENS-08. Each written entity carries the GUIDs its references name (DD-057); removals,
        relationships and classification instances are journaled too (DD-056, DD-062, DD-071).

        Raises:
            UniqueValueTakenError: A unique value is held by another entity.
            EntityVersionConflictError: An entity changed since it was read.
            EntityWriteError: An entity could not be written; the write was undone.
        """
        write_id = self._new_id()
        linked = _linked_changes(relationship_changes, classification_changes, task_changes)
        _check_removals(changes, linked)
        kept = [change for change in changes if not change.remove]
        removed = [change for change in changes if change.remove]
        instances = await self._listed_instances(kept, linked)
        entities = [self._stamped(change.entity, write_id, instances) for change in kept]
        before = await self._documents.get([change.entity.guid for change in changes if change.expected is not None])
        for change in changes:
            current = before.get(change.entity.guid)
            if change.expected is not None and (current is None or current.version != change.expected):
                raise EntityVersionConflictError(change.entity.guid)
        linked_before = {kind: await self._linked_before(kind, items) for kind, items in linked.items()}
        needed, released = self._key_changes(entities, before, [change.entity.guid for change in removed])
        entry = JournalEntry(
            write_id=write_id,
            lease_until=self.now() + LEASE_MILLISECONDS,
            before={change.entity.guid: _json_of(before.get(change.entity.guid)) for change in changes},
            reserved=[key.id for key, _ in needed],
            released=[key.id for key, _ in released],
            removed=[change.entity.guid for change in removed],
            linked_before={
                kind.value: {document.guid: linked_before[kind].get(document.guid) for document, _, _ in items}
                for kind, items in linked.items()
            },
            removed_linked={
                kind.value: [document.guid for document, _, remove in items if remove] for kind, items in linked.items()
            },
        )
        await self._documents.put_journal(entry)
        reserved = await self._reserve(needed, write_id)
        if reserved is not None:
            await self._abandon(entry, needed, [])
            raise reserved
        if self.now() > entry.lease_until:
            await self._abandon(entry, needed, [])
            raise EntityWriteError(LEASE_PASSED_ERROR.format(write_id=write_id))
        results = await self._documents.write(
            [(entity, change.expected) for entity, change in zip(entities, kept, strict=True)],
            [(change.entity.guid, change.expected) for change in removed if change.expected is not None],
            _linked_writes(linked, write_id),
        )
        failed = next((result for result in results if not result.written), None)
        if failed is not None:
            await self._abandon(entry, needed, results)
            if failed.conflict:
                raise EntityVersionConflictError(failed.guid)
            raise EntityWriteError(WRITE_FAILED_ERROR.format(guid=failed.guid))
        await self._documents.put_journal(entry.model_copy(update={"committed": True}))
        for key, guid in released:
            await self._documents.release(key.id, guid)
        await self._documents.delete_journal(write_id)
        self._notify(task_changes)

    def _notify(self, task_changes: Sequence[TaskChange]) -> None:
        """Wake the task listeners after a write that recorded new tasks (DD-080)."""
        if any(change.expected is None and not change.remove for change in task_changes):
            for listener in self.task_listeners:
                listener()

    async def recover(self) -> int:
        """Finish or undo the writes whose lease has passed; the number of entries handled (ENS-07, DD-046).

        A committed write only releases what it no longer holds; any other is undone: an entity is restored only
        while it carries the write's id, a reservation released only while the write holds it.
        """
        now, handled = self.now(), 0
        for entry in await self._documents.journal():
            if entry.lease_until >= now:
                continue
            if entry.committed:
                await self._finish_releases(entry)
            else:
                await self._undo(entry)
            await self._documents.delete_journal(entry.write_id)
            handled += 1
        return handled

    async def type_in_use(self, type_name: str) -> bool:
        """Whether an entity, relationship or classification of exactly this type exists, in any state.

        ENS-09, REL-10, CLS-12, DD-048.

        The typedef store's check.
        """
        if await self._documents.count_type(type_name) > 0:
            return True
        for kind in LinkedKind:
            if await self._documents.count_linked_type(kind, type_name) > 0:
                return True
        return False

    async def _linked_before(
        self, kind: LinkedKind, items: Sequence[tuple[Linked, DocumentVersion | None, bool]]
    ) -> dict[str, dict[str, Any]]:
        """The documents' states before, as JSON; each written only over the version it was read in (ENS-08)."""
        read = [document.guid for document, expected, _ in items if expected is not None]
        before = await self._documents.get_linked(kind, read)
        for document, expected, _ in items:
            current = before.get(document.guid)
            if expected is not None and (current is None or current[1] != expected):
                raise EntityVersionConflictError(document.guid)
        return {guid: document.to_json() for guid, (document, _) in before.items()}

    def _entity_type(self, entity: StoredEntity) -> EntityType:
        entity_type = self.registry.entity_type(entity.type_name)
        if entity_type is None:
            raise EntityWriteError(UNKNOWN_ENTITY_TYPE_ERROR.format(type=entity.type_name))
        return entity_type

    async def _listed_instances(
        self, kept: Sequence[EntityChange], linked: _LinkedChanges
    ) -> dict[str, StoredClassification]:
        """The classification instances the written entities list, as the write leaves them (DD-090)."""
        instances = {
            document.guid: document
            for document, _, remove in linked.get(LinkedKind.CLASSIFICATION, [])
            if not remove and isinstance(document, StoredClassification)
        }
        missing = [
            guid for change in kept for guid in change.entity.classification_guids or [] if guid not in instances
        ]
        if missing:
            found = await self._documents.get_linked(LinkedKind.CLASSIFICATION, list(dict.fromkeys(missing)))
            instances.update(
                {guid: document for guid, (document, _) in found.items() if isinstance(document, StoredClassification)}
            )
        return instances

    def _stamped(
        self, entity: StoredEntity, write_id: str, instances: Mapping[str, StoredClassification]
    ) -> StoredEntity:
        """The entity as written: the write's id, the GUIDs its references name and its search fields.

        DD-046, DD-057, DD-088, DD-090.
        """
        entity_type = self._entity_type(entity)
        references = entity.reference_guids(entity_type) or None
        search = search_fields(entity, entity_type, instances)
        return entity.model_copy(update={"write_id": write_id, "references": references, "search": search})

    def _key_changes(
        self, entities: Sequence[StoredEntity], before: Mapping[str, VersionedEntity], removed: Sequence[str]
    ) -> tuple[list[tuple[UniqueKey, str]], list[tuple[UniqueKey, str]]]:
        """The unique values to reserve, and those to release, with the GUID of their entity.

        A removed entity releases every value it held.
        """
        needed: list[tuple[UniqueKey, str]] = []
        released: list[tuple[UniqueKey, str]] = []
        for guid in removed:
            old = before.get(guid)
            if old is not None:
                old_type = self.registry.entity_type(old.entity.type_name)
                keys = [] if old_type is None else old.entity.unique_keys(old_type)
                released += [(key, guid) for key in keys]
        for entity in entities:
            entity_type = self._entity_type(entity)
            new_keys = {key.id: key for key in entity.unique_keys(entity_type)}
            old = before.get(entity.guid)
            old_keys = {} if old is None else {key.id: key for key in old.entity.unique_keys(entity_type)}
            needed += [(key, entity.guid) for key_id, key in new_keys.items() if key_id not in old_keys]
            released += [(key, entity.guid) for key_id, key in old_keys.items() if key_id not in new_keys]
        return needed, released

    async def _reserve(self, needed: Sequence[tuple[UniqueKey, str]], write_id: str) -> UniqueValueTakenError | None:
        """Reserve each value; the error for the first one another entity holds, else None."""
        for key, guid in needed:
            holder = await self._documents.reserve(Reservation(key.id, guid, write_id))
            if holder is not None and holder.guid != guid:
                return UniqueValueTakenError(key, holder.guid)
        return None

    async def _abandon(
        self, entry: JournalEntry, needed: Sequence[tuple[UniqueKey, str]], results: Sequence[WriteResult]
    ) -> None:
        """Undo a write that failed: restore what it wrote, release what it reserved, drop its entry."""
        for result in results:
            if result.written and result.kind is not None:
                await self._documents.restore_linked(
                    result.kind, result.guid, entry.before_linked(result.kind, result.guid)
                )
            elif result.written:
                await self._documents.restore(result.guid, entry.before_entity(result.guid))
        held = await self._documents.reservations([key.id for key, _ in needed])
        for key, guid in needed:
            reservation = held.get(key.id)
            if reservation is not None and reservation.write_id == entry.write_id:
                await self._documents.release(key.id, guid)
        await self._documents.delete_journal(entry.write_id)

    async def _undo(self, entry: JournalEntry) -> None:
        """Restore what the write wrote, and what it removed that no document has taken the place of (DD-056)."""
        current = await self._documents.get(list(entry.before))
        for guid in entry.before:
            found = current.get(guid)
            written = found is not None and found.entity.write_id == entry.write_id
            if written or (found is None and guid in entry.removed):
                await self._documents.restore(guid, entry.before_entity(guid))
        for name, befores in entry.linked_before.items():
            kind = LinkedKind(name)
            current_linked = await self._documents.get_linked(kind, list(befores))
            for guid in befores:
                found_linked = current_linked.get(guid)
                written = found_linked is not None and found_linked[0].write_id == entry.write_id
                if written or (found_linked is None and guid in entry.removed_linked.get(name, [])):
                    await self._documents.restore_linked(kind, guid, entry.before_linked(kind, guid))
        held = await self._documents.reservations(entry.reserved)
        for reservation in held.values():
            if reservation.write_id == entry.write_id:
                await self._documents.release(reservation.key, reservation.guid)

    async def _finish_releases(self, entry: JournalEntry) -> None:
        current = await self._documents.get(list(entry.before))
        held = await self._documents.reservations(entry.released)
        for reservation in held.values():
            holder = current.get(reservation.guid)
            entity_type = None if holder is None else self.registry.entity_type(holder.entity.type_name)
            still_held = (
                holder is not None
                and entity_type is not None
                and reservation.key in {key.id for key in holder.entity.unique_keys(entity_type)}
            )
            if not still_held:
                await self._documents.release(reservation.key, reservation.guid)


def _json_of(found: VersionedEntity | None) -> dict[str, Any] | None:
    return None if found is None else found.entity.to_json()


def _linked_changes(
    relationship_changes: Sequence[RelationshipChange],
    classification_changes: Sequence[ClassificationChange],
    task_changes: Sequence[TaskChange],
) -> _LinkedChanges:
    """A write's relationships, classification instances and tasks, by kind; kinds without any are left out."""
    linked: _LinkedChanges = {}
    if relationship_changes:
        linked[LinkedKind.RELATIONSHIP] = [(c.relationship, c.expected, c.remove) for c in relationship_changes]
    if classification_changes:
        linked[LinkedKind.CLASSIFICATION] = [(c.classification, c.expected, c.remove) for c in classification_changes]
    if task_changes:
        linked[LinkedKind.TASK] = [(c.task, c.expected, c.remove) for c in task_changes]
    return linked


def _check_removals(changes: Sequence[EntityChange], linked: _LinkedChanges) -> None:
    """A document is removed only over the version it was read in (DD-056).

    Raises:
        EntityWriteError: A removal without a version.
    """
    unread = [(change.entity.guid, change.remove, change.expected) for change in changes]
    unread += [(document.guid, remove, expected) for items in linked.values() for document, expected, remove in items]
    for guid, remove, expected in unread:
        if remove and expected is None:
            raise EntityWriteError(REMOVE_UNREAD_ERROR.format(guid=guid))


def _linked_writes(linked: _LinkedChanges, write_id: str) -> dict[LinkedKind, LinkedWrite]:
    """What the bulk request writes and removes of each kind, the written ones marked with the write's id."""
    return {
        kind: LinkedWrite(
            [
                (document.model_copy(update={"write_id": write_id}), expected)
                for document, expected, remove in items
                if not remove
            ],
            [(document.guid, expected) for document, expected, remove in items if remove and expected is not None],
        )
        for kind, items in linked.items()
    }
