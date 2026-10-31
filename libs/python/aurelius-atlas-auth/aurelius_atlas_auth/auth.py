"""Keycloak bearer-token authentication for Aurelius Atlas services (8.0, DD-197).

Ported from the template's FastAPI example (the workspace's reference for the
pattern: ``apps/aurelius-atlas-fastapi-example/.../providers/auth.py``),
reshaped as a per-service object so each application owns one
:class:`KeycloakAuth` built from its own settings — no module-level caches
shared across applications.

The verification story (AUX-02..AUX-05):

- OIDC discovery and JWKS are fetched through a circuit breaker (a Keycloak
  outage is a 503, not a hang) and cached for an hour.
- Tokens are verified with PyJWT by ``kid``: RS256 signature, issuer and
  expiry. The audience is checked after decoding against the union of the
  ``azp`` and ``aud`` claims, which pyjwt's built-in check cannot express.
- The write gate accepts the configured role from ``realm_access.roles`` or
  ``resource_access.<audience>.roles`` — Keycloak namespaces client roles per
  client, so only this service's own client entry counts.
"""

from __future__ import annotations

import logging
import ssl
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, cast

import httpx2 as httpx
import jwt
from cachetools import TTLCache
from fastapi import Depends, HTTPException
from fastapi.params import Depends as DependsMarker
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm
from pybreaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerListener, CircuitBreakerState

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

LOGGER = logging.getLogger("aurelius-atlas-auth")

HTTP_TIMEOUT_SECONDS = 5.0
"""Timeout for the issuer calls (discovery, JWKS)."""

CACHE_TTL_SECONDS = 3600
"""How long the discovery and JWKS documents are cached."""

_SERVER_ERROR_STATUS = 500
"""The status from which an issuer response counts as an outage for the circuit."""

bearer_scheme = HTTPBearer(auto_error=True)
"""The scheme every :class:`KeycloakAuth` shares: one instance keeps FastAPI's
OpenAPI security scheme singular across the dependencies below."""


@dataclass(frozen=True)
class AuthConfig:
    """What a service needs to verify its tokens. Apps map their settings in.

    :param server_url: the issuer root, e.g. ``https://keycloak.localhost:8443``
    :param realm: the realm name (``master`` in dev)
    :param audience: accepted ``azp``/``aud`` value — the service's Keycloak client id
    :param write_role: role required for mutating routes; empty disables the gate
    :param fail_max: issuer failures before the circuit opens
    :param reset_timeout: seconds the circuit stays open
    :param ca_file: PEM CA verifying the issuer's TLS (None: system trust)
    """

    server_url: str
    realm: str
    audience: str
    write_role: str = ""
    fail_max: int = 5
    reset_timeout: float = 60.0
    ca_file: str | None = None
    extra_audiences: tuple[str, ...] = ()
    """Further accepted ``azp``/``aud`` values: the clients whose tokens the service also takes (AUT-10)."""

    @property
    def audiences(self) -> frozenset[str]:
        """Every accepted ``azp``/``aud`` value: the audience and the extra ones (AUT-10)."""
        return frozenset({self.audience, *self.extra_audiences})


class _LoggingListener(CircuitBreakerListener):
    """Log the circuit's state changes — an open circuit must be visible."""

    def state_change(
        self,
        cb: CircuitBreaker,
        old_state: CircuitBreakerState | None,
        new_state: CircuitBreakerState | None,
    ) -> None:
        LOGGER.debug("Circuit breaker %s state changed from %s to %s", cb.name, old_state, new_state)


def _tls_context(config: AuthConfig) -> ssl.SSLContext:
    """The issuer client's TLS material as an ``ssl.SSLContext`` (DD-211).

    httpx2 deprecates ``verify=<path>`` in favour of a context. With a CA file the
    context is rooted at that CA alone — the same trust httpx's ``verify=<path>``
    built; without one it loads the system trust, which is what httpx2's
    truststore default reads.
    """
    return ssl.create_default_context(cafile=config.ca_file) if config.ca_file else ssl.create_default_context()


class KeycloakAuth:
    """One service's Keycloak verifier: dependencies for FastAPI routers.

    Use through the :attr:`require_bearer`, :attr:`require_auth` and
    :attr:`require_write` dependencies::

        @router.get("/", dependencies=[Depends(auth.require_auth)])
        def read(...): ...

    :param config: the verification configuration
    :param http: the HTTP client for the issuer calls; injectable for tests
    """

    _jwks: dict[str, dict[str, RSAPublicKey]]
    """The signing keys by issuer URL: a TTLCache, read and written as a dict."""

    def __init__(self, config: AuthConfig, http: httpx.Client | None = None) -> None:
        self.config = config
        self.base_url = f"{config.server_url.rstrip('/')}/realms/{config.realm}"
        self._breaker = CircuitBreaker(
            name=f"auth_{config.audience}",
            fail_max=config.fail_max,
            reset_timeout=config.reset_timeout,
            # A 4xx from the issuer is a fact, not an outage: only 5xx and
            # transport failures count towards opening the circuit.
            exclude=[lambda e: type(e) is httpx.HTTPStatusError and e.response.status_code < _SERVER_ERROR_STATUS],
            listeners=[_LoggingListener()],
        )
        self._http = (
            http if http is not None else httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, verify=_tls_context(config))
        )
        self._jwks = cast("dict[str, dict[str, RSAPublicKey]]", TTLCache(maxsize=1, ttl=CACHE_TTL_SECONDS))
        self._discovery = cast("dict[str, dict]", TTLCache(maxsize=1, ttl=CACHE_TTL_SECONDS))

    def close(self) -> None:
        """Close the issuer HTTP client (the app calls it on shutdown)."""
        self._http.close()

    # -- issuer documents --------------------------------------------------

    def _issuer_get(self, url: str) -> httpx.Response:
        try:
            with self._breaker.calling():
                response = self._http.get(url)
                response.raise_for_status()
        except CircuitBreakerError as e:
            LOGGER.exception("Circuit breaker is open for the issuer %s", self.base_url)
            raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable") from e
        except httpx.HTTPError as e:
            # An issuer that is down, unreachable, or answering 4xx is an
            # availability failure, not the caller's fault: 503, and the
            # response never reveals what the issuer said.
            LOGGER.exception("Issuer request failed: %s", url)
            raise HTTPException(status_code=503, detail="Authentication service unavailable") from e
        return response

    def discovery(self) -> dict:
        """The issuer's OpenID configuration: its endpoints, fetched once, cached an hour (AUT-10)."""
        if self.base_url in self._discovery:
            return self._discovery[self.base_url]
        found = self._issuer_get(f"{self.base_url}/.well-known/openid-configuration").json()
        self._discovery[self.base_url] = found
        return found

    def _jwks_keys(self) -> dict[str, RSAPublicKey]:
        """The issuer's signing keys by ``kid``: fetched once, cached an hour."""
        if self.base_url in self._jwks:
            return self._jwks[self.base_url]
        jwks_uri = self.discovery()["jwks_uri"]
        keys = self._issuer_get(jwks_uri).json()["keys"]
        result = {key["kid"]: cast("RSAPublicKey", RSAAlgorithm.from_jwk(key)) for key in keys}
        self._jwks[self.base_url] = result
        LOGGER.info("Loaded JWKS from %s", jwks_uri)
        return result

    # -- FastAPI dependencies -------------------------------------------------

    def bearer(self, auth: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]) -> str:
        """The raw bearer token, for routes that forward it upstream (AUX-05).

        The scheme proves a bearer credential is present; the token itself is
        not verified here — it is the caller's, forwarded to the upstream
        service, which verifies it.
        """
        return auth.credentials

    def user_info(self, auth: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]) -> dict:
        """Verify the bearer token and return its claims (AUX-02, AUX-03)."""
        return self.verify(auth.credentials)

    def verify(self, token: str) -> dict:
        """Verify a token and return its claims, for callers outside a route dependency (AUX-02, AUT-10).

        :raises HTTPException: 401 for a token that does not verify, 503 when the issuer cannot be reached
        """
        try:
            headers = jwt.get_unverified_header(token)  # NOSONAR(S5659) the token is verified below
            alg = headers.get("alg", "RS256")
            if alg != "RS256":
                LOGGER.warning("Unsupported JWT algorithm: %s", alg)
                raise HTTPException(status_code=401, detail="Unsupported token algorithm")

            kid = headers.get("kid")
            keys = self._jwks_keys()
            key = keys.get(kid) if kid else None
            if key is None:
                LOGGER.warning("No key found for key ID %s", kid)
                raise HTTPException(status_code=401, detail="Authentication key not available")

            # Audience is verified after decoding (against the union of 'azp'
            # and 'aud'), which pyjwt's built-in check cannot express;
            # signature, issuer and expiry are verified here.
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[alg],
                issuer=self.base_url,
                options={"verify_aud": False},
            )
        except jwt.ExpiredSignatureError as e:
            LOGGER.warning("Authentication token has expired")
            raise HTTPException(status_code=401, detail="Token has expired") from e
        except jwt.InvalidIssuerError as e:
            LOGGER.warning("Invalid token issuer")
            raise HTTPException(status_code=401, detail="Invalid token issuer") from e
        except jwt.PyJWTError as e:
            LOGGER.exception("Failed to verify authentication token")
            raise HTTPException(status_code=401, detail="Invalid authorization token") from e

        if not _audience_matches(claims, self.config.audiences):
            LOGGER.warning(
                "Token audience mismatch: expected one of %r in azp/aud claims", sorted(self.config.audiences)
            )
            raise HTTPException(status_code=401, detail="Invalid token audience")

        return claims

    def require_write_access(self, auth: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]) -> dict:
        """Require the write role for mutating routes (AUX-04).

        :attr:`user_info` only proves *who* the caller is; without this gate
        any valid token of the realm could write. An empty ``write_role``
        disables the check — a development-only posture the app's settings
        enforce.
        """
        claims = self.user_info(auth)
        if not self.config.write_role:
            return claims
        if self.config.write_role not in _token_roles(claims, client_id=self.config.audience):
            LOGGER.warning("Token lacks required write role %r", self.config.write_role)
            raise HTTPException(status_code=403, detail="Insufficient permissions for this operation")
        return claims

    # -- assembled dependencies ------------------------------------------------

    @property
    def require_bearer(self) -> DependsMarker:
        """Route dependency: a bearer credential must be present; yields the raw token."""
        return Depends(self.bearer)

    @property
    def require_auth(self) -> DependsMarker:
        """Route dependency: a verified token; yields its claims (AUX-02, AUX-03)."""
        return Depends(self.user_info)

    @property
    def require_write(self) -> DependsMarker:
        """Route dependency: a verified token carrying the write role (AUX-04)."""
        return Depends(self.require_write_access)


def _audience_matches(claims: dict, expected_audiences: frozenset[str]) -> bool:
    """Whether an expected audience appears in the token's ``azp`` or ``aud`` claim.

    Keycloak records the calling client in ``azp`` and only lists role-mapped
    clients in ``aud``, so accepting the union supports both plain client
    tokens and tokens carrying an explicit audience.
    """
    audiences: set[str] = set()
    if azp := claims.get("azp"):
        audiences.add(azp)
    match claims.get("aud"):
        case str() as aud:
            audiences.add(aud)
        case list() as aud_list:
            audiences.update(a for a in aud_list if isinstance(a, str))
    return not expected_audiences.isdisjoint(audiences)


def _token_roles(claims: dict, *, client_id: str) -> set[str]:
    """The roles a token carries for *this* service.

    Keycloak namespaces client roles per client: ``resource_access.<client-id>
    .roles`` lists the roles of that client. Client roles are therefore read
    only under ``client_id`` — the configured audience, whose presence in the
    token ``user_info`` has already verified. A same-named role under any other
    client belongs to that client, not to us, and is ignored. Realm roles
    (``realm_access.roles``) apply across clients and are kept, so a
    deployment may assign the write role either way.
    """
    roles: set[str] = set()
    match claims.get("realm_access"):
        case {"roles": list() as realm_roles}:
            roles.update(r for r in realm_roles if isinstance(r, str))
        case _:
            pass
    if client_id and isinstance(resource_access := claims.get("resource_access"), dict):
        match resource_access.get(client_id):
            case {"roles": list() as client_roles}:
                roles.update(r for r in client_roles if isinstance(r, str))
            case _:
                pass
    return roles


__all__ = [
    "AuthConfig",
    "KeycloakAuth",
    "bearer_scheme",
]
