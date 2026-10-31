import os
from collections.abc import AsyncIterator
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server import app as server_app
from aurelius_atlas_server.settings import ENV_PREFIX
from aurelius_atlas_store_es import store
from aurelius_atlas_store_es.testing.fake import FakeClient
from fake_issuer import CLIENT_SECRET, SERVER_URL, WEBAPP, FakeIssuer
from fastapi import FastAPI

BASE_URL = "https://aurelius-atlas"
"""The in-process server's address: HTTPS, so the session cookie (``Secure``) travels (AUT-05)."""


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from a clean environment (DD-199).

    ``nx test`` injects the project's ``.env`` into the task's environment, and
    pydantic-settings reads it: the dev values — TLS material and the
    dashboard dir as workspace-root-relative paths, the dev store password —
    would leak into the settings the fixtures and tests build, and the paths
    do not resolve at the test's working directory. Tests set exactly the
    variables they mean.
    """
    for name in list(os.environ):
        if name.startswith(ENV_PREFIX):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def ca_file(tmp_path: Path) -> Path:
    """A file standing in for the Elasticsearch CA; the fake client never reads it."""
    path = tmp_path / "ca.pem"
    path.write_text("not a certificate\n")
    return path


@pytest.fixture
def tls_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Files standing in for the serving certificate and key (SRV-06); unit tests never start uvicorn."""
    certificate, key = tmp_path / "server.pem", tmp_path / "server-key.pem"
    certificate.write_text("cert\n")
    key.write_text("key\n")
    return certificate, key


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """The server's models directory: none, as loading Atlas's takes seconds (MDL-16); a module may give some."""
    return tmp_path / "no-models"


@pytest.fixture
def settings(ca_file: Path, tls_pair: tuple[Path, Path], models_dir: Path) -> ServerSettings:
    """Settings for a server on a local store, without models: loading Atlas's takes seconds (MDL-16).

    Propagation happens in the request (TSK-08), so responses show it at once; the task tests turn tasks on.
    """
    certificate, key = tls_pair
    return ServerSettings.model_validate(
        {
            "elasticsearch_hosts": ["https://localhost:9200"],
            "elasticsearch_password": "test-password",
            "elasticsearch_ca_certs": ca_file,
            "tls_cert_file": certificate,
            "tls_key_file": key,
            "revision": "abc123",
            "models_dir": models_dir,
            "tasks_enabled": False,
            "auth_server_url": SERVER_URL,
            "auth_client_secret": CLIENT_SECRET,
            "auth_audiences": [WEBAPP],
        }
    )


@pytest.fixture(autouse=True)
def issuer(monkeypatch: pytest.MonkeyPatch) -> FakeIssuer:
    """The identity provider every application of a test verifies tokens with and signs browsers in at."""
    fake = FakeIssuer()
    build_auth, build_oidc = server_app.build_auth, server_app.build_oidc
    monkeypatch.setattr(server_app, "build_auth", lambda settings, *_: build_auth(settings, fake.sync_client()))
    monkeypatch.setattr(
        server_app, "build_oidc", lambda settings, auth, *_: build_oidc(settings, auth, fake.async_client())
    )
    return fake


@pytest.fixture
def auth_headers(issuer: FakeIssuer) -> dict[str, str]:
    """The bearer token of the webapp's user ``admin``, as the webapp sends it (AUT-02)."""
    return {"Authorization": f"Bearer {issuer.token()}"}


@pytest.fixture
def fake_es(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    """The Elasticsearch client the store builds, healthy unless a test changes it."""
    fake = FakeClient()

    def build(**kwargs: object) -> FakeClient:
        fake.kwargs = kwargs
        return fake

    monkeypatch.setattr(store, "AsyncElasticsearch", build)
    return fake


@pytest.fixture
def app(settings: ServerSettings, fake_es: FakeClient) -> FastAPI:
    """The application on the fake store."""
    _ = fake_es
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI, auth_headers: dict[str, str]) -> AsyncIterator[httpx.AsyncClient]:
    """A client talking to the started application in-process, as the webapp's user ``admin``."""
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, headers=auth_headers) as client:
            yield client
