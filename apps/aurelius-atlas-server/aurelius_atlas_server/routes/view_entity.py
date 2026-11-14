"""The view family's read and mutation doors: GET and POST on ``/api/aurelius/v1/entity``.

One read of the entity document answers its live 16.1 view: the entity's own values plus what the
indexer last stored, ``stale`` marked when the worker still owes a document (DD-585). Without
``ENTITY_READ`` the read answer is ``VIEW_FORBIDDEN`` (AVR-01); a GUID with no entity is the Atlas 404
(AVR-10), not the door's refusal shape. The POST door takes the view as the entity's desired state and
answers the live view of the written entity (AVW-07), its refusals in the door's own shape (AVR-13) and
its conflicts beside the stored view (DD-591).
"""

from aurelius_atlas_core.view_derivation import view_of
from aurelius_atlas_core.view_mutation import ViewMutationDoor, ViewVersionConflictError
from aurelius_atlas_model.errors import validate_guid
from aurelius_atlas_model.views import EntityView
from fastapi import APIRouter, Request

from aurelius_atlas_server.authentication import acting_user
from aurelius_atlas_server.authorization import AtlasPrivilege, authorizer, is_access_allowed
from aurelius_atlas_server.bodies import Body
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.openapi import json_response, request_body
from aurelius_atlas_server.routes.entity import Store, notifier, tasks_enabled

VIEW_ENTITY = APIRouter(prefix="/api/aurelius/v1", tags=["View family"])

VIEW_RESULT = json_response(EntityView, description="The entity's live view: fields, derived fields, sections.")

VIEW_BODY = request_body(EntityView, required=False, description="The entity's desired state as a view (AVW-02).")


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


@VIEW_ENTITY.post("/entity", responses=VIEW_RESULT, **VIEW_BODY)
async def write(request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """``POST /entity``: the view as desired state, applied in one request, the new live view out (AVW-01 to AVW-10).

    The create needs ``ENTITY_CREATE`` and the update ``ENTITY_UPDATE``, answered ``VIEW_FORBIDDEN_WRITE``
    without it (AVW-01); what the applied steps change is checked by the same internals the Atlas routes
    run. A lost update answers the conflict beside the stored view (AVW-04, DD-591).
    """
    creating = isinstance(body, dict) and body.get("guid") is None
    needed = AtlasPrivilege.ENTITY_CREATE if creating else AtlasPrivilege.ENTITY_UPDATE
    if not is_access_allowed(request, needed):
        raise AtlasError(AtlasErrorCode.VIEW_FORBIDDEN_WRITE, authorizer(request).user)
    door = ViewMutationDoor(
        store,
        user=acting_user(request),
        authorizer=authorizer(request),
        notifier=notifier(request, store),
        tasks=tasks_enabled(request),
    )
    try:
        view = await door.apply({} if body is None else body)
    except ViewVersionConflictError as conflict:
        return _conflict(conflict)
    return AtlasJSONResponse(view.to_json())


def _conflict(conflict: ViewVersionConflictError) -> AtlasJSONResponse:
    """The conflict answer: the door's code beside the stored view the editor merges from (AVW-04, DD-591)."""
    stored = conflict.view.to_json()
    return AtlasJSONResponse(
        status_code=409,
        content={"errorCode": AtlasErrorCode.ENTITY_VERSION_CONFLICT.code, "view": stored},
    )
