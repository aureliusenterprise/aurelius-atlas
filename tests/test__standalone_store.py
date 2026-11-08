"""The standalone stack's own store (SST-01..02, 9.5c).

The compose file is read as written: the stack's Elasticsearch, its volumes and configuration, and the
server's address of it, apart from the dev store's network.
"""

from typing import Any

import pytest
import yaml
from conftest import WORKSPACE

STANDALONE = WORKSPACE / "apps/aurelius-atlas-server/standalone"


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    """The stack's compose file."""
    return yaml.safe_load((STANDALONE / "docker-compose.yaml").read_text())


@pytest.mark.covers(rules=["SST-01"])
def test__stack_runs_its_own_store(compose: dict[str, Any]) -> None:
    """The stack's node has its own volumes, the dev store's configuration and certificate, no port (SST-01)."""
    store = compose["services"]["elasticsearch"]
    dev = yaml.safe_load((WORKSPACE / "dev/elasticsearch/docker-compose.yaml").read_text())["services"]
    assert store["image"] == dev["elasticsearch"]["image"]
    assert "ports" not in store
    assert {"elasticsearch-data", "elasticsearch-snapshots"} <= set(compose["volumes"])
    assert "elasticsearch-data:/usr/share/elasticsearch/data" in store["volumes"]
    assert "elasticsearch-snapshots:/usr/share/elasticsearch/snapshots" in store["volumes"]
    config = "../../../dev/elasticsearch/config/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml:ro"
    assert config in store["volumes"]
    assert "../../../dev/elasticsearch/certs:/usr/share/elasticsearch/config/tls:ro" in store["volumes"]
    assert store["healthcheck"]["test"] == dev["elasticsearch"]["healthcheck"]["test"]


@pytest.mark.covers(rules=["SST-02"])
def test__server_reaches_the_stack_store_alone(compose: dict[str, Any]) -> None:
    """The server's store is the stack's, with one password, healthy first; no dev network is joined (SST-02)."""
    services = compose["services"]
    server = services["aurelius-atlas-server"]
    assert server["environment"]["AURELIUS_ATLAS_SERVER_ELASTICSEARCH_HOSTS"] == '["https://elasticsearch:9200"]'
    password = "${AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD:?}"  # noqa: S105 - a placeholder
    assert server["environment"]["AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD"] == password
    assert services["elasticsearch"]["environment"]["ELASTIC_PASSWORD"] == password
    assert server["depends_on"]["elasticsearch"] == {"condition": "service_healthy"}
    assert "networks" not in compose
    assert all("networks" not in service for service in services.values())
