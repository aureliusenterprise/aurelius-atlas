from functools import cache
from typing import Annotated, cast

import httpx
import jwt
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from jwt.algorithms import RSAAlgorithm
from pybreaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerListener, CircuitBreakerState
from pydantic import BaseModel, ConfigDict, HttpUrl

from aurelius_atlas_fastapi_example.globals import LOGGER

from .http import http_client
from .settings import Settings

auth_scheme = HTTPBearer(auto_error=True)


class OpenIdConfig(BaseModel):
    """OpenID configuration settings."""

    model_config = ConfigDict(frozen=True)

    jwks_uri: HttpUrl


@cache
def auth_base_url(*, settings: Settings) -> str:
    """Return the base URL for the authentication server."""
    return f"{settings.auth_server_url}realms/{settings.auth_realm_name}"


@cache
def auth_circuit_breaker(*, settings: Settings) -> CircuitBreaker:
    """Return a circuit breaker instance for requests to the authentication server."""

    class AuthCircuitBreakerListener(CircuitBreakerListener):
        def state_change(
            self,
            cb: CircuitBreaker,
            old_state: CircuitBreakerState | None,
            new_state: CircuitBreakerState | None,
        ) -> None:
            LOGGER.debug("Circuit breaker %s state changed from %s to %s", cb.name, old_state, new_state)

    return CircuitBreaker(
        exclude=[
            lambda e: type(e) is httpx.HTTPStatusError and e.response.status_code < httpx.codes.INTERNAL_SERVER_ERROR
        ],
        fail_max=settings.auth_fail_max,
        listeners=[AuthCircuitBreakerListener()],
        name="auth_circuit_breaker",
        reset_timeout=settings.auth_reset_timeout,
    )


@cache
def auth_provider(*, auth_base_url: Annotated[str, Depends(auth_base_url)]) -> OAuth2PasswordBearer:
    """Return the OAuth2PasswordBearer instance for the authentication configuration."""
    return OAuth2PasswordBearer(
        tokenUrl=f"{auth_base_url}/protocol/openid-connect/token",
        description="Bearer token for authentication with the data source.",
    )


@cached(
    cache=TTLCache(maxsize=1, ttl=3600),
    key=lambda **kwargs: hashkey(kwargs["auth_base_url"]),
)
def openid_configuration(
    auth_base_url: Annotated[str, Depends(auth_base_url)],
    auth_circuit_breaker: Annotated[CircuitBreaker, Depends(auth_circuit_breaker)],
    http_client: Annotated[httpx.Client, Depends(http_client)],
) -> OpenIdConfig:
    """Return the OpenID configuration for the configured issuer."""
    well_known_url = f"{auth_base_url}/.well-known/openid-configuration"

    try:
        with auth_circuit_breaker.calling():
            response = http_client.get(well_known_url)
            response.raise_for_status()
    except CircuitBreakerError as e:
        LOGGER.error("Circuit breaker is open for authentication service")
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable") from e

    LOGGER.info("Loaded OpenID configuration from %s", well_known_url)

    return OpenIdConfig.model_validate_json(response.read())


@cached(
    cache=TTLCache(maxsize=1, ttl=3600),
    key=lambda **kwargs: hashkey(kwargs["openid"]),
)
def jwks(
    auth_circuit_breaker: Annotated[CircuitBreaker, Depends(auth_circuit_breaker)],
    http_client: Annotated[httpx.Client, Depends(http_client)],
    openid: Annotated[OpenIdConfig, Depends(openid_configuration)],
) -> dict[str, RSAPublicKey]:
    """Return the JWKS configuration for the JWT authentication."""
    try:
        with auth_circuit_breaker.calling():
            response = http_client.get(str(openid.jwks_uri))
            response.raise_for_status()
    except CircuitBreakerError as e:
        LOGGER.error("Circuit breaker is open for authentication service")
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable") from e

    response_json = response.json()

    result = {key["kid"]: cast("RSAPublicKey", RSAAlgorithm.from_jwk(key)) for key in response_json["keys"]}

    LOGGER.info("Loaded JWKS configuration from %s", openid.jwks_uri)

    return result


def auth_token(auth: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)]) -> str:
    """Return the authentication token from the request."""
    return auth.credentials


def jwk(
    auth_token: Annotated[str, Depends(auth_token)],
    jwks: Annotated[dict[str, RSAPublicKey], Depends(jwks)],
) -> RSAPublicKey:
    """Return the JWK key for decoding the authentication token."""
    try:
        headers = jwt.get_unverified_header(auth_token)
    except jwt.PyJWTError as e:
        LOGGER.exception("Failed to decode authentication token header")
        raise HTTPException(status_code=401, detail="Invalid authorization token format") from e

    if not (kid := headers.get("kid")):
        LOGGER.error("No key ID found in authentication token")
        raise HTTPException(status_code=401, detail="Missing key ID in token")

    if not (key := jwks.get(kid)):
        LOGGER.error("No key found for key ID %s", kid)
        raise HTTPException(status_code=401, detail="Authentication key not available")

    return key


def user_info(
    auth_base_url: Annotated[str, Depends(auth_base_url)],
    auth_token: Annotated[str, Depends(auth_token)],
    jwk: Annotated[RSAPublicKey, Depends(jwk)],
    settings: Settings,
) -> dict:
    """Decode the authentication token to verify the user's identity and return their information."""
    try:
        headers = jwt.get_unverified_header(auth_token)  # NOSONAR(S5659) token is verified a few lines down
        alg = headers.get("alg", "RS256")

        if alg != "RS256":
            LOGGER.error("Unsupported JWT algorithm: %s", alg)
            raise HTTPException(status_code=401, detail="Unsupported token algorithm")

        # Audience is verified after decoding (against the union of 'azp' and 'aud'), which pyjwt's
        # built-in audience check cannot express; signature, issuer, and expiry are verified here.
        claims = jwt.decode(
            auth_token,
            key=jwk,
            algorithms=[alg],
            issuer=auth_base_url,
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

    if not _audience_matches(claims, settings.auth_audience):
        LOGGER.warning(
            "Token audience mismatch: expected %r in azp/aud claims",
            settings.auth_audience,
        )
        raise HTTPException(status_code=401, detail="Invalid token audience")

    return claims


def _audience_matches(claims: dict, expected_audience: str) -> bool:
    """Check whether the expected audience appears in the token's 'azp' or 'aud' claims.

    Keycloak records the calling client in 'azp' and only lists role-mapped clients in 'aud', so
    accepting the union supports both plain client tokens and tokens carrying an explicit audience.
    """
    audiences: set[str] = set()

    if azp := claims.get("azp"):
        audiences.add(azp)

    match claims.get("aud"):
        case str() as aud:
            audiences.add(aud)
        case list() as aud_list:
            audiences.update(a for a in aud_list if isinstance(a, str))

    return expected_audience in audiences


def _token_roles(claims: dict, *, client_id: str) -> set[str]:
    """Collect the roles a token carries for *this* application.

    Keycloak namespaces client roles per client: ``resource_access.<client-id>.roles``
    lists the roles of the client ``<client-id>``, not of the application reading
    the token. Client roles are therefore read only under ``client_id`` — the
    configured audience, which ``user_info`` has already verified appears in the
    token's ``azp``/``aud`` claims. A same-named role carried under any other
    client (e.g. ``resource_access.other-client.roles``) is deliberately ignored:
    it belongs to that client, not to us. Realm roles (``realm_access.roles``)
    apply across clients and are kept, so a deployment may assign the write role
    either way. An empty ``client_id`` reads no client roles (realm only).
    """
    roles: set[str] = set()

    match claims.get("realm_access"):
        case {"roles": list() as realm_roles}:
            roles.update(r for r in realm_roles if isinstance(r, str))
        case _:
            pass

    if client_id:
        resource_access = claims.get("resource_access")
        if isinstance(resource_access, dict):
            # The client's own entry only: a same-named role under any other
            # key is another client's role and never satisfies the gate.
            match resource_access.get(client_id):
                case {"roles": list() as client_roles}:
                    roles.update(r for r in client_roles if isinstance(r, str))
                case _:
                    pass

    return roles


def require_write_access(
    claims: Annotated[dict, Depends(user_info)],
    settings: Settings,
) -> dict:
    """Require the configured write role for mutating operations (PUT/DELETE).

    ``require_auth`` only proves *who* the caller is; without this gate any valid
    token of the realm could write or delete any entity. An empty
    ``auth_write_role`` disables the check, which is only reachable in development
    (enforced by ``Settings.enforce_auth_security``).
    """
    if not settings.auth_write_role:
        return claims

    if settings.auth_write_role not in _token_roles(claims, client_id=settings.auth_audience):
        LOGGER.warning("Token lacks required write role %r", settings.auth_write_role)
        raise HTTPException(status_code=403, detail="Insufficient permissions for this operation")

    return claims


require_auth = Depends(user_info)
require_write = Depends(require_write_access)
