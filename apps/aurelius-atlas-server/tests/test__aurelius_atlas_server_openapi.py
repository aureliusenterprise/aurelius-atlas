"""The OpenAPI document every route declares (SRV-08, DD-556).

The routes read their bodies through a dependency and answer through ``AtlasJSONResponse``, so
FastAPI cannot infer either shape; each route states its own (``openapi.py``). These checks keep a
route from being added without its declaration: a write without a body, an answer whose JSON schema
says nothing, or a ``$ref`` to a model that never entered the document.
"""

import pytest
from aurelius_atlas_server.openapi import install
from aurelius_atlas_server.routes import GLOSSARY
from fastapi import FastAPI

METHODS = ("post", "put", "patch")
JSON_MEDIA = "application/json; charset=UTF-8"


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


@pytest.mark.covers("aurelius_atlas_server.openapi.install", rules=["SRV-08"])
def test__every_route_declares_its_body_and_answer(app: FastAPI) -> None:
    """No write without a body, no JSON answer saying nothing, no $ref left unresolved."""
    spec = app.openapi()
    assert spec["paths"], "the document holds no routes at all"
    assert _writes_missing_body(spec) == []
    assert _schemas_saying_nothing(spec) == []
    assert _dangling_refs(spec) == []


@pytest.mark.covers(
    "aurelius_atlas_server.openapi.install",
    "aurelius_atlas_server.openapi._names",
    "aurelius_atlas_server.openapi.schema_of",
    rules=["SRV-08", "SVC-07"],
)
def test__an_app_documents_only_the_models_of_the_routes_it_carries(app: FastAPI) -> None:
    """A second application in the same process documents its own routes, not the server's (SVC-07).

    The models of a document are the ones its own routes name: the glossary carries the glossary shapes,
    and neither the entity shapes nor the type shapes it never serves enter it.
    """
    glossary = FastAPI()
    glossary.include_router(GLOSSARY)
    install(glossary)

    held = glossary.openapi()["components"]["schemas"]
    whole = app.openapi()["components"]["schemas"]
    assert "AtlasGlossary" in held
    assert "AtlasEntityWithExtInfo" not in held
    assert "AtlasTypesDef" not in held
    assert {"AtlasGlossary", "AtlasEntityWithExtInfo", "AtlasTypesDef"} <= set(whole)
