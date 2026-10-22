"""``TypedefDocument`` and ``EntityDocuments`` in memory, for unit tests that need no Elasticsearch."""

from collections.abc import Sequence

from aurelius_atlas_model import codec
from aurelius_atlas_model.typedef import AtlasTypesDef

from aurelius_atlas_core.entity_documents import (
    JournalEntry,
    Reservation,
    VersionedEntity,
    VersionedRelationship,
    WriteResult,
)
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.typedef_document import DocumentVersion, StoredTypedefs, VersionConflictError


class MemoryTypedefDocument:
    """Keeps the definitions as JSON, as Elasticsearch would, with a version per write.

    Set ``fail_next_write`` to make the next write raise, or ``conflicts`` to make that many writes conflict.
    """

    def __init__(self) -> None:
        self.json: dict[str, object] | None = None
        self.patches: list[dict[str, object]] = []
        self.seq_no = -1
        self.prepared = False
        self.writes = 0
        self.conflicts = 0
        self.fail_next_write: BaseException | None = None

    async def prepare(self) -> None:
        """Record the call."""
        self.prepared = True

    async def read(self) -> tuple[StoredTypedefs | None, DocumentVersion | None]:
        """The stored definitions and their version."""
        if self.json is None:
            return None, None
        return StoredTypedefs.from_json({"typesDef": self.json, "patches": self.patches}), DocumentVersion(
            self.seq_no, 1
        )

    async def version(self) -> DocumentVersion | None:
        """The version of the stored definitions."""
        return None if self.json is None else DocumentVersion(self.seq_no, 1)

    async def write(self, stored: StoredTypedefs, expected: DocumentVersion | None) -> DocumentVersion:
        """Store the definitions if they are at ``expected``."""
        if self.fail_next_write is not None:
            error, self.fail_next_write = self.fail_next_write, None
            raise error
        if self.conflicts:
            self.conflicts -= 1
            raise VersionConflictError
        if expected != await self.version():
            raise VersionConflictError
        self.writes += 1
        self.seq_no += 1
        source = stored.to_json()
        self.json = source["typesDef"]
        self.patches = source["patches"]
        return DocumentVersion(self.seq_no, 1)

    def store(self, types_def: AtlasTypesDef) -> None:
        """Put definitions in place, as another process would."""
        self.seq_no += 1
        self.json = types_def.to_json()


class SimulatedCrashError(RuntimeError):
    """Raised by ``MemoryEntityDocuments`` to stand for a process dying part-way through a write."""


class MemoryEntityDocuments:
    """``EntityDocuments`` in memory, entities and relationships kept as JSON with a version per document.

    ``fail`` maps a GUID to ``"conflict"`` or ``"error"`` for the next bulk write of it; ``crash_after_write`` makes
    the next bulk write raise ``SimulatedCrashError`` after writing, as if the process died.
    """

    def __init__(self) -> None:
        self.entities: dict[str, tuple[dict[str, object], DocumentVersion]] = {}
        self.relationships: dict[str, tuple[dict[str, object], DocumentVersion]] = {}
        self.unique_values: dict[str, Reservation] = {}
        self.journal_entries: dict[str, dict[str, object]] = {}
        self.prepared = False
        self.fail: dict[str, str] = {}
        self.crash_after_write = False
        self._seq_no = -1

    def _next_version(self) -> DocumentVersion:
        self._seq_no += 1
        return DocumentVersion(self._seq_no, 1)

    async def prepare(self) -> None:
        """Record the call."""
        self.prepared = True

    async def get(self, guids: Sequence[str]) -> dict[str, VersionedEntity]:
        """The stored entities with these GUIDs."""
        return {
            guid: VersionedEntity(StoredEntity.model_validate(codec.loads(codec.dumps(source))), version)
            for guid in guids
            if (found := self.entities.get(guid)) is not None
            for source, version in [found]
        }

    async def write(
        self,
        items: Sequence[tuple[StoredEntity, DocumentVersion | None]],
        removed: Sequence[tuple[str, DocumentVersion]] = (),
        relationships: Sequence[tuple[StoredRelationship, DocumentVersion | None]] = (),
        removed_relationships: Sequence[tuple[str, DocumentVersion]] = (),
    ) -> list[WriteResult]:
        """Write and remove entities, then relationships, unless they conflict or ``fail`` names them."""
        results: list[WriteResult] = []
        for documents, written, gone, kind in (
            (self.entities, items, removed, False),
            (self.relationships, relationships, removed_relationships, True),
        ):
            for document, version in written:
                results.append(self._put(documents, document.guid, document.to_json(), version, relationship=kind))
            for guid, version in gone:
                results.append(self._put(documents, guid, None, version, relationship=kind))
        if self.crash_after_write:
            self.crash_after_write = False
            raise SimulatedCrashError
        return results

    def _put(
        self,
        documents: dict[str, tuple[dict[str, object], DocumentVersion]],
        guid: str,
        source: dict[str, object] | None,
        version: DocumentVersion | None,
        *,
        relationship: bool,
    ) -> WriteResult:
        """Write ``source`` (None removes) unless the version is not the current one or ``fail`` names it."""
        current = documents.get(guid)
        failure = self.fail.pop(guid, None)
        stale = (version is None and current is not None) or (
            version is not None and (current is None or current[1] != version)
        )
        if stale or failure == "conflict":
            return WriteResult(guid, written=False, conflict=True, relationship=relationship)
        if failure == "error":
            return WriteResult(guid, written=False, relationship=relationship)
        if source is None:
            del documents[guid]
        else:
            documents[guid] = (codec.loads(codec.dumps(source)), self._next_version())
        return WriteResult(guid, written=True, relationship=relationship)

    async def get_relationships(self, guids: Sequence[str]) -> dict[str, VersionedRelationship]:
        """The stored relationships with these GUIDs."""
        return {
            guid: VersionedRelationship(StoredRelationship.model_validate(codec.loads(codec.dumps(source))), version)
            for guid in guids
            if (found := self.relationships.get(guid)) is not None
            for source, version in [found]
        }

    async def restore_relationship(self, guid: str, before: StoredRelationship | None) -> None:
        """Put back the relationship's state before, or delete it."""
        if before is None:
            self.relationships.pop(guid, None)
        else:
            self.relationships[guid] = (codec.loads(codec.dumps(before.to_json())), self._next_version())

    async def count_relationship_type(self, type_name: str) -> int:
        """Relationships of the type."""
        return sum(1 for source, _ in self.relationships.values() if source.get("typeName") == type_name)

    async def restore(self, guid: str, before: StoredEntity | None) -> None:
        """Put back the state before, or delete."""
        if before is None:
            self.entities.pop(guid, None)
        else:
            self.entities[guid] = (codec.loads(codec.dumps(before.to_json())), self._next_version())

    async def reserve(self, reservation: Reservation) -> Reservation | None:
        """Create-only."""
        if reservation.key in self.unique_values:
            return self.unique_values[reservation.key]
        self.unique_values[reservation.key] = reservation
        return None

    async def reservations(self, keys: Sequence[str]) -> dict[str, Reservation]:
        """The reservations that exist."""
        return {key: self.unique_values[key] for key in keys if key in self.unique_values}

    async def release(self, key: str, guid: str) -> None:
        """Delete the reservation if ``guid`` holds it."""
        if (held := self.unique_values.get(key)) is not None and held.guid == guid:
            del self.unique_values[key]

    async def put_journal(self, entry: JournalEntry) -> None:
        """Keep the entry."""
        self.journal_entries[entry.write_id] = codec.loads(codec.dumps(entry.to_json()))

    async def delete_journal(self, write_id: str) -> None:
        """Drop the entry."""
        self.journal_entries.pop(write_id, None)

    async def journal(self) -> list[JournalEntry]:
        """Every entry."""
        return [JournalEntry.model_validate(source) for source in self.journal_entries.values()]

    async def referring(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities whose ``references`` hold any of the GUIDs."""
        wanted = set(guids)
        found = [guid for guid, (source, _) in self.entities.items() if wanted & set(source.get("references") or [])]  # type: ignore[arg-type]
        return list((await self.get(found)).values())

    async def count_type(self, type_name: str) -> int:
        """Entities of exactly the type."""
        return sum(1 for source, _ in self.entities.values() if source.get("typeName") == type_name)
