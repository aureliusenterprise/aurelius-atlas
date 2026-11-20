"""``GET /api/aurelius/v1/tenancy/dashboards`` (TDL-05 to TDL-07): a tenant's dashboards link, or its refusal.

Apache Atlas has no tenants and no Grafana; the expected answers are the spec's. Tokens come from the fake identity
provider, with the organization claim Keycloak's Organization Group Membership mapper writes.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings, create_app
from fake_issuer import FakeIssuer

PATH = "/api/aurelius/v1/tenancy/dashboards"
R = "aurelius_atlas_server.routes.tenancy.dashboards"
GRAFANA = "https://atlas.example/grafana/"
STEWARD = ["/atlas-read", "/atlas-write"]
SCIENTIST = ["/atlas-read"]
OPERATOR = {"roles": ["atlas-operator"]}


async def client_of(settings: ServerSettings) -> AsyncIterator[httpx.AsyncClient]:
    """A client without credentials of the started application."""
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas") as client:
            yield client


@pytest.fixture
async def tenanted(
    settings: ServerSettings, record_tenants: Callable[..., Awaitable[None]]
) -> AsyncIterator[httpx.AsyncClient]:
    """Tenancy on with Grafana's public address; acme with Grafana organization 7, globex with none."""
    await record_tenants("acme", grafanaOrg=7, operatorMembers=["id-op"])
    await record_tenants("globex")
    on = settings.model_copy(
        update={"tenancy_enabled": True, "tenancy_refresh_seconds": 0, "grafana_public_url": GRAFANA}
    )
    async for client in client_of(on):
        yield client


def bearer(issuer: FakeIssuer, user: str, tenant: str, groups: list[str], **claims: Any) -> dict[str, str]:  # noqa: ANN401
    """The ``Authorization`` header of the user's token acting in ``tenant`` with these groups."""
    token = issuer.token(user, atlas_roles=(), organization={tenant: {"groups": groups}}, **claims)
    return {"Authorization": f"Bearer {token}"}


def code(response: httpx.Response) -> tuple[int, str]:
    """The status and error code of a refused request."""
    return response.status_code, response.json()["errorCode"]


@pytest.mark.covers(R, "aurelius_atlas_server.authentication.user_of", rules=["TDL-05", "TDL-06"])
async def test__a_steward_and_an_operator_get_the_tenants_catalogue_link(
    tenanted: httpx.AsyncClient, issuer: FakeIssuer
) -> None:
    """A steward of acme, and an operator acme's trust made a member, with the read group alone, get the link to
    acme's catalogue in Grafana organization 7, the public address's trailing slash dropped.
    """  # noqa: D205 - one sentence
    url = "https://atlas.example/grafana/d/tenant-catalogue?orgId=7"
    steward = await tenanted.get(PATH, headers=bearer(issuer, "sam", "acme", STEWARD))
    assert (steward.status_code, steward.json()) == (200, {"url": url})
    # The webapp's tokens carry no realm roles: the operator is known by the record's operatorMembers, by subject.
    operator = await tenanted.get(PATH, headers=bearer(issuer, "op", "acme", SCIENTIST))
    assert (operator.status_code, operator.json()) == (200, {"url": url})


@pytest.mark.covers(R, rules=["TDL-07"])
async def test__a_scientist_is_refused_and_a_tenant_without_grafana_has_none(
    tenanted: httpx.AsyncClient, issuer: FakeIssuer
) -> None:
    """A scientist of acme, and an operator role holder acme's trust didn't make a member, get 403; a steward of
    globex, which has no Grafana organization, 404; no user, 401.
    """  # noqa: D205 - one sentence
    scientist = await tenanted.get(PATH, headers=bearer(issuer, "sue", "acme", SCIENTIST))
    assert code(scientist) == (403, "AURELIUS-403-00-006")
    stranger = await tenanted.get(PATH, headers=bearer(issuer, "ed", "acme", SCIENTIST, realm_access=OPERATOR))
    assert code(stranger) == (403, "AURELIUS-403-00-006")
    globex = await tenanted.get(PATH, headers=bearer(issuer, "sam", "globex", STEWARD))
    assert code(globex) == (404, "AURELIUS-404-00-002")
    assert (await tenanted.get(PATH)).status_code == 401


@pytest.mark.covers(R, rules=["TDL-05", "TDL-07"])
async def test__without_tenancy_or_a_public_address_there_are_no_dashboards(
    settings: ServerSettings, record_tenants: Callable[..., Awaitable[None]], issuer: FakeIssuer
) -> None:
    """Tenancy on without Grafana's public address: 404 even for a steward. Tenancy off: 404."""
    await record_tenants("acme", grafanaOrg=7)
    no_address = settings.model_copy(update={"tenancy_enabled": True, "tenancy_refresh_seconds": 0})
    async for client in client_of(no_address):
        answer = await client.get(PATH, headers=bearer(issuer, "sam", "acme", STEWARD))
        assert code(answer) == (404, "AURELIUS-404-00-002")
    off = settings.model_copy(update={"grafana_public_url": GRAFANA})
    async for client in client_of(off):
        token = issuer.token("admin")
        answer = await client.get(PATH, headers={"Authorization": f"Bearer {token}"})
        assert code(answer) == (404, "AURELIUS-404-00-002")
