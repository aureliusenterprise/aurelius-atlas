"""The semantic door on the dev Elasticsearch (ASV-03, ASV-04, ASV-05), in an index of its own per test.

The sample entities get two-dimension embeddings, so the nearest are known: ``t`` at ``[1, 0]``, ``c1`` near
it, ``c3`` between, ``c2`` across, ``d`` opposite. What only a real Elasticsearch shows: the door's kNN clause
carrying its filters inside, its hits paged by ``from`` and faceted over, and the hybrid score of text plus
weighted similarity (DD-596, DD-597, DD-598 — 11.4's e2e draws the same vectors).
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_embedding import source_hash
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.stored_entity import StoredEmbedding
from aurelius_atlas_core.testing.entity_samples import sample_entities, sample_registry
from aurelius_atlas_core.view_search import ViewSearchEngine
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

VECTORS = {"t": [1.0, 0.0], "c1": [0.9, 0.1], "c3": [0.5, 0.5], "c2": [0.0, 1.0], "d": [-1.0, 0.0]}
NEAR = [1.0, 0.0]


async def embedded_door(dev_store: ElasticsearchStore, prefix: str) -> ViewSearchEngine:
    """The door over the sample entities in indices of ``prefix``, each with its two-dimension embedding."""
    documents = ElasticsearchEntityDocuments(dev_store.client, prefix, embedding_dimensions=2)
    store = EntityStore(sample_registry(), documents)
    await store.prepare()
    await store.write([EntityChange(entity) for entity in sample_entities(store.registry)])
    registry = store.registry
    for guid, vector in VECTORS.items():
        found = (await documents.get([guid]))[guid]
        embedding = StoredEmbedding(vector=vector, model="m", source_hash=source_hash(found.entity))
        await documents.write([(found.entity.model_copy(update={"embedding": embedding}), found.version)])
    return ViewSearchEngine(documents, registry)


def cards(answer: dict[str, Any]) -> list[str]:
    """The GUIDs of the door's cards, in its order."""
    return [card["guid"] for card in answer["cards"]]


@pytest.mark.critical
@pytest.mark.covers(rules=["ASV-03", "ASV-04"])
async def test__the_nearest_come_first_filtered_paged_and_faceted(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Nearest first; a type inside the kNN search; a page of the hits; ``total`` and facets over them."""
    door = await embedded_door(dev_store, entity_prefix)

    first = await door.search(
        {"query": "anything", "mode": "semantic", "limit": 3, "facets": ["typeName"]}, vector=NEAR
    )
    columns = await door.search(
        {"query": "anything", "mode": "semantic", "filters": {"typeName": "s_column"}, "limit": 3}, vector=NEAR
    )
    paged = await door.search({"query": "anything", "mode": "semantic", "offset": 1, "limit": 2}, vector=NEAR)

    assert cards(first) == ["t", "c1", "c3"]
    assert first["total"] == 3  # the answer's hits, not the population of five (ASV-04)
    assert first["facets"]["typeName"] == [{"value": "s_column", "count": 2}, {"value": "s_table", "count": 1}]
    assert cards(columns) == ["c1", "c3", "c2"]  # the filter applies before the nearest are picked (ASV-03)
    assert cards(paged) == ["c1", "c3"]


@pytest.mark.critical
@pytest.mark.covers(rules=["ASV-05"])
async def test__hybrid_adds_the_text_s_matches_and_weighs_the_vector(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """``db``'s match joins the two nearest; weighed, the nearest lead; unweighed, the match does."""
    door = await embedded_door(dev_store, entity_prefix)
    asked = {"query": "db", "mode": "hybrid", "limit": 2}

    weighed = await door.search(asked, vector=NEAR, weight=10.0)
    unweighed = await door.search(asked, vector=NEAR, weight=0.0)

    assert cards(weighed) == ["t", "c1"]
    assert cards(unweighed)[0] == "d"  # the text's match, unweighed, beats every similarity
    assert weighed["total"] == 3  # the nearest and the text's match d, counted together (ASV-05)
