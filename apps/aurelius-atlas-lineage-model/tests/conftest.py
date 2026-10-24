"""Fixtures for the app tests: settings, a fake Keycloak issuer, a fake upstream.

The fake issuer is the 8.0 auth library's test double (AUX-01..05 are tested at
home, in ``aurelius-atlas-auth``). The fake upstream is the Atlas lineage feed
and the data2model ``/extract`` the app proxies to (DD-111): a ``MockTransport``
recording every request and answering from a handler each test sets.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import httpx
import jwt
import pytest
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_lineage_model import LineageModelSettings, create_app
from aurelius_atlas_lineage_model.settings import ENV_PREFIX
from cryptography.hazmat.primitives.asymmetric import rsa
from fake_upstream import FakeUpstream
from fastapi import FastAPI
from jwt.algorithms import RSAAlgorithm
from pydantic import HttpUrl

ISSUER = "http://issuer.test"
REALM = "master"
BASE_URL = f"{ISSUER}/realms/{REALM}"
KID = "test-key"
AUDIENCE = "aurelius-atlas-lineage-model"
ATLAS = "http://atlas.test"
DATA2MODEL = "http://data2model.test"

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from a clean environment (DD-110).

    ``nx test`` injects the project's ``.env`` into the task's environment, and
    pydantic-settings reads it: the dev values — TLS material as
    workspace-root-relative paths, the dev issuer, the dev upstreams — would
    leak into the settings the fixtures and tests build, and the paths do not
    resolve at the test's working directory. Tests set exactly the variables
    they mean.
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
def upstream() -> FakeUpstream:
    """The programmable fake Atlas/data2model the app's upstream client hits."""
    return FakeUpstream()


@pytest.fixture
def settings() -> LineageModelSettings:
    """The app's settings: fake issuer and upstreams, no TLS, console telemetry."""
    return LineageModelSettings(
        auth_server_url=HttpUrl(ISSUER),
        atlas_base_url=HttpUrl(ATLAS),
        data2model_url=HttpUrl(DATA2MODEL),
    )


@pytest.fixture
def auth() -> Iterator[KeycloakAuth]:
    """A verifier talking to the fake issuer, injected into the app."""
    instance = KeycloakAuth(AuthConfig(server_url=ISSUER, realm=REALM, audience=AUDIENCE), http=issuer_client())
    yield instance
    instance.close()


@pytest.fixture
def app(settings: LineageModelSettings, auth: KeycloakAuth, upstream: FakeUpstream) -> FastAPI:
    """The application, verifying tokens against the fake issuer and calling the fake upstream."""
    return create_app(settings, auth=auth, http=upstream.client())


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """A client talking to the application in-process, without a token."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://lineage-model") as client:
        yield client


@pytest.fixture
def token() -> Callable[..., str]:
    """The token minter: make_token as a fixture, so tests import no conftest."""
    return make_token
