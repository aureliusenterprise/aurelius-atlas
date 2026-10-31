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
    is_browser,
    is_open,
    user_of,
)
from aurelius_atlas_store_es.testing.fake import FakeClient
from cryptography.hazmat.primitives.asymmetric import rsa
from fake_issuer import AUTHORIZATION_ENDPOINT, CLIENT_ID, END_SESSION_ENDPOINT, FakeIssuer
from fastapi import FastAPI

A = "aurelius_atlas_server.authentication"
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
    assert user_of(claims, principal_claim="preferred_username", groups_claim="groups") == user_of(
        claims, principal_claim="preferred_username", groups_claim="groups"
    )
    assert user_of(claims, principal_claim="preferred_username", groups_claim="groups").groups == ("/g",)
    named = user_of(claims, principal_claim="email", groups_claim="missing")
    assert (named.name, named.groups) == ("id-1", ("r",))
    assert user_of({}, principal_claim="email", groups_claim="g").groups == ()


@pytest.mark.covers(
    f"{L}.login",
    f"{C}.authorization_url",
    f"{C}.sign_in",
    f"{A}.SessionStore.renew",
    f"{A}.set_session_cookie",
    rules=["AUT-05", "AUT-09"],
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
