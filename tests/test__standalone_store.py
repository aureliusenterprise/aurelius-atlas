"""The standalone stack's own store (SST-01..02, 9.5c; IRT-05, ADR 066).

The stack's compose is read as written, the umbrella and the fragments merged and each service's
`extends` resolved as compose does (ADR 065, DD-671): the stack's Elasticsearch, its volumes and
the server's address of it, apart from the infra store's network. The node is the infra slice's
service extended (DD-668), so the suite proves the inheritance rather than a copy.
"""

from typing import Any

import pytest
import yaml
from conftest import WORKSPACE, compose_load, standalone_compose

INFRA_ELASTICSEARCH = WORKSPACE / "infra/elasticsearch/docker-compose.yaml"


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    """The stack's compose file, the fragments merged and their `extends` resolved."""
    return standalone_compose()


@pytest.mark.covers(rules=["SST-01", "IRT-05"])
def test__stack_runs_its_own_store(compose: dict[str, Any]) -> None:
    """The stack's node is the infra service, extended: its image, configuration, roles,
    certificate, agent and healthcheck inherited; its own volumes, no port (SST-01, IRT-05).
    """  # noqa: D205 - one sentence
    store = compose["services"]["elasticsearch"]
    base = yaml.safe_load(INFRA_ELASTICSEARCH.read_text())["services"]["elasticsearch"]
    stated = compose_load(WORKSPACE / "docker/elasticsearch/compose.yaml")["services"]["elasticsearch"]
    # The definition is the slice's: image and healthcheck arrive by inheritance, written nowhere
    # in the stack (DD-668); the old byte-copy pin becomes this proof.
    assert store["image"] == base["image"]
    assert store["healthcheck"]["test"] == base["healthcheck"]["test"]
    assert "image" not in stated
    assert "healthcheck" not in stated
    # The stack's differences: its own volumes, no published port.
    assert "ports" not in store
    assert {"elasticsearch-data", "elasticsearch-snapshots"} <= set(compose["volumes"])
    assert "elasticsearch-data:/usr/share/elasticsearch/data" in store["volumes"]
    assert "elasticsearch-snapshots:/usr/share/elasticsearch/snapshots" in store["volumes"]
    config = "infra/elasticsearch/config/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml:ro"
    assert config in store["volumes"]
    assert "infra/elasticsearch/certs:/usr/share/elasticsearch/config/tls:ro" in store["volumes"]
    assert "infra/elasticsearch/config/roles.yml:/usr/share/elasticsearch/config/roles.yml:ro" in store["volumes"]
    assert "tools/es-coredump-agent/coredump-noop.jar:/agent/coredump-noop.jar:ro" in store["volumes"]
    # The heap is the slice's placeholder; the elastic password is the server's (DD-669).
    assert store["environment"]["ES_JAVA_OPTS"] == base["environment"]["ES_JAVA_OPTS"]
    assert store["ulimits"] == base["ulimits"]


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
