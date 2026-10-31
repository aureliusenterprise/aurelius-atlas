"""E2E fixtures: the Elasticsearch store on the cluster (DD-283).

The suite's one target is the Helm umbrella of ``tools/cluster/install.sh up``:
the release's own ``svc/atlas-elasticsearch`` dialled at its Service FQDN
through a port-forward (SAN-honest TLS, CHT-104), the ``elastic`` password read
from the release's ``atlas-elasticsearch`` Secret, the chart CA from the CA
Secret. The tests talk to Elasticsearch and nothing else, so swapping this one
fixture moves the whole suite — and the namespaced-alias discipline (DD-223) is
what makes the shared cluster store safe for these writes.
"""

import sys
from collections.abc import AsyncGenerator, Iterator
from uuid import uuid4

import pytest
from aurelius_atlas_cluster_lane import SecretReader, ServiceForward, install_cluster_fixtures
from aurelius_atlas_store_es import ElasticsearchStore, StoreSettings

# The cluster shapes (the umbrella install of tools/cluster/install.sh).
SERVICE_CLUSTER = "atlas-elasticsearch"
"""The elasticsearch chart's Service in the umbrella release."""
SERVICE_PORT = 9200
"""The Service's real port — what the shim rewrites alongside the name (CHT-104)."""
ELASTICSEARCH_SECRET = "atlas-elasticsearch"
"""The release Secret carrying the elastic password (CHT-78's family)."""
CLUSTER_NAMESPACE = "atlas"

# The session `cluster` gate and the autouse resolver shim come from the
# library (CHT-103).
install_cluster_fixtures(sys.modules[__name__])


@pytest.fixture(scope="session")
def store_settings(_cluster_dns: None, cluster: dict[str, str]) -> Iterator[StoreSettings]:
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


@pytest.fixture
async def dev_store(store_settings: StoreSettings) -> AsyncGenerator[ElasticsearchStore]:
    """An open store on the release's Elasticsearch."""
    async with ElasticsearchStore(store_settings) as store:
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
