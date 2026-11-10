"""Fixtures for the app tests: settings, a fake Keycloak issuer, a fake upstream.

The fake issuer is the 8.0 auth library's test double (AUX-01..05 are tested at
home, in ``aurelius-atlas-auth``), in its own module ``fake_issuer``; the fake
upstream is the Atlas lineage feed and the data2model ``/extract`` the app
proxies to (DD-200): a ``MockTransport`` recording every request and answering
from a handler each test sets, in its own module ``fake_upstream``. Helpers live
in modules of their own because the trace check collects ``tests/`` and ``e2e/``
in one run and same-named ``conftest`` modules collide on ``sys.path``.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator

import httpx2 as httpx
import pytest
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_data2model_client.client import Data2ModelClient
from aurelius_atlas_lineage_model import LineageModelSettings, create_app
from aurelius_atlas_lineage_model.settings import ENV_PREFIX
from aurelius_atlas_server_client.client import AtlasClient
from fake_issuer import AUDIENCE, ISSUER, REALM, issuer_client, make_token
from fake_upstream import FakeUpstream
from fastapi import FastAPI
from pydantic import HttpUrl

ATLAS = "http://atlas.test"
DATA2MODEL = "http://data2model.test"


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from a clean environment (DD-199).

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
    """The application, verifying tokens against the fake issuer and calling the fake upstream.

    Both upstream clients speak through an externally built httpx client on the
    fake's recording transport (DD-200's seam, typed with the 8.4 clients, built
    outside per DD-205); the token source is a placeholder — each request runs
    ``with_token`` with the caller's own.
    """
    atlas = AtlasClient(httpx.AsyncClient(base_url=ATLAS, transport=upstream.transport()), "test-token")
    d2m = Data2ModelClient(httpx.AsyncClient(base_url=DATA2MODEL, transport=upstream.transport()), "test-token")
    return create_app(settings, auth=auth, atlas=atlas, d2m=d2m)


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
