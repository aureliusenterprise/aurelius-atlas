"""The entities' documents in Elasticsearch: entities, unique value reservations and the write journal (ENS-01).

The I/O behind ``EntityStore``: reads in real time, conditional writes, create-only reservations (DD-043 to DD-047).
Documents go to Elasticsearch as the bytes of Atlas's JSON codec, so values keep their digits (DD-039).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from aurelius_atlas_model import codec
from aurelius_atlas_model.base import AtlasModel
from elasticsearch import AsyncElasticsearch, ConflictError, NotFoundError
from pydantic import Field

from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.typedef_document import DocumentVersion

INDEX_PREFIX = "aurelius-atlas"
"""The prefix of the three aliases; tests give their own."""
ENTITY_INDEX = f"{INDEX_PREFIX}-entities"
"""The alias of the entity index (DD-043)."""
UNIQUE_VALUE_INDEX = f"{INDEX_PREFIX}-unique-values"
"""The alias of the unique value reservations (DD-045)."""
JOURNAL_INDEX = f"{INDEX_PREFIX}-entity-journal"
"""The alias of the write journal (DD-046)."""

JOURNAL_PAGE = 1000
"""How many journal entries recovery reads at once; a live journal holds one entry per write in flight."""

_KEYWORD = {"type": "keyword"}
ENTITY_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "guid": _KEYWORD,
        "typeName": _KEYWORD,
        "superTypeNames": _KEYWORD,
        "state": _KEYWORD,
        "createTime": {"type": "long"},
        "updateTime": {"type": "long"},
        "createdBy": _KEYWORD,
        "updatedBy": _KEYWORD,
        "version": {"type": "long"},
        "isIncomplete": {"type": "boolean"},
        "isProxy": {"type": "boolean"},
        "provenanceType": {"type": "integer"},
        "homeId": _KEYWORD,
        "labels": _KEYWORD,
        "writeId": _KEYWORD,
        "attributes": {"type": "object", "dynamic": False},
        "customAttributes": {"type": "object", "dynamic": False},
    },
}
"""System properties mapped for exact lookup; attribute values stored, not indexed, until 4.1 (DD-043)."""


@dataclass(frozen=True)
class VersionedEntity:
    """A stored entity and the version it was read in (DD-047)."""

    entity: StoredEntity
    version: DocumentVersion


@dataclass(frozen=True)
class Reservation:
    """A unique value held by an entity: the key's id, the holder's GUID and the write that reserved it (DD-045)."""

    key: str
    guid: str
    write_id: str


@dataclass(frozen=True)
class WriteResult:
    """How one entity of a bulk write ended: written, or failed by a version conflict or another error."""

    guid: str
    written: bool
    conflict: bool = False


class JournalEntry(AtlasModel):
    """A write in flight: its id, lease, the entities' states before it, its reservations and releases (DD-046)."""

    write_id: str
    lease_until: int
    before: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
    reserved: list[str] = Field(default_factory=list)
    released: list[str] = Field(default_factory=list)
    committed: bool = False

    def before_entity(self, guid: str) -> StoredEntity | None:
        """The state of ``guid`` before the write, or None for an entity the write created."""
        source = self.before.get(guid)
        return None if source is None else StoredEntity.model_validate(source)


@runtime_checkable
class EntityDocuments(Protocol):
    """Where ``EntityStore`` keeps entities, reservations and its journal."""

    async def prepare(self) -> None:
        """Create the indices that are missing."""
        ...

    async def get(self, guids: Sequence[str]) -> dict[str, VersionedEntity]:
        """The stored entities with these GUIDs, in real time; unknown GUIDs are left out."""
        ...

    async def write(self, items: Sequence[tuple[StoredEntity, DocumentVersion | None]]) -> list[WriteResult]:
        """Write each entity, new (no version) or over the version given, in one bulk request."""
        ...

    async def restore(self, guid: str, before: StoredEntity | None) -> None:
        """Put back an entity's state before a write, or delete one the write created."""
        ...

    async def reserve(self, reservation: Reservation) -> Reservation | None:
        """Make a reservation, create-only; the one holding the key when it is taken."""
        ...

    async def reservations(self, keys: Sequence[str]) -> dict[str, Reservation]:
        """The reservations of these keys that exist."""
        ...

    async def release(self, key: str, guid: str) -> None:
        """Delete the reservation of ``key`` if ``guid`` holds it."""
        ...

    async def put_journal(self, entry: JournalEntry) -> None:
        """Write a journal entry."""
        ...

    async def delete_journal(self, write_id: str) -> None:
        """Delete a journal entry."""
        ...

    async def journal(self) -> list[JournalEntry]:
        """Every journal entry."""
        ...

    async def count_type(self, type_name: str) -> int:
        """How many entities of exactly this type exist, in any state, as of now."""
        ...


class ElasticsearchEntityDocuments:
    """``EntityDocuments`` in three Elasticsearch indices behind aliases (DD-043, DD-045, DD-046)."""

    def __init__(self, client: AsyncElasticsearch, prefix: str = INDEX_PREFIX) -> None:
        self._client = client
        self._entities = f"{prefix}-entities"
        self._unique_values = f"{prefix}-unique-values"
        self._journal = f"{prefix}-entity-journal"

    @property
    def aliases(self) -> tuple[str, str, str]:
        """The aliases of the entity index, the reservations and the journal."""
        return self._entities, self._unique_values, self._journal

    async def prepare(self) -> None:
        """Create each index behind its alias unless it exists; existing ones are not changed (ENS-01)."""
        mappings = {
            self._entities: ENTITY_MAPPING,
            self._unique_values: {"dynamic": False, "properties": {"guid": _KEYWORD, "writeId": _KEYWORD}},
            self._journal: {"dynamic": False, "properties": {"leaseUntil": {"type": "long"}}},
        }
        for alias, mapping in mappings.items():
            if not await self._client.indices.exists_alias(name=alias):
                await self._client.indices.create(
                    index=f"{alias}-000001", aliases={alias: {"is_write_index": True}}, mappings=mapping
                )

    async def get(self, guids: Sequence[str]) -> dict[str, VersionedEntity]:
        """``mget`` of the entity index: real time, as a get by id is (ENS-04)."""
        if not guids:
            return {}
        response = await self._client.mget(index=self._entities, ids=list(guids))
        return {
            doc["_id"]: VersionedEntity(
                StoredEntity.model_validate(doc["_source"]), DocumentVersion(doc["_seq_no"], doc["_primary_term"])
            )
            for doc in response["docs"]
            if doc.get("found")
        }

    async def write(self, items: Sequence[tuple[StoredEntity, DocumentVersion | None]]) -> list[WriteResult]:
        """One bulk request: ``create`` for a new entity, ``index`` with ``if_seq_no`` for a changed one (DD-047)."""
        lines: list[bytes] = []
        for entity, version in items:
            action: dict[str, Any] = {"_index": self._entities, "_id": entity.guid}
            if version is None:
                lines.append(codec.dumps({"create": action}))
            else:
                action |= {"if_seq_no": version.seq_no, "if_primary_term": version.primary_term}
                lines.append(codec.dumps({"index": action}))
            lines.append(codec.dumps(entity.to_json()))
        body = b"\n".join(lines) + b"\n"  # NDJSON bytes: the transport sends them as they are
        response = await self._client.bulk(operations=body)  # pyright: ignore[reportArgumentType]
        results = []
        for item in response["items"]:
            outcome = next(iter(item.values()))
            status = int(outcome["status"])
            results.append(WriteResult(outcome["_id"], written=status < 300, conflict=status == 409))  # noqa: PLR2004
        return results

    async def restore(self, guid: str, before: StoredEntity | None) -> None:
        """Index the state before, or delete an entity that did not exist before (DD-046)."""
        if before is None:
            try:
                await self._client.delete(index=self._entities, id=guid)
            except NotFoundError:
                return
        else:
            await self._client.index(index=self._entities, id=guid, document=codec.dumps(before.to_json()))  # type: ignore[arg-type]

    async def reserve(self, reservation: Reservation) -> Reservation | None:
        """``op_type=create``: of two processes reserving one value, one fails (DD-045)."""
        try:
            await self._client.index(
                index=self._unique_values,
                id=reservation.key,
                document=codec.dumps({"guid": reservation.guid, "writeId": reservation.write_id}),  # type: ignore[arg-type]
                op_type="create",
            )
        except ConflictError:
            held = (await self.reservations([reservation.key])).get(reservation.key)
            return held or reservation
        return None

    async def reservations(self, keys: Sequence[str]) -> dict[str, Reservation]:
        """``mget`` of the reservations, in real time."""
        if not keys:
            return {}
        response = await self._client.mget(index=self._unique_values, ids=list(keys))
        return {
            doc["_id"]: Reservation(doc["_id"], doc["_source"]["guid"], doc["_source"]["writeId"])
            for doc in response["docs"]
            if doc.get("found")
        }

    async def release(self, key: str, guid: str) -> None:
        """Delete the reservation when ``guid`` still holds it, guarded by its version."""
        try:
            held = await self._client.get(index=self._unique_values, id=key)
            if held["_source"]["guid"] == guid:
                await self._client.delete(
                    index=self._unique_values, id=key, if_seq_no=held["_seq_no"], if_primary_term=held["_primary_term"]
                )
        except NotFoundError, ConflictError:
            return

    async def put_journal(self, entry: JournalEntry) -> None:
        """Index the entry under its write id."""
        await self._client.index(index=self._journal, id=entry.write_id, document=codec.dumps(entry.to_json()))  # type: ignore[arg-type]

    async def delete_journal(self, write_id: str) -> None:
        """Delete the entry; one already gone is fine."""
        try:
            await self._client.delete(index=self._journal, id=write_id)
        except NotFoundError:
            return

    async def journal(self) -> list[JournalEntry]:
        """The entries of the journal, refreshed first so none written a moment ago is missed."""
        await self._client.indices.refresh(index=self._journal)
        response = await self._client.search(index=self._journal, size=JOURNAL_PAGE, query={"match_all": {}})
        return [JournalEntry.model_validate(hit["_source"]) for hit in response["hits"]["hits"]]

    async def count_type(self, type_name: str) -> int:
        """Refresh the entity index, then count the entities of the type (DD-048)."""
        await self._client.indices.refresh(index=self._entities)
        response = await self._client.count(index=self._entities, query={"term": {"typeName": type_name}})
        return int(response["count"])
