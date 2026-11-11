"""Fixtures for the app tests: settings, a fake Keycloak issuer, a fake catalogue, the app.

The fake issuer is the 8.0 auth library's test double (AUX-01..05 are tested at
home, in ``aurelius-atlas-auth``); the fake catalogue is the Atlas server the
rules door reads since 12.7 (VEV-03), in its own module ``fake_catalogue`` —
helpers live there, importable by a unique name (8.2's pattern).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import httpx2 as httpx
import jwt
import pytest
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_server_client.client import AtlasClient
from aurelius_atlas_validate_entity import ValidateEntitySettings, create_app
from aurelius_atlas_validate_entity.settings import ENV_PREFIX
from cryptography.hazmat.primitives.asymmetric import rsa
from fake_catalogue import FakeCatalogue
from fastapi import FastAPI
from jwt.algorithms import RSAAlgorithm
from pydantic import HttpUrl

ISSUER = "http://issuer.test"
CATALOGUE = "http://catalogue.test"
REALM = "master"
BASE_URL = f"{ISSUER}/realms/{REALM}"
KID = "test-key"
AUDIENCE = "aurelius-atlas-validate-entity"

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from a clean environment (DD-199).

    ``nx test`` injects the project's ``.env`` into the task's environment, and
    pydantic-settings reads it: the dev values — TLS material as
    workspace-root-relative paths and the dev issuer — would leak into the
    settings the fixtures and tests build, and the paths do not resolve at the
    test's working directory. Tests set exactly the variables they mean.
    """
    for name in list(os.environ):
        if name.startswith(ENV_PREFIX):
            monkeypatch.delenv(name, raising=False)


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
def catalogue() -> FakeCatalogue:
    """The programmable fake Atlas catalogue the app's rules door reads."""
    return FakeCatalogue()


@pytest.fixture
def settings() -> ValidateEntitySettings:
    """The app's settings: fake issuer and catalogue, no TLS, console telemetry."""
    return ValidateEntitySettings(auth_server_url=HttpUrl(ISSUER), server_base_url=HttpUrl(CATALOGUE))


@pytest.fixture
def auth() -> Iterator[KeycloakAuth]:
    """A verifier talking to the fake issuer, injected into the app."""
    instance = KeycloakAuth(AuthConfig(server_url=ISSUER, realm=REALM, audience=AUDIENCE), http=issuer_client())
    yield instance
    instance.close()


@pytest.fixture
def app(settings: ValidateEntitySettings, auth: KeycloakAuth, catalogue: FakeCatalogue) -> FastAPI:
    """The application, verifying tokens against the fake issuer and reading the fake catalogue.

    The catalogue client speaks through an externally built httpx client on the
    fake's recording transport (DD-200's seam, built outside per DD-205); the
    token source is the app's own service identity, standing in for the mint.
    """
    atlas = AtlasClient(httpx.AsyncClient(base_url=CATALOGUE, transport=catalogue.transport()), "app-identity")
    return create_app(settings, auth=auth, atlas=atlas)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """A client talking to the application in-process, without a token."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://validate-entity") as client:
        yield client


@pytest.fixture
def token() -> Callable[..., str]:
    """The token minter: make_token as a fixture, so tests import no conftest."""
    return make_token
