"""The authentication of the server: OIDC relying party, sessions, CSRF and the guard (increment 6.1)."""

from aurelius_atlas_server.auth.csrf import csrf_denied, csrf_rejected
from aurelius_atlas_server.auth.guard import SESSION_COOKIE, guard, install_auth
from aurelius_atlas_server.auth.oidc import OidcClient, OidcError, TokenError, principal_of
from aurelius_atlas_server.auth.sessions import Session, SessionStore, csrf_token

__all__ = [
    "SESSION_COOKIE",
    "OidcClient",
    "OidcError",
    "Session",
    "SessionStore",
    "TokenError",
    "csrf_denied",
    "csrf_rejected",
    "csrf_token",
    "guard",
    "install_auth",
    "principal_of",
]
