"""The type endpoints of ``TypesREST`` under ``/api/atlas/v2/types`` (TYR-01 to TYR-12)."""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from aurelius_atlas_core.authorization import filter_types_def
from aurelius_atlas_core.type_search import TypeSearchFilter, search_types_def, type_def_headers
from aurelius_atlas_core.typedef_store import TypedefStore, root_def
from aurelius_atlas_model.errors import validate_guid, validate_param_length
from aurelius_atlas_model.typedef import AtlasBaseTypeDef, AtlasTypeDefHeader, AtlasTypesDef, TypeCategory
from fastapi import APIRouter, Depends, Request, Response
from pydantic import ValidationError

from aurelius_atlas_server.authentication import acting_user
from aurelius_atlas_server.authorization import AtlasPrivilege, authorizer, verify_access
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.openapi import array_of, json_response, request_body
from aurelius_atlas_server.openapi import no_content as no_content_response
from aurelius_atlas_server.tenant_stores import stores

TYPES = APIRouter(prefix="/api/atlas/v2/types", tags=["Types"])

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
    """The typedef store of the request's tenant, its registry refreshed when due (TYR-12, TDS-13, TSS-06)."""
    store = stores(request).typedef_store
    await store.refresh()
    return store


type Store = Annotated[TypedefStore, Depends(typedef_store)]


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


@TYPES.get(
    "/typedef/name/{name}",
    responses=json_response(AtlasBaseTypeDef, description="The definition of any kind with that name (TYR-01)."),
)
async def get_typedef_by_name(name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getTypeDefByName``: the definition of any kind with that name, if the user may read it (TYR-01, AUZ-04)."""
    validate_param_length("name", name)
    found = store.get_by_name(name)
    verify_access(request, AtlasPrivilege.TYPE_READ, READ_TYPE, name)
    return _json(found.to_json())


@TYPES.get(
    "/typedef/guid/{guid}",
    responses=json_response(AtlasBaseTypeDef, description="The definition of any kind with that GUID (TYR-02)."),
)
async def get_typedef_by_guid(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getTypeDefByGuid``: the definition of any kind with that GUID, if the user may read it (TYR-02, AUZ-04)."""
    validate_guid("guid", guid)
    found = store.get_by_guid(guid)
    verify_access(request, AtlasPrivilege.TYPE_READ, READ_TYPE, guid)
    return _json(found.to_json())


@TYPES.get(
    "/typedefs/headers",
    responses=json_response(
        array_of(AtlasTypeDefHeader), description="The headers of the definitions the filter keeps (TYR-08)."
    ),
)
async def get_typedef_headers(request: Request, store: Store) -> AtlasJSONResponse:
    """``getTypeDefHeaders``: the headers of the definitions the filter keeps and the user may read (TYR-08, AUZ-14)."""
    found = _search_types_def(request, store)
    return _json([header.to_json() for header in type_def_headers(found)])


@TYPES.get(
    "/typedefs",
    responses=json_response(
        AtlasTypesDef, description="The definitions the filter keeps, each kind sorted by name (TYR-05)."
    ),
)
async def get_all_typedefs(request: Request, store: Store) -> AtlasJSONResponse:
    """``getAllTypeDefs``: the definitions the filter keeps and the user may read, each kind sorted by name.

    TYR-05 to TYR-07, AUZ-14.
    """
    return _json(_search_types_def(request, store).to_json())


def _search_types_def(request: Request, store: TypedefStore) -> AtlasTypesDef:
    """``searchTypesDef``: the definitions the query's filter keeps, of those the user may read (AUZ-14)."""
    found = search_types_def(store.registry, TypeSearchFilter.from_query(request.query_params.multi_items()))
    return filter_types_def(authorizer(request), found)


@TYPES.post(
    "/typedefs",
    responses=json_response(AtlasTypesDef, description="The created definitions (TYR-09)."),
    **request_body(AtlasTypesDef, description="The definitions to create, of any kind."),
)
async def create_typedefs(request: Request, types_def: Body, store: Store) -> AtlasJSONResponse:
    """``createAtlasTypeDefs``: create the definitions, all or none, as the request's user (TYR-09, USR-02, AUZ-04)."""
    _verify_each(request, types_def, AtlasPrivilege.TYPE_CREATE, "create")
    return _json((await store.create_types_def(types_def, user=acting_user(request))).to_json())


@TYPES.put(
    "/typedefs",
    responses=json_response(AtlasTypesDef, description="The updated definitions (TYR-09)."),
    **request_body(AtlasTypesDef, description="The definitions to update, each by its GUID."),
)
async def update_typedefs(request: Request, types_def: Body, store: Store) -> AtlasJSONResponse:
    """``updateAtlasTypeDefs``: update the definitions, all or none, as the request's user (TYR-09, USR-02, AUZ-04)."""
    _verify_each(request, types_def, AtlasPrivilege.TYPE_UPDATE, "update")
    return _json((await store.update_types_def(types_def, user=acting_user(request))).to_json())


@TYPES.delete(
    "/typedefs",
    status_code=204,
    responses=no_content_response("The definitions are deleted (TYR-10)."),
    **request_body(AtlasTypesDef, description="The definitions to delete, each by its GUID."),
)
async def delete_typedefs(request: Request, types_def: Body, store: Store) -> Response:
    """``deleteAtlasTypeDefs``: delete the definitions, all or none (TYR-10, AUZ-04)."""
    _verify_each(request, types_def, AtlasPrivilege.TYPE_DELETE, "delete")
    await store.delete_types_def(types_def)
    return Response(status_code=204)


@TYPES.delete(
    "/typedef/name/{type_name}",
    status_code=204,
    responses=no_content_response("The named definition is deleted (TYR-10)."),
)
async def delete_typedef_by_name(type_name: str, request: Request, store: Store) -> Response:
    """``deleteAtlasTypeByName``: delete the named definition (TYR-10, AUZ-04)."""
    found = store.get_by_name(type_name)
    verify_access(request, AtlasPrivilege.TYPE_DELETE, f"delete {KIND_TEXT[found.category]} ", type_name)
    await store.delete_type_by_name(type_name)
    return Response(status_code=204)


type Lookup = Callable[[str, Request, TypedefStore], Awaitable[AtlasJSONResponse]]


def kind_by_name(kind: TypeCategory) -> Lookup:
    """The endpoint answering ``kind``'s definition with a name (``get{Kind}DefByName``, TYR-03)."""

    async def lookup(name: str, request: Request, store: Store) -> AtlasJSONResponse:
        validate_param_length("name", name)
        found = store.get_def_by_name(kind, name)
        if found is not root_def(kind, name):  # Atlas answers a root without the access check (TYR-13)
            verify_access(request, AtlasPrivilege.TYPE_READ, READ_TYPE, name)
        return _json(found.to_json())

    return lookup


def kind_by_guid(kind: TypeCategory) -> Lookup:
    """The endpoint answering ``kind``'s definition with a GUID (``get{Kind}DefByGuid``, TYR-03)."""

    async def lookup(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
        validate_guid("guid", guid)
        found = store.get_def_by_guid(kind, guid)
        verify_access(request, AtlasPrivilege.TYPE_READ, READ_TYPE, guid)
        return _json(found.to_json())

    return lookup


KIND_RESPONSES = json_response(AtlasBaseTypeDef, description="The definition of this kind, found its way (TYR-03).")

for _path, _kind in KIND_PATHS.items():
    TYPES.add_api_route(
        f"/{_path}/name/{{name}}",
        kind_by_name(_kind),
        methods=["GET"],
        name=f"{_path}_by_name",
        responses=KIND_RESPONSES,
    )
    TYPES.add_api_route(
        f"/{_path}/guid/{{guid}}",
        kind_by_guid(_kind),
        methods=["GET"],
        name=f"{_path}_by_guid",
        responses=KIND_RESPONSES,
    )


READ_TYPE = "read type "
KIND_TEXT = {
    TypeCategory.ENUM: "enum-def",
    TypeCategory.STRUCT: "struct-def",
    TypeCategory.CLASSIFICATION: "classification-def",
    TypeCategory.ENTITY: "entity-def",
    TypeCategory.RELATIONSHIP: "relationship-def",
    TypeCategory.BUSINESS_METADATA: "businessMetadata-def",
}
"""How the definition stores name their kind in the actions they check (AUZ-04)."""


def _verify_each(request: Request, types_def: AtlasTypesDef, privilege: AtlasPrivilege, verb: str) -> None:
    """The privilege for each definition, in the order the stores write the kinds (AUZ-04).

    Raises:
        AtlasError: ``UNAUTHORIZED_ACCESS`` for the first the user may not change.
    """
    for kind, definitions in (
        (TypeCategory.ENUM, types_def.enum_defs),
        (TypeCategory.STRUCT, types_def.struct_defs),
        (TypeCategory.CLASSIFICATION, types_def.classification_defs),
        (TypeCategory.ENTITY, types_def.entity_defs),
        (TypeCategory.RELATIONSHIP, types_def.relationship_defs),
        (TypeCategory.BUSINESS_METADATA, types_def.business_metadata_defs),
    ):
        for definition in definitions or []:
            verify_access(request, privilege, f"{verb} {KIND_TEXT[kind]} ", definition.name)
