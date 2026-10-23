"""``TypedefDocument`` and ``EntityDocuments`` in memory, for unit tests that need no Elasticsearch."""

from collections.abc import Mapping, Sequence
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from aurelius_atlas_model.tasks import TaskStatus
from aurelius_atlas_model.typedef import AtlasTypesDef

from aurelius_atlas_core.entity_audit_repository import TAG_ACTIONS
from aurelius_atlas_core.entity_documents import (
    LINKED_MODELS,
    JournalEntry,
    Linked,
    LinkedKind,
    LinkedWrite,
    Reservation,
    VersionedEntity,
    WriteResult,
)
from aurelius_atlas_core.search_query import SearchQuery, selects
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_task import StoredTask
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
    """``EntityDocuments`` in memory, entities and linked documents kept as JSON with a version per document.

    ``fail`` maps a GUID to ``"conflict"`` or ``"error"`` for the next bulk write of it; ``crash_after_write`` makes
    the next bulk write raise ``SimulatedCrashError`` after writing, as if the process died.
    """

    def __init__(self) -> None:
        self.entities: dict[str, tuple[dict[str, object], DocumentVersion]] = {}
        self.linked: dict[LinkedKind, dict[str, tuple[dict[str, object], DocumentVersion]]] = {
            kind: {} for kind in LinkedKind
        }
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
        linked: Mapping[LinkedKind, LinkedWrite] | None = None,
    ) -> list[WriteResult]:
        """Write and remove entities, then each kind's documents, unless they conflict or ``fail`` names them."""
        results: list[WriteResult] = []
        groups: list[
            tuple[
                dict[str, tuple[dict[str, object], DocumentVersion]],
                Sequence[tuple[StoredEntity | Linked, DocumentVersion | None]],
                Sequence[tuple[str, DocumentVersion]],
                LinkedKind | None,
            ]
        ] = [(self.entities, items, removed, None)]
        groups += [(self.linked[kind], write.written, write.removed, kind) for kind, write in (linked or {}).items()]
        for documents, written, gone, kind in groups:
            for document, version in written:
                results.append(self._put(documents, document.guid, document.to_json(), version, kind=kind))
            for guid, version in gone:
                results.append(self._put(documents, guid, None, version, kind=kind))
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
        kind: LinkedKind | None,
    ) -> WriteResult:
        """Write ``source`` (None removes) unless the version is not the current one or ``fail`` names it."""
        current = documents.get(guid)
        failure = self.fail.pop(guid, None)
        stale = (version is None and current is not None) or (
            version is not None and (current is None or current[1] != version)
        )
        if stale or failure == "conflict":
            return WriteResult(guid, written=False, conflict=True, kind=kind)
        if failure == "error":
            return WriteResult(guid, written=False, kind=kind)
        if source is None:
            del documents[guid]
        else:
            documents[guid] = (codec.loads(codec.dumps(source)), self._next_version())
        return WriteResult(guid, written=True, kind=kind)

    async def get_linked(self, kind: LinkedKind, guids: Sequence[str]) -> dict[str, tuple[Linked, DocumentVersion]]:
        """The stored documents of the kind with these GUIDs."""
        return {
            guid: (LINKED_MODELS[kind].model_validate(codec.loads(codec.dumps(source))), version)
            for guid in guids
            if (found := self.linked[kind].get(guid)) is not None
            for source, version in [found]
        }

    async def restore_linked(self, kind: LinkedKind, guid: str, before: Linked | None) -> None:
        """Put back the document's state before, or delete it."""
        if before is None:
            self.linked[kind].pop(guid, None)
        else:
            self.linked[kind][guid] = (codec.loads(codec.dumps(before.to_json())), self._next_version())

    async def count_linked_type(self, kind: LinkedKind, type_name: str) -> int:
        """Documents of the kind and type."""
        return sum(1 for source, _ in self.linked[kind].values() if source.get("typeName") == type_name)

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

    async def classified(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities whose ``classificationGuids`` hold any of the GUIDs."""
        wanted = set(guids)
        found = [
            guid
            for guid, (source, _) in self.entities.items()
            if wanted & set(source.get("classificationGuids") or [])  # type: ignore[arg-type]
        ]
        return list((await self.get(found)).values())

    async def list_tasks(self, *, open_only: bool) -> list[tuple[StoredTask, DocumentVersion]]:
        """Every task, or the open ones, oldest first."""
        found = await self.get_linked(LinkedKind.TASK, list(self.linked[LinkedKind.TASK]))
        tasks = [(task, version) for task, version in found.values() if isinstance(task, StoredTask)]
        if open_only:
            tasks = [(task, v) for task, v in tasks if task.status in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}]
        return sorted(tasks, key=lambda item: (item[0].created_time, item[0].guid))

    async def count_type(self, type_name: str) -> int:
        """Entities of exactly the type."""
        return sum(1 for source, _ in self.entities.values() if source.get("typeName") == type_name)

    async def search(self, query: SearchQuery) -> tuple[list[StoredEntity], int]:
        """The query evaluated over every entity's search fields (DD-089)."""
        found = [
            StoredEntity.model_validate(source)
            for source, _ in self.entities.values()
            if selects(query, source.get("search") or {})  # type: ignore[arg-type]
        ]
        for name in reversed(query.tie_break):
            found.sort(key=lambda entity, field=name: _sort_key(entity, field))
        if query.sort_field is not None:
            present = [entity for entity in found if _sort_key(entity, query.sort_field)[0] == 0]
            absent = [entity for entity in found if _sort_key(entity, query.sort_field)[0] != 0]
            present.sort(
                key=lambda entity: _sort_key(entity, str(query.sort_field), largest=query.descending),
                reverse=query.descending,
            )
            found = present + absent
        return found[query.offset : query.offset + query.size], len(found)


class InMemoryEntityAuditRepository:
    """``EntityAuditRepository`` in memory: Atlas's ``InMemoryEntityAuditRepository``, ordered by event key."""

    def __init__(self) -> None:
        self.events: list[EntityAuditEventV2] = []

    async def prepare(self) -> None:
        """Nothing to create."""

    async def put_events(self, events: Sequence[EntityAuditEventV2]) -> None:
        """Keep the events without their entity definitions."""
        self.events += [event.model_copy(update={"entity": None, "type": None}) for event in events]

    async def list_events(
        self, entity_id: str, action: EntityAuditActionV2 | None, start_key: str | None, count: int
    ) -> list[EntityAuditEventV2]:
        """The entity's events, newest key first, from ``start_key`` on; ``count`` as the protocol says."""
        if count == 0 or count < -1:
            return []
        found = [
            event
            for event in sorted(self.events, key=lambda event: event.event_key or "", reverse=True)
            if event.entity_id == entity_id
            and (action is None or event.action is action)
            and (start_key is None or (event.event_key or "") <= start_key)
        ]
        return found if count == -1 else found[:count]

    async def entities_with_tag_changes(self, from_timestamp: int, to_timestamp: int) -> list[str]:
        """The entities with a classification event in the time range, newest key first."""
        events = sorted(self.events, key=lambda event: event.event_key or "", reverse=True)
        return list(
            dict.fromkeys(
                str(event.entity_id)
                for event in events
                if event.action in TAG_ACTIONS and from_timestamp <= event.timestamp < to_timestamp
            )
        )


def _sort_key(entity: StoredEntity, name: str, *, largest: bool = False) -> tuple[int, Any]:
    """Entities without a value after those with one; an array by its least element, or its largest when sorting
    descending, as Elasticsearch sorts.
    """  # noqa: D205 - one sentence
    value = (entity.search or {}).get(name)
    if isinstance(value, list):
        value = (max(value) if largest else min(value)) if value else None
    return (1, "") if value is None else (0, value)
