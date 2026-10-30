"""The lineage endpoints of ``LineageREST`` under ``/api/atlas/v2/lineage`` (LIN-01 to LIN-06)."""

from aurelius_atlas_core.entity_lineage_service import LINEAGE_ON_DEMAND_ENABLED, EntityLineageService
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_model.lineage import LineageDirection, LineageOnDemandConstraints
from fastapi import APIRouter, Request

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.routes.entity import (
    INT_RANGE,
    Body,
    Store,
    first_value,
    guid_by_unique_attributes,
    java_number,
    parsed_value,
)
from aurelius_atlas_server.routes.types import validate_param_length

LINEAGE = APIRouter(prefix="/api/atlas/v2/lineage", tags=["Lineage"])

DEFAULT_DIRECTION = LineageDirection.BOTH
DEFAULT_DEPTH = 3


def lineage_service(request: Request, store: EntityStore) -> EntityLineageService:
    """The lineage service with the server's lineage settings (LIN-04, LIN-06)."""
    settings = request.app.state.settings
    return EntityLineageService(
        store,
        on_demand_enabled=settings.lineage_on_demand_enabled,
        on_demand_default_node_count=settings.lineage_on_demand_default_node_count,
        max_node_count=settings.lineage_max_node_count,
    )


def direction_and_depth(request: Request) -> tuple[LineageDirection, int]:
    """``direction`` (``BOTH``) and ``depth`` (3) as JAX-RS converts them; ``BAD_REQUEST`` when it cannot (DV-39)."""
    value = first_value(request, "direction")
    direction = DEFAULT_DIRECTION if value is None else parsed_value("direction", value, LineageDirection)
    return direction, java_number(request, "depth", DEFAULT_DEPTH, INT_RANGE)


@LINEAGE.get("/{guid}")
async def get_lineage_graph(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getLineageGraph``: the entity's lineage in ``direction``, ``depth`` deep (LIN-01 to LIN-05)."""
    validate_param_length("guid", guid)
    direction, depth = direction_and_depth(request)
    info = await lineage_service(request, store).get_atlas_lineage_info(guid, direction, depth)
    return AtlasJSONResponse(content=info.to_json())


@LINEAGE.post("/{guid}")
async def get_lineage_graph_on_demand(guid: str, request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """``getLineageGraph`` on demand: within the constraints per GUID of the body (LIN-06, LIN-07)."""
    if not request.app.state.settings.lineage_on_demand_enabled:
        raise AtlasError(AtlasErrorCode.LINEAGE_ON_DEMAND_NOT_ENABLED, LINEAGE_ON_DEMAND_ENABLED)
    validate_param_length("guid", guid)
    constraints = (
        {key: LineageOnDemandConstraints.model_validate(value or {}) for key, value in dict(body).items()}
        if body
        else None
    )
    info = await lineage_service(request, store).get_atlas_lineage_info_on_demand(guid, constraints)
    return AtlasJSONResponse(content=info.to_json())


@LINEAGE.get("/uniqueAttribute/type/{type_name}")
async def get_lineage_by_unique_attribute(type_name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getLineageByUniqueAttribute``: the lineage of the entity holding the ``attr:`` values (LIN-01)."""
    validate_param_length("typeName", type_name)
    direction, depth = direction_and_depth(request)
    guid = await guid_by_unique_attributes(store, type_name, request)
    info = await lineage_service(request, store).get_atlas_lineage_info(guid, direction, depth)
    return AtlasJSONResponse(content=info.to_json())
