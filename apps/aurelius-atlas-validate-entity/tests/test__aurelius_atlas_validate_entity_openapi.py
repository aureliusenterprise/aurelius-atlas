"""The OpenAPI document the route declares (AUX-06, DD-558).

The route answers with the client library's ``ValidationResponse`` model, and its
body parses as the app's own ``DraftEntity`` (DD-558), so FastAPI infers both
shapes from the signatures. These checks keep a route from being added without its
declaration: a write without a body, an answer whose JSON schema says nothing, a
``$ref`` to a model that never entered the document, or a body whose shape does not
name the model the handler reads.
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


@pytest.mark.covers("aurelius_atlas_validate_entity.routes.validate.build_router", rules=["AUX-06"])
def test__every_route_declares_its_body_and_answer(app: FastAPI) -> None:
    """No write without a body, no JSON answer saying nothing, no $ref left unresolved."""
    spec = app.openapi()

    assert spec["paths"], "the document holds no routes at all"
    assert _writes_missing_body(spec) == []
    assert _schemas_saying_nothing(spec) == []
    assert _dangling_refs(spec) == []


@pytest.mark.covers("aurelius_atlas_validate_entity.routes.validate.build_router", rules=["AUX-06"])
def test__the_body_and_answer_name_their_models(app: FastAPI) -> None:
    """``POST /`` names the draft ``DraftEntity`` and the answer ``ValidationResponse`` (VEV-01/02, DD-558)."""
    spec = app.openapi()

    operation = spec["paths"]["/"]["post"]
    body = operation["requestBody"]["content"][JSON_MEDIA]["schema"]
    assert body == {"$ref": "#/components/schemas/DraftEntity"}
    assert operation["responses"]["200"]["content"][JSON_MEDIA]["schema"] == {
        "$ref": "#/components/schemas/ValidationResponse"
    }
    draft = spec["components"]["schemas"]["DraftEntity"]
    assert "attributes" in draft["properties"]
    assert "attributes" in draft["required"]
    # A draft the app will not read is its 400 with the Atlas error body (VEV-01): FastAPI's
    # automatic 422 and its validation models leave the document (DD-558, DD-559).
    assert "422" not in operation["responses"]
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    failure = operation["responses"]["400"]["content"][JSON_MEDIA]["schema"]
    assert failure["required"] == ["errorCode", "errorMessage"]
