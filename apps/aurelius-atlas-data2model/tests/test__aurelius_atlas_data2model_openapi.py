"""The OpenAPI document every route declares (AUX-06, DD-559).

The routes answer through a ``Response`` built from the client library's model, so
FastAPI cannot infer the answer from the return alone; each route states its model
with ``response_model``, which documents the shape without touching the bytes
(CL-50). These checks keep a route from being added without its declaration: a
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


@pytest.mark.covers("aurelius_atlas_data2model.routes.extract.build_router", rules=["AUX-06"])
def test__every_route_declares_its_body_and_answer(app: FastAPI) -> None:
    """No write without a body, no JSON answer saying nothing, no $ref left unresolved."""
    spec = app.openapi()

    assert spec["paths"], "the document holds no routes at all"
    assert _writes_missing_body(spec) == []
    assert _schemas_saying_nothing(spec) == []
    assert _dangling_refs(spec) == []


@pytest.mark.covers("aurelius_atlas_data2model.routes.extract.build_router", rules=["AUX-06"])
def test__the_extract_answer_names_the_client_model(app: FastAPI) -> None:
    """``POST /extract`` documents the client library's ``ExtractionResponse`` (CL-20, CL-50)."""
    spec = app.openapi()

    responses = spec["paths"]["/extract"]["post"]["responses"]
    schema = responses["200"]["content"][JSON_MEDIA]["schema"]
    assert schema == {"$ref": "#/components/schemas/ExtractionResponse"}
    assert "ExtractionRequest" in spec["components"]["schemas"]
    # The app answers a bad body 400 with the Atlas error body (DTM-11, DV-79): FastAPI's
    # automatic 422 and its validation models leave the document (DD-559).
    assert "422" not in responses
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    failure = responses["400"]["content"][JSON_MEDIA]["schema"]
    assert failure["required"] == ["errorCode", "errorMessage"]
