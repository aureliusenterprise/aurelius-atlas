"""The semantic door: ``mode`` semantic and hybrid over the entity index (ASV-01..08).

Every test opens the door over a fake store whose entities carry hand-picked two-dimension embeddings, so
which are nearest is known, as in 11.4's tests: the query vector ``[1, 0]`` puts ``t`` nearest, ``c`` near
it, and ``n`` across. The route's own embeddings are the server's tests (DD-598); here the vector arrives
through the engine's argument.
"""

import asyncio
from typing import Any

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_embedding import source_hash
from aurelius_atlas_core.stored_entity import StoredEmbedding
from aurelius_atlas_core.view_search import ViewSearchEngine
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_store_es.testing.fake import FakeClient
from aurelius_atlas_typesystem.registry import TypeRegistry
from test__app_search_quality import m4i_types
from test__view_search import hold


@pytest.fixture
def m4i() -> TypeRegistry:
    """Atlas's and the data dictionary's types (ADR 058), the door's registry."""
    return asyncio.run(m4i_types()).registry


V = "aurelius_atlas_core.view_search"
X = f"{V}.ViewSearchEngine.search"

QUERY_VECTOR = [1.0, 0.0]
"""The query's embedding: nearest is whichever entity points the same way (ASV-03)."""


def embedded(entity: Any, vector: list[float]) -> Any:  # noqa: ANN401 - a StoredEntity
    """``entity`` with a hand-picked embedding, as the indexer would have stored one."""
    return entity.model_copy(
        update={"embedding": StoredEmbedding(vector=vector, model="m", source_hash=source_hash(entity))}
    )


async def opened(m4i: TypeRegistry, *entities: Any) -> ViewSearchEngine:  # noqa: ANN401 - StoredEntity
    """The door over a fake store holding ``entities``, each already embedded."""
    documents = ElasticsearchEntityDocuments(FakeClient())  # type: ignore[arg-type]
    await documents.prepare()
    await documents.write([(entity, None) for entity in entities])
    return ViewSearchEngine(documents, m4i)


async def refused(door: ViewSearchEngine, body: object) -> list[str]:
    """The messages of the door's refusal of ``body``, in a meaning mode or any other (AVR-13, ASV-01)."""
    with pytest.raises(AtlasError) as raised:
        await door.search(body)
    assert raised.value.code is AtlasErrorCode.VIEW_REFUSED
    return raised.value.messages or [raised.value.message]


async def five(m4i: TypeRegistry) -> ViewSearchEngine:
    """The door over five embedded entities: ``t`` nearest, ``c`` near, ``m`` between, ``n`` and ``f`` across."""
    vectors: dict[str, tuple[str, list[float]]] = {
        "t": ("Asset", [1.0, 0.0]),
        "c": ("Asset", [0.9, 0.1]),
        "m": ("m4i_data_entity", [0.5, 0.5]),
        "n": ("m4i_data_entity", [0.0, 1.0]),
        "f": ("m4i_data_entity", [-1.0, 0.0]),
    }
    return await opened(
        m4i, *(embedded(hold(m4i, guid, type_name), vector) for guid, (type_name, vector) in vectors.items())
    )


@pytest.mark.covers(X, rules=["ASV-03"])
async def test__the_nearest_entities_come_first_among_those_the_filters_allow(m4i: TypeRegistry) -> None:
    """Nearest first among the filters' entities, the filters inside the kNN search (ASV-03, DD-441)."""
    door = await five(m4i)

    answer = await door.search({"query": "anything", "mode": "semantic", "limit": 5}, vector=QUERY_VECTOR)
    assert [card["guid"] for card in answer["cards"]] == ["t", "c", "m", "n", "f"]

    filtered = await door.search(
        {"query": "anything", "mode": "semantic", "filters": {"typeName": "Asset"}, "limit": 5},
        vector=QUERY_VECTOR,
    )
    assert [card["guid"] for card in filtered["cards"]] == ["t", "c"]


@pytest.mark.covers(X, rules=["ASV-03"])
async def test__a_page_further_down_is_taken_from_the_nearest(m4i: TypeRegistry) -> None:
    """``offset`` 1, ``limit`` 2: the second and third nearest of the k picked (ASV-03)."""
    door = await five(m4i)

    answer = await door.search({"query": "anything", "mode": "semantic", "offset": 1, "limit": 2}, vector=QUERY_VECTOR)
    assert [card["guid"] for card in answer["cards"]] == ["c", "m"]


@pytest.mark.covers(X, rules=["ASV-04"])
async def test__total_and_facets_count_the_nearest_hits_only(m4i: TypeRegistry) -> None:
    """``total`` counts the answer's hits, at most ``offset + limit``; the facets count over those (ASV-04)."""
    door = await five(m4i)

    answer = await door.search(
        {"query": "anything", "mode": "semantic", "limit": 2, "facets": ["typeName"]}, vector=QUERY_VECTOR
    )
    assert answer["total"] == 2
    assert answer["facets"]["typeName"] == [{"value": "Asset", "count": 2}]


@pytest.mark.covers(X, rules=["ASV-05"])
async def test__hybrid_scores_text_and_weighted_similarity_together(m4i: TypeRegistry) -> None:
    """The hybrid score is the text score plus the weight times the similarity; the weight turns the order (ASV-05)."""
    door = await opened(
        m4i,
        embedded(hold(m4i, "near", "Asset", name="Billing ledger"), [1.0, 0.0]),
        embedded(hold(m4i, "said", "Asset", name="Orders ledger"), [0.0, 1.0]),
    )

    asked = {"query": "orders", "mode": "hybrid", "limit": 5}
    weighted = await door.search(asked, vector=QUERY_VECTOR, weight=10.0)
    assert [card["guid"] for card in weighted["cards"]] == ["near", "said"]
    assert weighted["total"] == 2  # the nearest and the text's matches, together (ASV-05)

    unweighted = await door.search(asked, vector=QUERY_VECTOR, weight=0.0)
    assert [card["guid"] for card in unweighted["cards"]] == ["said", "near"]


@pytest.mark.covers(X, rules=["ASV-02"])
async def test__the_keyword_answer_is_the_same_with_and_without_the_key(m4i: TypeRegistry) -> None:
    """``mode`` keyword answers exactly as the door did before the key existed, embeddings and all (ASV-02)."""
    door = await five(m4i)

    before = await door.search({"query": "T", "facets": ["typeName"]})
    after = await door.search({"query": "T", "mode": "keyword", "facets": ["typeName"]})
    assert after == before
    assert sorted(card["guid"] for card in after["cards"]) == ["t"]


@pytest.mark.covers(f"{V}.parse", rules=["ASV-01"])
async def test__a_mode_outside_the_three_is_refused(m4i: TypeRegistry) -> None:
    """The door knows three modes and answers any other name with all three (ASV-01)."""
    door = await five(m4i)

    assert await refused(door, {"mode": "magic"}) == ["Mode must be one of: keyword, semantic, hybrid"]


@pytest.mark.covers(f"{V}.parse", rules=["ASV-06"])
async def test__a_meaning_mode_without_words_to_embed_is_refused(m4i: TypeRegistry) -> None:
    """A semantic or hybrid query must carry words; the keyword mode may still ask for everything (ASV-06)."""
    door = await five(m4i)

    assert await refused(door, {"mode": "semantic"}) == ["A semantic search needs a query to embed"]
    assert await refused(door, {"mode": "hybrid", "query": "  "}) == ["A hybrid search needs a query to embed"]


@pytest.mark.covers(f"{V}.parse", rules=["ASV-07"])
async def test__a_meaning_mode_sorts_by_score_descending_only(m4i: TypeRegistry) -> None:
    """The nearest order is the only order a meaning mode has (ASV-07)."""
    door = await five(m4i)

    assert await refused(door, {"mode": "semantic", "query": "x", "sort": {"createTime": "desc"}}) == [
        "A semantic search answers by score descending only"
    ]
    assert await refused(door, {"mode": "hybrid", "query": "x", "sort": {"_score": "asc"}}) == [
        "A hybrid search answers by score descending only"
    ]


@pytest.mark.covers(f"{V}.parse", rules=["ASV-08"])
async def test__the_nearest_window_stays_at_a_thousand(m4i: TypeRegistry) -> None:
    """``offset + limit`` over 1,000 leaves the kNN window and is refused, naming the mode (ASV-08, DD-441)."""
    door = await five(m4i)

    assert await refused(door, {"mode": "semantic", "query": "x", "offset": 901, "limit": 100}) == [
        "A semantic search answers at most 1000 entities: offset + limit is over it"
    ]
    at_the_edge = await door.search(
        {"query": "x", "mode": "semantic", "offset": 900, "limit": 100}, vector=QUERY_VECTOR
    )
    assert at_the_edge["total"] == 5
