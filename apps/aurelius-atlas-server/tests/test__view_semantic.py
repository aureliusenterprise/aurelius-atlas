"""The semantic door through the server (ASV-01, ASV-03, ASV-05, ASV-09), on the fake store with a mock embedder.

The door's three modes over HTTP: the mock embedder answers each query's embedding, so the nearest are known
(DD-598 — the route's errors and loop live here, the real kNN in the core's e2e). The worker polls rarely, so
no embedding but the test's own is written.
"""

from collections.abc import AsyncIterator
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_embedding import source_hash
from aurelius_atlas_core.stored_entity import StoredEmbedding
from aurelius_atlas_server import app as app_module
from aurelius_atlas_server.app import create_app
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_store_es.testing.fake import FakeClient
from conftest import BASE_URL
from test__aurelius_atlas_server_search_by_meaning import Embedder

R = "aurelius_atlas_server.routes.view_search"
SEARCH = "/api/aurelius/v1/search"
TYPES = "/api/atlas/v2/types/typedefs"
VECTORS = {"orders": [1.0, 0.0], "order lines": [0.8, 0.2], "customers": [0.0, 1.0]}
DATASET = {
    "entityDefs": [
        {
            "name": "m_dataset",
            "superTypes": [],
            "attributeDefs": [
                {
                    "name": "qualifiedName",
                    "typeName": "string",
                    "isOptional": False,
                    "cardinality": "SINGLE",
                    "isUnique": True,
                },
                {"name": "name", "typeName": "string", "isOptional": True, "cardinality": "SINGLE"},
            ],
        }
    ]
}


@pytest.fixture
def embedder() -> Embedder:
    """The mock embeddings API."""
    return Embedder()


@pytest.fixture
async def searching(
    settings: ServerSettings,
    fake_es: FakeClient,
    embedder: Embedder,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, dict[str, str]]]:
    """A started server with embedding on and the three datasets embedded; their GUIDs by name."""
    monkeypatch.setattr(
        app_module, "embedding_http", lambda _ca: httpx.AsyncClient(transport=httpx.MockTransport(embedder))
    )
    configured = settings.model_copy(
        update={"embedding_url": "https://embedder:21004", "embedding_dimensions": 2, "embedding_poll_seconds": 3600}
    )
    app = create_app(configured)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, headers=auth_headers) as client:
            assert (await client.post(TYPES, json=DATASET)).status_code == 200
            entities = [
                {"typeName": "m_dataset", "attributes": {"qualifiedName": f"{n}@x", "name": n}} for n in VECTORS
            ]
            created = (await client.post("/api/atlas/v2/entity/bulk", json={"entities": entities})).json()
            by_name = {header["attributes"]["name"]: header["guid"] for header in created["mutatedEntities"]["CREATE"]}
            documents = ElasticsearchEntityDocuments(fake_es, embedding_dimensions=2)  # type: ignore[arg-type]
            for name, vector in VECTORS.items():
                found = (await documents.get([by_name[name]]))[by_name[name]]
                embedding = StoredEmbedding(vector=vector, model="m", source_hash=source_hash(found.entity))
                await documents.write([(found.entity.model_copy(update={"embedding": embedding}), found.version)])
            yield client, by_name


def guides(answer: dict[str, Any]) -> list[str]:
    """The GUIDs of a door answer's cards, in order."""
    return [card["guid"] for card in answer["cards"]]


@pytest.mark.covers(f"{R}.search", rules=["ASV-03"])
async def test__the_semantic_mode_answers_the_nearest(searching: tuple[httpx.AsyncClient, dict[str, str]]) -> None:
    """The query is embedded as a query and the cards come nearest first (ASV-03, DD-443)."""
    client, by_name = searching

    answer = (await client.post(SEARCH, json={"query": "purchases", "mode": "semantic", "limit": 3})).json()
    assert guides(answer) == [by_name["orders"], by_name["order lines"], by_name["customers"]]
    assert answer["total"] == 3
    # The shared mock answers "people" with [0, 1] (SBM-01's fixture): the entity across is nearest.
    across = await client.post(SEARCH, json={"query": "people", "mode": "semantic", "limit": 1})
    assert guides(across.json()) == [by_name["customers"]]


@pytest.mark.covers(f"{R}.search", rules=["ASV-05"])
async def test__the_hybrid_mode_scores_text_and_similarity_together(
    searching: tuple[httpx.AsyncClient, dict[str, str]],
) -> None:
    """A worded entity no nearer comes first when the text outweighs the similarity (ASV-05, DD-442)."""
    client, by_name = searching  # the configured weight of 10 turns the order of the [0.8, 0.2] and the word hit

    answer = (await client.post(SEARCH, json={"query": "customers", "mode": "hybrid", "limit": 3})).json()
    assert guides(answer)[0] == by_name["customers"]  # [0, 1] scores no similarity to [0.5, 0.5] but holds the word
    assert answer["total"] == 3  # the text's matches and the nearest, together


@pytest.mark.covers(f"{R}.search", rules=["ASV-09"])
async def test__embedding_off_answers_404_for_a_meaning_mode_only(
    settings: ServerSettings, fake_es: FakeClient, auth_headers: dict[str, str]
) -> None:
    """Without an embedder the meaning modes answer 404; the keyword door stays open (ASV-09)."""
    _ = fake_es
    app = create_app(settings.model_copy(update={"embedding_url": None}))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, headers=auth_headers) as client:
            assert (await client.post(TYPES, json=DATASET)).status_code == 200
            refused = await client.post(SEARCH, json={"query": "purchases", "mode": "semantic"})
            assert refused.status_code == 404
            assert refused.json()["errorCode"] == "AURELIUS-404-00-001"
            assert (await client.post(SEARCH, json={"query": "purchases"})).status_code == 200


@pytest.mark.covers(f"{R}.search", rules=["ASV-09"])
async def test__an_unreachable_embedder_answers_503(
    searching: tuple[httpx.AsyncClient, dict[str, str]], embedder: Embedder
) -> None:
    """When the embedder refuses, the door answers 503 in the Aurelius shape (ASV-09, SBM-06)."""
    client, _ = searching
    embedder.status = 503

    answer = await client.post(SEARCH, json={"query": "purchases", "mode": "semantic"})
    assert answer.status_code == 503
    assert answer.json()["errorCode"] == "AURELIUS-503-00-001"


@pytest.mark.covers(f"{R}.search", rules=["ASV-06", "ASV-09"])
async def test__a_meaning_mode_without_a_query_is_refused_before_the_embedder_is_asked(
    searching: tuple[httpx.AsyncClient, dict[str, str]], embedder: Embedder
) -> None:
    """The door refuses an empty query itself; the embedder sees no request for it (ASV-06)."""
    client, _ = searching

    refused = await client.post(SEARCH, json={"mode": "semantic"})
    assert refused.status_code == 400
    assert refused.json()["errorCode"] == "AURELIUS-400-00-001"
    assert embedder.requests == []
