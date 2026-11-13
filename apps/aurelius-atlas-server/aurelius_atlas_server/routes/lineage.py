"""The lineage endpoints of ``LineageREST`` under ``/api/atlas/v2/lineage`` (LIN-01 to LIN-06)."""

from typing import Annotated

from aurelius_atlas_core.entity_lineage_service import LINEAGE_ON_DEMAND_ENABLED, EntityLineageService
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_model.errors import validate_param_length
from aurelius_atlas_model.lineage import (
    AtlasLineageInfo,
    LineageConstraintsByGuid,
    LineageDirection,
    LineageOnDemandConstraints,
)
from aurelius_atlas_model.params import LineageParams, read_params
from fastapi import APIRouter, Depends, Request

from aurelius_atlas_server.authorization import authorizer
from aurelius_atlas_server.bodies import json_root
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.openapi import json_response, request_body
from aurelius_atlas_server.routes.entity import Store, guid_by_unique_attributes

LINEAGE = APIRouter(prefix="/api/atlas/v2/lineage", tags=["Lineage"])

CONSTRAINTS = json_root(LineageConstraintsByGuid)
"""``getLineageGraph`` on demand: the constraints per entity GUID, each validated (LIN-06)."""

type ConstraintsBody = Annotated[dict[str, LineageOnDemandConstraints] | None, Depends(CONSTRAINTS)]


def lineage_service(request: Request, store: EntityStore) -> EntityLineageService:
    """The lineage service with the server's lineage settings (LIN-04, LIN-06), checked as the user (AUZ-13)."""
    settings = request.app.state.settings
    return EntityLineageService(
        store,
        on_demand_enabled=settings.lineage_on_demand_enabled,
        on_demand_default_node_count=settings.lineage_on_demand_default_node_count,
        max_node_count=settings.lineage_max_node_count,
        authorizer=authorizer(request),
    )


def direction_and_depth(request: Request) -> tuple[LineageDirection, int]:
    """``direction`` (``BOTH``) and ``depth`` (3) as JAX-RS converts them; ``BAD_REQUEST`` when it cannot (DV-39)."""
    asked = read_params(LineageParams, request.query_params)
    return asked.direction, asked.depth


LINEAGE_INFO = json_response(AtlasLineageInfo, description="The lineage graph.")

CONSTRAINTS_BODY = request_body(
    LineageConstraintsByGuid,
    required=False,
    description="The constraints per entity GUID; needs lineage_on_demand_enabled.",
)


@LINEAGE.get("/{guid}", responses=LINEAGE_INFO)
async def get_lineage_graph(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getLineageGraph``: the entity's lineage in ``direction``, ``depth`` deep (LIN-01 to LIN-05)."""
    validate_param_length("guid", guid)
    direction, depth = direction_and_depth(request)
    info = await lineage_service(request, store).get_atlas_lineage_info(guid, direction, depth)
    return AtlasJSONResponse(content=info.to_json())


@LINEAGE.post("/{guid}", responses=LINEAGE_INFO, **CONSTRAINTS_BODY)
async def get_lineage_graph_on_demand(
    guid: str, request: Request, constraints_body: ConstraintsBody, store: Store
) -> AtlasJSONResponse:
    """``getLineageGraph`` on demand: within the constraints per GUID of the body (LIN-06, LIN-07)."""
    if not request.app.state.settings.lineage_on_demand_enabled:
        raise AtlasError(AtlasErrorCode.LINEAGE_ON_DEMAND_NOT_ENABLED, LINEAGE_ON_DEMAND_ENABLED)
    validate_param_length("guid", guid)
    constraints = {key: value or LineageOnDemandConstraints() for key, value in (constraints_body or {}).items()}
    info = await lineage_service(request, store).get_atlas_lineage_info_on_demand(guid, constraints or None)
    return AtlasJSONResponse(content=info.to_json())


@LINEAGE.get("/uniqueAttribute/type/{type_name}", responses=LINEAGE_INFO)
async def get_lineage_by_unique_attribute(type_name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getLineageByUniqueAttribute``: the lineage of the entity holding the ``attr:`` values (LIN-01)."""
    validate_param_length("typeName", type_name)
    direction, depth = direction_and_depth(request)
    guid = await guid_by_unique_attributes(store, type_name, request)
    info = await lineage_service(request, store).get_atlas_lineage_info(guid, direction, depth)
    return AtlasJSONResponse(content=info.to_json())
