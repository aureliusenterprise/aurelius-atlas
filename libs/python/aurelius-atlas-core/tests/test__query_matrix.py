"""The saved query matrix answers the same hits and facets from both stores (QRY-04, DD-771).

``fixtures/query-matrix.json`` names each search, the entities it runs against, and the GUIDs and facet counts
it answers. The same fixture runs against the in-memory store and the fake store, so a shared misreading of a
query fails both, which is the gap QRY-04 closes.
"""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_embedding import source_hash
from aurelius_atlas_core.free_text import TextQuery
from aurelius_atlas_core.search_query import Criterion, Filter, Group, SearchQuery, Test, VectorQuery
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.discovery import Condition
from aurelius_atlas_store_es.testing.fake import FakeClient
from elasticsearch import AsyncElasticsearch

D = "aurelius_atlas_core.entity_documents"
E = f"{D}.ElasticsearchEntityDocuments"
M = "aurelius_atlas_core.testing.memory.MemoryEntityDocuments"

MATRIX = json.loads((Path(__file__).parent / "fixtures" / "query-matrix.json").read_text())
"""The saved matrix: ``entities`` to write, and the ``rows`` that search them."""


def _criterion(node: dict[str, Any]) -> Filter:
    """A filter tree from the fixture's JSON."""
    if "condition" in node:
        return Group(Condition(node["condition"]), tuple(_criterion(child) for child in node["criteria"]))
    value = frozenset(node["value"]) if node["test"] == Test.ANY_OF else node.get("value")
    return Criterion(node["field"], Test(node["test"]), value, node.get("value2"), node.get("array", False))


def _query(row: dict[str, Any]) -> SearchQuery:
    """The row's search, as the stores take it."""
    spec = row["query"]
    text = spec.get("text")
    vector = spec.get("vector")
    return SearchQuery(
        type_names=frozenset(spec["type_names"]) if spec.get("type_names") is not None else None,
        active_only=spec.get("active_only", False),
        filter=_criterion(spec["filter"]) if spec.get("filter") is not None else None,
        sort_field=spec.get("sort_field"),
        descending=spec.get("descending", False),
        offset=spec.get("offset", 0),
        size=spec.get("size", 100),
        text=TextQuery(text["text"], text["fields"]) if text is not None else None,
        facets=tuple(spec.get("facets", ())),
        vector=VectorQuery(tuple(vector["vector"]), vector["k"], vector["weight"]) if vector else None,
    )


def _entities() -> list[StoredEntity]:
    """The matrix's entities, each embedding current so neither store drops it (VEC-05)."""
    entities = []
    for item in MATRIX["entities"]:
        entity = StoredEntity.model_validate(item)
        if entity.embedding is not None:
            entity = entity.model_copy(
                update={"embedding": entity.embedding.model_copy(update={"source_hash": source_hash(entity)})}
            )
        entities.append(entity)
    return entities


@pytest.fixture
async def both() -> tuple[ElasticsearchEntityDocuments, MemoryEntityDocuments]:
    """The matrix's entities in each store."""
    entities = _entities()
    documents = ElasticsearchEntityDocuments(cast("AsyncElasticsearch", FakeClient()), prefix="t")
    await documents.prepare()
    await documents.write([(item, None) for item in entities])
    memory = MemoryEntityDocuments()
    await memory.write([(item, None) for item in entities])
    return documents, memory


@pytest.mark.covers(f"{E}.search", f"{M}.search", rules=["QRY-04"])
@pytest.mark.parametrize("row", MATRIX["rows"], ids=[row["name"] for row in MATRIX["rows"]])
async def test__the_matrix_answers_the_same_from_both_stores(
    both: tuple[ElasticsearchEntityDocuments, MemoryEntityDocuments], row: dict[str, Any]
) -> None:
    """The named query answers the saved GUID sequence, total and facets from each store (QRY-04, DD-771).

    The saved answers are what the stores agreed on when the matrix was written, next to the rows' predicates.
    """
    documents, memory = both
    query = _query(row)

    found, expected = await documents.search(query), await memory.search(query)

    assert [item.guid for item in found.entities] == row["guids"]
    assert found.total == row["total"]
    assert [item.guid for item in expected.entities] == row["guids"]
    assert expected.total == row["total"]
    assert found.facets == expected.facets
    if "facets" in row:
        assert found.facets == {name: [tuple(item) for item in buckets] for name, buckets in row["facets"].items()}
