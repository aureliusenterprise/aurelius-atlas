"""A search by meaning on the dev Elasticsearch (SBM-02, SBM-03, SBM-05), in indices of their own per test.

The sample entities get two-dimension embeddings, so the nearest are known: ``t`` at ``[1, 0]``, ``c1`` near it,
``c3`` between, ``c2`` across, ``d`` opposite. What only a real Elasticsearch shows: the ``knn`` clause with the
filters inside it, its hits paged by ``from``, the facets counted over them, and the text's score added.
"""

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_embedding import source_hash
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.stored_entity import StoredEmbedding
from aurelius_atlas_core.testing.entity_samples import sample_entities, sample_registry
from aurelius_atlas_model.discovery import AtlasQuickSearchResult, QuickSearchParameters
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

VECTORS = {"t": [1.0, 0.0], "c1": [0.9, 0.1], "c3": [0.5, 0.5], "c2": [0.0, 1.0], "d": [-1.0, 0.0]}


async def embedded_store(dev_store: ElasticsearchStore, prefix: str) -> EntityStore:
    """The sample entities in indices of ``prefix``, each with its two-dimension embedding."""
    documents = ElasticsearchEntityDocuments(dev_store.client, prefix, embedding_dimensions=2)
    store = EntityStore(sample_registry(), documents)
    await store.prepare()
    await store.write([EntityChange(entity) for entity in sample_entities(store.registry)])
    for guid, vector in VECTORS.items():
        found = (await documents.get([guid]))[guid]
        embedding = StoredEmbedding(vector=vector, model="m", source_hash=source_hash(found.entity))
        await documents.write([(found.entity.model_copy(update={"embedding": embedding}), found.version)])
    return store


def guids(result: AtlasQuickSearchResult) -> list[str]:
    """The GUIDs of the result's entities, in order."""
    assert result.search_results is not None
    return [entity.guid or "" for entity in result.search_results.entities or []]


@pytest.mark.covers(rules=["SBM-02"])
async def test__the_nearest_come_first_filtered_paged_and_faceted(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Nearest first; a type inside the kNN search; a page from its hits; facets of those hits."""
    service = EntityDiscoveryService(await embedded_store(dev_store, entity_prefix))
    near = [1.0, 0.0]

    first = await service.search_by_meaning(QuickSearchParameters(query="q", limit=3), near)
    columns = await service.search_by_meaning(QuickSearchParameters(query="q", type_name="s_column", limit=3), near)
    paged = await service.search_by_meaning(QuickSearchParameters(query="q", offset=1, limit=2), near)

    assert guids(first) == ["t", "c1", "c3"]
    assert first.search_results is not None
    assert first.search_results.approximate_count == 3
    assert first.aggregation_metrics is not None
    assert {bucket.name: bucket.count for bucket in first.aggregation_metrics["__typeName"]} == {
        "s_column": 2,
        "s_table": 1,
    }
    assert guids(columns) == ["c1", "c3", "c2"]
    assert guids(paged) == ["c1", "c3"]


@pytest.mark.covers(rules=["SBM-05"])
async def test__an_excluded_entity_is_never_among_the_nearest(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """The entity whose neighbours are searched is left out, and the next ones move up."""
    service = EntityDiscoveryService(await embedded_store(dev_store, entity_prefix))

    result = await service.search_by_meaning(
        QuickSearchParameters(limit=2), VECTORS["t"], exclude_guids=frozenset({"t"})
    )

    assert guids(result) == ["c1", "c3"]


@pytest.mark.covers(rules=["SBM-03"])
async def test__hybrid_adds_the_text_s_matches_and_weighs_the_vector(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """``db``'s match joins the two nearest; with the vector weighed, the nearest lead; unweighed, the match does."""
    service = EntityDiscoveryService(await embedded_store(dev_store, entity_prefix))
    parameters = QuickSearchParameters(query="db", limit=2)

    weighted = await service.search_by_meaning(parameters, [0.0, 1.0], hybrid=True, weight=10.0)
    unweighted = await service.search_by_meaning(parameters, [0.0, 1.0], hybrid=True, weight=0.0)

    assert guids(weighted) == ["c2", "c3"]
    assert weighted.search_results is not None
    assert weighted.search_results.approximate_count == 3
    assert guids(unweighted)[0] == "d"
