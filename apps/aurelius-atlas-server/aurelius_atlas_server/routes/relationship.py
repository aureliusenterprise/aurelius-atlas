"""The endpoints of ``RelationshipREST`` under ``/api/atlas/v2/relationship`` (REL-03 to REL-08)."""

from typing import Annotated

from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_model.errors import validate_guid
from aurelius_atlas_model.instance import AtlasRelationship, AtlasRelationshipWithExtInfo
from aurelius_atlas_model.params import ExtendedInfoParams, read_params
from fastapi import APIRouter, Depends, Request, Response

from aurelius_atlas_server.authentication import acting_user
from aurelius_atlas_server.authorization import authorizer
from aurelius_atlas_server.bodies import json_model
from aurelius_atlas_server.errors import AtlasJSONResponse
from aurelius_atlas_server.openapi import json_response, request_body
from aurelius_atlas_server.openapi import no_content as no_content_response
from aurelius_atlas_server.routes.entity import Store, delete_type, notifier, tasks_enabled

RELATIONSHIP = APIRouter(prefix="/api/atlas/v2/relationship", tags=["Relationship"])

RELATIONSHIP_BODY = json_model(AtlasRelationship)
"""``create``/``update``: the relationship, validated by its model (REL-04, REL-07)."""

type RelationshipBody = Annotated[AtlasRelationship | None, Depends(RELATIONSHIP_BODY)]


def relationships(request: Request, store: EntityStore) -> RelationshipStore:
    """A relationship store deleting as the server's ``delete_type`` setting says (EDL-04).

    Propagation is deferred as ``tasks_enabled`` says (TSK-02), what it changed audited (CAU-05), each change checked
    (AUZ-09).
    """
    return RelationshipStore(
        store,
        delete_type=DeleteType.of(request.app.state.settings.delete_type),
        user=acting_user(request),
        tasks=tasks_enabled(request),
        notifier=notifier(request, store),
        authorizer=authorizer(request),
    )


def relationship_body(body: AtlasRelationship | None) -> AtlasRelationship:
    """The body as an ``AtlasRelationship``; no body is one without type or ends."""
    return body or AtlasRelationship()


@RELATIONSHIP.post(
    "",
    responses=json_response(AtlasRelationship, description="The created relationship, with its GUID (REL-04)."),
    **request_body(AtlasRelationship, description="The relationship to create: its type and its two ends."),
)
async def create(request: Request, relationship: RelationshipBody, store: Store) -> AtlasJSONResponse:
    """``create``: a new relationship between two entities (REL-04, REL-05)."""
    created = await relationships(request, store).create(relationship_body(relationship))
    return AtlasJSONResponse(content=created.to_json())


@RELATIONSHIP.put(
    "",
    responses=json_response(AtlasRelationship, description="The updated relationship (REL-07)."),
    **request_body(AtlasRelationship, description="The relationship to update, by its GUID."),
)
async def update(request: Request, relationship: RelationshipBody, store: Store) -> AtlasJSONResponse:
    """``update``: the relationship's tag propagation and attributes (REL-07)."""
    updated = await relationships(request, store).update(relationship_body(relationship))
    return AtlasJSONResponse(content=updated.to_json())


@RELATIONSHIP.get(
    "/guid/{guid}",
    responses=json_response(
        AtlasRelationshipWithExtInfo,
        description="The relationship, with its ends' headers when extendedInfo is true (REL-03).",
    ),
)
async def get_by_id(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getById``: the relationship, with its ends' headers when ``extendedInfo`` is true (REL-03, REL-06)."""
    validate_guid("guid", guid)
    found = relationships(request, store)
    extended_info = read_params(ExtendedInfoParams, request.query_params).extended_info
    if extended_info:
        answer = await found.get_ext_info_by_id(guid)
    else:
        answer = AtlasRelationshipWithExtInfo(relationship=await found.get_by_id(guid))
    return AtlasJSONResponse(content=answer.to_json())


@RELATIONSHIP.delete(
    "/guid/{guid}",
    status_code=204,
    responses=no_content_response("The relationship is deleted, soft or hard as asked (REL-08)."),
)
async def delete_by_id(guid: str, request: Request, store: Store) -> Response:
    """``deleteById``: soft or hard, as the request may choose (REL-03, REL-08, EDL-04)."""
    validate_guid("guid", guid)
    await relationships(request, store).delete_by_id(guid, delete_type(request))
    return Response(status_code=204)
