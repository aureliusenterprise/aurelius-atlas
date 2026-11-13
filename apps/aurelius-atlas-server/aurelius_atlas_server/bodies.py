"""The request bodies of the endpoints: each read by the model that describes it (DV-10).

A route takes its JSON body through a dependency made by ``json_model``: the request is read as JSON
(a body that is not JSON is ``BAD_REQUEST``, as Jersey answers an unreadable one), an empty body stays
None, and the model validates the request — its own rules included, since a validator may raise an
``AtlasError`` and it reaches the answer unchanged. The OpenAPI document names the same model
(``openapi.request_body``), so the schema and the check are one and the same definition.

Endpoints that read a raw JSON value, a form, or a body their own engine validates (the App Search
request, the import request) keep reading it as they do; their shape is still named in the document.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.errors import ATLAS_REQUEST
from fastapi import Depends, Request
from pydantic import BaseModel, RootModel, ValidationError

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode

ATLAS_BODY_CONTEXT = {ATLAS_REQUEST: True}
"""The Pydantic context the body readers pass, so a model's request-only rules apply (DV-162)."""


async def json_body(request: Request) -> Any:  # noqa: ANN401 - any JSON value
    """The request body read by Atlas's JSON codec (DD-039); None when it is empty, as Jersey gives null.

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is not JSON (DV-10).
    """
    body = await request.body()
    if not body.strip():
        return None
    try:
        return codec.loads(body)
    except ValueError as error:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, f"Invalid JSON: {error}") from error


type Body = Annotated[Any, Depends(json_body)]
"""The body of a route that reads raw JSON itself, through ``json_body``."""


def model_body[T: AtlasModel](model: type[T], body: Any) -> T | None:  # noqa: ANN401 - any JSON value
    """``body`` as ``model``, or None for no body; unknown fields are ignored.

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is not a ``model`` (DV-10).
    """
    if body is None:
        return None
    try:
        return model.model_validate(body, context=ATLAS_BODY_CONTEXT)
    except ValidationError as error:
        problem = error.errors(include_url=False)[0]
        location = ".".join(str(part) for part in problem["loc"])
        message = f"Invalid {model.__name__}: {problem['msg']}" + (f" at {location}" if location else "")
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, message) from error


def json_model[T: BaseModel](model: type[T]) -> Callable[[Request], Awaitable[T | None]]:
    """The dependency that reads a request's body as ``model``, or None for no body (DV-10).

    The model validates the request itself; an ``AtlasError`` it raises answers as it is.

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is not JSON, or not a ``model``.
    """

    async def body(request: Request) -> T | None:
        value = await json_body(request)
        if value is None:
            return None
        try:
            return model.model_validate(value, context=ATLAS_BODY_CONTEXT)
        except ValidationError as error:
            problem = error.errors(include_url=False)[0]
            location = ".".join(str(part) for part in problem["loc"])
            message = f"Invalid {model.__name__}: {problem['msg']}" + (f" at {location}" if location else "")
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, message) from error

    body.__name__ = f"{model.__name__.lower()}_body"
    return body


def json_root[T: RootModel[Any]](model: type[T]) -> Callable[[Request], Awaitable[Any]]:
    """The dependency that reads a request's body as the plain value ``model`` wraps (DV-10).

    For the bodies Java reads as a bare array or map: the endpoint gets the value, the model owns the
    shape rule. Same rules as ``json_model``, None for no body.
    """
    read = json_model(model)

    async def body(request: Request) -> Any:  # noqa: ANN401 - the wrapped value
        found = await read(request)
        return None if found is None else found.root

    body.__name__ = f"{model.__name__.lower()}_body"
    return body
