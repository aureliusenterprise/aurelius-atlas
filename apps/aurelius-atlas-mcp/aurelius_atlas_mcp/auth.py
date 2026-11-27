"""The gate: the caller's bearer token, verified by the shared library before any tool runs (MCP-02, DD-888).

FastMCP ships its own JWT verifier, and it is deliberately not used: this app must decide
access the same way every other Aurelius service does, through one verifier (ADR 013,
ADR 017). So the gate is a thin ASGI middleware in front of FastMCP's ASGI app that calls
:class:`aurelius_atlas_auth.KeycloakAuth` — the code the 8.x apps gate their routes with —
and refuses at the HTTP boundary with ``401``. No MCP session opens, and the catalogue is
never called anonymously, for a token that does not verify.

The verified token and claims are stowed in the ASGI scope's ``state``, the same dict every
:class:`~starlette.requests.Request` of this request wraps. FastMCP binds its own request
object per call, so a concurrent agent's credential cannot reach another agent's tool call
(DD-890).

The bypass list is an allow-list, not a deny-list: a route added later is anonymous until
someone names it, which is the safe direction to fail in.
"""

from __future__ import annotations

from aurelius_atlas_auth import KeycloakAuth
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from aurelius_atlas_mcp.globals import LIVENESS_PATH, LOGGER
from aurelius_atlas_mcp.relay import BEARER_STATE_KEY, CLAIMS_STATE_KEY

UNAUTHENTICATED = {"error": "unauthorized", "message": "a valid bearer token is required"}
"""The body of a refusal. It says nothing about which claim failed — a caller learns that
from its own mint, not from this endpoint's error text."""

ISSUER_DOWN = {"error": "unavailable", "message": "the issuer cannot be reached"}
"""The 503 body: an issuer outage is not the caller's fault and must not read as one."""

ANONYMOUS_PATHS = frozenset({LIVENESS_PATH})
"""The paths the gate lets through without a token (MCP-15). FastMCP keeps its custom
routes outside its own auth gate for the same reason: an operational probe has no token."""

_UNAUTHORIZED = 401
_SERVICE_UNAVAILABLE = 503


class BearerGate:
    """ASGI middleware that verifies the bearer token and stows it for the tools (DD-888).

    :param app: the application to guard — FastMCP's ASGI app
    :param verifier: the shared Keycloak verifier, built from the app's settings
    :param anonymous_paths: paths served without a token; defaults to the health route
    """

    def __init__(
        self,
        app: ASGIApp,
        verifier: KeycloakAuth,
        anonymous_paths: frozenset[str] = ANONYMOUS_PATHS,
    ) -> None:
        self._app = app
        self._verifier = verifier
        self._anonymous = anonymous_paths

    @property
    def inner(self) -> ASGIApp:
        """The application behind the gate — the one whose lifespan uvicorn drives through here."""
        return self._app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Guard the scope: pass the health route, verify everything else, refuse the rest."""
        if scope["type"] != "http" or scope.get("path", "") in self._anonymous:
            await self._app(scope, receive, send)
            return

        token = _bearer_of(Request(scope, receive))
        if token is None:
            await _refuse(scope, receive, send, body=UNAUTHENTICATED)
            return

        try:
            claims = self._verifier.verify(token)
        except Exception as error:  # noqa: BLE001 - the library reports its own failures by status
            # The shared library refuses with a FastAPI HTTPException: its 401 becomes this
            # app's refusal, and its 503 — the issuer unreachable or its circuit open —
            # travels unchanged, because an outage must not read as a bad credential.
            if getattr(error, "status_code", _UNAUTHORIZED) == _SERVICE_UNAVAILABLE:
                await _refuse(scope, receive, send, status=_SERVICE_UNAVAILABLE, body=ISSUER_DOWN, challenge=False)
                return
            LOGGER.info("Refused an MCP request: %s", error)
            await _refuse(scope, receive, send, body=UNAUTHENTICATED)
            return

        # The verified credential for the tools (DD-890): written into the scope's own
        # state dict, which every Request of this call wraps.
        state: dict[str, object] = scope.setdefault("state", {})
        state[BEARER_STATE_KEY] = token
        state[CLAIMS_STATE_KEY] = claims
        await self._app(scope, receive, send)


def _bearer_of(request: Request) -> str | None:
    """The bearer credential of the request, or None when it carries none."""
    header = request.headers.get("authorization", "")
    scheme, _, credentials = header.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None
    return credentials.strip()


async def _refuse(  # noqa: PLR0913 - the ASGI triple plus what to answer with
    scope: Scope,
    receive: Receive,
    send: Send,
    *,
    status: int = _UNAUTHORIZED,
    body: dict[str, str],
    challenge: bool = True,
) -> None:
    """One refusal answer; a 401 names the scheme so a client knows to send a token."""
    headers = {"WWW-Authenticate": "Bearer"} if challenge else {}
    await JSONResponse(body, status_code=status, headers=headers)(scope, receive, send)


def token_roles(claims: dict, role_client: str) -> set[str]:
    """The roles a caller holds, from the two places Keycloak puts them (MCP-11, DD-891, DD-898).

    The same claim locations :class:`aurelius_atlas_auth.KeycloakAuth` reads for its write
    gate: ``realm_access.roles`` for a realm role, and ``resource_access.<role_client>.roles``
    for a client role — Keycloak namespaces client roles per client, so only the named
    client's entry counts (AUZ-01). For the write gate that client is the catalogue's
    (MCP-28): ``atlas-write`` rides it even when the caller signed in through another
    client. The test set pins both shapes, so a change to the shared rule fails a test here too.
    """
    roles: set[str] = set()
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict) and isinstance(realm_access.get("roles"), list):
        roles |= {str(role) for role in realm_access["roles"]}
    resource_access = claims.get("resource_access")
    if isinstance(resource_access, dict):
        client = resource_access.get(role_client)
        if isinstance(client, dict) and isinstance(client.get("roles"), list):
            roles |= {str(role) for role in client["roles"]}
    return roles


def may_write(claims: dict, role_client: str, write_role: str) -> bool:
    """Whether the caller may run a write tool (MCP-11, MCP-28).

    An empty ``write_role`` disables the gate — the development-only posture the shared
    library keeps (ADR 017), so the rule lives once.
    """
    if not write_role:
        return True
    return write_role in token_roles(claims, role_client)
