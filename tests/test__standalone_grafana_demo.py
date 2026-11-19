"""The standalone Grafana's dashboards on the demo tenant: its data sources, its dashboards and its store user.

The files are read as written, and the Grafana service as Compose resolves the stack.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import WORKSPACE, standalone_compose

GRAFANA = WORKSPACE / "docker/observability/config/grafana"
DASHBOARDS = GRAFANA / "demo-tenant"
TENANTS = WORKSPACE / "apps/aurelius-atlas-server/docker/tenants.py"


def _datasources() -> dict[str, dict[str, Any]]:
    return {
        ds["uid"]: ds for ds in yaml.safe_load((GRAFANA / "demo-tenant-datasources.yaml").read_text())["datasources"]
    }


def test__the_data_sources_read_the_demo_tenant_alone_as_the_read_only_user() -> None:
    """Each data source is the store's Elasticsearch over TLS against the store's CA, signed in to as
    ``grafana_demo_reader`` with the password from the environment, on one demo-tenant index with its time field.
    """  # noqa: D205 - one sentence
    datasources = _datasources()
    assert set(datasources) == {"demo-tenant-entities", "demo-tenant-audits"}
    expected = {
        "demo-tenant-entities": ("aurelius-atlas-tenant-demo-entities", "createTime"),
        "demo-tenant-audits": ("aurelius-atlas-tenant-demo-entity-audits", "timestamp"),
    }
    for uid, ds in datasources.items():
        assert ds["type"] == "elasticsearch"
        assert ds["url"] == "https://elasticsearch:9200"
        assert (ds["basicAuth"], ds["basicAuthUser"]) == (True, "grafana_demo_reader")
        assert ds["secureJsonData"]["basicAuthPassword"] == "${GRAFANA_ES_READER_PASSWORD}"
        assert ds["jsonData"]["tlsAuthWithCACert"] is True
        assert ds["secureJsonData"]["tlsCACert"] == "$__file{/etc/grafana/elasticsearch-certs/ca.pem}"
        assert (ds["jsonData"]["index"], ds["jsonData"]["timeField"]) == expected[uid]
        assert ds["editable"] is False


@pytest.mark.parametrize("name", ["catalogue", "activity"])
def test__every_panel_queries_a_demo_tenant_data_source_on_its_time_field(name: str) -> None:
    """A dashboard's panels each name one of the two data sources by uid and query on its time field; the
    dashboard is read-only and tagged for the demo tenant.
    """  # noqa: D205 - one sentence
    datasources = _datasources()
    board = json.loads((DASHBOARDS / f"{name}.json").read_text())
    assert board["uid"] == f"demo-tenant-{name}"
    assert "demo-tenant" in board["tags"]
    assert board["editable"] is False
    assert board["panels"]
    for panel in board["panels"]:
        for target in panel["targets"]:
            uid = target["datasource"]["uid"]
            assert uid in datasources, panel["title"]
            assert target["timeField"] == datasources[uid]["jsonData"]["timeField"], panel["title"]


def test__grafana_mounts_the_provisioning_the_ca_and_the_password() -> None:
    """The stack's Grafana keeps the slice's provisioning and adds the demo tenant's files, the store's CA and
    the reader's password.
    """  # noqa: D205 - one sentence
    grafana = standalone_compose()["services"]["grafana"]
    targets = {volume["target"] if isinstance(volume, dict) else volume.split(":")[1] for volume in grafana["volumes"]}
    for target in (
        "/etc/grafana/provisioning/datasources/datasources.yaml",
        "/etc/grafana/provisioning/datasources/demo-tenant.yaml",
        "/etc/grafana/provisioning/dashboards/demo-tenant.yaml",
        "/var/lib/grafana/demo-tenant-dashboards",
        "/etc/grafana/elasticsearch-certs",
    ):
        assert target in targets, target
    environment = grafana["environment"]
    names = environment if isinstance(environment, dict) else dict(item.split("=", 1) for item in environment)
    assert "GRAFANA_ES_READER_PASSWORD" in names
    provider = yaml.safe_load((GRAFANA / "demo-tenant-dashboards.yaml").read_text())["providers"][0]
    assert (provider["folder"], provider["options"]["path"]) == (
        "Demo tenant",
        "/var/lib/grafana/demo-tenant-dashboards",
    )


def test__the_store_user_reads_the_demo_tenant_and_writes_nothing() -> None:
    """The one shot gives ``grafana_demo_reader`` a role of read and index metadata on the demo tenant's
    indices, and of the cluster's status alone; no write, no other index.
    """  # noqa: D205 - one sentence
    script = TENANTS.read_text()
    role = script[script.index("name=DEMO_READER_ROLE") : script.index("store.security.put_user(username=DEMO_READER")]
    assert re.search(r'cluster=\["monitor"\]', role)
    assert '"names": ["aurelius-atlas-tenant-demo-*"]' in role
    assert '"privileges": ["read", "view_index_metadata"]' in role
    assert "write" not in role
    assert "store_grafana_reader()" in script.split('if __name__ == "__main__":')[1]


def test__the_dashboards_are_files_grafana_loads() -> None:
    """Each dashboard file is one JSON object of a unique uid."""
    uids = [json.loads(path.read_text())["uid"] for path in sorted(Path(DASHBOARDS).glob("*.json"))]
    assert len(uids) == len(set(uids)) == 2
