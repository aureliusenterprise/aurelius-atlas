"""The form-slice door of the view family: ``GET /api/aurelius/v1/types/for-type/{name}`` (AVW-11).

One read answers the whole type chain an editor needs to build a form for one type: the named entity
type and each of its supertypes with the attributes each declares (DD-593). The whole typedefs are
returned unchanged, not a view of them: the field widgets already know the Atlas typedef shape, and a
second shape for them would be a second thing to keep honest. Without ``TYPE_READ`` the answer is the
same ``UNAUTHORIZED_ACCESS`` the Atlas type endpoints answer (TYR-01); an unknown name is their 404.
"""

from aurelius_atlas_model.errors import validate_param_length
from aurelius_atlas_model.typedef import AtlasBaseTypeDef
from fastapi import APIRouter, Request

from aurelius_atlas_server.authorization import AtlasPrivilege, verify_access
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.models import ViewForTypeAnswer
from aurelius_atlas_server.openapi import json_response
from aurelius_atlas_server.routes.types import READ_TYPE, Store

VIEW_TYPES = APIRouter(prefix="/api/aurelius/v1", tags=["View family"])

FOR_TYPE_RESULT = json_response(
    ViewForTypeAnswer, description="The named type and its supertype chain, as whole typedefs (AVW-11)."
)


@VIEW_TYPES.get("/types/for-type/{name}", responses=FOR_TYPE_RESULT)
async def for_type(name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``for-type/{name}``: the named entity type and its supertypes, each typedef whole (AVW-11).

    Raises:
        AtlasError: ``TYPE_NAME_NOT_FOUND`` (404) when no type carries the name, or it is not an
            entity type - the editor only ever asks for one it read from a live view.
    """
    validate_param_length("name", name)
    verify_access(request, AtlasPrivilege.TYPE_READ, READ_TYPE, name)
    entity_type = store.registry.entity_type(name)
    if entity_type is None:
        raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, name)
    chain = [name, *entity_type.all_super_types]
    defs: list[AtlasBaseTypeDef] = []
    for type_name in chain:
        typedef = store.registry.typedef_by_name(type_name)
        if typedef is None:  # pragma: no cover - a registered type always has its own typedef
            raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, name)
        defs.append(typedef)
    return AtlasJSONResponse({"type": defs[0].to_json(), "superTypes": [d.to_json() for d in defs[1:]]})
