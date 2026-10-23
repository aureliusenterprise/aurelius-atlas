"""Fixtures for the app tests: the settings, a fake Keycloak issuer, and a client.

The fake issuer is the 8.0 auth library's test double, small enough to
duplicate here (AUX-01..05 are tested at home, in ``aurelius-atlas-auth``).
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import httpx
import jwt
import pytest
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_data2model import Data2ModelSettings, create_app
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from jwt.algorithms import RSAAlgorithm
from pydantic import HttpUrl

ISSUER = "http://issuer.test"
REALM = "master"
BASE_URL = f"{ISSUER}/realms/{REALM}"
KID = "test-key"
AUDIENCE = "aurelius-atlas-data2model"

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()


def _jwk() -> dict[str, Any]:
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = KID
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    return jwk


def issuer_client() -> httpx.Client:
    """An HTTP client answering discovery and JWKS like Keycloak."""
    jwk = _jwk()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(200, json={"jwks_uri": f"{BASE_URL}/protocol/openid-connect/certs"})
        if request.url.path.endswith("/certs"):
            return httpx.Response(200, json={"keys": [jwk]})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def make_token(
    *,
    audience: str | list[str] | None = AUDIENCE,
    azp: str | None = AUDIENCE,
    issuer: str = BASE_URL,
    expires_in: int = 60,
) -> str:
    """Mint an RS256 token as the fake issuer would, with the given claims."""
    now = int(time.time())
    claims: dict[str, Any] = {"iss": issuer, "iat": now, "exp": now + expires_in, "sub": "user-1", "nbf": now - 1}
    if audience is not None:
        claims["aud"] = audience
    if azp is not None:
        claims["azp"] = azp
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": KID})


@pytest.fixture
def settings() -> Data2ModelSettings:
    """The app's settings: the fake issuer as its auth server, no TLS, console telemetry."""
    return Data2ModelSettings(auth_server_url=HttpUrl(ISSUER))


@pytest.fixture
def auth() -> Iterator[KeycloakAuth]:
    """A verifier talking to the fake issuer, injected into the app."""
    instance = KeycloakAuth(AuthConfig(server_url=ISSUER, realm=REALM, audience=AUDIENCE), http=issuer_client())
    yield instance
    instance.close()


@pytest.fixture
def app(settings: Data2ModelSettings, auth: KeycloakAuth) -> FastAPI:
    """The application, verifying tokens against the fake issuer."""
    return create_app(settings, auth=auth)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """A client talking to the application in-process, without a token."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://data2model") as client:
        yield client


@pytest.fixture
def token() -> Callable[..., str]:
    """The token minter: make_token as a fixture, so tests import no conftest."""
    return make_token
