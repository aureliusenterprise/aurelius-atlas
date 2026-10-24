"""The entities' documents in Elasticsearch: entities, unique value reservations and the write journal (ENS-01).

The I/O behind ``EntityStore``: reads in real time, conditional writes, create-only reservations (DD-043 to DD-047).
Documents go to Elasticsearch as the bytes of Atlas's JSON codec, so values keep their digits (DD-039).
"""

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

from aurelius_atlas_core.free_text import TextQuery
from aurelius_atlas_core.search_fields import KEYWORD, KINDS, TEXT
from aurelius_atlas_core.search_query import (
    ACTIVE,
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
from aurelius_atlas_core.typedef_document import DocumentVersion

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

REFERRING_PAGE = 1000
"""How many referring entities one search page holds (DD-057)."""

_KEYWORD = {"type": "keyword"}
KEYWORD_LIMIT = 8191
"""``ignore_above`` of keyword search fields: the longest value a keyword holds, in characters (DD-092)."""


def _search_mapping(kind: str) -> dict[str, Any]:
    """A search field's mapping: a keyword also has an analysed ``text`` sub-field for free text (DD-092)."""
    if kind != KEYWORD:
        return {"type": kind}
    return {"type": kind, "ignore_above": KEYWORD_LIMIT, "fields": {TEXT: {"type": "text"}}}


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
        """Every journal entry."""
        ...

    async def count_type(self, type_name: str) -> int:
        """How many entities of exactly this type exist, in any state, as of now."""
        ...

    async def search(self, query: SearchQuery) -> SearchHits:
        """The entities of the query's page, as of now, how many match it in all, and their scores (DD-089)."""
        ...

    async def classifications_of_types(self, type_names: Collection[str] | None) -> list[StoredClassification]:
        """The classification instances of these types, or of every type for None, as of now (DD-090)."""
        ...


class ElasticsearchEntityDocuments:
    """``EntityDocuments`` in three Elasticsearch indices behind aliases (DD-043, DD-045, DD-046)."""

    def __init__(self, client: AsyncElasticsearch, prefix: str = INDEX_PREFIX) -> None:
        self._client = client
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
        """
        mappings = {
            self._entities: ENTITY_MAPPING,
            self._unique_values: {"dynamic": False, "properties": {"guid": _KEYWORD, "writeId": _KEYWORD}},
            self._journal: {"dynamic": False, "properties": {"leaseUntil": {"type": "long"}}},
            self._linked[LinkedKind.RELATIONSHIP]: RELATIONSHIP_MAPPING,
            self._linked[LinkedKind.CLASSIFICATION]: CLASSIFICATION_MAPPING,
            self._linked[LinkedKind.TASK]: TASK_MAPPING,
        }
        limit = {"index.mapping.total_fields.limit": ENTITY_FIELD_LIMIT}
        for alias, mapping in mappings.items():
            if not await self._client.indices.exists_alias(name=alias):
                await self._client.indices.create(
                    index=f"{alias}-000001",
                    aliases={alias: {"is_write_index": True}},
                    mappings=mapping,
                    settings=limit if alias == self._entities else None,
                )
            elif alias == self._entities:
                await self._client.indices.put_mapping(
                    index=alias, properties=mapping["properties"], dynamic_templates=mapping["dynamic_templates"]
                )
                await self._client.indices.put_settings(index=alias, settings=limit)

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
            for document, version in documents:
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
        response = await self._client.bulk(operations=body)  # pyright: ignore[reportArgumentType]
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
        """Index the document's state before, or delete one that did not exist before (DD-062)."""
        index = self._linked[kind]
        if before is None:
            try:
                await self._client.delete(index=index, id=guid)
            except NotFoundError:
                return
        else:
            await self._client.index(index=index, id=guid, document=codec.dumps(before.to_json()))  # type: ignore[arg-type]

    async def count_linked_type(self, kind: LinkedKind, type_name: str) -> int:
        """Refresh the kind's index, then count its documents of the type (REL-10, CLS-12)."""
        index = self._linked[kind]
        await self._client.indices.refresh(index=index)
        response = await self._client.count(index=index, query={"term": {"typeName": type_name}})
        return int(response["count"])

    async def referring(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """Refresh the entity index, then page through the entities whose ``references`` hold a GUID (DD-057)."""
        return await self._listing("references", guids)

    async def classified(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """Refresh the entity index, then page through the entities whose ``classificationGuids`` hold one (DD-076)."""
        return await self._listing("classificationGuids", guids)

    async def list_tasks(self, *, open_only: bool) -> list[tuple[StoredTask, DocumentVersion]]:
        """Refresh the task index, then page through its tasks by creation time (TSK-04, TSK-06)."""
        index = self._linked[LinkedKind.TASK]
        await self._client.indices.refresh(index=index)
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
        await self._client.indices.refresh(index=self._entities)
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

    async def classifications_of_types(self, type_names: Collection[str] | None) -> list[StoredClassification]:
        """Refresh the classification index, then page through the instances of the types by GUID (DD-090)."""
        index = self._linked[LinkedKind.CLASSIFICATION]
        await self._client.indices.refresh(index=index)
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

    async def search(self, query: SearchQuery) -> SearchHits:
        """Refresh the entity index, then answer the query as a ``bool`` query of the search fields (DD-089).

        Free text is a scored ``simple_query_string`` over the text sub-fields (DD-092).
        """
        await self._client.indices.refresh(index=self._entities)
        clauses: list[dict[str, Any]] = []
        if query.type_names is not None:
            clauses.append({"terms": {_search_path(TYPE_NAME_FIELD): sorted(query.type_names)}})
        if query.active_only:
            clauses.append({"term": {_search_path(STATE_FIELD): ACTIVE}})
        if query.filter is not None:
            clauses.append(_es_filter(query.filter))
        must = [] if query.text is None else [_es_text(query.text)]
        sort: list[dict[str, Any]] = []
        if query.sort_field is not None:
            sort.append(_es_sort(query.sort_field, descending=query.descending))
        elif query.text is not None:
            sort.append({"_score": {"order": "desc"}})
        sort += [_es_sort(name, descending=False) for name in query.tie_break]
        response = await self._client.search(
            index=self._entities,
            query={"bool": {"filter": clauses, "must": must}},
            sort=sort,
            from_=query.offset,
            size=query.size,
            track_total_hits=True,
            track_scores=True,
        )
        hits = response["hits"]
        return SearchHits(
            [StoredEntity.model_validate(hit["_source"]) for hit in hits["hits"]],
            int(hits["total"]["value"]),
            [float(hit.get("_score") or 0) for hit in hits["hits"]],
        )


def _search_path(name: str) -> str:
    return f"search.{name}"


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
