"""Fixtures for the MCP app tests: settings, a fake issuer, a fake catalogue, an MCP client.

The fake issuer is the 8.0 auth library's test double, the same shape the validate-entity
conftest uses (AUX-01..05 are proven at home); the fake catalogue is an httpx
MockTransport answering the Atlas REST paths the tools relay to, recorded so a test can
assert on the bearer the tool forwarded (MCP-03) and the body it sent (MCP-10).

The MCP client rides the in-process ASGI transport of the gate-wrapped app: no socket,
no subprocess — the same harness design as every aux app's unit suite (DD-892).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from typing import Any

import httpx2 as httpx
import jwt
import pytest
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_mcp import McpSettings, create_app
from aurelius_atlas_mcp.settings import ENV_PREFIX
from cryptography.hazmat.primitives.asymmetric import rsa
from fake_upstream import FakeUpstream
from jwt.algorithms import RSAAlgorithm
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ISSUER = "http://issuer.test"
CATALOGUE = "http://catalogue.test"
VERDICTS = "http://verdicts.test"
REALM = "master"
BASE_URL = f"{ISSUER}/realms/{REALM}"
KID = "test-key"
AUDIENCE = "aurelius"
WRITE_ROLE = "atlas-write"

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from a clean environment (DD-199).

    ``nx test`` injects the project's ``.env`` into the task's environment, and
    pydantic-settings reads it: the dev values would leak into the settings the
    fixtures and tests build. Tests set exactly what they mean.
    """
    for name in list(os.environ):
        if name.startswith(ENV_PREFIX):
            monkeypatch.delenv(name, raising=False)


# -- the fake issuer -------------------------------------------------------


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
    roles: list[str] | None = None,
    **extra: Any,  # noqa: ANN401 - further claims
) -> str:
    """Mint an RS256 token as the fake issuer would.

    :param roles: the realm roles to carry; ``["atlas-write"]`` unlocks the write tools.
    """
    now = int(time.time())
    claims: dict[str, Any] = {"iss": issuer, "iat": now, "exp": now + expires_in, "sub": "agent-1", "nbf": now - 1}
    if roles is not None:
        claims["realm_access"] = {"roles": roles}
    claims.update(extra)
    if audience is not None:
        claims["aud"] = audience
    if azp is not None:
        claims["azp"] = azp
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": KID})


# -- settings, verifier, app, and the MCP client ---------------------------


@pytest.fixture
def upstream() -> FakeUpstream:
    """The fake catalogue and verdicts API."""
    return FakeUpstream()


@pytest.fixture
def settings() -> McpSettings:
    """The app's settings: fake issuer, fake upstreams, no TLS."""
    return McpSettings(
        auth_server_url=ISSUER,  # pyright: ignore[reportArgumentType] - pydantic parses the URL text
        auth_audience=AUDIENCE,
        write_role=WRITE_ROLE,
        server_base_url=CATALOGUE,  # pyright: ignore[reportArgumentType] - pydantic parses the URL text
        validate_entity_base_url=VERDICTS,  # pyright: ignore[reportArgumentType] - pydantic parses the URL text
    )


@pytest.fixture
def auth() -> Iterator[KeycloakAuth]:
    """A verifier talking to the fake issuer, injected into the app."""
    instance = KeycloakAuth(
        AuthConfig(server_url=ISSUER, realm=REALM, audience=AUDIENCE, write_role=WRITE_ROLE),
        http=issuer_client(),
    )
    yield instance
    instance.close()


@pytest.fixture
def app(settings: McpSettings, auth: KeycloakAuth, upstream: FakeUpstream, monkeypatch: pytest.MonkeyPatch) -> Any:  # noqa: ANN401 - the gate-wrapped ASGI app
    """The app, verifying against the fake issuer and relaying to the fake upstream.

    The app's own pools are replaced before they are built: :func:`create_app` calls the
    module-level ``_pools``, so the patch is the seam (the aux apps' injected-client
    posture, DD-200).
    """
    pool = httpx.AsyncClient(base_url=CATALOGUE, transport=upstream.transport())
    verdicts = httpx.AsyncClient(base_url=VERDICTS, transport=upstream.transport())
    monkeypatch.setattr("aurelius_atlas_mcp.app._pools", lambda _settings: (pool, verdicts))
    return create_app(settings=settings, auth=auth)


@pytest.fixture
def token() -> Callable[..., str]:
    """The token minter as a fixture, so tests import no conftest."""
    return make_token


@asynccontextmanager
async def _mcp_session(app: Any, token: str | None) -> AsyncIterator[ClientSession]:  # noqa: ANN401 - the gate app
    """One MCP client session against the app in-process, with an optional bearer."""
    headers = {"authorization": f"Bearer {token}"} if token else {}
    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://mcp.test", headers=headers) as http_client,
        app.inner.router.lifespan_context(app.inner),
        streamable_http_client("http://mcp.test/mcp", http_client=http_client) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        yield session


@pytest.fixture
def mcp_session(app: Any) -> Callable[[str | None], Any]:  # noqa: ANN401 - the async context manager
    """Build one MCP session against the app, presenting the bearer given to it.

    A factory, not a fixture, because a test's identity is the token it presents: one
    app, many callers (MCP-02, MCP-11).
    """
    return lambda bearer: _mcp_session(app, bearer)
