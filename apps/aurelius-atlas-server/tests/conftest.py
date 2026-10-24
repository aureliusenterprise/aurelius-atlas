import os
from collections.abc import AsyncIterator
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server.settings import ENV_PREFIX
from aurelius_atlas_store_es import store
from aurelius_atlas_store_es.testing.fake import FakeClient
from fastapi import FastAPI


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
def settings(ca_file: Path, tmp_path: Path) -> ServerSettings:
    """Settings for a server on a local store, without models: loading Atlas's takes seconds (MDL-16).

    Propagation happens in the request (TSK-08), so responses show it at once; the task tests turn tasks on.
    """
    return ServerSettings.model_validate(
        {
            "elasticsearch_hosts": ["https://localhost:9200"],
            "elasticsearch_password": "test-password",
            "elasticsearch_ca_certs": ca_file,
            "revision": "abc123",
            "models_dir": tmp_path / "no-models",
            "tasks_enabled": False,
        }
    )


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
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """A client talking to the started application in-process."""
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://aurelius-atlas") as client:
            yield client
