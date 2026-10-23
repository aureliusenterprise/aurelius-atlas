"""The endpoints of ``RelationshipREST`` under ``/api/atlas/v2/relationship`` (REL-03 to REL-08)."""

from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_model.instance import AtlasRelationship, AtlasRelationshipWithExtInfo
from fastapi import APIRouter, Request, Response

from aurelius_atlas_server.errors import AtlasJSONResponse
from aurelius_atlas_server.routes.entity import Body, Store, delete_type, flag, model_body, tasks_enabled
from aurelius_atlas_server.routes.types import validate_param_length

RELATIONSHIP = APIRouter(prefix="/api/atlas/v2/relationship", tags=["Relationship"])


def relationships(request: Request, store: EntityStore) -> RelationshipStore:
    """A relationship store deleting as the server's ``delete_type`` setting says (EDL-04).

    Propagation is deferred as ``tasks_enabled`` says (TSK-02).
    """
    return RelationshipStore(
        store, delete_type=DeleteType.of(request.app.state.settings.delete_type), tasks=tasks_enabled(request)
    )


def relationship_body(body: object) -> AtlasRelationship:
    """The body as an ``AtlasRelationship``; no body is one without type or ends."""
    return model_body(AtlasRelationship, body) or AtlasRelationship()


@RELATIONSHIP.post("")
async def create(request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """``create``: a new relationship between two entities (REL-04, REL-05)."""
    created = await relationships(request, store).create(relationship_body(body))
    return AtlasJSONResponse(content=created.to_json())


@RELATIONSHIP.put("")
async def update(request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """``update``: the relationship's tag propagation and attributes (REL-07)."""
    updated = await relationships(request, store).update(relationship_body(body))
    return AtlasJSONResponse(content=updated.to_json())


@RELATIONSHIP.get("/guid/{guid}")
async def get_by_id(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getById``: the relationship, with its ends' headers when ``extendedInfo`` is true (REL-03, REL-06)."""
    validate_param_length("guid", guid)
    found = relationships(request, store)
    if flag(request, "extendedInfo"):
        answer = await found.get_ext_info_by_id(guid)
    else:
        answer = AtlasRelationshipWithExtInfo(relationship=await found.get_by_id(guid))
    return AtlasJSONResponse(content=answer.to_json())


@RELATIONSHIP.delete("/guid/{guid}", status_code=204)
async def delete_by_id(guid: str, request: Request, store: Store) -> Response:
    """``deleteById``: soft or hard, as the request may choose (REL-03, REL-08, EDL-04)."""
    validate_param_length("guid", guid)
    await relationships(request, store).delete_by_id(guid, delete_type(request))
    return Response(status_code=204)
