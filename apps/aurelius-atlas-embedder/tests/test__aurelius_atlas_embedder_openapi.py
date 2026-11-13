"""The OpenAPI document the routes declare (AUX-06, DD-559).

The embedder's routes are FastAPI's own: the body and the answer are pydantic
models in the signatures, so the shapes enter the document by inference (EMB-01,
EMB-02, EMB-06). This check keeps a route from being added without its shape: a
write without a body, an answer whose JSON schema says nothing, or a ``$ref`` to a
model that never entered the document.
"""

import pytest
from fastapi import FastAPI

METHODS = ("post", "put", "patch")
JSON_MEDIA = "application/json"


def _writes_missing_body(spec: dict) -> list[str]:
    return [
        f"{method.upper()} {path}"
        for path, item in spec["paths"].items()
        for method, operation in item.items()
        if method in METHODS and "requestBody" not in operation
    ]


def _schemas_saying_nothing(spec: dict) -> list[str]:
    """A JSON answer whose schema is a bare object: no properties, no $ref, no key/value shape."""
    silent = []
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            for code, response in operation.get("responses", {}).items():
                schema = response.get("content", {}).get(JSON_MEDIA, {}).get("schema", {})
                bare = (
                    schema.get("type") == "object"
                    and "properties" not in schema
                    and "$ref" not in schema
                    and "additionalProperties" not in schema
                )
                if bare:
                    silent.append(f"{method.upper()} {path} -> {code}")
    return silent


def _dangling_refs(spec: dict) -> list[str]:
    names = set(spec.get("components", {}).get("schemas", {}))

    def names_within(node: object) -> list[str]:
        if isinstance(node, dict):
            found = [node["$ref"]] if "$ref" in node else []
            return found + [dangling for value in node.values() for dangling in names_within(value)]
        if isinstance(node, list):
            return [dangling for value in node for dangling in names_within(value)]
        return []

    return sorted({ref for ref in names_within(spec) if ref.split("/")[-1] not in names})


@pytest.mark.covers("aurelius_atlas_embedder.routes.embeddings.create_embeddings", rules=["AUX-06"])
def test__every_route_declares_its_body_and_answer(app: FastAPI) -> None:
    """No write without a body, no JSON answer saying nothing, no $ref left unresolved."""
    spec = app.openapi()

    assert spec["paths"], "the document holds no routes at all"
    assert _writes_missing_body(spec) == []
    assert _schemas_saying_nothing(spec) == []
    assert _dangling_refs(spec) == []


@pytest.mark.covers("aurelius_atlas_embedder.routes.embeddings.create_embeddings", rules=["AUX-06"])
def test__the_validation_failure_names_the_openai_error(app: FastAPI) -> None:
    """``POST /v1/embeddings`` documents its 422 as the OpenAI error body, not FastAPI's (EMB-05, DD-559)."""
    spec = app.openapi()

    responses = spec["paths"]["/v1/embeddings"]["post"]["responses"]
    assert responses["422"]["content"][JSON_MEDIA]["schema"] == {"$ref": "#/components/schemas/ErrorResponse"}
    assert responses["404"]["content"][JSON_MEDIA]["schema"] == {"$ref": "#/components/schemas/ErrorResponse"}
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    error = spec["components"]["schemas"]["ErrorResponse"]
    assert "error" in error["properties"]
