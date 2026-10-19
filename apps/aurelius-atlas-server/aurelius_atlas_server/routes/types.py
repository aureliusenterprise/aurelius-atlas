"""The type endpoints of ``TypesREST`` under ``/api/atlas/v2/types`` (TYR-01 to TYR-12)."""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from aurelius_atlas_core.type_search import TypeSearchFilter, search_types_def, type_def_headers
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.typedef import AtlasTypesDef, TypeCategory
from fastapi import APIRouter, Depends, Request, Response
from pydantic import ValidationError

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse

TYPES = APIRouter(prefix="/api/atlas/v2/types", tags=["Types"])

QUERY_PARAM_MAX_LENGTH = 4 * 1024
"""The longest name or GUID a lookup takes (``atlas.query.param.max.length``)."""

KIND_PATHS = {
    "enumdef": TypeCategory.ENUM,
    "structdef": TypeCategory.STRUCT,
    "classificationdef": TypeCategory.CLASSIFICATION,
    "entitydef": TypeCategory.ENTITY,
    "relationshipdef": TypeCategory.RELATIONSHIP,
    "businessmetadatadef": TypeCategory.BUSINESS_METADATA,
}
"""The path of each kind's lookups (``TypesREST.get{Kind}DefByName`` and ``ByGuid``)."""


async def typedef_store(request: Request) -> TypedefStore:
    """The server's typedef store, its registry refreshed when due (TYR-12, TDS-13)."""
    store: TypedefStore = request.app.state.typedef_store
    await store.refresh()
    return store


type Store = Annotated[TypedefStore, Depends(typedef_store)]


def validate_param_length(name: str, value: str) -> None:
    """``Servlets.validateQueryParamLength``: at most 4096 characters (TYR-04).

    Raises:
        AtlasError: ``INVALID_QUERY_PARAM_LENGTH`` naming the parameter.
    """
    if len(value) > QUERY_PARAM_MAX_LENGTH:
        raise AtlasError(AtlasErrorCode.INVALID_QUERY_PARAM_LENGTH, name)


async def types_def_body(request: Request) -> AtlasTypesDef:
    """The request body as an ``AtlasTypesDef``; unknown fields are ignored (TYR-11).

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is not JSON or not an ``AtlasTypesDef`` (DV-10).
    """
    try:
        return AtlasTypesDef.model_validate_json(await request.body())
    except ValidationError as error:
        problem = error.errors(include_url=False)[0]
        location = ".".join(str(part) for part in problem["loc"])
        message = f"Invalid AtlasTypesDef: {problem['msg']}" + (f" at {location}" if location else "")
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, message) from error


type Body = Annotated[AtlasTypesDef, Depends(types_def_body)]


def _json(content: Any) -> AtlasJSONResponse:  # noqa: ANN401 - Atlas JSON
    return AtlasJSONResponse(content=content)


@TYPES.get("/typedef/name/{name}")
async def get_typedef_by_name(name: str, store: Store) -> AtlasJSONResponse:
    """``getTypeDefByName``: the definition of any kind with that name (TYR-01)."""
    validate_param_length("name", name)
    return _json(store.get_by_name(name).to_json())


@TYPES.get("/typedef/guid/{guid}")
async def get_typedef_by_guid(guid: str, store: Store) -> AtlasJSONResponse:
    """``getTypeDefByGuid``: the definition of any kind with that GUID (TYR-02)."""
    validate_param_length("guid", guid)
    return _json(store.get_by_guid(guid).to_json())


@TYPES.get("/typedefs/headers")
async def get_typedef_headers(request: Request, store: Store) -> AtlasJSONResponse:
    """``getTypeDefHeaders``: the headers of the definitions the filter keeps (TYR-08)."""
    found = search_types_def(store.registry, TypeSearchFilter.from_query(request.query_params.multi_items()))
    return _json([header.to_json() for header in type_def_headers(found)])


@TYPES.get("/typedefs")
async def get_all_typedefs(request: Request, store: Store) -> AtlasJSONResponse:
    """``getAllTypeDefs``: the definitions the filter keeps, each kind sorted by name (TYR-05 to TYR-07)."""
    found = search_types_def(store.registry, TypeSearchFilter.from_query(request.query_params.multi_items()))
    return _json(found.to_json())


@TYPES.post("/typedefs")
async def create_typedefs(types_def: Body, store: Store) -> AtlasJSONResponse:
    """``createAtlasTypeDefs``: create the definitions, all or none (TYR-09)."""
    return _json((await store.create_types_def(types_def)).to_json())


@TYPES.put("/typedefs")
async def update_typedefs(types_def: Body, store: Store) -> AtlasJSONResponse:
    """``updateAtlasTypeDefs``: update the definitions, all or none (TYR-09)."""
    return _json((await store.update_types_def(types_def)).to_json())


@TYPES.delete("/typedefs", status_code=204)
async def delete_typedefs(types_def: Body, store: Store) -> Response:
    """``deleteAtlasTypeDefs``: delete the definitions, all or none (TYR-10)."""
    await store.delete_types_def(types_def)
    return Response(status_code=204)


@TYPES.delete("/typedef/name/{type_name}", status_code=204)
async def delete_typedef_by_name(type_name: str, store: Store) -> Response:
    """``deleteAtlasTypeByName``: delete the named definition (TYR-10)."""
    await store.delete_type_by_name(type_name)
    return Response(status_code=204)


type Lookup = Callable[[str, TypedefStore], Awaitable[AtlasJSONResponse]]


def kind_by_name(kind: TypeCategory) -> Lookup:
    """The endpoint answering ``kind``'s definition with a name (``get{Kind}DefByName``, TYR-03)."""

    async def lookup(name: str, store: Store) -> AtlasJSONResponse:
        validate_param_length("name", name)
        return _json(store.get_def_by_name(kind, name).to_json())

    return lookup


def kind_by_guid(kind: TypeCategory) -> Lookup:
    """The endpoint answering ``kind``'s definition with a GUID (``get{Kind}DefByGuid``, TYR-03)."""

    async def lookup(guid: str, store: Store) -> AtlasJSONResponse:
        validate_param_length("guid", guid)
        return _json(store.get_def_by_guid(kind, guid).to_json())

    return lookup


for _path, _kind in KIND_PATHS.items():
    TYPES.add_api_route(f"/{_path}/name/{{name}}", kind_by_name(_kind), methods=["GET"], name=f"{_path}_by_name")
    TYPES.add_api_route(f"/{_path}/guid/{{guid}}", kind_by_guid(_kind), methods=["GET"], name=f"{_path}_by_guid")
