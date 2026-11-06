"""The m4i data dictionary types, loaded at start-up after Atlas's models unless turned off (MDD-01, MDD-03)."""

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_core.model_loader import M4I_MODELS_DIR
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient
from base_models import base_models

TYPES = "/api/atlas/v2/types"


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model: ``DataSet``, ``Process`` and ``Referenceable``, which the m4i types extend."""
    return base_models(tmp_path)


@contextlib.asynccontextmanager
async def started(settings: ServerSettings, headers: dict[str, str], *, m4i: bool) -> AsyncIterator[httpx.AsyncClient]:
    """A client of a server started with the m4i types on or off."""
    app = create_app(settings.model_copy(update={"m4i_models_enabled": m4i}))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas", headers=headers) as client:
            yield client


@pytest.mark.covers("aurelius_atlas_server.settings.ServerSettings.model_dirs", rules=["MDD-01", "MDD-03"])
def test__the_m4i_models_follow_atlas_models_unless_turned_off(settings: ServerSettings) -> None:
    """On by default; off leaves only the models directory."""
    default = ServerSettings.model_validate(settings.model_dump(exclude={"m4i_models_enabled"}))

    assert default.m4i_models_enabled
    assert default.model_dirs == [settings.models_dir, M4I_MODELS_DIR]
    assert settings.model_copy(update={"m4i_models_enabled": False}).model_dirs == [settings.models_dir]


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["MDD-01", "MDD-03"])
async def test__a_started_server_knows_the_m4i_types(
    settings: ServerSettings, auth_headers: dict[str, str], fake_es: FakeClient
) -> None:
    """With the m4i types on, the type and its classification read; a restart with them off keeps them stored."""
    _ = fake_es
    async with started(settings, auth_headers, m4i=True) as client:
        dataset = await client.get(f"{TYPES}/entitydef/name/m4i_dataset")
        pii = await client.get(f"{TYPES}/classificationdef/name/PII")
    async with started(settings, auth_headers, m4i=False) as client:
        kept = await client.get(f"{TYPES}/entitydef/name/m4i_dataset")

    assert dataset.status_code == 200
    assert "DataSet" in dataset.json()["superTypes"]
    assert pii.status_code == 200
    assert kept.status_code == 200


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["MDD-03"])
async def test__a_server_without_them_has_none(
    settings: ServerSettings, auth_headers: dict[str, str], fake_es: FakeClient
) -> None:
    """Off on a new store: no m4i type is created."""
    _ = fake_es
    async with started(settings, auth_headers, m4i=False) as client:
        dataset = await client.get(f"{TYPES}/entitydef/name/m4i_dataset")

    assert dataset.status_code == 404
