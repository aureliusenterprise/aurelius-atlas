from collections.abc import AsyncGenerator
from pathlib import Path

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
