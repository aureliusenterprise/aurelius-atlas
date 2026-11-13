"""The OpenAPI shapes of the hand-parsed bodies and the ``AtlasJSONResponse`` answers (DD-556).

A route reads its body through a dependency (``Body``, codec-decoded) and answers through
``AtlasJSONResponse``, so FastAPI sees neither and its schema generator writes ``object`` with no
properties for both. These helpers declare the shapes in the OpenAPI document instead: every body
and answer names a model — from ``aurelius-atlas-model`` for the Atlas shapes, from
``aurelius_atlas_server.models`` for the Aurelius ones — whose schema is the wire shape, aliases
included. A bare array of strings (``array_of(str)``) is the only shape given inline.

The referenced models are collected as routes are declared and enter ``components/schemas`` when
the spec is first built (``install``), each once and shared by ``$ref``. Development-only surface:
``create_app`` serves the spec only under development (SRV-08), where it documents what the parity
scenarios pin — it changes no request handling.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from aurelius_atlas_model.base import AtlasModel
from fastapi import FastAPI
from pydantic import RootModel

MEDIA = "application/json; charset=UTF-8"
"""The media type of every JSON answer of the server (``AtlasJSONResponse``) and of its bodies."""

_models: list[type[Any]] = []
"""The models referenced by a route's body or answer, in declaration order; ``install`` adds them."""

Shape = type[AtlasModel] | type[RootModel[Any]] | type[str] | Mapping[str, Any]
"""What a shape may be given as: a model (its ``$ref``), ``str`` (a string), or a raw JSON-schema dict."""


def schema_of(model: Shape) -> dict[str, Any]:
    """The schema of a model as a ``$ref``, or a raw shape as it is.

    A raw shape is a plain JSON-schema dict: use ``array_of`` for a JSON array of strings (``item=str``).
    """
    if model is str:
        return {"type": "string"}
    if isinstance(model, Mapping):
        return dict(model)
    if model not in _models:
        _models.append(model)
    return {"$ref": f"#/components/schemas/{model.__name__}"}


def array_of(item: Shape) -> dict[str, Any]:
    """The schema of a JSON array of the item: a list of strings (``item=str``) or of a model."""
    return {"type": "array", "items": schema_of(item)}


def request_body(model: Shape, *, required: bool = True, description: str = "") -> dict[str, Any]:
    """The decorator keyword of a route that reads this JSON body (Atlas ignores an absent optional one).

    Spread into the decorator (``**request_body(...)``); it carries FastAPI's ``openapi_extra``.
    """
    content: dict[str, Any] = {MEDIA: {"schema": schema_of(model)}}
    if description:
        content[MEDIA]["description"] = description
    return {"openapi_extra": {"requestBody": {"required": required, "content": content}}}


def form_request(*, fields: Mapping[str, str], text: Sequence[str] = (), description: str = "") -> dict[str, Any]:
    """The decorator keyword of a multipart upload.

    ``fields`` maps each form field to a description; a name in ``text`` is a plain text field, the
    rest are uploaded files. Spread into the decorator (``**form_request(...)``).
    """
    properties = {
        name: {"type": "string", **({} if name in text else {"format": "binary"}), **({"description": d} if d else {})}
        for name, d in fields.items()
    }
    schema: dict[str, Any] = {"type": "object", "properties": properties, "required": list(fields)}
    content: dict[str, Any] = {"multipart/form-data": {"schema": schema}}
    if description:
        content["multipart/form-data"]["description"] = description
    return {"openapi_extra": {"requestBody": {"required": True, "content": content}}}


def json_response(model: Shape | None, *, description: str, status: int = 200) -> dict[int | str, dict[str, Any]]:
    """The ``responses`` entry of a JSON answer (a 204 needs none; a ``None`` model is an untyped body)."""
    content: dict[str, Any] = {MEDIA: {"schema": schema_of(model)}} if model is not None else {}
    return {status: {"description": description, **({"content": content} if content else {})}}


def no_content(description: str) -> dict[int | str, dict[str, Any]]:
    """The ``responses`` entry of an empty answer: the decorator sets ``status_code=204`` as it is answered."""
    return {204: {"description": description}}


def text_response(description: str, *, status: int = 200) -> dict[int | str, dict[str, Any]]:
    """The ``responses`` entry of a plain-text answer (the probes of ``admin/liveness`` and ``readiness``)."""
    return {
        status: {"description": description, "content": {"text/plain; charset=utf-8": {"schema": {"type": "string"}}}}
    }


def download_response(media_type: str, *, description: str) -> dict[int | str, dict[str, Any]]:
    """The ``responses`` entry of a file download: the export ZIP or a CSV template (no OpenAPI schema)."""
    return {
        200: {"description": description, "content": {media_type: {"schema": {"type": "string", "format": "binary"}}}}
    }


def install(app: FastAPI) -> None:
    """Put every referenced model into the spec's ``components/schemas`` when the spec is built."""

    def openapi() -> dict[str, Any]:
        spec = original()
        if _models:
            schemas = spec.setdefault("components", {}).setdefault("schemas", {})
            for model in _models:
                generated = model.model_json_schema(ref_template="#/components/schemas/{model}")
                for name, definition in generated.pop("$defs", {}).items():
                    schemas.setdefault(name, definition)
                schemas.setdefault(generated["title"], generated)
        return spec

    original = app.openapi
    app.openapi = openapi
