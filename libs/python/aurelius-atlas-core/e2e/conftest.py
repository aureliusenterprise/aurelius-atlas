from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import uuid4

import pytest
from aurelius_atlas_store_es import ElasticsearchStore, StoreSettings
from dotenv import dotenv_values

WORKSPACE = Path(__file__).resolve().parents[4]
DEV_ELASTICSEARCH = WORKSPACE / "dev" / "elasticsearch"


@pytest.fixture(scope="session")
def dev_dir() -> Path:
    """The ``dev/elasticsearch`` project directory."""
    return DEV_ELASTICSEARCH


@pytest.fixture(scope="session")
def dev_env() -> dict[str, str]:
    """The dev store's decrypted ``.env``; the e2e target decrypts it before the run."""
    values = dotenv_values(DEV_ELASTICSEARCH / ".env")
    return {key: value for key, value in values.items() if value is not None}


@pytest.fixture(scope="session")
def dev_settings(dev_env: dict[str, str]) -> StoreSettings:
    """Settings for the store started by ``nx up aurelius-atlas-dev-elasticsearch``."""
    return StoreSettings.model_validate(
        {
            "hosts": [f"https://localhost:{dev_env['ELASTICSEARCH_PORT']}"],
            "password": dev_env["ELASTICSEARCH_PASSWORD"],
            "ca_certs": DEV_ELASTICSEARCH / "certs" / "ca.pem",
        },
    )


@pytest.fixture
async def dev_store(dev_settings: StoreSettings) -> AsyncGenerator[ElasticsearchStore]:
    """An open store on the dev Elasticsearch."""
    async with ElasticsearchStore(dev_settings) as store:
        yield store


@pytest.fixture
async def typedef_index(dev_store: ElasticsearchStore) -> AsyncGenerator[str]:
    """A typedef alias of its own for one test, deleted with its index afterwards."""
    alias = f"aurelius-atlas-typedefs-e2e-{uuid4().hex[:12]}"
    yield alias
    await dev_store.client.indices.delete(index=f"{alias}-000001", ignore_unavailable=True)


@pytest.fixture
async def entity_prefix(dev_store: ElasticsearchStore) -> AsyncGenerator[str]:
    """An alias prefix of its own for one test's entity indices, deleted with them afterwards."""
    prefix = f"aurelius-atlas-e2e-{uuid4().hex[:12]}"
    yield prefix
    for name in (
        "entities",
        "unique-values",
        "entity-journal",
        "relationships",
        "classifications",
        "tasks",
        "entity-audits",
    ):
        await dev_store.client.indices.delete(index=f"{prefix}-{name}-000001", ignore_unavailable=True)
