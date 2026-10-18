"""The authentication guard and the auth endpoints of the relying party (AUTH-01 to AUTH-10, DD-036).

The guard ports what the Keycloak filter chain of ``AtlasSecurityConfig`` decides per request, in the
order that chain applies it: the CSRF check of ``AtlasCSRFPreventionFilter``, then the principal — a
verified bearer (the ``Authorization`` header ``KEYCLOAK_REQUEST_MATCHER`` matches), else a session, else
rejection. A rejected API call answers 401 with the Atlas error body (AUTH-04, DV-11); a rejected
navigation starts the browser flow (AUTH-06), whose endpoints answer under ``/api/atlas/auth`` — the path
the dashboard origin's ``auth_request`` gate redirects page loads to (DD-036).

The guard returns its rejections instead of raising: a Starlette user middleware sits outside the
exception-handler middleware, so a raise here would answer 500 rather than the error body (SRV-04).
"""

import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

from fastapi import APIRouter, FastAPI, Request, Response

from aurelius_atlas_server.auth.csrf import csrf_denied, csrf_rejected
from aurelius_atlas_server.auth.oidc import REFRESH_SKEW_SECONDS, OidcClient, OidcError, TokenError, principal_of
from aurelius_atlas_server.auth.sessions import Session, SessionStore
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.settings import ServerSettings

LOGGER = logging.getLogger(__name__)

SESSION_COOKIE = "ATLASSESSIONID"
"""The session cookie's name, which Atlas's logout deletes."""

LOGIN_PATH = "/api/atlas/auth/login"
CALLBACK_PATH = "/api/atlas/auth/callback"
CHECK_PATH = "/api/atlas/auth/check"
LOGOUT_PATH = "/logout.html"
LOGIN_JSP_PATH = "/login.jsp"
"""Atlas's ``logoutSuccessUrl``: the login page the browser lands on after logout (DD-040)."""

AUTH = APIRouter(prefix="/api/atlas/auth", tags=["Auth"])
"""The relying party's endpoints, under ``/api/`` so the dashboard origin's proxy carries them."""

PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/api/atlas/admin/status",  # public in Atlas's ignore list (ADM-02)
        "/api/atlas/admin/version",
        LOGOUT_PATH,  # AUTH-10: logging out without a session is a no-op, not a loop
    }
)
PUBLIC_PREFIXES: tuple[str, ...] = (
    "/api/atlas/admin/liveness",  # DV-12: probes and load balancers hold no session
    "/api/atlas/admin/readiness",
    LOGIN_PATH,
    CALLBACK_PATH,
    CHECK_PATH,
)
"""What the guard answers without a principal (AUTH-02)."""


def is_public(path: str) -> bool:
    """Whether a path is one the guard never demands a principal for (AUTH-02)."""
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def unauthorized_response() -> AtlasJSONResponse:
    """The 401 answer of the guard, with the Atlas error body (AUTH-04, DV-11)."""
    error = AtlasError(AtlasErrorCode.UNAUTHENTICATED)
    return AtlasJSONResponse(status_code=401, content={"errorCode": error.code.code, "errorMessage": error.message})


def issuer_error_response() -> AtlasJSONResponse:
    """The 500 answer for an issuer that cannot be reached (AUTH-07, SRV-04)."""
    error = AtlasError(AtlasErrorCode.INTERNAL_ERROR, "cannot reach the identity provider")
    return AtlasJSONResponse(status_code=500, content={"errorCode": error.code.code, "errorMessage": error.message})


@dataclass
class PendingLogin:
    """The in-flight browser flow of one login start (AUTH-06)."""

    state: str
    nonce: str
    next: str
    created_at: float
    verifier: str = ""
    """The PKCE verifier the authorization URL was built with, kept for the exchange (AUTH-07)."""


class LoginStates:
    """The login flows in flight between the login start and its callback (AUTH-06, AUTH-07)."""

    def __init__(self, *, ttl_seconds: float = 600) -> None:
        self._pending: dict[str, PendingLogin] = {}
        self._ttl = ttl_seconds

    def start(self, next_url: str) -> PendingLogin:
        """Keep a newly started flow — state and nonce minted here — and return it."""
        self._sweep()
        pending = PendingLogin(
            state=secrets.token_urlsafe(24),
            nonce=secrets.token_urlsafe(16),
            next=next_url,
            created_at=time.monotonic(),
        )
        self._pending[pending.state] = pending
        return pending

    def take(self, state: str | None) -> PendingLogin | None:
        """Consume the flow a callback names; a state used twice is unknown the second time (AUTH-07)."""
        self._sweep()
        return self._pending.pop(state, None) if state is not None else None

    def _sweep(self) -> None:
        now = time.monotonic()
        for state in [s for s, p in self._pending.items() if now - p.created_at > self._ttl]:
            del self._pending[state]


@dataclass
class Principal:
    """A resolved principal: who the request came from, and whose session it used, if any."""

    username: str
    groups: list[str]
    session: Session | None = field(default=None)


@dataclass(frozen=True)
class NoPrincipal:
    """The request carries neither a session nor a bearer token."""


@dataclass(frozen=True)
class BearerRejected:
    """The request carries a bearer token the issuer's keys do not verify (AUTH-03): always a 401."""


@dataclass(frozen=True)
class IssuerUnreachable:
    """The issuer could not be reached while a token was verified: a 500, not the caller's fault."""


def safe_next(raw: str | None) -> str:
    """The URL a login may return to: a path of this origin, or the root.

    A URL with a scheme or host, or one not starting at the root, is dropped so the login start cannot
    be aimed at another site (an open redirect).
    """
    if raw is None:
        return "/"
    parts = urlsplit(raw)
    if parts.scheme or parts.netloc or not raw.startswith("/"):
        return "/"
    return raw


def bearer_of(request: Request) -> str | None:
    """The bearer token of the request's ``Authorization`` header, or None (AUTH-03)."""
    header = request.headers.get("authorization")
    if header is not None and header.lower().startswith("bearer "):
        return header[7:].strip() or None  # an empty token is no token: the session behind it still answers
    return None


def wants_html(request: Request) -> bool:
    """Whether an unauthenticated request is a browser navigation rather than an API call (DV-11).

    The dashboards call the API with XHRs asking for JSON; a navigation asks for HTML and takes no API
    path. Atlas guards statics in the serving process (DV-10); here nginx gates them (DD-036) and this
    is the fallback for a navigation that reaches the server on its own origin (AUTH-06).
    """
    return "text/html" in request.headers.get("accept", "") and not request.url.path.startswith("/api/")


def _origin_of(settings: ServerSettings) -> str:
    """The deployment's own origin, taken from its registered redirect URI."""
    redirect = str(settings.auth_redirect_uri)
    return redirect[: redirect.index("/api/")]


async def _refresh_if_due(oidc: OidcClient, sessions: SessionStore, session: Session) -> Session | None:
    """Refresh the session's access token when it nears expiry, or destroy the session (AUTH-09).

    Returns:
        The session, or None when the refresh failed and the session was destroyed.
    """
    if session.refresh_token is None or session.access_expires_at - time.monotonic() > REFRESH_SKEW_SECONDS:
        return session
    try:
        tokens = await oidc.refresh(session.refresh_token)
    except (OidcError, TokenError) as error:
        LOGGER.info("The session refresh failed; the session is destroyed: %s", error)
        sessions.destroy(session.sid)
        return None
    session.access_token = tokens.access_token
    session.refresh_token = tokens.refresh_token or session.refresh_token
    session.access_expires_at = tokens.expires_at
    return session


async def authenticate(request: Request) -> Principal | NoPrincipal | BearerRejected | IssuerUnreachable:
    """Resolve who sent the request (AUTH-03, AUTH-08, AUTH-09). Never raises; always answers."""
    settings: ServerSettings = request.app.state.settings
    oidc: OidcClient = request.app.state.oidc
    sessions: SessionStore = request.app.state.sessions

    if (token := bearer_of(request)) is not None:
        try:
            claims = await oidc.verify_access_token(token)
        except TokenError as error:
            LOGGER.info("A bearer token was rejected: %s", error)
            return BearerRejected()
        except OidcError:
            LOGGER.exception("The issuer cannot be reached to verify a bearer token")
            return IssuerUnreachable()
        username, groups = principal_of(claims, settings.auth_client_id)
        return Principal(username, groups)

    session = sessions.get(request.cookies.get(SESSION_COOKIE))
    if session is None:
        return NoPrincipal()
    refreshed = await _refresh_if_due(oidc, sessions, session)
    if refreshed is None:
        return NoPrincipal()
    return Principal(refreshed.username, refreshed.groups, refreshed)


@AUTH.get("/login")
async def login_start(request: Request, next: str | None = None) -> Response:  # noqa: A002 - the kept URL
    """Start the browser flow (AUTH-06): 302 to the issuer's authorization endpoint.

    Args:
        request: The request that reached a guarded page without a session.
        next: The URL to return to afterwards; one off this origin falls back to the root.
    """
    settings: ServerSettings = request.app.state.settings
    oidc: OidcClient = request.app.state.oidc
    pending = request.app.state.login_states.start(safe_next(next))
    try:
        url, verifier = await oidc.authorize_url(
            redirect_uri=str(settings.auth_redirect_uri), state=pending.state, nonce=pending.nonce
        )
    except OidcError:
        LOGGER.exception("The login cannot start, the issuer is unreachable")
        return issuer_error_response()
    pending.verifier = verifier
    return Response(status_code=302, headers={"location": url})


@AUTH.get("/callback")
async def login_callback(request: Request, code: str | None = None, state: str | None = None) -> Response:
    """Finish the browser flow: exchange the code, mint the session, return to the kept URL (AUTH-07)."""
    settings: ServerSettings = request.app.state.settings
    oidc: OidcClient = request.app.state.oidc
    sessions: SessionStore = request.app.state.sessions
    pending = request.app.state.login_states.take(state)
    if not code or pending is None:
        LOGGER.info("A login callback was rejected: unknown state or missing code")
        return unauthorized_response()
    try:
        tokens = await oidc.exchange(
            code=code,
            code_verifier=pending.verifier,
            redirect_uri=str(settings.auth_redirect_uri),
            nonce=pending.nonce,
        )
    except TokenError as error:
        LOGGER.info("A login callback was rejected: %s", error)
        return unauthorized_response()
    except OidcError:
        LOGGER.exception("The issuer could not be reached during a login callback")
        return issuer_error_response()
    username, groups = principal_of(tokens.claims, settings.auth_client_id)
    session = sessions.create(
        username=username,
        groups=groups,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_expires_at=tokens.expires_at,
    )
    response = Response(status_code=302, headers={"location": pending.next})
    response.set_cookie(SESSION_COOKIE, session.sid, httponly=True, secure=True, samesite="lax", path="/")
    return response


@AUTH.get("/check")
async def auth_check(request: Request) -> Response:
    """The ``auth_request`` answer nginx asks for: 200 or 401, never a redirect (DD-036, AUTH-05)."""
    result = await authenticate(request)
    return Response(status_code=200 if isinstance(result, Principal) else 401)


async def logout(request: Request) -> Response:
    """End the local session and the issuer's, and land back at the login page (AUTH-10).

    The dashboard's logout link is a navigation, so this answers a redirect to the issuer's end-session
    endpoint with ``/login.jsp`` as the post-logout redirect — Atlas's ``logoutSuccessUrl`` — which is
    where the vendored UIs expect the browser after logout (DD-040); an issuer without an end-session
    endpoint lands there directly. From it, the login flow returns to the dashboard the user was on.
    """
    settings: ServerSettings = request.app.state.settings
    oidc: OidcClient = request.app.state.oidc
    sessions: SessionStore = request.app.state.sessions
    sessions.destroy(request.cookies.get(SESSION_COOKIE))
    landing = f"{_origin_of(settings)}{LOGIN_JSP_PATH}"
    try:
        target = await oidc.end_session_url(post_logout_redirect_uri=landing)
    except OidcError as error:
        LOGGER.warning("The issuer's end-session endpoint is unreachable: %s", error)
        target = None
    response = Response(status_code=302, headers={"location": target if target is not None else landing})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


async def guard(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """The per-request decision of AUTH-01 to AUTH-05, in the order Atlas's chain applies it.

    Authentication off, or a public path: pass (AUTH-01, AUTH-02). Then the CSRF check, which Atlas's
    chain runs before the authorisation decision and compares against the session's token (CRS-01).
    Then the principal: bearer or session (AUTH-03, AUTH-08); a request without one starts the browser
    flow when it is a navigation (AUTH-06) and answers 401 when it is an API call (AUTH-04).
    """
    settings: ServerSettings = request.app.state.settings
    if not settings.auth_enabled or is_public(request.url.path):
        return await call_next(request)

    sessions: SessionStore = request.app.state.sessions
    session = sessions.get(request.cookies.get(SESSION_COOKIE))
    if csrf_rejected(request, session.csrf_token if session is not None else None):
        return csrf_denied()

    result = await authenticate(request)
    if isinstance(result, Principal):
        request.state.username = result.username
        request.state.groups = result.groups
        request.state.session = result.session
        return await call_next(request)
    if isinstance(result, IssuerUnreachable):
        return issuer_error_response()
    if isinstance(result, NoPrincipal) and wants_html(request):
        return Response(
            status_code=302,
            headers={"location": f"{LOGIN_PATH}?next={quote(request.url.path, safe='/')}"},
        )
    return unauthorized_response()  # AUTH-04, DV-11; AUTH-03 for a rejected bearer


def install_auth(app: FastAPI) -> None:
    """Wire the relying party into the application when an issuer is configured (AUTH-01, DD-037).

    Without an issuer the server answers as before 6.1: no guard, no auth endpoints, no session
    (AUTH-01, DV-04). The OIDC client's connections close with the application.
    """
    settings: ServerSettings = app.state.settings
    if not settings.auth_enabled:
        return
    issuer = settings.auth_issuer
    client_secret = settings.auth_client_secret
    if issuer is None or client_secret is None:  # the settings validator keeps this pair together (AUTH-01)
        return
    app.state.oidc = OidcClient(
        issuer=issuer,
        client_id=settings.auth_client_id,
        client_secret=client_secret.get_secret_value(),
        ca_file=str(settings.auth_ca_file) if settings.auth_ca_file else None,
    )
    app.state.sessions = SessionStore(idle_seconds=settings.auth_session_idle_seconds)
    app.state.login_states = LoginStates()
    app.middleware("http")(guard)
    app.include_router(AUTH)
    app.add_api_route(LOGOUT_PATH, logout, methods=["GET", "POST"], include_in_schema=False)
