"""Whether the server serves tenants, and the link to a tenant's dashboards.

``GET /api/aurelius/v1/tenancy`` is answered without a user (TNW-01, DD-636); ``GET
/api/aurelius/v1/tenancy/dashboards`` gives the signed-in user the link to their tenant's dashboards (TDL-06).

The webapp reads it before it signs in, to know whether to ask Keycloak for the organization scope and how to
read the tenant's roles. The answer tells nothing a token doesn't carry: the operator organization and role are
the claims the server reads (TEN-04, TEN-06). The path is Aurelius's own; no Atlas answer changes (TNW-09).
"""

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from fastapi import APIRouter, Request

from aurelius_atlas_server.authentication import User
from aurelius_atlas_server.deps import Settings
from aurelius_atlas_server.errors import AtlasJSONResponse
from aurelius_atlas_server.openapi import json_response
from aurelius_atlas_server.tenancy import Tenancy
from aurelius_atlas_server.tenants import TenantDirectory

__all__ = ["DASHBOARD", "TENANCY", "TENANCY_PATH", "DashboardsAnswer", "TenancyAnswer"]

TENANCY = APIRouter(prefix="/api/aurelius/v1", tags=["Tenancy"])

TENANCY_PATH = "/api/aurelius/v1/tenancy"
"""The answer's path, which needs no user (TNW-01)."""


DASHBOARD = "tenant-catalogue"
"""The dashboard the link opens: the tenant's catalogue (TGF-06, DD-769)."""

WRITE_ROLE = "atlas-write"
"""The tenant role that sees its dashboards: its administrators' and stewards' (TDL-01, DD-767)."""


class DashboardsAnswer(AtlasModel):
    """The link to the user's tenant's catalogue dashboard in Grafana (TDL-06)."""

    url: str


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


@TENANCY.get(
    "/tenancy/dashboards",
    responses=json_response(DashboardsAnswer, description="The link to the tenant's catalogue dashboard."),
)
async def dashboards(request: Request, settings: Settings) -> AtlasJSONResponse:
    """The signed-in user's link to their tenant's catalogue dashboard, for its stewards, administrators and the
    operators its trust made members (TDL-06, TDL-07).

    Raises:
        AtlasError: ``NO_DASHBOARDS`` without tenancy, Grafana's public address or the tenant's Grafana
            organization; ``DASHBOARDS_FORBIDDEN`` for a user who holds no ``atlas-write`` in the tenant and is
            none of the operators its trust made members.
    """  # noqa: D205 - one sentence
    user: User = request.state.user
    tenancy: Tenancy | None = request.app.state.tenancy
    directory: TenantDirectory | None = request.app.state.tenant_directory
    if tenancy is None or directory is None or user.tenant is None or settings.grafana_public_url is None:
        raise AtlasError(AtlasErrorCode.NO_DASHBOARDS, user.tenant or "-")
    record = await directory.index.get(user.tenant)
    if record is None or record.grafana_org is None:
        raise AtlasError(AtlasErrorCode.NO_DASHBOARDS, user.tenant)
    if WRITE_ROLE not in user.roles and user.subject not in record.operator_members:
        raise AtlasError(AtlasErrorCode.DASHBOARDS_FORBIDDEN, user.name, user.tenant)
    url = f"{settings.grafana_public_url.rstrip('/')}/d/{DASHBOARD}?orgId={record.grafana_org}"
    return AtlasJSONResponse(DashboardsAnswer(url=url).model_dump(by_alias=True))
