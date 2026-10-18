"""The guard and the relying party's endpoints (AUTH-01 to AUTH-10, CRS-01, ADM-06, ADM-07).

The issuer is replaced by a fake hung on ``app.state.oidc``: unit tests never reach Keycloak, and each
test scripts the answer the issuer gives (claims, refusal, unreachable). Everything else — the guard,
the sessions, the CSRF check, the error bodies — is the application's own.
"""

import json
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server.auth.csrf import csrf_denied
from aurelius_atlas_server.auth.guard import (
    SESSION_COOKIE,
    LoginStates,
    bearer_of,
    is_public,
    issuer_error_response,
    safe_next,
    unauthorized_response,
    wants_html,
)
from aurelius_atlas_server.auth.oidc import OidcError, TokenError, Tokens
from aurelius_atlas_server.errors import ATLAS_JSON_MEDIA_TYPE
from aurelius_atlas_store_es import store
from aurelius_atlas_store_es.testing.fake import FakeClient
from fastapi import FastAPI, Request

ISSUER = "https://keycloak.localhost:8443/realms/master"
REDIRECT_URI = "https://localhost:8444/api/atlas/auth/callback"
ORIGIN = "https://localhost:8444"
AUTH_ERROR = {"errorCode": "ATLAS-401-00-001", "errorMessage": "Authentication is required"}
CLAIMS = {
    "preferred_username": "writer",
    "sub": "1111",
    "realm_access": {"roles": ["ADMIN"]},
    "resource_access": {"aurelius-atlas": {"roles": ["aurelius-write"]}},
}
BROWSER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
ISSUER_AT = "access"
ISSUER_RT = "refresh"
ISSUER_AT2 = "access-2"
ISSUER_RT2 = "refresh-2"
ISSUER_DOWN_ERROR = "the issuer is down"


class FakeOidc:
    """The answers the guard expects from an issuer, scripted per test."""

    def __init__(self) -> None:
        self.authorize_calls: list[dict[str, str]] = []
        self.refresh_calls = 0
        self.verify_raises: Exception | None = None
        self.exchange_raises: Exception | None = None
        self.refresh_raises: Exception | None = None
        self.end_session: str | None = f"{ISSUER}/protocol/openid-connect/logout"
        self.end_session_raises = False
        self.closed = False

    async def authorize_url(self, *, redirect_uri: str, state: str, nonce: str | None = None) -> tuple[str, str]:
        """The authorization URL a login start asks for, with the parameters the test can read back."""
        self.authorize_calls.append({"redirect_uri": redirect_uri, "state": state, "nonce": nonce or ""})
        url = httpx.URL(
            f"{ISSUER}/protocol/openid-connect/auth",
            params={"state": state, "client_id": "aurelius-atlas", "redirect_uri": redirect_uri, "nonce": nonce or ""},
        )
        return str(url), "verifier"

    async def exchange(
        self,
        *,
        code: str,  # noqa: ARG002 - the real client's interface, unused by the scripted answer
        code_verifier: str,  # noqa: ARG002
        redirect_uri: str,  # noqa: ARG002
        nonce: str,  # noqa: ARG002
    ) -> Tokens:
        """The tokens a callback exchange gets back, or the scripted refusal."""
        if self.exchange_raises is not None:
            raise self.exchange_raises
        return Tokens(
            access_token=ISSUER_AT,
            refresh_token=ISSUER_RT,
            expires_at=time.monotonic() + 300,
            claims=dict(CLAIMS),
        )

    async def refresh(self, refresh_token: str) -> Tokens:  # noqa: ARG002 - the interface, unused by the answer
        """The refreshed tokens, or the scripted refusal."""
        self.refresh_calls += 1
        if self.refresh_raises is not None:
            raise self.refresh_raises
        return Tokens(access_token=ISSUER_AT2, refresh_token=ISSUER_RT2, expires_at=time.monotonic() + 300)

    async def verify_access_token(self, token: str) -> dict[str, object]:  # noqa: ARG002 - the interface
        """The claims a bearer verifies to, or the scripted refusal."""
        if self.verify_raises is not None:
            raise self.verify_raises
        return dict(CLAIMS)

    async def end_session_url(self, *, post_logout_redirect_uri: str) -> str | None:
        """The issuer's end-session URL, None when it has none, or the scripted unreachability."""
        if self.end_session_raises:
            raise OidcError(ISSUER_DOWN_ERROR)
        if self.end_session is None:
            return None
        return f"{self.end_session}?post_logout_redirect_uri={post_logout_redirect_uri}"

    async def aclose(self) -> None:
        """Record that the application closed the client with itself."""
        self.closed = True


@pytest.fixture
def fake_es(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    """The fake Elasticsearch the store builds."""
    fake = FakeClient()

    def build(**kwargs: object) -> FakeClient:
        _ = kwargs
        return fake

    monkeypatch.setattr(store, "AsyncElasticsearch", build)
    return fake


def _settings(ca_file: Path, **auth: object) -> ServerSettings:
    fields: dict[str, object] = {
        "elasticsearch_hosts": ["https://localhost:9200"],
        "elasticsearch_password": "test-password",
        "elasticsearch_ca_certs": ca_file,
        "revision": "abc123",
        "models_dir": "tests/no-models-does-not-exist",
    }
    fields.update(auth)
    return ServerSettings.model_validate(fields)


AUTH_FIELDS: dict[str, object] = {
    "auth_issuer": ISSUER,
    "auth_client_secret": "rp-secret",
    "auth_redirect_uri": REDIRECT_URI,
}


@asynccontextmanager
async def served(
    settings: ServerSettings,
) -> AsyncIterator[tuple[httpx.AsyncClient, FakeOidc, FastAPI]]:
    """The application running in-process with a fake issuer in place of the real one."""
    app = create_app(settings)
    fake = FakeOidc()
    app.state.oidc = fake  # replace before the lifespan: the flow never leaves the process
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            yield client, fake, app


@pytest.fixture
async def auth_client(fake_es: FakeClient, ca_file: Path) -> AsyncIterator[tuple[httpx.AsyncClient, FakeOidc, FastAPI]]:
    """A client of the application with authentication on."""
    _ = fake_es
    async with served(_settings(ca_file, **AUTH_FIELDS)) as client:
        yield client


async def _login(client: httpx.AsyncClient, *, next_url: str | None = None) -> tuple[str, httpx.Response]:
    """Run the browser flow end to end against the fake issuer; return the session cookie and callback."""
    start = await client.get("/api/atlas/auth/login", params={"next": next_url or "/"}, follow_redirects=False)
    assert start.status_code == 302
    state = httpx.URL(start.headers["location"]).params["state"]
    callback = await client.get(
        "/api/atlas/auth/callback", params={"code": "code-1", "state": state}, follow_redirects=False
    )
    assert callback.status_code == 302
    sid = callback.headers["set-cookie"].split("=", 1)[1].split(";", 1)[0]
    return sid, callback


def _cookie(sid: str) -> dict[str, str]:
    return {"cookie": f"{SESSION_COOKIE}={sid}"}


@pytest.mark.covers("aurelius_atlas_server.auth.guard.is_public", rules=["AUTH-02"])
@pytest.mark.parametrize(
    ("path", "public"),
    [
        ("/api/atlas/admin/status", True),
        ("/api/atlas/admin/version", True),
        ("/api/atlas/admin/liveness", True),
        ("/api/atlas/admin/readiness", True),
        ("/api/atlas/auth/login", True),
        ("/api/atlas/auth/callback", True),
        ("/api/atlas/auth/check", True),
        ("/logout.html", True),
        ("/api/atlas/admin/session", False),
        ("/api/atlas/entity", False),
        ("/api/atlas/admin/statuses", False),
    ],
)
def test__the_public_paths_are_the_ones_atlas_answers_without_a_principal(path: str, *, public: bool) -> None:
    """Probes, status, version, the login endpoints and logout are open; everything else is guarded."""
    assert is_public(path) is public


@pytest.mark.covers("aurelius_atlas_server.auth.guard.unauthorized_response", rules=["AUTH-04"])
def test__a_rejected_call_answers_the_atlas_error_body() -> None:
    """The 401 carries an Atlas error body with the media type of every Atlas answer, never HTML."""
    response = unauthorized_response()

    assert response.status_code == 401
    assert response.media_type == ATLAS_JSON_MEDIA_TYPE


@pytest.mark.covers("aurelius_atlas_server.auth.guard.issuer_error_response", rules=["AUTH-07"])
def test__an_unreachable_issuer_answers_the_internal_error_body() -> None:
    """The 500 for an unreachable issuer is an Atlas error body too, not framework HTML."""
    response = issuer_error_response()

    assert response.status_code == 500
    assert response.media_type == ATLAS_JSON_MEDIA_TYPE
    assert json.loads(bytes(response.body)) == {
        "errorCode": "ATLAS-500-00-001",
        "errorMessage": "Internal server error cannot reach the identity provider",
    }


@pytest.mark.covers("aurelius_atlas_server.auth.csrf.csrf_denied", rules=["CRS-01"])
def test__the_csrf_denial_is_the_filters_400_body() -> None:
    """The CSRF refusal keeps the filter's status, message and JSON media type."""
    response = csrf_denied()

    assert response.status_code == 400
    assert json.loads(bytes(response.body)) == {
        "msgDesc": "Missing header or invalid Header value for CSRF Vulnerability Protection"
    }


def _scope_request(headers: dict[str, str], *, method: str = "GET", path: str = "/api/atlas/entity") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "scheme": "https",
        "server": ("aurelius-atlas", 443),
        "client": ("127.0.0.1", 1234),
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
    }
    return Request(scope)


@pytest.mark.covers("aurelius_atlas_server.auth.guard.bearer_of", rules=["AUTH-03"])
@pytest.mark.parametrize(
    ("header", "token"),
    [
        ({"authorization": "Bearer abc.def.ghi"}, "abc.def.ghi"),
        ({"authorization": "bearer abc.def.ghi"}, "abc.def.ghi"),
        ({"authorization": "Bearer  spaced  "}, "spaced"),
        ({"authorization": "Basic dXNlcjpwdw=="}, None),
        ({"authorization": "Bearer "}, None),
        ({}, None),
    ],
)
def test__the_bearer_is_the_authorization_headers_token(header: dict[str, str], token: str | None) -> None:
    """The adapter's header matcher: only a Bearer scheme yields a token (KEYCLOAK_REQUEST_MATCHER)."""
    assert bearer_of(_scope_request(header)) == token


@pytest.mark.covers("aurelius_atlas_server.auth.guard.wants_html", rules=["AUTH-06", "AUTH-04"])
@pytest.mark.parametrize(
    ("accept", "path", "html"),
    [
        ("text/html", "/n/v2/index.html", True),
        ("text/html,application/xhtml+xml", "/", True),
        ("text/html", "/api/atlas/admin/session", False),  # an XHR asking for HTML stays a 401
        ("application/json", "/n/v2/index.html", False),
        ("", "/n/v2", False),
    ],
)
def test__a_navigation_is_told_from_an_api_call(accept: str, path: str, *, html: bool) -> None:
    """Only an Accept of text/html outside /api/ is a navigation that may start the login (DV-11)."""
    assert wants_html(_scope_request({"accept": accept}, path=path)) is html


@pytest.mark.covers("aurelius_atlas_server.auth.guard.safe_next", rules=["AUTH-06"])
@pytest.mark.parametrize(
    ("raw", "kept"),
    [
        (None, "/"),
        ("/n/v2/index.html", "/n/v2/index.html"),
        ("/api/atlas/admin/session?a=1", "/api/atlas/admin/session?a=1"),
        ("https://evil.example/steal", "/"),
        ("//evil.example/steal", "/"),
        ("javascript:alert(1)", "/"),
        ("relative/path", "/"),
    ],
)
def test__a_login_returns_only_to_paths_of_this_origin(raw: str | None, kept: str) -> None:
    """The kept URL is a path of this origin; anything else falls back to the root (no open redirect)."""
    assert safe_next(raw) == kept


@pytest.mark.covers(
    "aurelius_atlas_server.auth.guard.LoginStates.start",
    "aurelius_atlas_server.auth.guard.LoginStates.take",
    rules=["AUTH-06", "AUTH-07"],
)
def test__a_login_state_is_kept_once() -> None:
    """The flow a start keeps is handed to its callback once, and to nobody after that."""
    states = LoginStates()
    pending = states.start("/n/v2")

    assert pending.state
    assert pending.nonce
    assert pending.next == "/n/v2"
    assert states.take(pending.state) is pending
    assert states.take(pending.state) is None  # replayed state: unknown
    assert states.take(None) is None


@pytest.mark.covers("aurelius_atlas_server.auth.guard.LoginStates.take", rules=["AUTH-06"])
def test__an_expired_login_state_is_swept() -> None:
    """A flow older than its TTL never reaches a callback."""
    states = LoginStates(ttl_seconds=-1)
    pending = states.start("/")

    assert states.take(pending.state) is None


@pytest.mark.covers("aurelius_atlas_server.auth.guard.install_auth", rules=["AUTH-01"])
async def test__without_an_issuer_the_server_answers_as_before(client: httpx.AsyncClient) -> None:
    """No issuer, no guard: the session endpoint answers, reporting nobody (DV-04), and has no auth endpoints."""
    session = await client.get("/api/atlas/admin/session")

    assert session.status_code == 200
    assert session.json()["userName"] is None
    assert session.json()["groups"] == []
    assert session.json()["atlas.entity.update.allowed"] is False
    assert re.fullmatch(r"[A-Za-z0-9]{20}", session.json()["_csrfToken"])
    assert "atlas.session.timeout.secs" not in session.json()
    assert (await client.get("/api/atlas/auth/check")).status_code == 404
    assert (await client.get("/logout.html", follow_redirects=False)).status_code == 404


@pytest.mark.covers("aurelius_atlas_server.auth.guard.guard", rules=["AUTH-02"])
async def test__public_endpoints_answer_without_a_principal(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """Status, version, liveness and readiness answer although authentication is on (AUTH-02, DV-12)."""
    client, _, _ = auth_client

    assert (await client.get("/api/atlas/admin/status")).json() == {"Status": "ACTIVE"}
    assert (await client.get("/api/atlas/admin/version")).status_code == 200
    assert (await client.get("/api/atlas/admin/liveness")).status_code == 200
    assert (await client.get("/api/atlas/admin/readiness")).status_code == 200


@pytest.mark.covers("aurelius_atlas_server.auth.guard.guard", rules=["AUTH-04"])
async def test__an_unauthenticated_api_call_is_401_never_a_redirect(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """An API call without a session gets the Atlas 401 body; it is never sent to the login (DV-11)."""
    client, _, _ = auth_client

    response = await client.get("/api/atlas/admin/session", follow_redirects=False)

    assert response.status_code == 401
    assert response.headers["content-type"] == ATLAS_JSON_MEDIA_TYPE
    assert response.json() == AUTH_ERROR
    assert "location" not in response.headers


@pytest.mark.covers("aurelius_atlas_server.auth.guard.guard", rules=["AUTH-06"])
async def test__an_unauthenticated_page_load_starts_the_login(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """A navigation (Accept: text/html, not /api/) without a session is sent to the login start, keeping its URL."""
    client, _, _ = auth_client

    response = await client.get("/n/v2/index.html", headers={"accept": "text/html"}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/api/atlas/auth/login?next=/n/v2/index.html"


@pytest.mark.covers(
    "aurelius_atlas_server.auth.guard.login_start",
    "aurelius_atlas_server.auth.guard.login_callback",
    rules=["AUTH-06", "AUTH-07", "AUTH-08"],
)
async def test__the_browser_flow_ends_with_a_session_cookie(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """The browser flow ends with a session cookie that answers the API."""
    client, fake, _ = auth_client

    start = await client.get("/api/atlas/auth/login?next=/n/v2", follow_redirects=False)
    assert start.status_code == 302
    authorize = httpx.URL(start.headers["location"])
    assert str(authorize).startswith(f"{ISSUER}/protocol/openid-connect/auth?")
    assert authorize.params["redirect_uri"] == REDIRECT_URI
    assert authorize.params["nonce"]  # the id_token check of AUTH-07
    assert fake.authorize_calls[-1]["redirect_uri"] == REDIRECT_URI

    callback = await client.get(
        "/api/atlas/auth/callback",
        params={"code": "code-1", "state": authorize.params["state"]},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert callback.headers["location"] == "/n/v2"
    cookie = callback.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite" in cookie
    assert "jsessionid" not in str(callback.url).lower()  # AUTH-08: no URL rewriting
    sid = cookie.split("=", 1)[1].split(";", 1)[0]

    session = await client.get("/api/atlas/admin/session", headers=_cookie(sid))
    assert session.status_code == 200
    assert session.json()["userName"] == "writer"
    assert session.json()["groups"] == ["ADMIN", "aurelius-write"]  # ADM-06


@pytest.mark.covers("aurelius_atlas_server.auth.guard.login_callback", rules=["AUTH-07"])
@pytest.mark.parametrize(
    ("code", "state", "raises", "status"),
    [
        (None, "kept", None, 401),
        ("code", None, None, 401),
        ("code", "kept", "token", 401),
        ("code", "kept", "issuer", 500),
    ],
)
async def test__a_callback_that_cannot_be_trusted_mints_no_session(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
    code: str | None,
    state: str | None,
    raises: str | None,
    status: int,
) -> None:
    """A missing code or state, a failed exchange, or an unreachable issuer answer 401/500 and create no session."""
    client, fake, app = auth_client
    if raises == "token":
        fake.exchange_raises = TokenError("bad id_token")
    elif raises == "issuer":
        fake.exchange_raises = OidcError("unreachable")
    start = await client.get("/api/atlas/auth/login", follow_redirects=False)
    if state == "kept":
        state = httpx.URL(start.headers["location"]).params["state"]

    response = await client.get(
        "/api/atlas/auth/callback", params={"code": code, "state": state}, follow_redirects=False
    )

    assert response.status_code == status
    assert "set-cookie" not in response.headers
    assert len(app.state.sessions) == 0


@pytest.mark.covers("aurelius_atlas_server.auth.guard.authenticate", rules=["AUTH-03"])
async def test__a_bearer_token_answers_as_its_principal_without_a_session(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """A verified bearer names the user and groups (ADM-06) and never touches the session store (AUTH-03)."""
    client, _, app = auth_client

    session = await client.get("/api/atlas/admin/session", headers={"authorization": "Bearer access"})

    assert session.status_code == 200
    assert session.json()["userName"] == "writer"
    assert session.json()["groups"] == ["ADMIN", "aurelius-write"]
    assert len(app.state.sessions) == 0  # a bearer call is stateless


@pytest.mark.covers("aurelius_atlas_server.auth.guard.authenticate", rules=["AUTH-03"])
async def test__a_bearer_the_issuer_does_not_verify_is_401(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """A bearer token whose signature, issuer or audience fails verification is refused (AUTH-03)."""
    client, fake, _ = auth_client
    fake.verify_raises = TokenError("no key for kid")

    response = await client.get("/api/atlas/admin/session", headers={"authorization": "Bearer garbage"})

    assert response.status_code == 401
    assert response.json() == AUTH_ERROR


@pytest.mark.covers("aurelius_atlas_server.auth.guard.guard", rules=["AUTH-03"])
async def test__an_unreachable_issuer_is_a_server_error_not_a_rejection(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """While Keycloak is down, a bearer call answers 500 — the caller's token may be fine (SRV-04)."""
    client, fake, _ = auth_client
    fake.verify_raises = OidcError("cannot reach the issuer")

    response = await client.get("/api/atlas/admin/session", headers={"authorization": "Bearer access"})

    assert response.status_code == 500
    assert response.json() == {
        "errorCode": "ATLAS-500-00-001",
        "errorMessage": "Internal server error cannot reach the identity provider",
    }


@pytest.mark.covers("aurelius_atlas_server.auth.guard.auth_check", rules=["AUTH-05"])
async def test__the_check_endpoint_answers_nginx_200_or_401_never_a_redirect(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """The auth_request endpoint mirrors the session for nginx: 200 with one, 401 without (DD-036)."""
    client, _, _ = auth_client

    assert (await client.get("/api/atlas/auth/check")).status_code == 401
    sid, _ = await _login(client)
    assert (await client.get("/api/atlas/auth/check", headers=_cookie(sid))).status_code == 200


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_session", rules=["CRS-02"])
async def test__the_sessions_csrf_token_is_minted_once_and_kept(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """The token of a session appears on every call and never changes; two calls without a session differ."""
    client, _, _ = auth_client
    sid, _ = await _login(client)

    first = (await client.get("/api/atlas/admin/session", headers=_cookie(sid))).json()["_csrfToken"]
    second = (await client.get("/api/atlas/admin/session", headers=_cookie(sid))).json()["_csrfToken"]
    assert first == second

    client.cookies.clear()  # the answer without any session
    anonymous = await client.get("/api/atlas/admin/session")
    assert anonymous.status_code == 401  # no session: not even a token is handed out


@pytest.mark.covers("aurelius_atlas_server.auth.guard.guard", rules=["CRS-01", "CRS-02"])
async def test__a_browser_post_without_the_csrf_header_is_denied(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """A browser POST without the CSRF header gets the filter's 400; with it, the request proceeds."""
    client, _, _ = auth_client
    sid, _ = await _login(client)
    token = (await client.get("/api/atlas/admin/session", headers=_cookie(sid))).json()["_csrfToken"]

    denied = await client.post("/api/atlas/entity", headers={**_cookie(sid), "user-agent": BROWSER})
    assert denied.status_code == 400
    assert denied.json() == {"msgDesc": "Missing header or invalid Header value for CSRF Vulnerability Protection"}

    wrong = await client.post(
        "/api/atlas/entity", headers={**_cookie(sid), "user-agent": BROWSER, "X-XSRF-HEADER": "wrong"}
    )
    assert wrong.status_code == 400

    passed = await client.post(
        "/api/atlas/entity", headers={**_cookie(sid), "user-agent": BROWSER, "X-XSRF-HEADER": token}
    )
    assert passed.status_code == 404  # the path does not exist, but the CSRF check let it through
    assert passed.json().get("msgDesc") is None


@pytest.mark.covers("aurelius_atlas_server.auth.guard.guard", rules=["CRS-03"])
async def test__a_service_client_post_needs_no_csrf_header(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """A non-browser user agent (a service client with a bearer) is not CSRF-guarded (CRS-03)."""
    client, _, _ = auth_client

    response = await client.post(
        "/api/atlas/entity", headers={"authorization": "Bearer access", "user-agent": "atlas-sdk/0.6"}
    )

    assert response.status_code == 404  # not the CSRF 400


@pytest.mark.covers("aurelius_atlas_server.auth.guard.authenticate", rules=["AUTH-09"])
async def test__a_session_near_expiry_refreshes_and_a_failed_refresh_destroys_it(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """A request within the skew refreshes the access token; a refresh the issuer refuses costs the session."""
    client, fake, app = auth_client
    sid, _ = await _login(client)
    session = app.state.sessions.get(sid)
    assert session is not None
    session.access_expires_at = time.monotonic() + 10  # inside the 60 s skew

    response = await client.get("/api/atlas/admin/session", headers=_cookie(sid))
    assert response.status_code == 200
    assert fake.refresh_calls == 1
    assert session.access_token == ISSUER_AT2

    session.access_expires_at = time.monotonic() + 10
    fake.refresh_raises = TokenError("invalid_grant")
    destroyed = await client.get("/api/atlas/admin/session", headers=_cookie(sid))
    assert destroyed.status_code == 401
    assert app.state.sessions.get(sid) is None  # AUTH-09: destroyed, not answered


@pytest.mark.covers("aurelius_atlas_server.auth.guard.logout", rules=["AUTH-10"])
async def test__logout_ends_the_session_and_the_issuers(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """Logout destroys the session, expires the cookie, and sends the browser to the issuer's end-session endpoint."""
    client, _, app = auth_client
    sid, _ = await _login(client)

    response = await client.get("/logout.html", headers=_cookie(sid), follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(f"{ISSUER}/protocol/openid-connect/logout")
    # Atlas's logoutSuccessUrl("/login.jsp"): the browser returns to the login page (DD-040).
    assert f"post_logout_redirect_uri={ORIGIN}/login.jsp" in location
    assert f"{SESSION_COOKIE}=" in response.headers["set-cookie"]  # expired by deletion
    assert app.state.sessions.get(sid) is None
    assert (await client.get("/api/atlas/admin/session", headers=_cookie(sid))).status_code == 401


@pytest.mark.covers("aurelius_atlas_server.auth.guard.logout", rules=["AUTH-10"])
async def test__logout_without_the_issuers_end_session_lands_at_the_login_page(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """An issuer without an end-session endpoint (or unreachable) still lands the browser at the login page."""
    client, fake, _ = auth_client
    sid, _ = await _login(client)
    fake.end_session = None

    response = await client.get("/logout.html", headers=_cookie(sid), follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == f"{ORIGIN}/login.jsp"

    sid, _ = await _login(client)
    fake.end_session_raises = True
    response = await client.get("/logout.html", headers=_cookie(sid), follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == f"{ORIGIN}/login.jsp"


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_session", rules=["ADM-07"])
async def test__the_session_reports_the_idle_timeout_when_configured(fake_es: FakeClient, ca_file: Path) -> None:
    """atlas.session.timeout.secs appears with the configured idle seconds, and only then (ADM-07)."""
    _ = fake_es
    async with served(_settings(ca_file, auth_session_idle_seconds=3600, **AUTH_FIELDS)) as (client, _, _):
        anonymous = await client.get("/api/atlas/admin/session")
        assert anonymous.status_code == 401
        sid, _ = await _login(client)
        session = (await client.get("/api/atlas/admin/session", headers=_cookie(sid))).json()
        assert session["atlas.session.timeout.secs"] == 3600
    async with served(_settings(ca_file, **AUTH_FIELDS)) as (client, _, _):
        sid, _ = await _login(client)
        session = (await client.get("/api/atlas/admin/session", headers=_cookie(sid))).json()
        assert "atlas.session.timeout.secs" not in session


@pytest.mark.covers("aurelius_atlas_server.auth.guard.login_start", rules=["AUTH-06"])
async def test__a_login_with_a_foreign_next_lands_at_the_root(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """A next aimed at another site is dropped: the callback returns to the root."""
    client, _, _ = auth_client
    start = await client.get("/api/atlas/auth/login?next=https://evil.example/steal", follow_redirects=False)
    state = httpx.URL(start.headers["location"]).params["state"]

    callback = await client.get(
        "/api/atlas/auth/callback", params={"code": "code-1", "state": state}, follow_redirects=False
    )
    assert callback.headers["location"] == "/"


@pytest.mark.covers("aurelius_atlas_server.auth.guard.login_start", rules=["AUTH-06"])
async def test__a_login_start_with_an_unreachable_issuer_is_500(
    auth_client: tuple[httpx.AsyncClient, FakeOidc, FastAPI],
) -> None:
    """When discovery fails the login cannot start: 500, the Atlas error body (SRV-04)."""
    client, fake, _ = auth_client

    async def refusing_authorize_url(*, redirect_uri: str, state: str, nonce: str | None = None) -> tuple[str, str]:
        """The scripted answer: the issuer cannot be reached."""
        _ = redirect_uri, state, nonce  # the interface, unused by the scripted refusal
        raise OidcError(ISSUER_DOWN_ERROR)

    fake.authorize_url = refusing_authorize_url
    response = await client.get("/api/atlas/auth/login", follow_redirects=False)

    assert response.status_code == 500
    assert response.json()["errorCode"] == "ATLAS-500-00-001"
