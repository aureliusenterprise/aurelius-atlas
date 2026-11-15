"""Whether the server serves tenants: ``GET /api/aurelius/v1/tenancy``, answered without a user (TNW-01, DD-636).

The webapp reads it before it signs in, to know whether to ask Keycloak for the organization scope and how to
read the tenant's roles. The answer tells nothing a token doesn't carry: the operator organization and role are
the claims the server reads (TEN-04, TEN-06). The path is Aurelius's own; no Atlas answer changes (TNW-09).
"""

from aurelius_atlas_model.base import AtlasModel
from fastapi import APIRouter, Request

from aurelius_atlas_server.errors import AtlasJSONResponse
from aurelius_atlas_server.openapi import json_response
from aurelius_atlas_server.tenancy import Tenancy

__all__ = ["TENANCY", "TENANCY_PATH", "TenancyAnswer"]

TENANCY = APIRouter(prefix="/api/aurelius/v1", tags=["Tenancy"])

TENANCY_PATH = "/api/aurelius/v1/tenancy"
"""The answer's path, which needs no user (TNW-01)."""


class TenancyAnswer(AtlasModel):
    """Whether tenancy is on and, when it is, the operator organization and role (TNW-01)."""

    enabled: bool
    operator_organization: str | None = None
    operator_role: str | None = None


@TENANCY.get(
    "/tenancy",
    responses=json_response(TenancyAnswer, description="Whether the server serves tenants, and its operators."),
)
async def tenancy(request: Request) -> AtlasJSONResponse:
    """Whether tenancy is on, with the operator organization and role when it is (TNW-01)."""
    found: Tenancy | None = request.app.state.tenancy
    answer = (
        TenancyAnswer(enabled=False)
        if found is None
        else TenancyAnswer(
            enabled=True, operator_organization=found.operator_organization, operator_role=found.operator_role
        )
    )
    return AtlasJSONResponse(answer.model_dump(by_alias=True, exclude_none=True))
