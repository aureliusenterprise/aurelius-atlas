"""Fixtures for the auth library: a fake Keycloak issuer and minted tokens."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from typing import Any

import httpx2 as httpx
import jwt
import pytest
from aurelius_atlas_auth.auth import AuthConfig, KeycloakAuth
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

ISSUER = "https://keycloak.localhost:8443"
REALM = "master"
BASE_URL = f"{ISSUER}/realms/{REALM}"
KID = "test-key"
AUDIENCE = "aux-test"

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()


def _jwk() -> dict[str, Any]:
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = KID
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    return jwk


def issuer_handler(*, fail: bool = False):  # noqa: ANN201  # returns the httpx handler callable
    """The fake issuer's request handler: discovery and JWKS, or failing."""
    jwk = _jwk()

    def handler(request: httpx.Request) -> httpx.Response:
        if fail:
            msg = "connection refused"
            raise httpx.ConnectError(msg, request=request)
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(200, json={"jwks_uri": f"{BASE_URL}/protocol/openid-connect/certs"})
        if request.url.path.endswith("/certs"):
            return httpx.Response(200, json={"keys": [jwk]})
        return httpx.Response(404)

    return handler


def issuer_client(*, fail: bool = False) -> httpx.Client:
    """An HTTP client answering discovery and JWKS like Keycloak, or failing."""
    return httpx.Client(transport=httpx.MockTransport(issuer_handler(fail=fail)))


def make_token(  # noqa: PLR0913  # the claim shaper names each claim it can set
    *,
    audience: str | list[str] | None = AUDIENCE,
    azp: str | None = AUDIENCE,
    issuer: str = BASE_URL,
    expires_in: int = 60,
    realm_roles: list[str] | None = None,
    client_roles: dict[str, list[str]] | None = None,
    kid: str = KID,
    key: rsa.RSAPrivateKey | None = None,
    alg: str = "RS256",
) -> str:
    """Mint an RS256 token as the fake issuer would, with the given claims."""
    now = int(time.time())
    claims: dict[str, Any] = {"iss": issuer, "iat": now, "exp": now + expires_in, "sub": "user-1", "nbf": now - 1}
    if audience is not None:
        claims["aud"] = audience
    if azp is not None:
        claims["azp"] = azp
    if realm_roles is not None:
        claims["realm_access"] = {"roles": realm_roles}
    if client_roles is not None:
        claims["resource_access"] = {client: {"roles": roles} for client, roles in client_roles.items()}
    return jwt.encode(claims, key if key is not None else private_key, algorithm=alg, headers={"kid": kid})


@pytest.fixture
def auth_config() -> AuthConfig:
    """The verification config of a test service."""
    return AuthConfig(server_url=ISSUER, realm=REALM, audience=AUDIENCE, write_role="aux-write")


@pytest.fixture
def auth(auth_config: AuthConfig) -> Iterator[KeycloakAuth]:
    """A verifier talking to the fake issuer."""
    instance = KeycloakAuth(auth_config, http=issuer_client())
    yield instance
    instance.close()


@pytest.fixture
def audience() -> str:
    """The audience the fake issuer mints and the verifier accepts."""
    return AUDIENCE


@pytest.fixture
def base_url() -> str:
    """The issuer realm URL the tokens are minted against."""
    return BASE_URL


@pytest.fixture
def token() -> Callable[..., str]:
    """The token minter: make_token as a fixture, so tests import no conftest."""
    return make_token


@pytest.fixture
def foreign_key() -> rsa.RSAPrivateKey:
    """A signing key the fake issuer does not know."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def issuer_client_factory() -> Callable[..., httpx.Client]:
    """Build fake-issuer HTTP clients (fail=True for an unreachable issuer)."""
    return issuer_client


@pytest.fixture
def issuer_handler_factory() -> Callable[..., Any]:
    """The raw fake-issuer handler, for counting transports."""
    return issuer_handler
