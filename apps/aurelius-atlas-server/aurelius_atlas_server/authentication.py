"""Authentication: each request's user, from its bearer token or its browser session (AUT-01 to AUT-09).

Atlas's Keycloak provider, as its Spring Security configuration wires it: open paths, the bearer token, the
session the login starts, the entry point's 401 or redirect to sign in, and the CSRF filter (DD-250).
"""

import re
import secrets
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aurelius_atlas_auth import KeycloakAuth, client_roles
from fastapi import HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from aurelius_atlas_server.errors import AtlasError, atlas_error_handler
from aurelius_atlas_server.root_path import site_path, under_root
from aurelius_atlas_server.tenancy import Tenancy, tenant_of, tenant_roles
from aurelius_atlas_server.tenant_stores import open_request_stores

SESSION_COOKIE = "ATLASSESSIONID"
"""The session cookie's name, as Atlas's ``web.xml`` names it."""

REALM = "atlas.com"
"""The realm the 401's challenge names, as Atlas's entry point sets it."""

LOGIN_PATH = "/login.jsp"
LOGOUT_PATH = "/logout.html"

OPEN_PATHS = frozenset(
    {
        "/api/atlas/admin/status",
        "/api/atlas/admin/liveness",
        "/api/atlas/admin/readiness",
        "/ieerror.html",
        "/migration-status.html",
        LOGIN_PATH,
        LOGOUT_PATH,
        # The dev OpenAPI surface (create_app serves it only under development; these paths 404 elsewhere).
        "/api/atlas/docs",
        "/api/atlas/openapi.json",
    }
)
OPEN_PREFIXES = ("/css/", "/n/css/", "/img/", "/n/img/", "/libs/", "/n/libs/", "/js/", "/n/js/")
"""What needs no user: ``AtlasSecurityConfig``'s ignored paths, the probes, the login and logout (AUT-01)."""

BROWSER_AGENTS = (re.compile(r"^Mozilla.*"), re.compile(r"^Opera.*"), re.compile(r"^Chrome"))
"""``atlas.rest-csrf.browser-useragents-regex``'s default; each matches a whole user agent (AUT-08)."""

SAFE_METHODS = frozenset({"GET", "OPTIONS", "HEAD", "TRACE"})
"""``atlas.rest-csrf.methods-to-ignore``'s default (AUT-08)."""

CSRF_HEADER = "X-XSRF-HEADER"
CSRF_REFUSED = "Missing header or invalid Header value for CSRF Vulnerability Protection"
CSRF_TOKEN_LENGTH = 20
_CSRF_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

MAX_SESSIONS = 10_000
"""The most sessions kept; the least recently used goes first, so visits without a login cannot fill memory."""

EXPIRY_MARGIN_SECONDS = 10
"""An access token this close to its expiry is refreshed first."""


@dataclass(frozen=True)
class User:
    """An authenticated user: their name, groups (``Authentication``'s name and authorities), roles (AUZ-01), and
    the tenant they act in while tenancy is on (TEN-03).
    """  # noqa: D205 - one sentence

    name: str
    groups: tuple[str, ...] = ()
    roles: frozenset[str] = frozenset()
    tenant: str | None = None


def user_of(
    claims: dict[str, Any],
    *,
    principal_claim: str,
    groups_claim: str,
    client_id: str = "",
    tenancy: Tenancy | None = None,
) -> User:
    """The user a token's claims name: the principal claim, falling back to ``sub``; the groups claim, else the
    realm roles (AUT-03). Without ``tenancy``, no tenant and the roles of the server's client ``client_id``
    (AUZ-01, TEN-01); with it, the one tenant the token names and the roles of its own groups (TEN-02 to TEN-06).

    Raises:
        AtlasError: With ``tenancy``, when the token names no organization, several, or one not provisioned.
    """  # noqa: D205 - one sentence
    name = str(claims.get(principal_claim) or claims.get("sub") or "")
    groups = claims.get(groups_claim)
    if not isinstance(groups, list):
        realm_access = claims.get("realm_access")
        groups = realm_access.get("roles") if isinstance(realm_access, dict) else None
    named_groups = tuple(str(group) for group in groups or [])
    if tenancy is None:
        return User(name, named_groups, client_roles(claims, client_id))
    tenant, entry = tenant_of(claims, tenancy, name)
    return User(name, named_groups, tenant_roles(claims, tenancy, tenant, entry), tenant)


async def current_tenancy(request: Request) -> Tenancy | None:
    """The provisioned tenants as the server last read them, read again when due; None while tenancy is off
    (TPR-07, DD-575).
    """  # noqa: D205 - one sentence
    directory = request.app.state.tenant_directory
    return None if directory is None else await directory.current()


def tenancy_admits(tenancy: Tenancy | None, tenant: str) -> bool:
    """Whether a session's tenant is still provisioned: always while tenancy is off (TPR-07)."""
    return tenancy is None or tenancy.is_provisioned(tenant)


def acting_user(request: Request) -> str | None:
    """The name of the user the request acts as, whom its writes and audits name (USR-01, AUT-03)."""
    user: User | None = getattr(request.state, "user", None)
    return None if user is None else user.name


def csrf_token() -> str:
    """A new random token of 20 letters and digits, as ``AdminResource.getUserProfile`` makes one."""
    return "".join(secrets.choice(_CSRF_ALPHABET) for _ in range(CSRF_TOKEN_LENGTH))


@dataclass
class Login:
    """A sign-in under way: the state, nonce and PKCE verifier sent to the provider (AUT-05)."""

    state: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    nonce: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    verifier: str = field(default_factory=lambda: secrets.token_urlsafe(64))


@dataclass
class Session:
    """A browser's session: its user and tokens once signed in, its sign-in under way, its CSRF token."""

    id: str
    last_used: float
    user: User | None = None
    access_token: str | None = None
    access_expires: float = 0.0
    refresh_token: str | None = None
    id_token: str | None = None
    login: Login | None = None
    return_to: str | None = None
    csrf_token: str | None = None


class SessionStore:
    """The server's sessions, in memory, each ending after ``timeout_seconds`` unused (AUT-06, DD-251)."""

    def __init__(
        self, timeout_seconds: float, *, clock: Callable[[], float] = time.monotonic, max_sessions: int = MAX_SESSIONS
    ) -> None:
        self._timeout = timeout_seconds
        self._clock = clock
        self._max = max_sessions
        self._sessions: OrderedDict[str, Session] = OrderedDict()

    def get(self, session_id: str | None) -> Session | None:
        """The session of the id, unless it timed out; using it keeps it."""
        if not session_id:
            return None
        found = self._sessions.get(session_id)
        if found is None:
            return None
        now = self._clock()
        if now - found.last_used > self._timeout:
            del self._sessions[session_id]
            return None
        found.last_used = now
        self._sessions.move_to_end(session_id)
        return found

    def create(self) -> Session:
        """A new, empty session under a new random id."""
        created = Session(id=secrets.token_urlsafe(32), last_used=self._clock())
        self._sessions[created.id] = created
        while len(self._sessions) > self._max:
            self._sessions.popitem(last=False)
        return created

    def renew(self, session: Session) -> Session:
        """The session under a new id, the old one gone: a sign-in starts a new session (``sessionFixation``)."""
        self.remove(session.id)
        session.id = secrets.token_urlsafe(32)
        session.last_used = self._clock()
        self._sessions[session.id] = session
        return session

    def remove(self, session_id: str) -> None:
        """End the session of the id."""
        self._sessions.pop(session_id, None)


def is_open(path: str) -> bool:
    """Whether a path needs no user (AUT-01)."""
    return path in OPEN_PATHS or path.startswith(OPEN_PREFIXES)


def is_browser(user_agent: str | None) -> bool:
    """``isBrowser``: a user agent a browser pattern matches whole (AUT-08)."""
    return user_agent is not None and any(pattern.fullmatch(user_agent) for pattern in BROWSER_AGENTS)


def set_session_cookie(response: Response, session: Session) -> None:
    """The session's cookie: only the server reads it, only over HTTPS, not on cross-site posts (AUT-05)."""
    response.set_cookie(SESSION_COOKIE, session.id, httponly=True, secure=True, samesite="lax", path="/")


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Every request's user, or its 401 or redirect to sign in (AUT-01 to AUT-08).

    The verifier, the OpenID client and the sessions are the application's state, so tests can replace them.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Authenticate the request, then pass it on with ``request.state.user``, ``.session`` and ``.tenant``."""
        request.state.user = None
        request.state.session = None
        request.state.tenant = None
        if is_open(site_path(request.scope)):
            return await call_next(request)
        tenancy = await current_tenancy(request)
        authorization = request.headers.get("authorization")
        if authorization is not None:
            return await self._bearer(request, authorization, call_next, tenancy)
        state = request.app.state
        session = state.sessions.get(request.cookies.get(SESSION_COOKIE))
        if session is not None and session.user is not None and await state.oidc.fresh(session):
            if _csrf_refused(request, session):
                return PlainTextResponse(CSRF_REFUSED, status_code=400)
            if session.user.tenant is not None and not tenancy_admits(tenancy, session.user.tenant):
                state.sessions.remove(session.id)  # its tenant is no longer provisioned (TPR-07)
                return _unauthenticated(request, None)
            request.state.user, request.state.session = session.user, session
            request.state.tenant = session.user.tenant
            await open_request_stores(request, tenancy)
            return await call_next(request)
        return _unauthenticated(request, session)

    async def _bearer(
        self, request: Request, authorization: str, call_next: RequestResponseEndpoint, tenancy: Tenancy | None
    ) -> Response:
        """A request with an ``Authorization`` header: its bearer token alone authenticates it (AUT-02)."""
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            return _unauthorized()
        auth: KeycloakAuth = request.app.state.auth
        try:
            claims = await run_in_threadpool(auth.verify, token.strip())
        except HTTPException as error:
            return Response(status_code=error.status_code) if error.status_code != 401 else _unauthorized()  # noqa: PLR2004 - the issuer's outage stays 503
        settings = request.app.state.settings
        try:
            user = user_of(
                claims,
                principal_claim=settings.auth_principal_claim,
                groups_claim=settings.auth_groups_claim,
                client_id=settings.auth_client_id,
                tenancy=tenancy,
            )
        except AtlasError as refused:  # no tenant to act in: refused before any route (TEN-07)
            return await atlas_error_handler(request, refused)
        request.state.user, request.state.tenant = user, user.tenant
        await open_request_stores(request, tenancy)
        return await call_next(request)


def _csrf_refused(request: Request, session: Session) -> bool:
    """``AtlasCSRFPreventionFilter``: a browser's unsafe request without the session's token (AUT-08, DV-107)."""
    if not is_browser(request.headers.get("user-agent")) or request.method in SAFE_METHODS:
        return False
    given = request.headers.get(CSRF_HEADER)
    return given is None or session.csrf_token is None or not secrets.compare_digest(given, session.csrf_token)


def _unauthenticated(request: Request, session: Session | None) -> Response:
    """``KeycloakAuthenticationEntryPoint``: 401 for an API or script, else to sign in, the page remembered (AUT-04)."""
    if site_path(request.scope).startswith("/api/") or request.headers.get("x-requested-with") == "XMLHttpRequest":
        return _unauthorized()
    sessions: SessionStore = request.app.state.sessions
    session = session if session is not None else sessions.create()
    query = f"?{request.url.query}" if request.url.query else ""
    session.return_to = f"{request.url.path}{query}"
    response = RedirectResponse(under_root(request.scope, LOGIN_PATH), status_code=302)
    set_session_cookie(response, session)
    return response


def _unauthorized() -> Response:
    """401 with the bearer challenge of Atlas's realm (AUT-04, DV-106)."""
    return Response(status_code=401, headers={"WWW-Authenticate": f'Bearer realm="{REALM}"'})
