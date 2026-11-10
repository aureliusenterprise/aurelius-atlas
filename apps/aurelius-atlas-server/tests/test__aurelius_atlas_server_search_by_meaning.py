"""The searches by meaning through the server (SBM-01 to SBM-08), on the fake store with a mock embedder.

Three datasets get two-dimension embeddings, so the nearest are known: ``orders`` at ``[1, 0]``, ``order lines``
near it, ``customers`` across. The embedder answers the queries ``purchases`` and ``people`` with ``[1, 0]`` and
``[0, 1]``. The worker polls rarely, so no embedding but the test's own is written.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_embedding import source_hash
from aurelius_atlas_core.stored_entity import StoredEmbedding
from aurelius_atlas_model.errors import AtlasErrorCode
from aurelius_atlas_server import app as app_module
from aurelius_atlas_server.app import create_app
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_store_es.testing.fake import FakeClient
from conftest import BASE_URL

R = "aurelius_atlas_server.routes.search_by_meaning"
SEARCH = "/api/aurelius/v1/search/semantic"
TYPES = "/api/atlas/v2/types/typedefs"
VECTORS = {"orders": [1.0, 0.0], "order lines": [0.8, 0.2], "customers": [0.0, 1.0]}
QUERIES = {"purchases": [1.0, 0.0], "people": [0.0, 1.0]}
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


class Embedder:
    """A mock embeddings API: the query vectors above, or a failure; records each request's body."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.status = 200

    def __call__(self, request: httpx.Request) -> httpx.Response:
        """The answer to one request."""
        body = json.loads(request.content)
        self.requests.append(body)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "down"}})
        data = [{"index": i, "embedding": QUERIES.get(text, [0.5, 0.5])} for i, text in enumerate(body["input"])]
        return httpx.Response(200, json={"object": "list", "data": data})


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
    """A started server with embedding on, the three datasets embedded and a fourth not; their GUIDs by name."""
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
            names = [*VECTORS, "unembedded"]
            entities = [{"typeName": "m_dataset", "attributes": {"qualifiedName": f"{n}@x", "name": n}} for n in names]
            created = (await client.post("/api/atlas/v2/entity/bulk", json={"entities": entities})).json()
            by_name = {header["attributes"]["name"]: header["guid"] for header in created["mutatedEntities"]["CREATE"]}
            documents = ElasticsearchEntityDocuments(fake_es, embedding_dimensions=2)  # type: ignore[arg-type]
            for name, vector in VECTORS.items():
                found = (await documents.get([by_name[name]]))[by_name[name]]
                embedding = StoredEmbedding(vector=vector, model="m", source_hash=source_hash(found.entity))
                await documents.write([(found.entity.model_copy(update={"embedding": embedding}), found.version)])
            yield client, by_name


def names(response: httpx.Response) -> list[str]:
    """The names of a quick search answer's entities, in order."""
    return [entity["attributes"]["name"] for entity in response.json()["searchResults"].get("entities", [])]


@pytest.mark.covers(f"{R}.search_by_meaning", rules=["SBM-01", "SBM-02"])
async def test__a_semantic_search_answers_the_nearest_as_quick_search_answers(
    searching: tuple[httpx.AsyncClient, dict[str, str]], embedder: Embedder
) -> None:
    """The query embedded as a query; the nearest first; quick search's shape with its facets."""
    client, _ = searching

    response = await client.post(SEARCH, json={"query": "purchases", "typeName": "m_dataset", "limit": 2})

    assert response.status_code == 200
    assert names(response) == ["orders", "order lines"]
    body = response.json()
    assert body["searchResults"]["queryText"] == "purchases"
    assert body["searchResults"]["approximateCount"] == 2
    assert body["aggregationMetrics"]["__typeName"] == [{"name": "m_dataset", "count": 2}]
    assert embedder.requests[-1] == {
        "input": ["purchases"],
        "model": "intfloat/multilingual-e5-small",
        "input_type": "query",
    }


@pytest.mark.covers(f"{R}.search_by_meaning", rules=["SBM-03"])
async def test__a_hybrid_search_adds_the_text_s_matches(searching: tuple[httpx.AsyncClient, dict[str, str]]) -> None:
    """``customers``' text joins the nearest to ``people``; the unembedded dataset is found by its words."""
    client, _ = searching

    near = await client.post(SEARCH, json={"query": "people", "mode": "hybrid", "limit": 5})
    words = await client.post(SEARCH, json={"query": "unembedded", "mode": "hybrid", "limit": 5})
    semantic = await client.post(SEARCH, json={"query": "unembedded", "limit": 5})

    assert names(near)[0] == "customers"
    assert "unembedded" in names(words)
    assert "unembedded" not in names(semantic)


@pytest.mark.covers(f"{R}.validate_search_by_meaning", rules=["SBM-04"])
@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({}, "needs a query"),
        ({"query": "  "}, "needs a query"),
        ({"query": "x", "mode": "fuzzy"}, "mode must be one of"),
        ({"query": "x", "limit": -1}, "non-negative"),
        (
            {"query": "x", "entityFilters": {"attributeName": "name", "operator": "eq", "attributeValue": "a"}},
            "without Type",
        ),
        ({"query": "x", "typeName": "m_dataset", "sortBy": "name"}, "ordered by meaning"),
        ({"query": "x", "offset": 999, "limit": 2}, "may not exceed 1000"),
    ],
)
async def test__an_invalid_search_answers_400(
    searching: tuple[httpx.AsyncClient, dict[str, str]], body: dict[str, Any], message: str
) -> None:
    """In Atlas's error shape, naming what is wrong."""
    client, _ = searching

    response = await client.post(SEARCH, json=body)

    assert response.status_code == 400
    assert message in response.json()["errorMessage"]


@pytest.mark.covers(f"{R}.search_by_meaning", rules=["SBM-04"])
async def test__a_query_longer_than_4096_characters_is_refused(
    searching: tuple[httpx.AsyncClient, dict[str, str]],
) -> None:
    """As quick search refuses it."""
    client, _ = searching

    response = await client.post(SEARCH, json={"query": "x" * 4097})

    assert response.status_code == 400
    assert response.json()["errorCode"] == AtlasErrorCode.INVALID_QUERY_LENGTH.code


@pytest.mark.covers(f"{R}.similar_entities", rules=["SBM-05"])
async def test__the_entities_nearest_to_one_leave_it_out(searching: tuple[httpx.AsyncClient, dict[str, str]]) -> None:
    """``orders``' neighbours: ``order lines`` first, ``customers`` after; ``orders`` itself never."""
    client, guids = searching

    response = await client.get(f"/api/aurelius/v1/entity/guid/{guids['orders']}/similar", params={"limit": 5})

    assert response.status_code == 200
    assert names(response) == ["order lines", "customers"]


@pytest.mark.covers(f"{R}.similar_entities", rules=["SBM-05"])
async def test__an_unknown_or_unembedded_entity_has_no_neighbours(
    searching: tuple[httpx.AsyncClient, dict[str, str]],
) -> None:
    """404 for an unknown GUID, 409 for one not embedded yet, 400 for a negative page."""
    client, guids = searching
    similar = "/api/aurelius/v1/entity/guid/{}/similar"

    unknown = await client.get(similar.format("no-such-guid"))
    unembedded = await client.get(similar.format(guids["unembedded"]))
    negative = await client.get(similar.format(guids["orders"]), params={"offset": -1})

    assert (unknown.status_code, unknown.json()["errorCode"]) == (404, "ATLAS-404-00-005")
    assert (unembedded.status_code, unembedded.json()["errorCode"]) == (409, "AURELIUS-409-00-001")
    assert negative.status_code == 400


@pytest.mark.covers(f"{R}.search_by_meaning", rules=["SBM-06"])
async def test__an_embedder_that_fails_answers_503(
    searching: tuple[httpx.AsyncClient, dict[str, str]], embedder: Embedder
) -> None:
    """The query cannot be embedded: 503, not an empty answer."""
    client, _ = searching
    embedder.status = 500

    response = await client.post(SEARCH, json={"query": "purchases"})

    assert response.status_code == 503
    assert response.json()["errorCode"] == "AURELIUS-503-00-001"


@pytest.mark.covers(f"{R}.search_by_meaning", rules=["SBM-06"])
@pytest.mark.covers(f"{R}.similar_entities", rules=["SBM-06"])
async def test__without_embedding_both_answer_404(client: httpx.AsyncClient) -> None:
    """The default server has no embedding: ``AURELIUS-404-00-001``."""
    searched = await client.post(SEARCH, json={"query": "purchases"})
    similar = await client.get("/api/aurelius/v1/entity/guid/g/similar")

    assert (searched.status_code, searched.json()["errorCode"]) == (404, "AURELIUS-404-00-001")
    assert (similar.status_code, similar.json()["errorCode"]) == (404, "AURELIUS-404-00-001")


@pytest.mark.covers(f"{R}.search_by_meaning", rules=["SBM-07"])
async def test__a_search_by_meaning_needs_a_signed_in_user(searching: tuple[httpx.AsyncClient, dict[str, str]]) -> None:
    """Without a token: 401, as every API path."""
    client, _ = searching

    response = await client.post(SEARCH, json={"query": "purchases"}, headers={"authorization": ""})

    assert response.status_code == 401


@pytest.mark.covers(rules=["SBM-08"])
async def test__atlas_s_quick_search_answers_as_before(searching: tuple[httpx.AsyncClient, dict[str, str]]) -> None:
    """Quick search finds by words, untouched by the embeddings."""
    client, _ = searching

    response = await client.post("/api/atlas/v2/search/quick", json={"query": "customers", "typeName": "m_dataset"})

    assert response.status_code == 200
    assert names(response) == ["customers"]
