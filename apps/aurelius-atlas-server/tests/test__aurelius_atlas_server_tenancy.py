"""Tenancy over HTTP (TEN-03, TEN-04, TEN-06 to TEN-08): the tenant a request acts in, or its refusal.

Apache Atlas has no tenants (ADR 063); the expected answers are the spec's. Tokens come from the fake identity
provider (``fake_issuer``), with the organization claim Keycloak's Organization Group Membership mapper writes.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx2 as httpx
import pytest
from aurelius_atlas_core.request_context import current
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server.authentication import SESSION_COOKIE
from aurelius_atlas_store_es.testing.fake import FakeClient
from fake_issuer import FakeIssuer
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute

A = "aurelius_atlas_server.authentication"
L = "aurelius_atlas_server.routes.login"
C = "aurelius_atlas_server.oidc_client.OidcClient"
R = "aurelius_atlas_server.request_context.RequestContextMiddleware"
SESSION = "/api/atlas/admin/session"
TENANT = "/api/atlas/test/tenant"
TYPEDEFS = "/api/atlas/v2/types/typedefs"
EVERY_GROUP = ["/atlas-read", "/atlas-write", "/atlas-types", "/atlas-admin"]
OPERATOR = {"roles": ["atlas-operator"]}
DEFINITIONS: dict[str, Any] = {"entityDefs": [{"name": "t_tenant", "superTypes": [], "attributeDefs": []}]}


async def tenant_seen(request: Request) -> dict[str, str | None]:
    """The tenant on the request's state and on the bound core context (TEN-08)."""
    return {"state": request.state.tenant, "context": current().tenant}


def serve(settings: ServerSettings, *, enabled: bool) -> FastAPI:
    """The application with tenancy on or off, reading the tenants index at every request, and a route showing the
    tenant.
    """  # noqa: D205 - one sentence
    app = create_app(settings.model_copy(update={"tenancy_enabled": enabled, "tenancy_refresh_seconds": 0}))
    app.router.routes.insert(0, APIRoute(TENANT, tenant_seen, methods=["GET"]))
    return app


@pytest.fixture
async def tenanted(
    settings: ServerSettings, record_tenants: Callable[..., Awaitable[None]]
) -> AsyncIterator[httpx.AsyncClient]:
    """A client without credentials of the started application with tenancy on, acme and globex provisioned,
    keeping cookies.
    """  # noqa: D205 - one sentence
    await record_tenants("acme", "globex")
    app = serve(settings, enabled=True)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas") as client:
            yield client


def bearer(issuer: FakeIssuer, user: str = "ann", **claims: Any) -> dict[str, str]:  # noqa: ANN401 - any claim
    """The ``Authorization`` header of a token of the user with these claims, and no client roles."""
    return {"Authorization": f"Bearer {issuer.token(user, atlas_roles=(), **claims)}"}


def refusal(response: httpx.Response) -> tuple[int, str, str]:
    """The status, error code and message of a refused request."""
    body = response.json()
    return response.status_code, body["errorCode"], body["errorMessage"]


async def sign_in(client: httpx.AsyncClient, issuer: FakeIssuer, user: str) -> httpx.Response:
    """A browser's sign-in as the user, from a dashboard page; the provider's return to ``login.jsp``."""
    await client.get("/n/")
    started = await client.get("/login.jsp")
    query = parse_qs(urlparse(started.headers["location"]).query)
    code = issuer.grant_code(query["nonce"][0], user)
    return await client.get("/login.jsp", params={"code": code, "state": query["state"][0]})


@pytest.mark.covers(f"{A}.AuthenticationMiddleware.dispatch", rules=["TEN-03", "TEN-04", "TEN-07"])
async def test__a_bearer_token_without_one_provisioned_tenant_is_refused(
    tenanted: httpx.AsyncClient, issuer: FakeIssuer
) -> None:
    """None, several, unprovisioned or malformed: 403 in Atlas's shape, on an API path and a dashboard page."""
    for path in (SESSION, "/n/index.html"):
        assert refusal(await tenanted.get(path, headers=bearer(issuer))) == (
            403,
            "AURELIUS-403-00-001",
            "ann acts in no tenant: the token names no organization",
        )
    assert refusal(await tenanted.get(SESSION, headers=bearer(issuer, organization=["acme", "globex"]))) == (
        403,
        "AURELIUS-403-00-002",
        "ann acts in no tenant: the token names 2 organizations",
    )
    for alias in ("initech", "Acme", "acme_x"):
        refused = await tenanted.get("/n/index.html", headers=bearer(issuer, organization=[alias]))
        assert refusal(refused) == (403, "AURELIUS-403-00-003", f"Tenant {alias} is not provisioned")
        assert refused.headers["content-type"] == "application/json; charset=UTF-8"
    for alias in ("acme", "operators"):
        assert (await tenanted.get(SESSION, headers=bearer(issuer, organization=[alias]))).status_code == 200


@pytest.mark.covers(f"{R}.dispatch", rules=["TEN-08"])
async def test__the_request_context_carries_its_tenant(
    tenanted: httpx.AsyncClient, issuer: FakeIssuer, settings: ServerSettings, fake_es: FakeClient
) -> None:
    """The tenant is on the request's state and the core's bound context; with tenancy off, none (TEN-01)."""
    seen = await tenanted.get(TENANT, headers=bearer(issuer, organization={"acme": {"groups": ["/atlas-read"]}}))
    assert seen.json() == {"state": "acme", "context": "acme"}
    _ = fake_es
    off = serve(settings, enabled=False)
    async with off.router.lifespan_context(off):
        transport = httpx.ASGITransport(app=off)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas") as client:
            answer = await client.get(TENANT, headers=bearer(issuer, organization=["acme"]))
    assert answer.json() == {"state": None, "context": None}


@pytest.mark.covers(f"{A}.user_of", rules=["TEN-05", "TEN-06"])
async def test__an_operator_writes_in_the_operator_organization_only(
    tenanted: httpx.AsyncClient, issuer: FakeIssuer
) -> None:
    """In a trusting tenant an operator's type change is refused despite its groups; at home it is allowed."""
    in_acme = bearer(issuer, "op", organization={"acme": {"groups": EVERY_GROUP}}, realm_access=OPERATOR)
    assert refusal(await tenanted.post(TYPEDEFS, json=DEFINITIONS, headers=in_acme)) == (
        403,
        "ATLAS-403-00-001",
        "op is not authorized to perform create entity-def t_tenant",
    )
    assert (await tenanted.get(f"{TYPEDEFS}/headers", headers=in_acme)).status_code == 200
    at_home = bearer(issuer, "op", organization={"operators": {"groups": EVERY_GROUP}}, realm_access=OPERATOR)
    assert (await tenanted.post(TYPEDEFS, json=DEFINITIONS, headers=at_home)).status_code == 200


@pytest.mark.covers(f"{L}.login", f"{C}.sign_in", rules=["TEN-03", "TEN-07"])
async def test__a_sign_in_without_a_tenant_keeps_no_session(tenanted: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """The sign-in's return answers 403 in Atlas's shape, the session and its cookie gone; one tenant signs in."""
    issuer.claims_of["ann"] = {"organization": ["acme", "globex"]}
    back = await sign_in(tenanted, issuer, "ann")
    assert refusal(back)[:2] == (403, "AURELIUS-403-00-002")
    assert f'{SESSION_COOKIE}=""' in back.headers["set-cookie"]
    assert (await tenanted.get(SESSION)).status_code == 401
    tenanted.cookies.clear()
    issuer.claims_of["bob"] = {"organization": {"globex": {"groups": ["/atlas-read"]}}}
    assert (await sign_in(tenanted, issuer, "bob")).status_code == 302
    assert (await tenanted.get(TENANT)).json() == {"state": "globex", "context": "globex"}


@pytest.mark.covers(f"{C}.fresh", rules=["TEN-07"])
async def test__a_refresh_without_a_tenant_signs_the_session_out(
    tenanted: httpx.AsyncClient, issuer: FakeIssuer
) -> None:
    """A member removed from the organization loses the session at its next refresh."""
    issuer.lifetime = 5
    issuer.claims_of["ann"] = {"organization": ["acme"]}
    await sign_in(tenanted, issuer, "ann")
    assert (await tenanted.get(SESSION)).status_code == 200
    issuer.claims_of["ann"] = {}
    assert (await tenanted.get(SESSION)).status_code == 401
