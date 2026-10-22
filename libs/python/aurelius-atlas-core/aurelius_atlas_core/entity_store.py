"""``EntityStore``: entities by GUID and unique attributes, written all or nothing (ENS-02 to ENS-09).

The storage side of ``AtlasEntityStoreV2`` and ``EntityGraphMapper``: what a graph transaction gave Atlas, rebuilt on
Elasticsearch with reserved unique values, conditional writes and a journal (DD-044 to DD-048).
"""

import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.entity_documents import (
    EntityDocuments,
    JournalEntry,
    Reservation,
    VersionedEntity,
    VersionedRelationship,
    WriteResult,
)
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
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

    async def get_relationships(self, guids: Sequence[str]) -> dict[str, VersionedRelationship]:
        """The relationships with these GUIDs that exist, as last written (REL-06, DD-061)."""
        return await self._documents.get_relationships(list(dict.fromkeys(guids)))

    async def write(
        self, changes: Sequence[EntityChange], relationship_changes: Sequence[RelationshipChange] = ()
    ) -> None:
        """Write new, changed and removed entities and relationships, all or nothing, through the journal.

        ENS-05, ENS-07, ENS-08. Each written entity carries the GUIDs its references name (DD-057); removals and
        relationships are journaled too (DD-056, DD-062).

        Raises:
            UniqueValueTakenError: A unique value is held by another entity.
            EntityVersionConflictError: An entity changed since it was read.
            EntityWriteError: An entity could not be written; the write was undone.
        """
        write_id = self._new_id()
        for guid, change in [(change.entity.guid, change) for change in changes] + [
            (change.relationship.guid, change) for change in relationship_changes
        ]:
            if change.remove and change.expected is None:
                raise EntityWriteError(REMOVE_UNREAD_ERROR.format(guid=guid))
        kept = [change for change in changes if not change.remove]
        removed = [change for change in changes if change.remove]
        entities = [self._stamped(change.entity, write_id) for change in kept]
        before = await self._documents.get([change.entity.guid for change in changes if change.expected is not None])
        for change in changes:
            current = before.get(change.entity.guid)
            if change.expected is not None and (current is None or current.version != change.expected):
                raise EntityVersionConflictError(change.entity.guid)
        relationships_before = await self._relationships_before(relationship_changes)
        needed, released = self._key_changes(entities, before, [change.entity.guid for change in removed])
        entry = JournalEntry(
            write_id=write_id,
            lease_until=self.now() + LEASE_MILLISECONDS,
            before={change.entity.guid: _json_of(before.get(change.entity.guid)) for change in changes},
            reserved=[key.id for key, _ in needed],
            released=[key.id for key, _ in released],
            removed=[change.entity.guid for change in removed],
            relationships_before={
                change.relationship.guid: _relationship_json_of(relationships_before.get(change.relationship.guid))
                for change in relationship_changes
            },
            removed_relationships=[change.relationship.guid for change in relationship_changes if change.remove],
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
            [
                (change.relationship.model_copy(update={"write_id": write_id}), change.expected)
                for change in relationship_changes
                if not change.remove
            ],
            [
                (change.relationship.guid, change.expected)
                for change in relationship_changes
                if change.remove and change.expected is not None
            ],
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
        """Whether an entity or relationship of exactly this type exists, in any state (ENS-09, REL-10, DD-048).

        The typedef store's check.
        """
        if await self._documents.count_type(type_name) > 0:
            return True
        return await self._documents.count_relationship_type(type_name) > 0

    async def _relationships_before(self, changes: Sequence[RelationshipChange]) -> dict[str, VersionedRelationship]:
        """The relationships' states before, each written only over the version it was read in (ENS-08)."""
        read = [change.relationship.guid for change in changes if change.expected is not None]
        before = await self._documents.get_relationships(read)
        for change in changes:
            current = before.get(change.relationship.guid)
            if change.expected is not None and (current is None or current.version != change.expected):
                raise EntityVersionConflictError(change.relationship.guid)
        return before

    def _entity_type(self, entity: StoredEntity) -> EntityType:
        entity_type = self.registry.entity_type(entity.type_name)
        if entity_type is None:
            raise EntityWriteError(UNKNOWN_ENTITY_TYPE_ERROR.format(type=entity.type_name))
        return entity_type

    def _stamped(self, entity: StoredEntity, write_id: str) -> StoredEntity:
        """The entity as written: the write's id, and the GUIDs its references name (DD-046, DD-057)."""
        references = entity.reference_guids(self._entity_type(entity)) or None
        return entity.model_copy(update={"write_id": write_id, "references": references})

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
            if result.written and result.relationship:
                await self._documents.restore_relationship(result.guid, entry.before_relationship(result.guid))
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
        relationships = await self._documents.get_relationships(list(entry.relationships_before))
        for guid in entry.relationships_before:
            found_relationship = relationships.get(guid)
            written = found_relationship is not None and found_relationship.relationship.write_id == entry.write_id
            if written or (found_relationship is None and guid in entry.removed_relationships):
                await self._documents.restore_relationship(guid, entry.before_relationship(guid))
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


def _relationship_json_of(found: VersionedRelationship | None) -> dict[str, Any] | None:
    return None if found is None else found.relationship.to_json()
