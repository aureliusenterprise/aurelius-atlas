"""Embedding in the server: its settings, the embeddings API's client, the worker, and the wiring (VEC-07 to
VEC-09), on the fake store and a mock embedder.
"""  # noqa: D205 - one sentence

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import certifi
import httpx2 as httpx
import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_embedding_indexer import EntityEmbeddingIndexer
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_server import app as app_module
from aurelius_atlas_server import tenant_workers
from aurelius_atlas_server.app import create_app
from aurelius_atlas_server.embedding import EmbeddingClient, EmbeddingError, EmbeddingWorker, embedding_http
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_store_es.testing.fake import FakeClient

C = "aurelius_atlas_server.embedding.EmbeddingClient"
W = "aurelius_atlas_server.embedding.EmbeddingWorker"
URL = "https://embedder:21004"
MODEL = "intfloat/multilingual-e5-small"


def embedder(requests: list[dict[str, Any]], *, dimensions: int = 3, extra: int = 0) -> httpx.MockTransport:
    """An embeddings API answering ``[i, 1, …]`` per text, its entries reversed; records each request's body."""

    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append({"url": str(request.url), **body})
        data = [
            {"object": "embedding", "index": index, "embedding": [float(index)] + [1.0] * (dimensions - 1)}
            for index in range(len(body["input"]) + extra)
        ]
        return httpx.Response(200, json={"object": "list", "data": list(reversed(data)), "model": body["model"]})

    return httpx.MockTransport(answer)


@pytest.mark.covers(f"{C}.embed", rules=["VEC-09"])
async def test__the_client_posts_passages_and_answers_the_vectors_in_the_texts_order() -> None:
    """The texts, the model and ``input_type: passage`` to ``/v1/embeddings``; vectors by their index."""
    requests: list[dict[str, Any]] = []
    async with httpx.AsyncClient(transport=embedder(requests)) as http:
        client = EmbeddingClient(f"{URL}/", MODEL, 3, http=http)

        vectors = await client.embed(["a", "b"])

    assert client.model == MODEL
    assert requests == [{"url": f"{URL}/v1/embeddings", "input": ["a", "b"], "model": MODEL, "input_type": "passage"}]
    assert vectors == [[0.0, 1.0, 1.0], [1.0, 1.0, 1.0]]


@pytest.mark.covers(f"{C}.embed", rules=["VEC-09"])
@pytest.mark.parametrize(("dimensions", "extra", "reason"), [(3, 1, "2 embeddings for 1 texts"), (4, 0, "dimensions")])
async def test__the_client_refuses_another_count_or_other_dimensions(dimensions: int, extra: int, reason: str) -> None:
    """One vector per text, each of the configured dimensions, or the round fails."""
    async with httpx.AsyncClient(transport=embedder([], dimensions=dimensions, extra=extra)) as http:
        with pytest.raises(EmbeddingError, match=reason):
            await EmbeddingClient(URL, MODEL, 3, http=http).embed(["a"])


@pytest.mark.covers(f"{C}.embed", rules=["VEC-09"])
async def test__a_refusal_of_the_embedder_fails_the_call() -> None:
    """An HTTP error is raised, for the worker to log."""
    transport = httpx.MockTransport(lambda _request: httpx.Response(503, json={"error": {"message": "loading"}}))
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(httpx.HTTPStatusError):
            await EmbeddingClient(URL, MODEL, 3, http=http).embed(["a"])


@pytest.mark.covers("aurelius_atlas_server.embedding.embedding_http", rules=["VEC-08"])
async def test__the_http_client_verifies_against_the_configured_ca() -> None:
    """A client with a CA file, here certifi's bundle, or with the system's trust store."""
    for http in (embedding_http(Path(certifi.where())), embedding_http(None)):
        assert isinstance(http, httpx.AsyncClient)
        await http.aclose()


class Indexer:
    """An indexer whose rounds answer ``results`` in turn; an exception is raised."""

    def __init__(self, *results: int | Exception) -> None:
        self.results = list(results)
        self.rounds = 0

    async def run_once(self) -> int:
        """The next result."""
        self.rounds += 1
        result = self.results.pop(0) if self.results else 0
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.covers(f"{W}.run_once", rules=["VEC-07"])
async def test__a_failed_round_is_logged_and_the_next_one_tries_again(caplog: pytest.LogCaptureFixture) -> None:
    """The embedder down: logged, 0 written; the next round embeds."""
    indexer = Indexer(RuntimeError("embedder down"), 3)
    worker = EmbeddingWorker(indexer, poll_seconds=60)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="aurelius-atlas-server"):
        assert await worker.run_once() == 0
        assert await worker.run_once() == 3

    assert "Embedding the entities failed" in caplog.text
    assert "Embedded 3 entities" in caplog.text


@pytest.mark.covers(f"{W}.start", rules=["VEC-07"])
@pytest.mark.covers(f"{W}.stop", rules=["VEC-07"])
async def test__the_worker_runs_a_round_at_start_and_then_every_poll_interval() -> None:
    """Started, it embeds at once and again after each interval; stopped, it closes its HTTP client."""
    indexer = Indexer(1, 0, 0)
    http = httpx.AsyncClient()
    worker = EmbeddingWorker(indexer, poll_seconds=0.01, http=http)  # type: ignore[arg-type]

    worker.start()
    for _ in range(100):
        if indexer.rounds >= 3:
            break
        await asyncio.sleep(0.01)
    await worker.stop()
    await worker.stop()  # stopping twice is harmless

    assert indexer.rounds >= 3
    assert http.is_closed


@pytest.mark.covers(rules=["VEC-08"])
def test__embedding_is_off_by_default_and_configured_by_its_settings(settings: ServerSettings) -> None:
    """No URL, no embedding; the defaults are the embedder's model and dimensions."""
    configured = ServerSettings.model_validate(
        settings.model_dump() | {"embedding_url": URL, "embedding_batch_size": 16}
    )

    assert settings.embedding_url is None
    assert (settings.embedding_model, settings.embedding_dimensions) == (MODEL, 384)
    assert (settings.embedding_batch_size, settings.embedding_poll_seconds) == (32, 10.0)
    assert str(configured.embedding_url).rstrip("/") == URL
    assert configured.embedding_batch_size == 16


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["VEC-08"])
async def test__without_embedding_the_server_maps_no_vector(settings: ServerSettings, fake_es: FakeClient) -> None:
    """The entity index as before: no vector mapped, no setting changed (ADR 059, R6)."""
    app = create_app(settings)

    async with app.router.lifespan_context(app):
        pass

    [entities] = [name for name in fake_es.index_settings if name.startswith("aurelius-atlas-entities-")]
    assert "index.mapping.exclude_source_vectors" not in fake_es.index_settings[entities]
    assert "embedding" not in fake_es.index_mappings[entities]["properties"]


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["VEC-03", "VEC-07", "VEC-08"])
async def test__with_embedding_the_server_maps_the_vector_and_embeds_the_entities_in_the_background(
    settings: ServerSettings, fake_es: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The entity index keeps its sources and maps the vector; an entity written is embedded by the worker."""
    requests: list[dict[str, Any]] = []
    monkeypatch.setattr(app_module, "embedding_http", lambda _ca: httpx.AsyncClient(transport=embedder(requests)))
    configured = settings.model_copy(
        update={"embedding_url": URL, "embedding_dimensions": 3, "embedding_poll_seconds": 0.01}
    )
    app = create_app(configured)

    async with app.router.lifespan_context(app):
        documents = ElasticsearchEntityDocuments(fake_es, embedding_dimensions=3)  # type: ignore[arg-type]
        await documents.write(
            [(StoredEntity(guid="e", type_name="m4i_data_entity", attributes={"Asset.name": "Customer"}), None)]
        )
        for _ in range(200):
            if (await documents.get(["e"]))["e"].entity.embedding is not None:
                break
            await asyncio.sleep(0.01)
        stored = (await documents.get(["e"]))["e"].entity

    [entities] = [name for name in fake_es.index_settings if name.startswith("aurelius-atlas-entities-")]
    assert fake_es.index_settings[entities]["index.mapping.exclude_source_vectors"] is False
    assert fake_es.index_mappings[entities]["properties"]["embedding"]["properties"]["vector"]["dims"] == 3
    assert stored.embedding is not None
    assert stored.embedding.model == MODEL
    assert {"input": ["m4i_data_entity\nCustomer"], "model": MODEL, "input_type": "passage"}.items() <= requests[
        -1
    ].items()


@pytest.mark.parametrize("app_search", [True, False])
@pytest.mark.usefixtures("fake_es")
@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["EMC-04"])
async def test__the_embedding_indexer_waits_for_documents_while_the_app_search_worker_runs(
    settings: ServerSettings, monkeypatch: pytest.MonkeyPatch, *, app_search: bool
) -> None:
    """The indexer is told to wait exactly when ``APP_SEARCH_ENABLED`` is on (DD-540)."""
    made: list[EntityEmbeddingIndexer] = []

    class Recorded(EntityEmbeddingIndexer):
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401 - passed through
            super().__init__(*args, **kwargs)
            made.append(self)

    monkeypatch.setattr(tenant_workers, "EntityEmbeddingIndexer", Recorded)
    monkeypatch.setattr(app_module, "embedding_http", lambda _ca: httpx.AsyncClient(transport=embedder([])))
    configured = settings.model_copy(
        update={"embedding_url": URL, "embedding_dimensions": 3, "app_search_enabled": app_search}
    )
    app = create_app(configured)

    async with app.router.lifespan_context(app):
        pass

    [indexer] = made
    assert indexer._wait_for_documents is app_search  # noqa: SLF001 - the wiring under test
