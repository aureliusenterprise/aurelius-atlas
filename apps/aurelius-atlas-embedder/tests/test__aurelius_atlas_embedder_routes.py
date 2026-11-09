"""Unit tests for the routes: the embeddings API, its refusals, the model list and the probes (EMB-01..07)."""

from typing import Any

import pytest
from aurelius_atlas_embedder.app import create_app
from aurelius_atlas_embedder.model import Model
from aurelius_atlas_embedder.settings import EmbedderSettings
from fakes import FakeTokenizer
from fastapi.testclient import TestClient

MODEL_ID = "intfloat/multilingual-e5-small"


def _embed(client: TestClient, body: dict[str, Any]) -> Any:  # noqa: ANN401 - JSON
    return client.post("/v1/embeddings", json=body)


@pytest.mark.covers("aurelius_atlas_embedder.routes.embeddings.create_embeddings", rules=["EMB-01", "EMB-02"])
def test__a_list_of_texts_gets_one_embedding_each_in_the_order_sent(client: TestClient, model: Model) -> None:
    """The answer is OpenAI's list shape; each embedding is the model's vector of the text at its index."""
    texts = ["first", "second text", "3"]

    response = _embed(client, {"input": texts, "model": MODEL_ID})

    assert response.status_code == 200
    body = response.json()
    expected = model.embed(texts)
    assert body["object"] == "list"
    assert body["model"] == MODEL_ID
    assert [entry["index"] for entry in body["data"]] == [0, 1, 2]
    assert {entry["object"] for entry in body["data"]} == {"embedding"}
    vectors = [entry["embedding"] for entry in body["data"]]
    for answered, own in zip(vectors, expected.vectors, strict=True):
        assert answered == pytest.approx(own)
    assert len({tuple(vector) for vector in vectors}) == len(texts)
    assert body["usage"] == {"prompt_tokens": expected.tokens, "total_tokens": expected.tokens}


@pytest.mark.covers("aurelius_atlas_embedder.routes.embeddings.create_embeddings", rules=["EMB-01"])
def test__a_single_text_and_no_model_are_accepted(client: TestClient) -> None:
    """``input`` may be one text; ``model`` may be left out."""
    response = _embed(client, {"input": "one text"})

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.covers("aurelius_atlas_embedder.routes.embeddings.create_embeddings", rules=["EMB-01", "EMB-03"])
@pytest.mark.parametrize(
    ("input_type", "prefix"), [(None, "passage: "), ("passage", "passage: "), ("query", "query: ")]
)
def test__the_input_type_sets_the_prefix(client: TestClient, model: Model, input_type: str | None, prefix: str) -> None:
    """Passages by default; ``input_type: query`` for a search."""
    body: dict[str, Any] = {"input": ["text"]} | ({"input_type": input_type} if input_type else {})

    assert _embed(client, body).status_code == 200

    tokenizer = model._tokenizer  # noqa: SLF001 - the fake records its input
    assert isinstance(tokenizer, FakeTokenizer)
    assert tokenizer.seen[-1] == [f"{prefix}text"]


@pytest.mark.covers("aurelius_atlas_embedder.errors.install_error_handlers", rules=["EMB-05"])
@pytest.mark.parametrize(
    ("body", "param"),
    [
        ({}, "input"),
        ({"input": []}, "input"),
        ({"input": ["x"] * 257}, "input"),
        ({"input": ""}, "input"),
        ({"input": ["ok", ""]}, "input"),
        ({"input": "x" * 32_001}, "input"),
        ({"input": "ok", "encoding_format": "base64"}, "encoding_format"),
        ({"input": "ok", "input_type": "document"}, "input_type"),
    ],
)
def test__an_invalid_request_answers_422_in_openai_s_error_shape(
    client: TestClient, body: dict[str, Any], param: str
) -> None:
    """No text, too many, an empty or too long one, or an unknown format or type: 422, naming the field."""
    response = _embed(client, body)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["type"] == "invalid_request_error"
    assert error["param"] == param
    assert error["message"]


@pytest.mark.covers("aurelius_atlas_embedder.routes.embeddings.create_embeddings", rules=["EMB-01", "EMB-05"])
def test__256_texts_of_32000_characters_are_the_limit_and_accepted(client: TestClient) -> None:
    """The limits are inclusive."""
    assert _embed(client, {"input": ["x"] * 256}).status_code == 200
    assert _embed(client, {"input": "x" * 32_000}).status_code == 200


@pytest.mark.covers("aurelius_atlas_embedder.routes.embeddings.create_embeddings", rules=["EMB-05"])
def test__another_model_answers_404(client: TestClient) -> None:
    """A ``model`` the embedder does not serve: 404 ``model_not_found``."""
    response = _embed(client, {"input": "x", "model": "text-embedding-3-small"})

    assert response.status_code == 404
    assert response.json()["error"] == {
        "message": f"The model 'text-embedding-3-small' does not exist; this embedder serves {MODEL_ID!r}",
        "type": "invalid_request_error",
        "param": "model",
        "code": "model_not_found",
    }


@pytest.mark.covers("aurelius_atlas_embedder.routes.embeddings.list_models", rules=["EMB-06"])
def test__the_model_list_names_the_model_its_dimensions_and_revision(client: TestClient) -> None:
    """One model, with the dimensions its vectors have."""
    response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json() == {
        "object": "list",
        "data": [{"id": MODEL_ID, "object": "model", "owned_by": "aurelius-atlas", "dimensions": 4, "revision": "rev"}],
    }


@pytest.mark.covers("aurelius_atlas_embedder.routes.health.liveness", rules=["EMB-07"])
@pytest.mark.covers("aurelius_atlas_embedder.routes.health.readiness", rules=["EMB-07"])
def test__the_probes_answer_204_once_the_model_has_loaded(client: TestClient) -> None:
    """Both probes, without credentials."""
    assert client.get("/liveness").status_code == 204
    assert client.get("/readiness").status_code == 204


@pytest.mark.covers("aurelius_atlas_embedder.routes.health.readiness", rules=["EMB-07"])
@pytest.mark.covers("aurelius_atlas_embedder.routes.embeddings.ready_model", rules=["EMB-07"])
def test__before_the_model_loads_readiness_and_the_api_answer_503(settings: EmbedderSettings, model: Model) -> None:
    """An app that has not started holds no model: liveness 204, readiness and the API 503."""
    client = TestClient(create_app(settings, loader=lambda _settings: model))  # not started: no lifespan

    assert client.get("/liveness").status_code == 204
    assert client.get("/readiness").status_code == 503
    response = _embed(client, {"input": "x"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_not_ready"
    assert client.get("/v1/models").status_code == 503
