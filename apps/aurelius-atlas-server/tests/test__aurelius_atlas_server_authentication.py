"""Authentication (AUT-01 to AUT-09): bearer tokens, the browser sign-in and session, CSRF, sign-out.

Read from Atlas 2.4.0's ``AtlasSecurityConfig``, ``AtlasKeycloakAuthenticationProvider``,
``AtlasCSRFPreventionFilter``, ``AdminResource#getUserProfile`` and the Keycloak adapter it configures, against
a fake identity provider (``fake_issuer``).
"""

from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlparse

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server.authentication import (
    CSRF_REFUSED,
    SESSION_COOKIE,
    SessionStore,
    User,
    is_browser,
    is_open,
    user_of,
)
from aurelius_atlas_server.authorization import ROLE_PRIVILEGES
from aurelius_atlas_server.errors import AtlasError
from aurelius_atlas_server.tenancy import TENANT_ROLES, Tenancy, organizations, tenant_of, tenant_roles
from aurelius_atlas_store_es.testing.fake import FakeClient
from cryptography.hazmat.primitives.asymmetric import rsa
from fake_issuer import AUTHORIZATION_ENDPOINT, CLIENT_ID, END_SESSION_ENDPOINT, FakeIssuer
from fastapi import FastAPI

A = "aurelius_atlas_server.authentication"
TN = "aurelius_atlas_server.tenancy"
TENANCY = Tenancy(tenants=frozenset({"acme", "globex"}))
L = "aurelius_atlas_server.routes.login"
C = "aurelius_atlas_server.oidc_client.OidcClient"
SESSION = "/api/atlas/admin/session"
BROWSER = "Mozilla/5.0 (X11; Linux x86_64) Chrome/130.0"


@pytest.fixture
async def anonymous(settings: ServerSettings, fake_es: FakeClient) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    """The started application and a client without credentials, keeping cookies as a browser does."""
    _ = fake_es
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas") as client:
            yield app, client


async def sign_in(client: httpx.AsyncClient, issuer: FakeIssuer, page: str = "/n/") -> httpx.Response:
    """A browser's sign-in from a page: to ``login.jsp``, to the provider and back; the last answer."""
    asked = await client.get(page)
    assert (asked.status_code, asked.headers["location"]) == (302, "/login.jsp")
    started = await client.get("/login.jsp")
    query = parse_qs(urlparse(started.headers["location"]).query)
    code = issuer.grant_code(query["nonce"][0])
    return await client.get("/login.jsp", params={"code": code, "state": query["state"][0]})


@pytest.mark.covers(f"{A}.is_open", f"{A}.AuthenticationMiddleware.dispatch", rules=["AUT-01", "AUT-04"])
async def test__only_open_paths_answer_without_a_user(anonymous: tuple[FastAPI, httpx.AsyncClient]) -> None:
    """The status and probes answer; an API answers 401 with the challenge; a page goes to sign in."""
    _, client = anonymous
    assert (await client.get("/api/atlas/admin/status")).status_code == 200
    assert (await client.get("/api/atlas/admin/liveness")).status_code == 200
    assert (await client.get("/css/missing.css")).status_code == 404
    refused = await client.get("/api/atlas/admin/version")
    assert (refused.status_code, refused.headers["www-authenticate"], refused.content) == (
        401,
        'Bearer realm="atlas.com"',
        b"",
    )
    assert (await client.get("/index.html", headers={"X-Requested-With": "XMLHttpRequest"})).status_code == 401
    page = await client.get("/n/index.html", params={"tab": "x"})
    assert (page.status_code, page.headers["location"]) == (302, "/login.jsp")
    assert SESSION_COOKIE in page.cookies
    assert {is_open("/n/js/app.js"), is_open("/login.jsp"), is_open("/api/atlas/v2/types/typedefs")} == {True, False}


@pytest.mark.covers(f"{A}.AuthenticationMiddleware.dispatch", f"{A}.user_of", rules=["AUT-02", "AUT-03"])
async def test__a_bearer_token_authenticates_alone(
    anonymous: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """A valid token of an accepted audience names the user; any other token is refused (DV-108)."""
    _, client = anonymous

    async def status(token: str, scheme: str = "Bearer") -> int:
        return (await client.get(SESSION, headers={"Authorization": f"{scheme} {token}"})).status_code

    answer = await client.get(SESSION, headers={"Authorization": f"Bearer {issuer.token('reader', roles=['r'])}"})
    assert (answer.json()["userName"], answer.json()["groups"]) == ("reader", ["r"])
    assert await status(issuer.token(azp=CLIENT_ID)) == 200
    assert await status(issuer.token(expires_in=-60)) == 401
    assert await status(issuer.token(azp="another-client")) == 401
    assert await status(issuer.token(issuer="https://evil.test/realms/master")) == 401
    assert await status(issuer.token(key=rsa.generate_private_key(public_exponent=65537, key_size=2048))) == 401
    assert await status("not-a-token") == 401
    assert await status("dXNlcjpwYXNz", "Basic") == 401
    assert await status("", "Bearer") == 401


@pytest.mark.covers(f"{A}.user_of", rules=["AUT-03"])
def test__a_user_is_named_by_the_configured_claims() -> None:
    """The principal claim, else ``sub``; the groups claim, else the realm roles."""
    claims = {"sub": "id-1", "preferred_username": "ann", "groups": ["/g"], "realm_access": {"roles": ["r"]}}
    found = user_of(claims, principal_claim="preferred_username", groups_claim="groups")
    assert (found.name, found.groups) == ("ann", ("/g",))
    named = user_of(claims, principal_claim="email", groups_claim="missing")
    assert (named.name, named.groups) == ("id-1", ("r",))
    assert user_of({}, principal_claim="email", groups_claim="g").groups == ()


@pytest.mark.covers(
    f"{L}.login",
    f"{C}.authorization_url",
    f"{C}.sign_in",
    f"{A}.SessionStore.renew",
    f"{A}.set_session_cookie",
    rules=["AUT-05", "AUT-09", "RLM-03"],
)
async def test__a_browser_signs_in_at_the_provider(
    anonymous: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """Code flow with state, nonce and PKCE; back to the page first asked, in a new session that names the user."""
    _, client = anonymous
    await client.get("/n/")
    first_cookie = client.cookies[SESSION_COOKIE]
    started = await client.get("/login.jsp")
    location = urlparse(started.headers["location"])
    query = {name: values[0] for name, values in parse_qs(location.query).items()}
    assert f"{location.scheme}://{location.netloc}{location.path}" == AUTHORIZATION_ENDPOINT
    assert (query["client_id"], query["redirect_uri"], query["scope"], query["code_challenge_method"]) == (
        CLIENT_ID,
        "https://aurelius-atlas/login.jsp",
        "openid",
        "S256",
    )
    assert "set-cookie" in started.headers
    back = await client.get("/login.jsp", params={"code": issuer.grant_code(query["nonce"]), "state": query["state"]})
    assert (back.status_code, back.headers["location"]) == (302, "/n/")
    cookie = back.headers["set-cookie"]
    assert all(part in cookie for part in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"))
    assert client.cookies[SESSION_COOKIE] != first_cookie
    session = (await client.get(SESSION)).json()
    assert (session["userName"], session["groups"]) == ("admin", ["default-roles-master"])
    assert (await client.get(SESSION)).json()["_csrfToken"] == session["_csrfToken"]
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, first_cookie)
    assert (await client.get(SESSION)).status_code == 401


@pytest.mark.covers(f"{L}.login", f"{C}.sign_in", rules=["AUT-05"])
async def test__a_sign_in_that_does_not_match_is_refused(
    anonymous: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """Another state, an error, an unknown code or another nonce answer 401; a foreign page is not returned to."""
    _, client = anonymous
    assert (await client.get("/login.jsp", params={"code": "c", "state": "s"})).status_code == 401
    started = await client.get("/login.jsp")
    query = parse_qs(urlparse(started.headers["location"]).query)
    state, nonce = query["state"][0], query["nonce"][0]
    assert (await client.get("/login.jsp", params={"code": issuer.grant_code(nonce), "state": "x"})).status_code == 401
    assert (await client.get("/login.jsp", params={"error": "access_denied", "state": state})).status_code == 401
    assert (await client.get("/login.jsp", params={"code": "unknown", "state": state})).status_code == 401
    other = issuer.grant_code("another-nonce")
    assert (await client.get("/login.jsp", params={"code": other, "state": state})).status_code == 401
    assert (await client.get(SESSION)).status_code == 401
    back = await sign_in(client, issuer, "//evil.test/")
    assert back.headers["location"] == "/"


@pytest.mark.covers(f"{A}.AuthenticationMiddleware.dispatch", f"{A}.is_browser", rules=["AUT-08"])
async def test__a_browsers_unsafe_request_needs_the_csrf_header(
    anonymous: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """With the session alone, a browser's POST needs ``X-XSRF-HEADER`` equal to the session's token (DV-107)."""
    _, client = anonymous
    await sign_in(client, issuer)
    token = (await client.get(SESSION)).json()["_csrfToken"]
    url = "/api/atlas/v2/types/typedefs"
    refused = await client.post(url, json={}, headers={"User-Agent": BROWSER})
    assert (refused.status_code, refused.text) == (400, CSRF_REFUSED)
    wrong = await client.post(url, json={}, headers={"User-Agent": BROWSER, "X-XSRF-HEADER": "wrong"})
    assert wrong.status_code == 400
    assert (await client.post(url, json={}, headers={"User-Agent": BROWSER, "X-XSRF-HEADER": token})).status_code == 200
    assert (await client.post(url, json={}, headers={"User-Agent": "curl/8"})).status_code == 200
    bearer = {"User-Agent": BROWSER, "Authorization": f"Bearer {issuer.token()}"}
    assert (await client.post(url, json={}, headers=bearer)).status_code == 200
    assert (is_browser("Opera/9"), is_browser("Chrome"), is_browser("Chrome/1"), is_browser(None)) == (
        True,
        True,
        False,
        False,
    )


@pytest.mark.covers(f"{C}.fresh", rules=["AUT-06"])
async def test__a_session_refreshes_its_token_until_the_provider_refuses(
    anonymous: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """An access token about to expire is refreshed; a refused refresh signs the session out."""
    _, client = anonymous
    issuer.lifetime = 5
    await sign_in(client, issuer)
    assert (await client.get(SESSION)).status_code == 200
    assert issuer.grants[-1] == "refresh_token"
    issuer.refresh_tokens.clear()
    assert (await client.get(SESSION)).status_code == 401


@pytest.mark.covers(
    f"{A}.SessionStore.get",
    f"{A}.SessionStore.create",
    f"{A}.SessionStore.remove",
    f"{A}.SessionStore.renew",
    rules=["AUT-06"],
)
def test__sessions_end_when_unused_or_crowded_out() -> None:
    """A session unused for the timeout is gone; past the most kept, the least recently used goes."""
    now = [0.0]
    store = SessionStore(60, clock=lambda: now[0], max_sessions=2)
    first, second = store.create(), store.create()
    now[0] = 30
    assert store.get(first.id) is first
    now[0] = 80
    assert store.get(second.id) is None
    assert store.get(first.id) is first
    third, fourth = store.create(), store.create()
    assert (store.get(first.id), store.get(third.id), store.get(fourth.id)) == (None, third, fourth)
    old = third.id
    assert store.renew(third).id != old
    assert store.get(old) is None
    store.remove(fourth.id)
    assert (store.get(fourth.id), store.get(None)) == (None, None)


@pytest.mark.covers(f"{L}.logout", f"{C}.end_session_url", rules=["AUT-07"])
async def test__signing_out_ends_the_session_at_the_provider_too(
    anonymous: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """The session ends, its cookie expires, the browser goes to the provider's end-session endpoint."""
    _, client = anonymous
    await sign_in(client, issuer)
    cookie = client.cookies[SESSION_COOKIE]
    out = await client.get("/logout.html")
    location = urlparse(out.headers["location"])
    query = {name: values[0] for name, values in parse_qs(location.query).items()}
    assert f"{location.scheme}://{location.netloc}{location.path}" == END_SESSION_ENDPOINT
    assert (query["post_logout_redirect_uri"], query["client_id"], "id_token_hint" in query) == (
        "https://aurelius-atlas/",
        CLIENT_ID,
        True,
    )
    assert f'{SESSION_COOKIE}=""' in out.headers["set-cookie"]
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, cookie)
    assert (await client.get(SESSION)).status_code == 401
    again = await client.get("/logout.html")
    assert "id_token_hint" not in again.headers["location"]


@pytest.mark.covers(f"{C}.close", "aurelius_atlas_server.app.build_auth", "aurelius_atlas_server.app.build_oidc")
async def test__the_provider_clients_follow_the_settings(app: FastAPI, settings: ServerSettings) -> None:
    """The verifier takes the server's client and the further audiences; the clients close with the app."""
    async with app.router.lifespan_context(app):
        config = app.state.auth.config
        assert (config.audience, config.audiences, config.realm) == (
            settings.auth_client_id,
            frozenset({"aurelius-atlas-server", "aurelius"}),
            "master",
        )


def tenant_user(**claims: object) -> User:
    """The user of a token of ``ann`` with these claims, while tenancy is on (TEN-02 to TEN-06)."""
    return user_of(
        {"preferred_username": "ann", **claims},
        principal_claim="preferred_username",
        groups_claim="groups",
        client_id=CLIENT_ID,
        tenancy=TENANCY,
    )


@pytest.mark.covers(f"{A}.user_of", rules=["TEN-01"])
def test__without_tenancy_a_user_has_no_tenant_and_the_client_roles() -> None:
    """The organization claim is not read; the roles are the server client's, as before."""
    claims = {
        "preferred_username": "ann",
        "organization": {"acme": {"groups": ["/atlas-admin"]}},
        "resource_access": {CLIENT_ID: {"roles": ["atlas-read"]}},
    }
    found = user_of(claims, principal_claim="preferred_username", groups_claim="groups", client_id=CLIENT_ID)
    assert (found.tenant, found.roles) == (None, {"atlas-read"})


@pytest.mark.covers(f"{TN}.organizations", rules=["TEN-02"])
def test__the_organization_claim_names_the_organizations() -> None:
    """A list's strings, an object's keys; a missing claim or another shape names none."""
    assert organizations({"organization": ["acme", 7, "globex"]}, "organization") == {"acme": None, "globex": None}
    assert organizations({"organization": {"acme": {"id": "1"}}}, "organization") == {"acme": {"id": "1"}}
    assert organizations({"org": ["acme"]}, "org") == {"acme": None}
    for claims in ({}, {"organization": "acme"}, {"organization": 1}, {"organization": None}):
        assert organizations(claims, "organization") == {}


@pytest.mark.covers(
    f"{TN}.tenant_of", f"{TN}.Tenancy.is_provisioned", f"{A}.user_of", rules=["TEN-02", "TEN-03", "TEN-04"]
)
def test__a_user_acts_in_the_one_provisioned_organization_their_token_names() -> None:
    """One organization, list or object, is the tenant; none, several or an unprovisioned one are refused."""
    assert tenant_user(organization=["acme"]).tenant == "acme"
    assert tenant_user(organization={"operators": {}}).tenant == "operators"

    def refused(**claims: object) -> tuple[int, str, str]:
        with pytest.raises(AtlasError) as error:
            tenant_user(**claims)
        return error.value.code.http_status, error.value.code.code, error.value.message

    assert refused() == (403, "AURELIUS-403-00-001", "ann acts in no tenant: the token names no organization")
    assert refused(organization="acme")[1] == "AURELIUS-403-00-001"
    assert refused(organization=["acme", "globex"]) == (
        403,
        "AURELIUS-403-00-002",
        "ann acts in no tenant: the token names 2 organizations",
    )
    assert refused(organization=["initech"]) == (403, "AURELIUS-403-00-003", "Tenant initech is not provisioned")
    for alias in ("Acme", "-acme", "acme_corp", "a" * 64, "acme.corp", ""):
        assert not TENANCY.is_provisioned(alias)
    assert Tenancy(tenants=frozenset({"a" * 63, "0-x"})).is_provisioned("a" * 63)
    with pytest.raises(AtlasError):
        tenant_of({"organization": ["Acme"]}, Tenancy(tenants=frozenset({"Acme"})), "ann")


@pytest.mark.covers(f"{TN}.tenant_roles", f"{A}.user_of", rules=["TEN-05"])
def test__the_roles_in_a_tenant_are_its_own_top_level_role_groups() -> None:
    """The tenant's ``/<role>`` groups grant; nested, unknown, realm groups and client roles grant nothing."""
    found = tenant_user(
        organization={"acme": {"groups": ["/atlas-write", "/atlas-read/team", "/other", "atlas-types", 3]}},
        groups=["/atlas-admin"],
        resource_access={CLIENT_ID: {"roles": ["atlas-admin"]}},
    )
    assert (found.tenant, found.roles, found.groups) == ("acme", {"atlas-write"}, ("/atlas-admin",))
    assert tenant_user(organization=["acme"]).roles == frozenset()
    assert tenant_user(organization={"acme": {"groups": "/atlas-read"}}).roles == frozenset()
    assert set(ROLE_PRIVILEGES) == TENANT_ROLES


@pytest.mark.covers(f"{TN}.tenant_roles", rules=["TEN-06"])
def test__an_operator_only_reads_outside_the_operator_organization() -> None:
    """The operator role caps another tenant's roles at ``atlas-read``; in the operator organization it doesn't."""
    every = ["/atlas-read", "/atlas-write", "/atlas-types", "/atlas-admin"]
    operator = {"roles": ["atlas-operator"]}
    assert tenant_user(organization={"acme": {"groups": every}}, realm_access=operator).roles == {"atlas-read"}
    assert tenant_user(organization={"acme": {"groups": ["/atlas-write"]}}, realm_access=operator).roles == set()
    assert tenant_user(organization={"operators": {"groups": every}}, realm_access=operator).roles == TENANT_ROLES
    assert tenant_user(organization={"acme": {"groups": every}}, realm_access={"roles": []}).roles == TENANT_ROLES
    assert tenant_roles({"realm_access": "x"}, TENANCY, "acme", {"groups": every}) == TENANT_ROLES
