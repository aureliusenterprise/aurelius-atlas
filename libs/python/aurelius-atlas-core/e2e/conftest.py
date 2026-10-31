"""E2E fixtures: the Elasticsearch store, per lane (10.5b, DD-282).

Compose (the default, CI's lane): the dev store started by
``nx up aurelius-atlas-dev-elasticsearch``, its decrypted ``.env`` and mkcert
CA. Cluster (``ATLAS_E2E_TARGET=cluster``): the release's own
``svc/atlas-elasticsearch`` dialled at its Service FQDN through a port-forward
(SAN-honest TLS, CHT-104), the ``elastic`` password read from the release's
``atlas-elasticsearch`` Secret, the chart CA from the CA Secret. The tests
talk to Elasticsearch and nothing else, so swapping this one fixture moves
the whole suite — and the namespaced-alias discipline (DD-223) is what makes
the shared cluster store safe for these writes.
"""

import sys
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from aurelius_atlas_cluster_lane import SecretReader, ServiceForward, install_cluster_fixtures, lane_target
from aurelius_atlas_store_es import ElasticsearchStore, StoreSettings
from dotenv import dotenv_values

WORKSPACE = Path(__file__).resolve().parents[4]
DEV_ELASTICSEARCH = WORKSPACE / "dev" / "elasticsearch"

# The cluster shapes (the umbrella install of tools/cluster/install.sh).
SERVICE_CLUSTER = "atlas-elasticsearch"
"""The elasticsearch chart's Service in the umbrella release."""
SERVICE_PORT = 9200
"""The Service's real port — what the shim rewrites alongside the name (CHT-104)."""
ELASTICSEARCH_SECRET = "atlas-elasticsearch"
"""The release Secret carrying the elastic password (CHT-78's family)."""
CLUSTER_NAMESPACE = "atlas"

# The session `cluster` gate and the autouse resolver shim come from the lane
# library (CHT-103). The certs path only feeds the lib's generic ca_file
# fixture, which this suite does not use — dev_settings carries the CA.
install_cluster_fixtures(sys.modules[__name__], DEV_ELASTICSEARCH / "certs")


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
def cluster_store(_cluster_dns: None, cluster: dict[str, str]) -> Iterator[StoreSettings]:
    """The release's store: the Service FQDN through a port-forward, SAN-honest (CHT-104).

    The forward lives for the session; the shim maps the
    ``atlas-elasticsearch.atlas.svc.cluster.local`` host onto it (the URL
    carries the forward's own port), so the URL, SNI, and verified SAN stay
    honest (the chart leaf carries the 4-name FQDN block plus the headless
    names). The password rides the release Secret.
    """
    password = SecretReader(CLUSTER_NAMESPACE).read(ELASTICSEARCH_SECRET, "elastic-password")
    with ServiceForward(
        SERVICE_CLUSTER,
        SERVICE_PORT,
        f"{SERVICE_CLUSTER}.atlas.svc.cluster.local",
        namespace=CLUSTER_NAMESPACE,
        probe_path="/_cluster/health",
        ca_file=cluster["ca_file"],
        ready_timeout=60.0,
    ) as forward:
        yield StoreSettings.model_validate(
            {
                "hosts": [forward.url],
                "password": password,
                "ca_certs": cluster["ca_file"],
            },
        )


@pytest.fixture(scope="session")
def dev_settings(request: pytest.FixtureRequest, dev_env: dict[str, str]) -> StoreSettings:
    """The store settings for the lane ATLAS_E2E_TARGET picked.

    Compose: the dev store on its published port and mkcert CA —
    ``nx up aurelius-atlas-dev-elasticsearch``. Cluster: :func:`cluster_store`
    (requested lazily — a compose-mode run never imports a kubectl-shaped
    call, CHT-103).
    """
    if lane_target() == "cluster":
        return request.getfixturevalue("cluster_store")
    return StoreSettings.model_validate(
        {
            "hosts": [f"https://localhost:{dev_env['ELASTICSEARCH_PORT']}"],
            "password": dev_env["ELASTICSEARCH_PASSWORD"],
            "ca_certs": DEV_ELASTICSEARCH / "certs" / "ca.pem",
        },
    )


@pytest.fixture
async def dev_store(dev_settings: StoreSettings) -> AsyncGenerator[ElasticsearchStore]:
    """An open store on the lane's Elasticsearch."""
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
