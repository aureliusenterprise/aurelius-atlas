"""The embedder image with its real model, over TLS (EMB-01 to EMB-07, EMB-10)."""

import math
from typing import Any

import httpx2 as httpx
import pytest
from testcontainers.compose import DockerCompose

MODEL_ID = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
DIMENSIONS = 384

PINNED = {
    "model.onnx": "ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665",
    "tokenizer.json": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
    "MODEL_CARD.md": "0038de97aee16258cecbad7ffda4b4febd6953e747a00e0ddbc8e6ed241e9c1c",
}
"""The SHA-256 of each file the image fetches (EMB-10)."""


def _vectors(client: httpx.Client, texts: list[str], input_type: str = "passage") -> list[list[float]]:
    response = client.post("/v1/embeddings", json={"input": texts, "model": MODEL_ID, "input_type": input_type})
    assert response.status_code == 200, response.text
    return [entry["embedding"] for entry in response.json()["data"]]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


@pytest.mark.covers(rules=["EMB-01", "EMB-02", "EMB-03"])
def test__texts_get_384_dimension_embeddings_of_length_1_in_their_order(client: httpx.Client) -> None:
    """OpenAI's answer shape, one vector per text in order, each of length 1, and the tokens read."""
    texts = ["customer table", "klantentabel", "orders per day"]

    response = client.post("/v1/embeddings", json={"input": texts})

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "list"
    assert body["model"] == MODEL_ID
    assert [entry["index"] for entry in body["data"]] == [0, 1, 2]
    for entry in body["data"]:
        assert entry["object"] == "embedding"
        assert len(entry["embedding"]) == DIMENSIONS
        assert math.fsum(value * value for value in entry["embedding"]) == pytest.approx(1.0, abs=1e-5)
    assert body["usage"]["prompt_tokens"] == body["usage"]["total_tokens"] > 0
    assert len({tuple(entry["embedding"]) for entry in body["data"]}) == len(texts)


@pytest.mark.covers(rules=["EMB-03"])
def test__a_query_ranks_texts_of_its_meaning_above_an_unrelated_one_also_in_dutch(client: httpx.Client) -> None:
    """The model's purpose: "customer address" is nearer an English and a Dutch paraphrase than sensor readings."""
    [query] = _vectors(client, ["customer address"], "query")
    english, dutch, unrelated = _vectors(
        client, ["client location data", "klantadres en woonplaats", "sensor temperature readings per minute"]
    )

    assert _cosine(query, english) > _cosine(query, unrelated)
    assert _cosine(query, dutch) > _cosine(query, unrelated)


@pytest.mark.covers(rules=["EMB-03"])
def test__a_query_and_a_passage_of_one_text_differ(client: httpx.Client) -> None:
    """``input_type`` reaches the model: the prefixes give one text two embeddings."""
    [as_query] = _vectors(client, ["customer address"], "query")
    [as_passage] = _vectors(client, ["customer address"], "passage")

    assert as_query != as_passage


@pytest.mark.covers(rules=["EMB-04"])
def test__a_text_s_embedding_does_not_depend_on_its_batch(client: httpx.Client) -> None:
    """Alone, or padded beside a long text, a text gets the same vector."""
    [alone] = _vectors(client, ["client location data"])
    beside, _ = _vectors(client, ["client location data", "a much longer description of a dataset " * 20])

    assert beside == pytest.approx(alone, abs=1e-5)


@pytest.mark.covers(rules=["EMB-05"])
@pytest.mark.parametrize(
    ("body", "status", "param"),
    [
        ({"input": []}, 422, "input"),
        ({"input": ["x"] * 257}, 422, "input"),
        ({"input": ""}, 422, "input"),
        ({"input": "x", "encoding_format": "base64"}, 422, "encoding_format"),
        ({"input": "x", "model": "text-embedding-3-small"}, 404, "model"),
    ],
)
def test__refusals_answer_in_openai_s_error_shape(
    client: httpx.Client, body: dict[str, Any], status: int, param: str
) -> None:
    """Invalid requests 422, another model 404, each naming the field at fault."""
    response = client.post("/v1/embeddings", json=body)

    assert response.status_code == status
    assert response.json()["error"]["type"] == "invalid_request_error"
    assert response.json()["error"]["param"] == param


@pytest.mark.covers(rules=["EMB-06"])
def test__the_model_list_names_the_shipped_model(client: httpx.Client) -> None:
    """The pinned model, its revision and its 384 dimensions."""
    response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json()["data"] == [
        {
            "id": MODEL_ID,
            "object": "model",
            "owned_by": "aurelius-atlas",
            "dimensions": DIMENSIONS,
            "revision": REVISION,
        }
    ]


@pytest.mark.covers(rules=["EMB-07"])
def test__the_probes_answer_204_without_credentials(client: httpx.Client) -> None:
    """Liveness and readiness, over TLS."""
    assert client.get("/liveness").status_code == 204
    assert client.get("/readiness").status_code == 204


@pytest.mark.covers(rules=["EMB-10"])
def test__the_image_holds_the_pinned_model_files(compose: DockerCompose) -> None:
    """Each file the image fetched has its pinned SHA-256; the hardened image has Python but no shell."""
    script = (
        "import hashlib, pathlib; "
        "files = sorted(pathlib.Path('/model').iterdir()); "
        "print(*(f'{p.name} {hashlib.sha256(p.read_bytes()).hexdigest()}' for p in files), sep='\\n')"
    )
    output, _, exit_code = compose.exec_in_container(["python", "-c", script], service_name="aurelius-atlas-embedder")

    assert exit_code == 0
    assert dict(line.split(" ") for line in output.strip().splitlines()) == PINNED
