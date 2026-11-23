"""The Elasticsearch client for the entities' documents (EDS-02, DD-789).

The client that used to sit in ``entity_documents``: it reads index names and mappings from ``index_setup``,
builds queries through ``es_clauses``, and keeps the write journal and the unique-value reservations that make a
cut-short write recoverable (DD-043 to DD-047). The protocols and the stored-state models stay in
``entity_documents``.
"""

import logging
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import RelationshipStatus
from aurelius_atlas_model.tasks import TaskStatus
from elasticsearch import AsyncElasticsearch, ConflictError, NotFoundError

from aurelius_atlas_core import es_clauses
from aurelius_atlas_core.app_search_document import (
    APP_SEARCH_FIELD,
    DERIVATION_VERSION,
    DERIVATION_VERSION_FIELD,
    GOV_RULE_TYPE,
    GOVERNED_BY_FIELD,
    GOVERNED_FIELD,
    GUID_FIELDS,
    M4I_PREFIX,
    QUALITY_RESULT_FIELD,
    QUALITY_TOTALS_FIELD,
    SCORE_TYPE,
    SOURCE_HASH_FIELD,
    STALE_FIELD,
    WITHOUT_DOCUMENT,
    StoredVerdict,
    verdict_mapping,
    with_current_app_search,
)
from aurelius_atlas_core.entity_documents import (
    JournalEntry,
    LinkedWrite,
    Reservation,
    TypeCount,
    VersionedEntity,
    VersionedRelationship,
    WriteResult,
)
from aurelius_atlas_core.entity_embedding import (
    EMBEDDING_FIELD,
    INTERNAL_PREFIX,
    MODEL_FIELD,
    embedding_mapping,
    with_current_embedding,
)
from aurelius_atlas_core.free_text import TERM_COUNT
from aurelius_atlas_core.index_setup import (
    _KEYWORD,
    CLASSIFICATION_MAPPING,
    CLASSIFICATION_PAGE,
    COUNT_PAGE,
    ENTITY_DOCUMENTS,
    ENTITY_FIELD_LIMIT,
    ENTITY_MAPPING,
    GOV_QUALITY,
    INDEX_PREFIX,
    JOURNAL_PAGE,
    KEEP_SOURCE_VECTORS,
    LINKED_MODELS,
    REFERRING_PAGE,
    RELATIONSHIP_MAPPING,
    TASK_MAPPING,
    TASK_PAGE,
    WRITE_REFRESH,
    EmbeddingDimensionsError,
    Linked,
    LinkedKind,
    _keeps_source_vectors,
    _next_generation,
)
from aurelius_atlas_core.search_fields import TEXT
from aurelius_atlas_core.search_query import (
    ACTIVE,
    FACET_SIZE,
    STATE_FIELD,
    TYPE_NAME_FIELD,
    SearchHits,
    SearchQuery,
)
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.typedef_document import INDEX_SETTINGS, DocumentVersion, ensure_index

LOGGER = logging.getLogger(__name__)


def _awaiting_document() -> dict[str, Any]:
    """The entities the App Search indexer has a document to derive for: active ones of m4i types with a document
    that have none, those with a stale one, and those derived under older rules (LAS-01, ASD-04, ASD-07, ASU-02,
    DD-500).
    """  # noqa: D205 - one sentence
    missing = es_clauses.bool_(
        filter=[es_clauses.term("state", ACTIVE), es_clauses.prefix("typeName", M4I_PREFIX)],
        must_not=[
            es_clauses.terms("typeName", sorted(WITHOUT_DOCUMENT)),
            es_clauses.exists(SOURCE_HASH_FIELD),
        ],
    )
    outdated = es_clauses.bool_(
        filter=[
            es_clauses.term("state", ACTIVE),
            es_clauses.prefix("typeName", M4I_PREFIX),
            es_clauses.exists(SOURCE_HASH_FIELD),
        ],
        must_not=[
            es_clauses.terms("typeName", sorted(WITHOUT_DOCUMENT)),
            es_clauses.term(DERIVATION_VERSION_FIELD, DERIVATION_VERSION),
        ],
    )
    return es_clauses.should([missing, es_clauses.term(STALE_FIELD, value=True), outdated])


class ElasticsearchEntityDocuments:
    """``StoreDocuments`` in three Elasticsearch indices behind aliases (DD-043, DD-045, DD-046)."""

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
        self._verdicts = f"{prefix}-{GOV_QUALITY}"

    @property
    def aliases(self) -> tuple[str, ...]:
        """The aliases of the entity index, the reservations, the journal, the linked documents' indices and the
        governance verdicts' (DD-534).
        """  # noqa: D205 - one sentence
        return self._entities, self._unique_values, self._journal, *self._linked.values(), self._verdicts

    async def prepare(self) -> None:
        """Create each index behind its alias unless it exists (ENS-01).

        An existing entity or relationship index gets the fields it lacks mapped, as ``references`` (EDL-10) and
        ``appSearchState`` (DD-520); mapped ones stay.
        Every existing index gets the settings of a new one, as its replicas (IDX-02). With embedding on, the entity
        index keeps each document's source as written beside its vector: a new one is created so, and an existing
        one that is not moves to a new generation behind its alias first (VEC-03, DD-434, DD-439).
        """
        mappings = self._index_mappings()
        limit = {"index.mapping.total_fields.limit": ENTITY_FIELD_LIMIT}
        for alias, mapping in mappings.items():
            settings = INDEX_SETTINGS | limit if alias == self._entities else INDEX_SETTINGS
            await self._prepare_alias(alias, mapping, settings)

    def _index_mappings(self) -> dict[str, dict[str, Any]]:
        """The mapping of each index behind its alias, the entity's with its vector field when embedding is on.

        ENS-01, VEC-01.
        """
        entity_mapping = ENTITY_MAPPING
        if self._embedding_dimensions is not None:
            entity_mapping = ENTITY_MAPPING | {
                "properties": ENTITY_MAPPING["properties"]
                | {EMBEDDING_FIELD: embedding_mapping(self._embedding_dimensions)}
            }
        return {
            self._entities: entity_mapping,
            self._unique_values: {"dynamic": False, "properties": {"guid": _KEYWORD, "writeId": _KEYWORD}},
            self._journal: {"dynamic": False, "properties": {"leaseUntil": {"type": "long"}}},
            self._linked[LinkedKind.RELATIONSHIP]: RELATIONSHIP_MAPPING,
            self._linked[LinkedKind.CLASSIFICATION]: CLASSIFICATION_MAPPING,
            self._linked[LinkedKind.TASK]: TASK_MAPPING,
            self._verdicts: verdict_mapping(),
        }

    async def _prepare_alias(self, alias: str, mapping: dict[str, Any], settings: dict[str, Any]) -> None:
        """Create one index behind its alias unless it exists, and bring an existing one up to date.

        ENS-01, EDL-10, DD-520, IDX-02, VEC-03.
        """
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
                return
        if vectors:
            await self._keep_source_vectors(mapping, settings)
        if alias == self._entities:
            await self._client.indices.put_mapping(
                index=alias, properties=mapping["properties"], dynamic_templates=mapping["dynamic_templates"]
            )
        elif alias == self._linked[LinkedKind.RELATIONSHIP]:
            await self._client.indices.put_mapping(index=alias, properties=mapping["properties"])
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
                document = with_current_app_search(with_current_embedding(written)) if group_kind is None else written
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
        purged = [result.guid for result in results[len(items) : len(items) + len(removed)] if result.written]
        if purged:
            await self.replace_verdicts(dict.fromkeys(purged, ()))
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
        response = await self._client.count(index=index, query=es_clauses.term("typeName", type_name))
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
            es_clauses.terms("status", [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value])
            if open_only
            else es_clauses.match_all()
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
        return await self._paged(es_clauses.terms(field, list(guids)))

    async def _paged(self, query: dict[str, Any]) -> list[VersionedEntity]:
        found: list[VersionedEntity] = []
        after: list[Any] | None = None
        while True:
            response = await self._client.search(
                index=self._entities,
                size=REFERRING_PAGE,
                query=query,
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
                document=codec.dumps(reservation.to_json()),  # type: ignore[arg-type]
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
            doc["_id"]: Reservation.model_validate({"key": doc["_id"], **doc["_source"]})
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
        response = await self._client.search(index=self._journal, size=JOURNAL_PAGE, query=es_clauses.match_all())
        return [JournalEntry.model_validate(hit["_source"]) for hit in response["hits"]["hits"]]

    async def count_type(self, type_name: str) -> int:
        """Count the entities of the type (DD-048): every write refreshes, so the count is current (ENS-11)."""
        response = await self._client.count(index=self._entities, query=es_clauses.term("typeName", type_name))
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
        query: dict[str, Any] = (
            es_clauses.match_all() if type_names is None else es_clauses.terms("typeName", sorted(type_names))
        )
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

    async def without_embedding(
        self, model: str, limit: int, *, wait_for_documents: bool = False
    ) -> list[VersionedEntity]:
        """The entities without an embedding of ``model``, internal types left out, by GUID (VEC-06, DD-436); with
        ``wait_for_documents``, also those awaiting their App Search document (EMC-04, DD-540).
        """  # noqa: D205 - one sentence
        left_out: list[dict[str, Any]] = [
            es_clauses.term(MODEL_FIELD, model),
            es_clauses.prefix("typeName", INTERNAL_PREFIX),
        ]
        if wait_for_documents:
            left_out.append(_awaiting_document())
        response = await self._client.search(
            index=self._entities,
            size=limit,
            query=es_clauses.must_not(left_out),
            sort=[{"guid": "asc"}],
            seq_no_primary_term=True,
        )
        return [
            VersionedEntity(
                StoredEntity.model_validate(hit["_source"]), DocumentVersion(hit["_seq_no"], hit["_primary_term"])
            )
            for hit in response["hits"]["hits"]
        ]

    async def without_app_search(self, limit: int) -> list[VersionedEntity]:
        """The active entities of m4i types with a document that have none, and those with a stale one, by GUID
        (LAS-01, ASD-04, ASU-02, DD-500).
        """  # noqa: D205 - one sentence
        response = await self._client.search(
            index=self._entities,
            size=limit,
            query=_awaiting_document(),
            sort=[{"guid": "asc"}],
            seq_no_primary_term=True,
        )
        return [
            VersionedEntity(
                StoredEntity.model_validate(hit["_source"]), DocumentVersion(hit["_seq_no"], hit["_primary_term"])
            )
            for hit in response["hits"]["hits"]
        ]

    async def naming(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """Page through the entities whose App Search GUID fields hold one (ASU-03): writes refresh (ENS-11)."""
        if not guids:
            return []
        fields = [es_clauses.terms(f"{APP_SEARCH_FIELD}.{field}", list(guids)) for field in GUID_FIELDS]
        return await self._paged(es_clauses.should(fields))

    async def unseen_relationships(self, limit: int) -> list[VersionedRelationship]:
        """The relationships deleted whose record is not, and those active whose record is, by GUID (ASU-04)."""
        deleted = RelationshipStatus.DELETED.value
        response = await self._client.search(
            index=self._linked[LinkedKind.RELATIONSHIP],
            size=limit,
            query=es_clauses.should(
                [
                    es_clauses.bool_(
                        filter=[es_clauses.term("state", deleted)],
                        must_not=[es_clauses.term("appSearchState", deleted)],
                    ),
                    es_clauses.filter_([es_clauses.term("state", ACTIVE), es_clauses.term("appSearchState", deleted)]),
                ]
            ),
            sort=[{"guid": "asc"}],
            seq_no_primary_term=True,
        )
        return [
            VersionedRelationship(
                StoredRelationship.model_validate(hit["_source"]), DocumentVersion(hit["_seq_no"], hit["_primary_term"])
            )
            for hit in response["hits"]["hits"]
        ]

    async def scores(self) -> list[VersionedEntity]:
        """Page through the active score entities (ASQ-02): writes refresh (ENS-11)."""
        active = [es_clauses.term("state", ACTIVE), es_clauses.term("typeName", SCORE_TYPE)]
        return await self._paged(es_clauses.filter_(active))

    async def quality_holders(self) -> list[VersionedEntity]:
        """Page through the entities holding a quality result or score totals (ASQ-07): writes refresh (ENS-11)."""
        held = [
            es_clauses.exists(f"{QUALITY_RESULT_FIELD}.qualityguid"),
            es_clauses.exists(f"{QUALITY_TOTALS_FIELD}.overall.count"),
        ]
        return await self._paged(es_clauses.should(held))

    async def governance_rules(self) -> list[VersionedEntity]:
        """Page through the active governance rule entities (ASG-03): writes refresh (ENS-11)."""
        rules = [es_clauses.term("state", ACTIVE), es_clauses.term("typeName", GOV_RULE_TYPE)]
        return await self._paged(es_clauses.filter_(rules))

    async def to_govern(self, digests: Mapping[str, str], limit: int) -> list[VersionedEntity]:
        """The entities to judge by GUID, a page of them: those of a ruled type judged otherwise, those that lost
        their verdicts' cause (ASG-06, DD-535).
        """  # noqa: D205 - one sentence
        judged = [es_clauses.term("state", ACTIVE), es_clauses.exists(SOURCE_HASH_FIELD)]
        stale = [
            es_clauses.bool_(
                filter=[es_clauses.term("typeName", type_name)],
                must_not=[es_clauses.term(GOVERNED_BY_FIELD, digest)],
            )
            for type_name, digest in digests.items()
        ]
        lost = es_clauses.bool_(
            filter=[es_clauses.term(GOVERNED_FIELD, value=True)],
            must_not=[es_clauses.filter_([*judged, es_clauses.terms("typeName", sorted(digests))])],
        )
        should: list[dict[str, Any]] = [lost]
        if stale:
            should.append(es_clauses.bool_(filter=judged, should=stale, minimum_should_match=1))
        response = await self._client.search(
            index=self._entities,
            size=limit,
            query=es_clauses.should(should),
            sort=[{"guid": "asc"}],
            seq_no_primary_term=True,
        )
        return [
            VersionedEntity(
                StoredEntity.model_validate(hit["_source"]), DocumentVersion(hit["_seq_no"], hit["_primary_term"])
            )
            for hit in response["hits"]["hits"]
        ]

    async def replace_verdicts(self, verdicts: Mapping[str, Sequence[StoredVerdict]]) -> None:
        """One bulk request: each verdict indexed, each other one of these entities deleted (DD-534).

        Raises:
            RuntimeError: Elasticsearch refused an action of the request, so an entity keeps a verdict it no
                longer holds or misses one it gained (ASG-06, DD-705).
        """
        if not verdicts:
            return
        wanted = {verdict.id: verdict for found in verdicts.values() for verdict in found}
        held = await self._verdict_ids(list(verdicts))
        lines: list[bytes] = []
        for verdict_id, verdict in wanted.items():
            lines += [
                codec.dumps({"index": {"_index": self._verdicts, "_id": verdict_id}}),
                codec.dumps(verdict.to_json()),
            ]
        lines += [
            codec.dumps({"delete": {"_index": self._verdicts, "_id": verdict_id}})
            for verdict_id in held
            if verdict_id not in wanted
        ]
        if lines:
            body = b"\n".join(lines) + b"\n"
            response = await self._client.bulk(
                operations=body,  # pyright: ignore[reportArgumentType] - the NDJSON bytes, as the entity write sends them
                refresh=WRITE_REFRESH,
            )
            if response.get("errors"):
                message = f"The verdicts could not all be written to {self._verdicts}"
                raise RuntimeError(message)

    async def _verdict_ids(self, entity_guids: list[str]) -> list[str]:
        """Page through the ids of these entities' verdicts."""
        found: list[str] = []
        after: list[Any] | None = None
        while True:
            response = await self._client.search(
                index=self._verdicts,
                size=REFERRING_PAGE,
                query=es_clauses.terms("entity_guid", entity_guids),
                sort=[{"id": "asc"}],
                search_after=after,
            )
            hits = response["hits"]["hits"]
            found += [hit["_id"] for hit in hits]
            if len(hits) < REFERRING_PAGE:
                return found
            after = hits[-1]["sort"]

    async def verdicts_by_entity(self, entity_guids: Sequence[str]) -> dict[str, list[StoredVerdict]]:
        """Page through these entities' verdict documents, grouped by entity GUID (ASG-08, DD-838).

        The same paged terms read ``_verdict_ids`` runs, with the sources kept: one filter over
        ``entity_guid``, sorted by ``id`` with ``search_after`` (ASG-03). The sort is global, so each
        entity's group keeps its id order. An empty request asks the store nothing, and an entity with no
        verdict documents gets no key.
        """
        if not entity_guids:
            return {}
        grouped: dict[str, list[StoredVerdict]] = {}
        after: list[Any] | None = None
        while True:
            response = await self._client.search(
                index=self._verdicts,
                size=REFERRING_PAGE,
                query=es_clauses.terms("entity_guid", list(entity_guids)),
                sort=[{"id": "asc"}],
                search_after=after,
            )
            hits = response["hits"]["hits"]
            for hit in hits:
                verdict = StoredVerdict.model_validate(hit["_source"])
                grouped.setdefault(verdict.entity_guid, []).append(verdict)
            if len(hits) < REFERRING_PAGE:
                return grouped
            after = hits[-1]["sort"]

    async def search_app_search(  # noqa: PLR0913 - Elasticsearch's search arguments; and the index
        self,
        *,
        query: dict[str, Any] | None,
        sort: list[dict[str, Any]],
        aggs: dict[str, Any],
        from_: int,
        size: int,
        index: str = ENTITY_DOCUMENTS,
        knn: dict[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """One search of an engine's index, the entities' or the verdicts' (DD-534): hits with scores, the exact
        total, the aggregations (DD-523). A ``knn`` searches the nearest with its own filter inside, the scores
        of both added (ASV-03, DD-596). Writes refresh (ENS-11).
        """  # noqa: D205 - one sentence
        response: Mapping[str, Any] = await self._client.search(  # pyright: ignore[reportAssignmentType]
            index=self._verdicts if index == GOV_QUALITY else self._entities,
            query=query,
            knn=knn,
            sort=sort,
            aggs=aggs or None,
            from_=from_,
            size=size,
            track_total_hits=True,
            track_scores=True,
        )
        return response

    async def search(self, query: SearchQuery) -> SearchHits:
        """Answer the query as a ``bool`` query of the search fields (DD-089): writes refresh (ENS-11).

        Free text is a scored ``simple_query_string`` over the text sub-fields (DD-092); facets are ``terms``
        aggregations of the same query (DD-093). A vector is a ``knn`` search with the same filters inside it, so
        they apply before the nearest are picked; with free text, an entity's score is the sum (DD-441, DD-442).
        """
        clauses: list[dict[str, Any]] = []
        if query.type_names is not None:
            clauses.append(es_clauses.terms(es_clauses.search_path(TYPE_NAME_FIELD), sorted(query.type_names)))
        if query.active_only:
            clauses.append(es_clauses.term(es_clauses.search_path(STATE_FIELD), ACTIVE))
        if query.filter is not None:
            clauses.append(es_clauses.filter_clause(query.filter))
        must = [] if query.text is None else [es_clauses.text_clause(query.text)]
        excluded = [{"ids": {"values": sorted(query.exclude_guids)}}] if query.exclude_guids else []
        sort: list[dict[str, Any]] = []
        if query.sort_field is not None and query.vector is None:
            sort.append(_es_sort(query.sort_field, descending=query.descending))
        elif query.text is not None or query.vector is not None:
            sort.append({"_score": {"order": "desc"}})
        sort += [_es_sort(name, descending=False) for name in query.tie_break]
        selected = es_clauses.bool_(filter=clauses, must=must, must_not=excluded)
        knn = None
        if query.vector is not None:
            knn = es_clauses.knn(
                query.vector,
                es_clauses.bool_(filter=clauses, must_not=excluded),
            )
        response = await self._client.search(
            index=self._entities,
            query=None if knn is not None and query.text is None else selected,
            knn=knn,
            sort=sort,
            from_=query.offset,
            size=query.size,
            track_total_hits=True,
            track_scores=True,
            aggs={
                str(index): es_clauses.terms_agg(es_clauses.search_path(name), FACET_SIZE)
                for index, name in enumerate(query.facets)
            }
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
            query=es_clauses.match_all(),
            aggs={
                str(index): es_clauses.terms_agg(
                    f"{es_clauses.search_path(name)}.{TEXT}", TERM_COUNT, include=f"{include}.*"
                )
                for index, name in enumerate(fields)
            },
        )
        aggregations = response.get("aggregations") or {}
        return {name: _buckets(aggregations, str(index)) for index, name in enumerate(fields)}


_REGEX_RESERVED = set('.?+*|{}[]()"\\#@&<>~')
"""Characters Lucene's regular expressions reserve, escaped in a prefix."""


def _buckets(aggregations: Mapping[str, Any], name: str) -> list[tuple[str, int]]:
    return [(str(bucket["key"]), int(bucket["doc_count"])) for bucket in aggregations.get(name, {}).get("buckets", [])]


def _es_sort(name: str, *, descending: bool) -> dict[str, Any]:
    """A sort on a search field, entities without a value last; a field no entity has yet sorts as its kind."""
    kind = name.partition(".")[0]
    return {
        es_clauses.search_path(name): {
            "order": "desc" if descending else "asc",
            "missing": "_last",
            "unmapped_type": kind,
        }
    }
