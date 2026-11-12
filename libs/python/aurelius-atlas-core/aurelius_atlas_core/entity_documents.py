"""The entities' documents in Elasticsearch: entities, unique value reservations and the write journal (ENS-01).

The I/O behind ``EntityStore``: reads in real time, conditional writes, create-only reservations (DD-043 to DD-047).
Documents go to Elasticsearch as the bytes of Atlas's JSON codec, so values keep their digits (DD-039).
"""

import logging
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from aurelius_atlas_model import codec
from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.discovery import Condition
from aurelius_atlas_model.tasks import TaskStatus
from elasticsearch import AsyncElasticsearch, ConflictError, NotFoundError
from pydantic import Field

from aurelius_atlas_core.entity_embedding import (
    EMBEDDING_FIELD,
    INTERNAL_PREFIX,
    MODEL_FIELD,
    VECTOR_FIELD,
    embedding_mapping,
    with_current_embedding,
)
from aurelius_atlas_core.free_text import TERM_COUNT, TextQuery
from aurelius_atlas_core.search_fields import KEYWORD, KINDS, TEXT
from aurelius_atlas_core.search_query import (
    ACTIVE,
    FACET_SIZE,
    STATE_FIELD,
    TYPE_NAME_FIELD,
    Filter,
    Group,
    SearchHits,
    SearchQuery,
    Test,
)
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.typedef_document import INDEX_SETTINGS, DocumentVersion, ensure_index

LOGGER = logging.getLogger(__name__)

INDEX_PREFIX = "aurelius-atlas"
"""The prefix of the three aliases; tests give their own."""
ENTITY_INDEX = f"{INDEX_PREFIX}-entities"
"""The alias of the entity index (DD-043)."""
UNIQUE_VALUE_INDEX = f"{INDEX_PREFIX}-unique-values"
"""The alias of the unique value reservations (DD-045)."""
JOURNAL_INDEX = f"{INDEX_PREFIX}-entity-journal"
"""The alias of the write journal (DD-046)."""
RELATIONSHIP_INDEX = f"{INDEX_PREFIX}-relationships"
"""The alias of the relationship index (DD-061)."""
CLASSIFICATION_INDEX = f"{INDEX_PREFIX}-classifications"
"""The alias of the classification index (DD-070)."""


class LinkedKind(StrEnum):
    """The documents an entity lists besides itself, each in an index of its own (DD-061, DD-070)."""

    RELATIONSHIP = "relationships"
    CLASSIFICATION = "classifications"
    TASK = "tasks"


type Linked = StoredRelationship | StoredClassification | StoredTask
"""A document an entity lists: a relationship or a classification instance."""

LINKED_MODELS: dict[LinkedKind, type[StoredRelationship | StoredClassification | StoredTask]] = {
    LinkedKind.RELATIONSHIP: StoredRelationship,
    LinkedKind.CLASSIFICATION: StoredClassification,
    LinkedKind.TASK: StoredTask,
}

JOURNAL_PAGE = 1000
"""How many journal entries recovery reads at once; a live journal holds one entry per write in flight."""

WRITE_REFRESH = "true"

KEEP_SOURCE_VECTORS = {"index.mapping.exclude_source_vectors": False}
"""The entity index's setting with vectors: each document's source stays as written, vector and digits alike, and
every read returns it. Elasticsearch 9.5's default rewrites the source of every document of an index that maps a
vector (VEC-03, VEC-04, DD-434). Static: only an index's creation sets it."""
"""Every write's ``refresh`` parameter (ENS-11, IDX-01, DD-322): the write refreshes the shards it wrote and
returns after its documents are visible, so the next read sees them — no read path pays a refresh of its own,
and no write waits for the index's next scheduled refresh."""

REFERRING_PAGE = 1000
"""How many referring entities one search page holds (DD-057)."""

_KEYWORD = {"type": "keyword"}
KEYWORD_LIMIT = 8191
"""``ignore_above`` of keyword search fields: the longest value a keyword holds, in characters (DD-092)."""


def _search_mapping(kind: str) -> dict[str, Any]:
    """A search field's mapping: a keyword also has an analysed ``text`` sub-field for free text (DD-092)."""
    if kind != KEYWORD:
        return {"type": kind}
    return {"type": kind, "ignore_above": KEYWORD_LIMIT, "fields": {TEXT: {"type": "text", "fielddata": True}}}


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
        "references": _KEYWORD,
        "relationshipGuids": _KEYWORD,
        "classificationGuids": _KEYWORD,
        "pendingTasks": _KEYWORD,
        "attributes": {"type": "object", "dynamic": False},
        "customAttributes": {"type": "object", "dynamic": False},
        "search": {"type": "object", "dynamic": True, "subobjects": False},
    },
    "dynamic_templates": [
        {f"search_{kind}": {"path_match": f"search.{kind}.*", "mapping": _search_mapping(kind)}} for kind in KINDS
    ],
}
"""System properties and referenced GUIDs mapped for exact lookup; attribute values stored, not indexed, and searched
in the typed fields of ``search``, which the dynamic templates map by their kind (DD-043, DD-057, DD-088).
"""

ENTITY_FIELD_LIMIT = 100_000
"""``index.mapping.total_fields.limit`` of the entity index: a field per searchable attribute (DD-088)."""


class EmbeddingDimensionsError(RuntimeError):
    """The entity index maps vectors of other dimensions than the configured ones (VEC-03, DD-438)."""

    def __init__(self, mapped: int, configured: int) -> None:
        """The error for an index of ``mapped`` dimensions, configured for ``configured``."""
        super().__init__(
            f"The entity index maps vectors of {mapped} dimensions, the embedding is configured for {configured}: "
            "a model of other dimensions needs a new entity index (DD-438)"
        )
        self.mapped = mapped
        self.configured = configured


@dataclass(frozen=True)
class VersionedEntity:
    """A stored entity and the version it was read in (DD-047)."""

    entity: StoredEntity
    version: DocumentVersion


RELATIONSHIP_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "guid": _KEYWORD,
        "typeName": _KEYWORD,
        "label": _KEYWORD,
        "end1Guid": _KEYWORD,
        "end2Guid": _KEYWORD,
        "state": _KEYWORD,
        "writeId": _KEYWORD,
        "attributes": {"type": "object", "dynamic": False},
    },
}
"""Relationships by type, label, ends and state; attribute values stored, not indexed (DD-061)."""

CLASSIFICATION_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "guid": _KEYWORD,
        "typeName": _KEYWORD,
        "superTypeNames": _KEYWORD,
        "entityGuid": _KEYWORD,
        "entityStatus": _KEYWORD,
        "writeId": _KEYWORD,
        "attributes": {"type": "object", "dynamic": False},
    },
}
"""Classification instances by type and entity; attribute values stored, not indexed (DD-070)."""

TASK_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "guid": _KEYWORD,
        "type": _KEYWORD,
        "status": _KEYWORD,
        "createdTime": {"type": "long"},
        "claimedUntil": {"type": "long"},
        "writeId": _KEYWORD,
    },
}
"""Tasks by status and creation time; parameters stored, not indexed (DD-079)."""

TASK_PAGE = 1000
"""How many tasks one search page holds."""

CLASSIFICATION_PAGE = 1000
"""How many classification instances one search page holds."""

COUNT_PAGE = 1000
"""How many buckets one page of a composite count aggregation holds (MET-02)."""


@dataclass(frozen=True)
class TypeCount:
    """How many entities of a type are in a state, shells (``isIncomplete``) or not (MET-02)."""

    type_name: str
    state: str
    incomplete: bool
    count: int


@dataclass(frozen=True)
class VersionedRelationship:
    """A stored relationship and the version it was read in (DD-047, DD-061).

    None for one a write request creates and has not written yet (DD-068).
    """

    relationship: StoredRelationship
    version: DocumentVersion | None


@dataclass(frozen=True)
class VersionedClassification:
    """A stored classification instance and the version it was read in (DD-047, DD-070)."""

    classification: StoredClassification
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
    kind: LinkedKind | None = None


@dataclass(frozen=True)
class LinkedWrite:
    """What a write does to the documents of one ``LinkedKind``: written ones at a version or new, removed ones."""

    written: Sequence[tuple[Linked, DocumentVersion | None]] = ()
    removed: Sequence[tuple[str, DocumentVersion]] = ()


class JournalEntry(AtlasModel):
    """A write in flight: its id, lease, the entities' states before it, its reservations, releases and removals.

    DD-046, DD-056.
    """

    write_id: str
    lease_until: int
    before: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
    reserved: list[str] = Field(default_factory=list)
    released: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    linked_before: dict[str, dict[str, dict[str, Any] | None]] = Field(default_factory=dict)
    removed_linked: dict[str, list[str]] = Field(default_factory=dict)
    committed: bool = False

    def before_entity(self, guid: str) -> StoredEntity | None:
        """The state of ``guid`` before the write, or None for an entity the write created."""
        source = self.before.get(guid)
        return None if source is None else StoredEntity.model_validate(source)

    def before_linked(self, kind: LinkedKind, guid: str) -> Linked | None:
        """The state of a linked document before the write, or None for one the write created (DD-062, DD-071)."""
        source = self.linked_before.get(kind, {}).get(guid)
        return None if source is None else LINKED_MODELS[kind].model_validate(source)


@runtime_checkable
class EntityDocuments(Protocol):
    """Where ``EntityStore`` keeps entities, reservations and its journal."""

    async def prepare(self) -> None:
        """Create the indices that are missing."""
        ...

    async def get(self, guids: Sequence[str]) -> dict[str, VersionedEntity]:
        """The stored entities with these GUIDs, in real time; unknown GUIDs are left out."""
        ...

    async def write(
        self,
        items: Sequence[tuple[StoredEntity, DocumentVersion | None]],
        removed: Sequence[tuple[str, DocumentVersion]] = (),
        linked: Mapping[LinkedKind, LinkedWrite] | None = None,
    ) -> list[WriteResult]:
        """Write and remove entities and linked documents, new (no version) or at the version given.

        One bulk request; the results are in order: entities written, removed, then each kind's written, removed
        (DD-056, DD-062, DD-071).
        """
        ...

    async def get_linked(self, kind: LinkedKind, guids: Sequence[str]) -> dict[str, tuple[Linked, DocumentVersion]]:
        """The stored documents of a kind with these GUIDs, in real time; unknown GUIDs are left out (DD-061)."""
        ...

    async def restore_linked(self, kind: LinkedKind, guid: str, before: Linked | None) -> None:
        """Put back a linked document's state before a write, or delete one the write created (DD-062)."""
        ...

    async def count_linked_type(self, kind: LinkedKind, type_name: str) -> int:
        """How many documents of the kind and type exist, in any state, as of now (REL-10, CLS-12)."""
        ...

    async def referring(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities whose references name any of these GUIDs, as of now (DD-057)."""
        ...

    async def of_types(self, type_names: Sequence[str]) -> list[VersionedEntity]:
        """The entities of exactly these types, in any state, as of now (EXP-03)."""
        ...

    async def classified(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities listing any of these classification instances, as of now (DD-076)."""
        ...

    async def list_tasks(self, *, open_only: bool) -> list[tuple[StoredTask, DocumentVersion]]:
        """Every task, or those ``PENDING`` or ``IN_PROGRESS``, oldest first, as of now (TSK-04, TSK-06)."""
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
        """Every journal entry, as the last refresh shows them."""
        ...

    async def get_journal(self, write_id: str) -> JournalEntry | None:
        """The journal entry of a write as of now, None when there is none."""
        ...

    async def count_type(self, type_name: str) -> int:
        """How many entities of exactly this type exist, in any state, as of now."""
        ...

    async def type_counts(self) -> list[TypeCount]:
        """How many entities there are of each type, state and shell flag, as of now (MET-02)."""
        ...

    async def linked_type_counts(self, kind: LinkedKind) -> dict[str, int]:
        """How many documents of the kind there are of each type, as of now (MET-02)."""
        ...

    async def search(self, query: SearchQuery) -> SearchHits:
        """The entities of the query's page, as of now, how many match it in all, their scores, and the query's
        facets (DD-089, DD-093).
        """  # noqa: D205 - one sentence
        ...

    async def terms(self, fields: Sequence[str], prefix: str) -> dict[str, list[tuple[str, int]]]:
        """Per search field, the 5 words of every entity's text in it that begin with ``prefix``, with how many
        entities hold each, most first, then by word (DD-094).
        """  # noqa: D205 - one sentence
        ...

    async def classifications_of_types(self, type_names: Collection[str] | None) -> list[StoredClassification]:
        """The classification instances of these types, or of every type for None, as of now (DD-090)."""
        ...

    async def without_embedding(self, model: str, limit: int) -> list[VersionedEntity]:
        """Up to ``limit`` entities without an embedding of ``model``, internal types left out (VEC-06, DD-436)."""
        ...


def _keeps_source_vectors(settings: dict[str, Any]) -> bool:
    """Whether an index's settings, flat or nested as Elasticsearch answers them, keep the source of vectors."""
    flat = settings.get("index.mapping.exclude_source_vectors")
    nested = settings.get("index", {}).get("mapping", {}).get("exclude_source_vectors")
    return str(flat if flat is not None else nested).lower() == "false"


def _next_generation(index: str) -> str:
    """The index after ``index`` behind its alias: ``…-000001`` is followed by ``…-000002``."""
    stem, _, number = index.rpartition("-")
    return f"{stem}-{int(number) + 1:06d}"


class ElasticsearchEntityDocuments:
    """``EntityDocuments`` in three Elasticsearch indices behind aliases (DD-043, DD-045, DD-046)."""

    def __init__(
        self, client: AsyncElasticsearch, prefix: str = INDEX_PREFIX, *, embedding_dimensions: int | None = None
    ) -> None:
        """The documents behind the aliases of ``prefix``; with ``embedding_dimensions``, the entities' vectors."""
        self._client = client
        self._embedding_dimensions = embedding_dimensions
        self._entities = f"{prefix}-entities"
        self._unique_values = f"{prefix}-unique-values"
        self._journal = f"{prefix}-entity-journal"
        self._linked = {kind: f"{prefix}-{kind.value}" for kind in LinkedKind}

    @property
    def aliases(self) -> tuple[str, ...]:
        """The aliases of the entity index, the reservations, the journal and the linked documents' indices."""
        return self._entities, self._unique_values, self._journal, *self._linked.values()

    async def prepare(self) -> None:
        """Create each index behind its alias unless it exists (ENS-01).

        An existing entity index gets the fields it lacks mapped, as ``references`` (EDL-10); mapped ones stay.
        Every existing index gets the settings of a new one, as its replicas (IDX-02). With embedding on, the entity
        index keeps each document's source as written beside its vector: a new one is created so, and an existing
        one that is not moves to a new generation behind its alias first (VEC-03, DD-434, DD-439).
        """
        entity_mapping = ENTITY_MAPPING
        if self._embedding_dimensions is not None:
            entity_mapping = ENTITY_MAPPING | {
                "properties": ENTITY_MAPPING["properties"]
                | {EMBEDDING_FIELD: embedding_mapping(self._embedding_dimensions)}
            }
        mappings = {
            self._entities: entity_mapping,
            self._unique_values: {"dynamic": False, "properties": {"guid": _KEYWORD, "writeId": _KEYWORD}},
            self._journal: {"dynamic": False, "properties": {"leaseUntil": {"type": "long"}}},
            self._linked[LinkedKind.RELATIONSHIP]: RELATIONSHIP_MAPPING,
            self._linked[LinkedKind.CLASSIFICATION]: CLASSIFICATION_MAPPING,
            self._linked[LinkedKind.TASK]: TASK_MAPPING,
        }
        limit = {"index.mapping.total_fields.limit": ENTITY_FIELD_LIMIT}
        for alias, mapping in mappings.items():
            settings = INDEX_SETTINGS | limit if alias == self._entities else INDEX_SETTINGS
            vectors = alias == self._entities and self._embedding_dimensions is not None
            if not await self._client.indices.exists_alias(name=alias):
                made = await ensure_index(
                    self._client,
                    index=f"{alias}-000001",
                    aliases={alias: {"is_write_index": True}},
                    mappings=mapping,
                    settings=settings | KEEP_SOURCE_VECTORS if vectors else settings,
                )
                if made:
                    continue
            if vectors:
                await self._keep_source_vectors(mapping, settings)
            if alias == self._entities:
                await self._client.indices.put_mapping(
                    index=alias, properties=mapping["properties"], dynamic_templates=mapping["dynamic_templates"]
                )
            await self._client.indices.put_settings(index=alias, settings=settings)

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

    async def write(
        self,
        items: Sequence[tuple[StoredEntity, DocumentVersion | None]],
        removed: Sequence[tuple[str, DocumentVersion]] = (),
        linked: Mapping[LinkedKind, LinkedWrite] | None = None,
    ) -> list[WriteResult]:
        """One bulk request over the indices: ``create`` a new document, ``index`` or ``delete`` with ``if_seq_no``.

        DD-047, DD-056, DD-062, DD-071.
        """
        lines: list[bytes] = []
        kinds: list[LinkedKind | None] = []
        groups: list[tuple[str, Sequence[tuple[Any, DocumentVersion | None]], Sequence[Any], LinkedKind | None]] = [
            (self._entities, items, removed, None)
        ]
        groups += [(self._linked[kind], write.written, write.removed, kind) for kind, write in (linked or {}).items()]
        for index, documents, removals, group_kind in groups:
            for written, version in documents:
                document = with_current_embedding(written) if group_kind is None else written
                action: dict[str, Any] = {"_index": index, "_id": document.guid}
                if version is None:
                    lines.append(codec.dumps({"create": action}))
                else:
                    action |= {"if_seq_no": version.seq_no, "if_primary_term": version.primary_term}
                    lines.append(codec.dumps({"index": action}))
                lines.append(codec.dumps(document.to_json()))
                kinds.append(group_kind)
            for guid, version in removals:
                action = {"_index": index, "_id": guid}
                action |= {"if_seq_no": version.seq_no, "if_primary_term": version.primary_term}
                lines.append(codec.dumps({"delete": action}))
                kinds.append(group_kind)
        body = b"\n".join(lines) + b"\n"  # NDJSON bytes: the transport sends them as they are
        response = await self._client.bulk(operations=body, refresh=WRITE_REFRESH)  # pyright: ignore[reportArgumentType]
        results = []
        for item, kind in zip(response["items"], kinds, strict=True):
            outcome = next(iter(item.values()))
            status = int(outcome["status"])
            results.append(
                WriteResult(
                    outcome["_id"],
                    written=status < 300,  # noqa: PLR2004
                    conflict=status == 409,  # noqa: PLR2004
                    kind=kind,
                )
            )
        return results

    async def get_linked(self, kind: LinkedKind, guids: Sequence[str]) -> dict[str, tuple[Linked, DocumentVersion]]:
        """``mget`` of the kind's index: real time (DD-061, DD-070)."""
        if not guids:
            return {}
        response = await self._client.mget(index=self._linked[kind], ids=list(guids))
        return {
            doc["_id"]: (
                LINKED_MODELS[kind].model_validate(doc["_source"]),
                DocumentVersion(doc["_seq_no"], doc["_primary_term"]),
            )
            for doc in response["docs"]
            if doc.get("found")
        }

    async def restore_linked(self, kind: LinkedKind, guid: str, before: Linked | None) -> None:
        """Put back a linked document's state before a write, or delete one the write created (DD-062)."""
        index = self._linked[kind]
        if before is None:
            try:
                await self._client.delete(index=index, id=guid, refresh=WRITE_REFRESH)
            except NotFoundError:
                return
        else:
            await self._client.index(
                index=index,
                id=guid,
                document=codec.dumps(before.to_json()),  # type: ignore[arg-type]
                refresh=WRITE_REFRESH,
            )

    async def count_linked_type(self, kind: LinkedKind, type_name: str) -> int:
        """Count the kind's documents of the type (REL-10, CLS-12): writes refresh, so the count is current (ENS-11)."""
        index = self._linked[kind]
        response = await self._client.count(index=index, query={"term": {"typeName": type_name}})
        return int(response["count"])

    async def referring(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """Page through the entities whose ``references`` hold a GUID (DD-057): writes refresh (ENS-11)."""
        return await self._listing("references", guids)

    async def of_types(self, type_names: Sequence[str]) -> list[VersionedEntity]:
        """Page through the entities whose ``typeName`` is one of these (EXP-03): writes refresh (ENS-11)."""
        return await self._listing("typeName", type_names)

    async def classified(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """Page through the entities whose ``classificationGuids`` hold one (DD-076): writes refresh (ENS-11)."""
        return await self._listing("classificationGuids", guids)

    async def list_tasks(self, *, open_only: bool) -> list[tuple[StoredTask, DocumentVersion]]:
        """Page through the task index by creation time (TSK-04, TSK-06): writes refresh (ENS-11)."""
        index = self._linked[LinkedKind.TASK]
        query: dict[str, Any] = (
            {"terms": {"status": [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]}}
            if open_only
            else {"match_all": {}}
        )
        found: list[tuple[StoredTask, DocumentVersion]] = []
        after: list[Any] | None = None
        while True:
            response = await self._client.search(
                index=index,
                size=TASK_PAGE,
                query=query,
                sort=[{"createdTime": "asc"}, {"guid": "asc"}],
                search_after=after,
                seq_no_primary_term=True,
            )
            hits = response["hits"]["hits"]
            found += [
                (StoredTask.model_validate(hit["_source"]), DocumentVersion(hit["_seq_no"], hit["_primary_term"]))
                for hit in hits
            ]
            if len(hits) < TASK_PAGE:
                return found
            after = hits[-1]["sort"]

    async def _listing(self, field: str, guids: Sequence[str]) -> list[VersionedEntity]:
        if not guids:
            return []
        found: list[VersionedEntity] = []
        after: list[Any] | None = None
        while True:
            response = await self._client.search(
                index=self._entities,
                size=REFERRING_PAGE,
                query={"terms": {field: list(guids)}},
                sort=[{"guid": "asc"}],
                search_after=after,
                seq_no_primary_term=True,
            )
            hits = response["hits"]["hits"]
            found += [
                VersionedEntity(
                    StoredEntity.model_validate(hit["_source"]), DocumentVersion(hit["_seq_no"], hit["_primary_term"])
                )
                for hit in hits
            ]
            if len(hits) < REFERRING_PAGE:
                return found
            after = hits[-1]["sort"]

    async def restore(self, guid: str, before: StoredEntity | None) -> None:
        """Index the state before, or delete an entity that did not exist before (DD-046)."""
        if before is None:
            try:
                await self._client.delete(index=self._entities, id=guid, refresh=WRITE_REFRESH)
            except NotFoundError:
                return
        else:
            await self._client.index(
                index=self._entities,
                id=guid,
                document=codec.dumps(before.to_json()),  # type: ignore[arg-type]
                refresh=WRITE_REFRESH,
            )

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
        """Index the entry under its write id, without waiting for a refresh (ENS-11, DD-247)."""
        await self._client.index(
            index=self._journal,
            id=entry.write_id,
            document=codec.dumps(entry.to_json()),  # type: ignore[arg-type]
        )

    async def delete_journal(self, write_id: str) -> None:
        """Delete the entry, without waiting for a refresh; one already gone is fine (ENS-11, DD-247)."""
        try:
            await self._client.delete(index=self._journal, id=write_id)
        except NotFoundError:
            return

    async def get_journal(self, write_id: str) -> JournalEntry | None:
        """The entry by its write id, real time: what recovery acts on (ENS-07, DD-247)."""
        try:
            response = await self._client.get(index=self._journal, id=write_id)
        except NotFoundError:
            return None
        return JournalEntry.model_validate(response["_source"])

    async def journal(self) -> list[JournalEntry]:
        """The entries of the journal as the last refresh shows them: recovery reads only entries whose lease has
        passed, long after the index's own refresh (DD-247), and acts on each as ``get_journal`` reads it.
        """  # noqa: D205 - one sentence
        response = await self._client.search(index=self._journal, size=JOURNAL_PAGE, query={"match_all": {}})
        return [JournalEntry.model_validate(hit["_source"]) for hit in response["hits"]["hits"]]

    async def count_type(self, type_name: str) -> int:
        """Count the entities of the type (DD-048): every write refreshes, so the count is current (ENS-11)."""
        response = await self._client.count(index=self._entities, query={"term": {"typeName": type_name}})
        return int(response["count"])

    async def type_counts(self) -> list[TypeCount]:
        """A composite aggregation of the entities by type, state and shell flag (MET-02): writes refresh (ENS-11)."""
        sources = [
            {"type": {"terms": {"field": "typeName"}}},
            {"state": {"terms": {"field": "state"}}},
            {"incomplete": {"terms": {"field": "isIncomplete", "missing_bucket": True}}},
        ]
        return [
            TypeCount(str(key["type"]), str(key["state"]), key["incomplete"] in {True, "true"}, count)
            for key, count in await self._composite(self._entities, sources)
        ]

    async def linked_type_counts(self, kind: LinkedKind) -> dict[str, int]:
        """A composite aggregation of the kind's documents by type (MET-02): writes refresh (ENS-11)."""
        sources = [{"type": {"terms": {"field": "typeName"}}}]
        return {str(key["type"]): count for key, count in await self._composite(self._linked[kind], sources)}

    async def _composite(self, index: str, sources: list[dict[str, Any]]) -> list[tuple[dict[str, Any], int]]:
        """Every bucket of a composite aggregation of the index, page by page."""
        found: list[tuple[dict[str, Any], int]] = []
        after: dict[str, Any] | None = None
        while True:
            composite: dict[str, Any] = {"size": COUNT_PAGE, "sources": sources}
            if after is not None:
                composite["after"] = after
            response = await self._client.search(index=index, size=0, aggs={"counts": {"composite": composite}})
            counts = (response.get("aggregations") or {}).get("counts") or {}
            buckets = counts.get("buckets") or []
            found += [(bucket["key"], int(bucket["doc_count"])) for bucket in buckets]
            after = counts.get("after_key")
            if len(buckets) < COUNT_PAGE or after is None:
                return found

    async def classifications_of_types(self, type_names: Collection[str] | None) -> list[StoredClassification]:
        """Page through the classification index for the instances of the types by GUID (DD-090).

        Writes refresh (ENS-11).
        """
        index = self._linked[LinkedKind.CLASSIFICATION]
        query: dict[str, Any] = {"match_all": {}} if type_names is None else {"terms": {"typeName": sorted(type_names)}}
        found: list[StoredClassification] = []
        after: list[Any] | None = None
        while True:
            response = await self._client.search(
                index=index, size=CLASSIFICATION_PAGE, query=query, sort=[{"guid": "asc"}], search_after=after
            )
            hits = response["hits"]["hits"]
            found += [StoredClassification.model_validate(hit["_source"]) for hit in hits]
            if len(hits) < CLASSIFICATION_PAGE:
                return found
            after = hits[-1]["sort"]

    async def _keep_source_vectors(self, mapping: dict[str, Any], settings: dict[str, Any]) -> None:
        """Make the entity index one that keeps its documents' source beside their vectors (VEC-03, DD-439).

        An index created so is checked for its vectors' dimensions; one created without it moves to a new
        generation, as its setting cannot change.

        Raises:
            EmbeddingDimensionsError: The index maps vectors of other dimensions than the configured ones.
        """
        response = await self._client.indices.get(index=self._entities)
        ((name, index),) = response.body.items()
        if not _keeps_source_vectors(index.get("settings", {})):
            await self._move_to_new_generation(name, mapping, settings)
            return
        mapped = index.get("mappings", {}).get("properties", {}).get(EMBEDDING_FIELD, {}).get("properties", {})
        dims = mapped.get("vector", {}).get("dims")
        if dims is not None and dims != self._embedding_dimensions:
            raise EmbeddingDimensionsError(dims, self._embedding_dimensions or 0)

    async def _move_to_new_generation(self, old: str, mapping: dict[str, Any], settings: dict[str, Any]) -> None:
        """Copy the entity index into the next generation that keeps its sources, then point the alias at it.

        ``_reindex`` copies each document's source as written (DD-039). It runs while this process starts, before
        it writes; another process writing meanwhile would lose its write (DD-439).

        Raises:
            RuntimeError: The new generation does not hold every document of the old one.
        """
        new = _next_generation(old)
        LOGGER.warning("Moving %s to %s, which keeps its documents' source beside their vectors (DD-439)", old, new)
        await self._client.indices.create(index=new, mappings=mapping, settings=settings | KEEP_SOURCE_VECTORS)
        await self._client.reindex(
            source={"index": old}, dest={"index": new, "op_type": "create"}, refresh=True, wait_for_completion=True
        )
        copied, held = [int((await self._client.count(index=index))["count"]) for index in (new, old)]
        if copied != held:
            message = f"{new} holds {copied} of the {held} entities of {old}; {old} stays the entity index"
            raise RuntimeError(message)
        await self._client.indices.update_aliases(
            actions=[
                {"remove": {"index": old, "alias": self._entities}},
                {"add": {"index": new, "alias": self._entities, "is_write_index": True}},
            ]
        )
        await self._client.indices.delete(index=old)
        LOGGER.warning("Moved %d entities to %s", copied, new)

    async def without_embedding(self, model: str, limit: int) -> list[VersionedEntity]:
        """The entities without an embedding of ``model``, internal types left out, by GUID (VEC-06, DD-436)."""
        response = await self._client.search(
            index=self._entities,
            size=limit,
            query={"bool": {"must_not": [{"term": {MODEL_FIELD: model}}, {"prefix": {"typeName": INTERNAL_PREFIX}}]}},
            sort=[{"guid": "asc"}],
            seq_no_primary_term=True,
        )
        return [
            VersionedEntity(
                StoredEntity.model_validate(hit["_source"]), DocumentVersion(hit["_seq_no"], hit["_primary_term"])
            )
            for hit in response["hits"]["hits"]
        ]

    async def search(self, query: SearchQuery) -> SearchHits:
        """Answer the query as a ``bool`` query of the search fields (DD-089): writes refresh (ENS-11).

        Free text is a scored ``simple_query_string`` over the text sub-fields (DD-092); facets are ``terms``
        aggregations of the same query (DD-093). A vector is a ``knn`` search with the same filters inside it, so
        they apply before the nearest are picked; with free text, an entity's score is the sum (DD-441, DD-442).
        """
        clauses: list[dict[str, Any]] = []
        if query.type_names is not None:
            clauses.append({"terms": {_search_path(TYPE_NAME_FIELD): sorted(query.type_names)}})
        if query.active_only:
            clauses.append({"term": {_search_path(STATE_FIELD): ACTIVE}})
        if query.filter is not None:
            clauses.append(_es_filter(query.filter))
        must = [] if query.text is None else [_es_text(query.text)]
        excluded = [{"ids": {"values": sorted(query.exclude_guids)}}] if query.exclude_guids else []
        sort: list[dict[str, Any]] = []
        if query.sort_field is not None and query.vector is None:
            sort.append(_es_sort(query.sort_field, descending=query.descending))
        elif query.text is not None or query.vector is not None:
            sort.append({"_score": {"order": "desc"}})
        sort += [_es_sort(name, descending=False) for name in query.tie_break]
        selected = {"bool": {"filter": clauses, "must": must, "must_not": excluded}}
        knn = None
        if query.vector is not None:
            knn = {
                "field": VECTOR_FIELD,
                "query_vector": list(query.vector.vector),
                "k": query.vector.k,
                "num_candidates": query.vector.num_candidates,
                "filter": {"bool": {"filter": clauses, "must_not": excluded}},
                "boost": query.vector.weight,
            }
        response = await self._client.search(
            index=self._entities,
            query=None if knn is not None and query.text is None else selected,
            knn=knn,
            sort=sort,
            from_=query.offset,
            size=query.size,
            track_total_hits=True,
            track_scores=True,
            aggs={str(index): _es_terms(_search_path(name), FACET_SIZE) for index, name in enumerate(query.facets)}
            or None,
        )
        hits = response["hits"]
        aggregations = response.get("aggregations") or {}
        return SearchHits(
            [StoredEntity.model_validate(hit["_source"]) for hit in hits["hits"]],
            int(hits["total"]["value"]),
            [float(hit.get("_score") or 0) for hit in hits["hits"]],
            {name: _buckets(aggregations, str(index)) for index, name in enumerate(query.facets)},
        )

    async def terms(self, fields: Sequence[str], prefix: str) -> dict[str, list[tuple[str, int]]]:
        """A ``terms`` aggregation of each field's text sub-field (DD-094): writes refresh (ENS-11)."""
        include = "".join(f"\\{character}" if character in _REGEX_RESERVED else character for character in prefix)
        response = await self._client.search(
            index=self._entities,
            size=0,
            query={"match_all": {}},
            aggs={
                str(index): _es_terms(f"{_search_path(name)}.{TEXT}", TERM_COUNT, include=f"{include}.*")
                for index, name in enumerate(fields)
            },
        )
        aggregations = response.get("aggregations") or {}
        return {name: _buckets(aggregations, str(index)) for index, name in enumerate(fields)}


def _search_path(name: str) -> str:
    return f"search.{name}"


_REGEX_RESERVED = set('.?+*|{}[]()"\\#@&<>~')
"""Characters Lucene's regular expressions reserve, escaped in a prefix."""


def _es_terms(field: str, size: int, *, include: str | None = None) -> dict[str, Any]:
    """A ``terms`` aggregation of a field, most documents first, then by value."""
    terms: dict[str, Any] = {"field": field, "size": size, "order": [{"_count": "desc"}, {"_key": "asc"}]}
    if include is not None:
        terms["include"] = include
    return {"terms": terms}


def _buckets(aggregations: Mapping[str, Any], name: str) -> list[tuple[str, int]]:
    return [(str(bucket["key"]), int(bucket["doc_count"])) for bucket in aggregations.get(name, {}).get("buckets", [])]


def _es_text(text: TextQuery) -> dict[str, Any]:
    """Free text: ``simple_query_string`` over the text sub-fields, each boosted by its weight (DD-092)."""
    fields = [f"{_search_path(name)}.{TEXT}^{weight}" for name, weight in text.fields.items()]
    return {
        "simple_query_string": {
            "query": text.text,
            "fields": fields,
            "default_operator": "or",
            "analyze_wildcard": True,
            "lenient": True,
        }
    }


def _es_sort(name: str, *, descending: bool) -> dict[str, Any]:
    """A sort on a search field, entities without a value last; a field no entity has yet sorts as its kind."""
    kind = name.partition(".")[0]
    return {_search_path(name): {"order": "desc" if descending else "asc", "missing": "_last", "unmapped_type": kind}}


def _escape_wildcard(value: str) -> str:
    return "".join(f"\\{character}" if character in "*?\\" else character for character in value)


def _es_filter(node: Filter) -> dict[str, Any]:  # noqa: C901, PLR0911, PLR0912 - one clause per test
    """A filter of the search query as an Elasticsearch query (SRC-05, DD-089)."""
    if isinstance(node, Group):
        clauses = [_es_filter(child) for child in node.criteria]
        if node.condition is Condition.AND:
            return {"bool": {"filter": clauses}}
        return {"bool": {"should": clauses, "minimum_should_match": 1}}
    path, value = _search_path(node.field), node.value
    match node.test:
        case Test.NOTHING:
            return {"match_none": {}}
        case Test.ANYTHING:
            return {"match_all": {}}
        case Test.ANY_OF:
            return {"terms": {path: sorted(value)}}
        case Test.MATCHES:
            pattern = "*".join(_escape_wildcard(part) for part in str(value).split("*"))
            return {"wildcard": {path: {"value": pattern, "case_insensitive": True}}}
        case Test.REGEX:
            return {"regexp": {path: {"value": value, "flags": "NONE"}}}
        case Test.WORD_REGEX:
            return {"regexp": {f"{path}.{TEXT}": {"value": value, "flags": "NONE", "case_insensitive": True}}}
        case Test.EQ:
            return {"term": {path: value}}
        case Test.NEQ:
            return {"bool": {"must_not": [{"term": {path: value}}]}}
        case Test.LT | Test.LTE | Test.GT | Test.GTE:
            return {"range": {path: {node.test.value.lower(): value}}}
        case Test.RANGE:
            return {"range": {path: {"gte": value, "lte": node.value2}}}
        case Test.STARTS_WITH:
            return {"prefix": {path: value}}
        case Test.ENDS_WITH:
            return {"wildcard": {path: {"value": "*" + _escape_wildcard(value)}}}
        case Test.CONTAINS:
            return _es_contains(path, value, array=node.array)
        case Test.NOT_CONTAINS:
            return {"bool": {"must_not": [_es_contains(path, value, array=node.array)]}}
        case Test.IS_NULL:
            return {"bool": {"must_not": [{"exists": {"field": path}}]}}
        case Test.NOT_NULL:
            return {"exists": {"field": path}}
        case _:  # Test.NOT_EMPTY
            empty = [{"term": {path: ""}}] if node.field.startswith(f"{KEYWORD}.") else []
            return {"bool": {"filter": [{"exists": {"field": path}}], "must_not": empty}}


def _es_contains(path: str, value: Any, *, array: bool) -> dict[str, Any]:  # noqa: ANN401 - a field's value
    if array:
        return {"term": {path: value}}
    return {"wildcard": {path: {"value": "*" + _escape_wildcard(str(value)) + "*"}}}
