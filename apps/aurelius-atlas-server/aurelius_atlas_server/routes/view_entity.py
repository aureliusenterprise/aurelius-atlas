"""The read door of the view family: ``GET /api/aurelius/v1/entity/guid/{guid}`` (AVR-01, AVR-10).

One read of the entity document answers its live 16.1 view: the entity's own values plus what the
indexer last stored, ``stale`` marked when the worker still owes a document (DD-585). Without
``ENTITY_READ`` the answer is ``VIEW_FORBIDDEN`` (AVR-01); a GUID with no entity is the Atlas 404
(AVR-10), not the door's refusal shape.
"""

from aurelius_atlas_core.view_derivation import view_of
from aurelius_atlas_model.errors import validate_guid
from aurelius_atlas_model.views import EntityView
from fastapi import APIRouter, Request

from aurelius_atlas_server.authorization import AtlasPrivilege, authorizer, is_access_allowed
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.openapi import json_response
from aurelius_atlas_server.routes.entity import Store

VIEW_ENTITY = APIRouter(prefix="/api/aurelius/v1", tags=["View family"])

VIEW_RESULT = json_response(EntityView, description="The entity's live view: fields, derived fields, sections.")


@VIEW_ENTITY.get("/entity/guid/{guid}", responses=VIEW_RESULT)
async def read(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """The live view of one entity: one read, derived fresh (AVR-10)."""
    if not is_access_allowed(request, AtlasPrivilege.ENTITY_READ):
        raise AtlasError(AtlasErrorCode.VIEW_FORBIDDEN, authorizer(request).user)
    validate_guid("guid", guid)
    found = await store.get(guid)
    if found is None:
        raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
    entity_type = store.registry.entity_type(found.entity.type_name)
    if entity_type is None:  # pragma: no cover - the store only holds entities of known types
        raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, f"the type {found.entity.type_name} of entity {guid}")
    return AtlasJSONResponse(view_of(found.entity, entity_type).to_json())
