"""The OpenAPI document the route declares (AUX-06, DD-559).

The route answers through a ``Response`` built from the client library's model, so
FastAPI cannot infer the answer from the return alone; the route states its model
with ``response_model``, which documents the shape without touching the bytes
(CL-50). These checks keep a route from being added without its declaration: an
answer whose JSON schema says nothing, or a ``$ref`` to a model that never entered
the document.
"""

import pytest
from fastapi import FastAPI

JSON_MEDIA = "application/json"


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


@pytest.mark.covers("aurelius_atlas_lineage_model.routes.lineage.build_router", rules=["AUX-06"])
def test__every_answer_declares_its_model(app: FastAPI) -> None:
    """No JSON answer saying nothing, no $ref left unresolved."""
    spec = app.openapi()

    assert spec["paths"], "the document holds no routes at all"
    assert _schemas_saying_nothing(spec) == []
    assert _dangling_refs(spec) == []


@pytest.mark.covers("aurelius_atlas_lineage_model.routes.lineage.build_router", rules=["AUX-06"])
def test__the_lineage_answer_names_the_client_model(app: FastAPI) -> None:
    """``GET /`` documents the 200 as the client library's ``ExtractionResponse`` and the 204 empty (LM-05, CL-20)."""
    spec = app.openapi()

    operation = spec["paths"]["/"]["get"]
    assert operation["responses"]["200"]["content"][JSON_MEDIA]["schema"] == {
        "$ref": "#/components/schemas/ExtractionResponse"
    }
    assert "content" not in operation["responses"]["204"]
    # The query keeps its shape rules: guid is UUID text, depth is at least 1 (LM-07).
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert parameters["guid"]["schema"]["format"] == "uuid"
    assert parameters["depth"]["schema"]["minimum"] == 1
    # A rejected query is the app's 400 with the Atlas error body (LM-07): FastAPI's
    # automatic 422 and its validation models leave the document (DD-559).
    assert "422" not in operation["responses"]
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    failure = operation["responses"]["400"]["content"][JSON_MEDIA]["schema"]
    assert failure["required"] == ["errorCode", "errorMessage"]
