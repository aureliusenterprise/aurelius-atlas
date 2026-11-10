"""A search by meaning over the sample entities in the in-memory store (SBM-02, SBM-03, SBM-05).

Each sample entity gets a two-dimension embedding, so which entities are nearest is known: ``t`` at ``[1, 0]``,
``c1`` near it, ``c3`` between, ``c2`` across, and ``d`` opposite.
"""

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_embedding import source_hash
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.search_query import SearchQuery, VectorQuery
from aurelius_atlas_core.stored_entity import StoredEmbedding
from aurelius_atlas_core.testing.entity_samples import sample_entities, sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.discovery import QuickSearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

S = "aurelius_atlas_core.discovery_service.EntityDiscoveryService.search_by_meaning"
VECTORS = {"t": [1.0, 0.0], "c1": [0.9, 0.1], "c3": [0.5, 0.5], "c2": [0.0, 1.0], "d": [-1.0, 0.0]}


@pytest.fixture
async def store() -> EntityStore:
    """The sample entities, each with its embedding."""
    documents = MemoryEntityDocuments()
    store = EntityStore(sample_registry(), documents)
    await store.write([EntityChange(entity) for entity in sample_entities(store.registry)])
    for guid, vector in VECTORS.items():
        found = (await documents.get([guid]))[guid]
        embedding = StoredEmbedding(vector=vector, model="m", source_hash=source_hash(found.entity))
        await documents.write([(found.entity.model_copy(update={"embedding": embedding}), found.version)])
    return store


def guids(result: object) -> list[str]:
    """The GUIDs of a quick search result's entities, in order."""
    return [entity.guid for entity in result.search_results.entities or []]  # type: ignore[attr-defined]


@pytest.mark.covers(S, rules=["SBM-02"])
async def test__the_nearest_entities_come_first_with_their_facets(store: EntityStore) -> None:
    """``offset + limit`` nearest, nearest first; counted and faceted over them."""
    result = await EntityDiscoveryService(store).search_by_meaning(
        QuickSearchParameters(query="orders", limit=3), [1.0, 0.0]
    )

    assert guids(result) == ["t", "c1", "c3"]
    assert result.search_results is not None
    assert result.search_results.approximate_count == 3
    assert result.search_results.query_text == "orders"
    assert result.aggregation_metrics is not None
    assert {bucket.name: bucket.count for bucket in result.aggregation_metrics["__typeName"]} == {
        "s_column": 2,
        "s_table": 1,
    }


@pytest.mark.covers(S, rules=["SBM-02"])
async def test__the_type_selects_before_the_nearest_are_picked(store: EntityStore) -> None:
    """Only columns, however far: the filter is inside the nearest search."""
    result = await EntityDiscoveryService(store).search_by_meaning(
        QuickSearchParameters(query="orders", type_name="s_column", limit=3), [1.0, 0.0]
    )

    assert guids(result) == ["c1", "c3", "c2"]


@pytest.mark.covers(S, rules=["SBM-02"])
async def test__a_page_further_down_is_taken_from_the_nearest(store: EntityStore) -> None:
    """``offset`` 1, ``limit`` 2: the second and third nearest."""
    result = await EntityDiscoveryService(store).search_by_meaning(
        QuickSearchParameters(query="orders", offset=1, limit=2), [1.0, 0.0]
    )

    assert guids(result) == ["c1", "c3"]


@pytest.mark.covers(S, rules=["SBM-05"])
async def test__an_excluded_entity_is_never_answered(store: EntityStore) -> None:
    """The entity whose neighbours are searched is left out of them."""
    result = await EntityDiscoveryService(store).search_by_meaning(
        QuickSearchParameters(limit=2), VECTORS["t"], exclude_guids=frozenset({"t"})
    )

    assert guids(result) == ["c1", "c3"]


@pytest.mark.covers(S, rules=["SBM-03"])
async def test__hybrid_adds_the_text_s_matches_and_their_scores(store: EntityStore) -> None:
    """``db``'s text match joins the two nearest; weighted, the nearest still lead it."""
    service = EntityDiscoveryService(store)

    weighted = await service.search_by_meaning(
        QuickSearchParameters(query="db", limit=2), [0.0, 1.0], hybrid=True, weight=10.0
    )
    unweighted = await service.search_by_meaning(
        QuickSearchParameters(query="db", limit=2), [0.0, 1.0], hybrid=True, weight=0.0
    )

    assert guids(weighted) == ["c2", "c3"]
    assert weighted.search_results is not None
    assert weighted.search_results.approximate_count == 3
    assert guids(unweighted)[0] == "d"


@pytest.mark.covers(S, rules=["SBM-04"])
async def test__more_than_a_thousand_nearest_are_refused(store: EntityStore) -> None:
    """``offset + limit`` over 1,000 answers ``BAD_REQUEST``."""
    with pytest.raises(AtlasError) as refused:
        await EntityDiscoveryService(store).search_by_meaning(
            QuickSearchParameters(query="x", offset=900, limit=101), [1.0, 0.0]
        )

    assert refused.value.code is AtlasErrorCode.BAD_REQUEST


@pytest.mark.covers("aurelius_atlas_core.search_query.VectorQuery.num_candidates", rules=["SBM-02"])
def test__the_candidates_are_ten_per_entity_asked_between_100_and_10000() -> None:
    """Elasticsearch's HNSW search looks wider than it answers."""
    assert VectorQuery((1.0,), 5).num_candidates == 100
    assert VectorQuery((1.0,), 50).num_candidates == 500
    assert VectorQuery((1.0,), 1_000).num_candidates == 10_000


@pytest.mark.covers("aurelius_atlas_core.testing.memory.MemoryEntityDocuments.search", rules=["SBM-02"])
async def test__an_entity_without_an_embedding_is_never_among_the_nearest(store: EntityStore) -> None:
    """The nearest are of the entities with an embedding."""
    hits = await store.search(SearchQuery(type_names=None, vector=VectorQuery((1.0, 0.0), 100)))

    assert {entity.guid for entity in hits.entities} == set(VECTORS)
