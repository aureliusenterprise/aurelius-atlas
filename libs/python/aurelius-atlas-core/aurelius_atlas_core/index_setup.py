"""The indices the documents live in: their names, their mappings, and the index-level constants (EDS-01, DD-789).

The index names and mappings that sit beside the write and read paths, moved out of ``entity_documents`` so that
adding a mapped field or an index is a change to one module. The client reads names and mappings from here, and
query translation from ``es_clauses``.
"""

from enum import StrEnum
from typing import Any

from aurelius_atlas_core.app_search_document import (
    APP_SEARCH_FIELD,
    GOVERNED_FIELD,
    QUALITY_RESULT_FIELD,
    QUALITY_TOTALS_FIELD,
    app_search_mapping,
    quality_result_mapping,
    quality_totals_mapping,
)
from aurelius_atlas_core.search_fields import KEYWORD, KINDS, TEXT
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.stored_task import StoredTask

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

ENTITY_DOCUMENTS = "entities"
GOV_QUALITY = "gov-quality"
"""The indices an App Search engine searches: the entities', and the governance verdicts' (DD-534)."""

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
        APP_SEARCH_FIELD: app_search_mapping(),
        QUALITY_RESULT_FIELD: quality_result_mapping(),
        QUALITY_TOTALS_FIELD: quality_totals_mapping(),
        GOVERNED_FIELD: {"type": "boolean"},
    },
    "dynamic_templates": [
        {f"search_{kind}": {"path_match": f"search.{kind}.*", "mapping": _search_mapping(kind)}} for kind in KINDS
    ],
}
"""System properties and referenced GUIDs mapped for exact lookup; attribute values stored, not indexed, and searched
in the typed fields of ``search``, which the dynamic templates map by their kind (DD-043, DD-057, DD-088); the App
Search document's fields, by name (ASD-02).
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
        "appSearchState": _KEYWORD,
        "attributes": {"type": "object", "dynamic": False},
    },
}
"""Relationships by type, label, ends and state, and the state their ends' App Search documents saw; attribute
values stored, not indexed (DD-061, DD-520).
"""

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


def _keeps_source_vectors(settings: dict[str, Any]) -> bool:
    """Whether an index's settings, flat or nested as Elasticsearch answers them, keep the source of vectors."""
    flat = settings.get("index.mapping.exclude_source_vectors")
    nested = settings.get("index", {}).get("mapping", {}).get("exclude_source_vectors")
    return str(flat if flat is not None else nested).lower() == "false"


def _next_generation(index: str) -> str:
    """The index after ``index`` behind its alias: ``…-000001`` is followed by ``…-000002``."""
    stem, _, number = index.rpartition("-")
    return f"{stem}-{int(number) + 1:06d}"
