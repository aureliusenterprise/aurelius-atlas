"""The authentication flow against the real issuer, over TLS (6.1; AUTH-03 to AUTH-10, CRS-01 to CRS-03, ADM-06/07).

The stack (``e2e/docker-compose.yaml``) runs the server with ``AUTH_*`` set against dev/keycloak, so
these tests walk what a browser walks — with the dashboard origin's nginx left out: the server's
login start answers instead (DD-036 splits the same flow between the two). The unit tests cover the
same rules against a scripted issuer; these prove the port talks to a real one.
"""

import html
import re
from collections.abc import Awaitable, Callable
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

SESSION = "/api/atlas/admin/session"
WRITER = "aurelius-writer"
BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/144.0"


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(
    "aurelius_atlas_server.auth.guard.login_start",
    "aurelius_atlas_server.auth.guard.login_callback",
    rules=["AUTH-04", "AUTH-06", "AUTH-07", "AUTH-08", "ADM-06", "ADM-07"],
)
async def test__the_login_flow_returns_the_kept_url_with_a_session(
    auth_client: httpx.AsyncClient, sign_in: Callable[..., Awaitable[httpx.Response]]
) -> None:
    """A guarded API call answers 401; the flow through Keycloak ends at the kept URL on a session (AUTH-04 to AUTH-08).

    The access token the session stores is 60 s old by the second session call, past the refresh
    window, so the server refreshes it mid-test (AUTH-09) and the session reports the user
    throughout.
    """
    anonymous = await auth_client.get(SESSION, headers={"Accept": "application/json"})
    assert anonymous.status_code == 401
    assert anonymous.json() == {"errorCode": "ATLAS-401-00-001", "errorMessage": "Authentication is required"}

    start = await auth_client.get(f"/api/atlas/auth/login?next={SESSION}")
    assert start.status_code == 302
    authorize = urlparse(start.headers["location"])
    assert f"{authorize.scheme}://{authorize.netloc}" == "https://keycloak.localhost:8443"
    query = parse_qs(authorize.query)
    assert query["client_id"] == ["aurelius-atlas"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == ["https://localhost:21000/api/atlas/auth/callback"]
    assert query["state"]

    callback = await sign_in(SESSION)  # the sign_in fixture drives this same client's jar
    assert callback.status_code == 302
    assert callback.headers["location"] == SESSION
    cookie = next(m for m in callback.headers.get_list("set-cookie") if m.startswith("ATLASSESSIONID="))
    assert "HttpOnly" in cookie  # AUTH-08
    assert "Secure" in cookie
    assert "samesite=lax" in cookie.lower()  # the attribute's value is case-insensitive (RFC 6265)

    first = await auth_client.get(SESSION)
    assert first.status_code == 200
    assert first.json()["userName"] == WRITER
    assert first.json()["groups"] == ["ADMIN"]  # ADM-06: the realm role the dev user holds
    assert first.json()["atlas.session.timeout.secs"] == 900  # ADM-07: what this stack configured

    second = await auth_client.get(SESSION)  # past the refresh window; AUTH-09 refreshes it
    assert second.status_code == 200
    assert second.json()["userName"] == WRITER


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(
    "aurelius_atlas_server.auth.guard.logout",
    "aurelius_atlas_server.auth.guard.auth_check",
    rules=["AUTH-10"],
)
async def test__logout_ends_the_session_and_sends_the_browser_to_the_issuer(
    auth_client: httpx.AsyncClient, sign_in: Callable[..., Awaitable[httpx.Response]]
) -> None:
    """Logout destroys the session, expires the cookie, and points at the issuer's end-session (AUTH-10)."""
    await sign_in()
    assert (await auth_client.get("/api/atlas/auth/check")).status_code == 200

    left = await auth_client.get("/logout.html")
    assert left.status_code == 302
    end_session = urlparse(left.headers["location"])
    assert end_session.path.endswith("/logout")
    # Atlas's logoutSuccessUrl("/login.jsp"): the flow returns to the login page (DD-040).
    assert parse_qs(end_session.query)["post_logout_redirect_uri"] == ["https://localhost:21000/login.jsp"]
    expired = next(m for m in left.headers.get_list("set-cookie") if m.startswith("ATLASSESSIONID="))
    assert "Max-Age=0" in expired

    assert (await auth_client.get("/api/atlas/auth/check")).status_code == 401
    again = await auth_client.get("/api/atlas/auth/login?next=/")  # a fresh flow starts as before
    assert again.status_code == 302
    assert again.headers["location"].startswith("https://keycloak.localhost:8443")

    # Following the issuer redirect instead of only inspecting its URL: on a session, the end-session
    # endpoint answers its confirm page (the landing URI is registered — an unregistered one is
    # refused with an error instead) and confirming walks the browser to the post-logout landing
    # (DD-040: the direct-server stack's /login.jsp, registered beside the dashboard's).
    await sign_in()
    left = await auth_client.get("/logout.html")
    assert left.status_code == 302
    confirm = await auth_client.get(left.headers["location"])
    assert confirm.status_code == 200
    assert 'id="kc-logout"' in confirm.text  # Keycloak accepted the landing and asks for the final click
    action = re.search(r'<form class="form-actions" action="([^"]+)"', confirm.text)  # the confirm form
    session_code = re.search(r'name="session_code" value="([^"]*)"', confirm.text)  # its one hidden field
    assert action is not None
    assert session_code is not None
    # The form's action is relative to the issuer; the client's base is the server, so join it
    # against the confirm response's own URL.
    done = await auth_client.post(
        str(confirm.url.join(html.unescape(action.group(1)))), data={"session_code": session_code.group(1)}
    )
    assert done.status_code == 302
    assert done.headers["location"] == "https://localhost:21000/login.jsp"


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(
    "aurelius_atlas_server.auth.guard.auth_check",
    "aurelius_atlas_server.auth.guard.wants_html",
    rules=["AUTH-02", "AUTH-06"],
)
async def test__the_check_endpoint_answers_and_a_navigation_starts_the_flow(auth_client: httpx.AsyncClient) -> None:
    """The nginx subrequest target answers 200/401 and never redirects; a navigation on this origin takes 302."""
    check = await auth_client.get("/api/atlas/auth/check")
    assert check.status_code == 401  # public to nginx (AUTH-02), and answers the anonymous state
    assert "location" not in check.headers

    navigation = await auth_client.get("/", headers={"Accept": "text/html"})
    assert navigation.status_code == 302  # the same answer nginx's gate produces upstream (DD-036)
    assert navigation.headers["location"] == "/api/atlas/auth/login?next=/"


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers("aurelius_atlas_server.auth.guard.authenticate", rules=["AUTH-03", "ADM-06"])
async def test__bearer_tokens_authenticate_a_call_without_a_session(
    auth_client: httpx.AsyncClient, writer_bearer: str, reader_bearer: str
) -> None:
    """A verified bearer answers as the user it names, without a session (AUTH-03); roles report as groups (ADM-06)."""
    writer = await auth_client.get(SESSION, headers={"Authorization": f"Bearer {writer_bearer}"})
    assert writer.status_code == 200
    assert writer.json()["userName"] == WRITER
    assert writer.json()["groups"] == ["ADMIN"]
    assert not [m for m in writer.headers.get_list("set-cookie") if m.startswith("ATLASSESSIONID=")]

    reader = await auth_client.get(SESSION, headers={"Authorization": f"Bearer {reader_bearer}"})
    assert reader.status_code == 200
    assert reader.json()["userName"] == "aurelius-reader"
    assert reader.json()["groups"] == []  # the no-roles dev user

    tampered = f"{writer_bearer[:-4]}dead"
    rejected = await auth_client.get(SESSION, headers={"Authorization": f"Bearer {tampered}"})
    assert rejected.status_code == 401  # an invalid bearer is answered 401, never a redirect
    assert auth_client.cookies.get("ATLASSESSIONID") is None


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers("aurelius_atlas_server.auth.csrf.csrf_rejected", rules=["CRS-01", "CRS-02", "CRS-03"])
async def test__csrf_guards_browser_calls_on_the_session(
    auth_client: httpx.AsyncClient, sign_in: Callable[..., Awaitable[httpx.Response]]
) -> None:
    """A browser call on a session needs its reported header (CRS-01, CRS-02); others are exempt (CRS-03)."""
    await sign_in()
    token = (await auth_client.get(SESSION, headers={"Accept": "application/json"})).json()["_csrfToken"]
    assert re.fullmatch(r"[A-Za-z0-9]{20}", token)

    denied = await auth_client.post(SESSION, headers={"User-Agent": BROWSER_UA})
    assert denied.status_code == 400
    assert denied.json() == {"msgDesc": "Missing header or invalid Header value for CSRF Vulnerability Protection"}

    wrong = await auth_client.post(SESSION, headers={"User-Agent": BROWSER_UA, "X-XSRF-HEADER": token + "x"})
    assert wrong.status_code == 400

    # The right token passes the CSRF gate; the route itself answers 405 (POST is not the session's).
    allowed = await auth_client.post(SESSION, headers={"User-Agent": BROWSER_UA, "X-XSRF-HEADER": token})
    assert allowed.status_code == 405

    service = await auth_client.post(SESSION, headers={"User-Agent": "curl/8.14.0"})
    assert service.status_code == 405  # CRS-03: a non-browser User-Agent is exempt

    stable = (await auth_client.get(SESSION, headers={"Accept": "application/json"})).json()["_csrfToken"]
    assert stable == token  # CRS-02: the token stays the session's for its life
