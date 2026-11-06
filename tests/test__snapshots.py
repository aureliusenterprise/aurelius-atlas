"""Snapshots contract suite (SNP-01, SNP-03, SNP-07; 6.4e, ADR 026).

The store keeps its snapshots on a volume apart from its data, below the node's ``path.repo``, in dev and in
the chart; the server chart turns the snapshots on; an overdue snapshot raises an alert; and the server chart's
restore Job restores the store only while no server runs.
"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from conftest import (
    ES_CHART,
    SERVER_CHART,
    WORKSPACE,
    container,
    env_map,
    env_value,
    find,
    helm_render,
    helm_render_fails,
    pod_spec,
)

SNAPSHOTS_DIR = "/usr/share/elasticsearch/snapshots"
DEV_STORE = WORKSPACE / "dev/elasticsearch"
SERVER_TEST_VALUES = (SERVER_CHART / "tests/values.test.yaml",)


@pytest.mark.covers(rules=["SNP-01"])
def test__the_dev_store_keeps_its_snapshots_on_their_own_volume() -> None:
    """``path.repo`` names the snapshots directory, a named volume of its own, handed to the node's user."""
    config = yaml.safe_load((DEV_STORE / "config/elasticsearch.yml").read_text())
    compose = yaml.safe_load((DEV_STORE / "docker-compose.yaml").read_text())
    services = compose["services"]

    assert config["path.repo"] == [SNAPSHOTS_DIR]
    assert "snapshots" in compose["volumes"]
    assert f"snapshots:{SNAPSHOTS_DIR}" in services["elasticsearch"]["volumes"]
    assert f"snapshots:{SNAPSHOTS_DIR}" in services["volume-init"]["volumes"]
    assert SNAPSHOTS_DIR in services["volume-init"]["entrypoint"]


@pytest.mark.covers(rules=["SNP-01"])
def test__the_chart_s_store_keeps_its_snapshots_on_a_claim_that_outlives_the_release(
    es_docs: list[dict[str, Any]],
) -> None:
    """A claim apart from the data's, kept on uninstall, mounted at ``path.repo``."""
    settings = yaml.safe_load(find(es_docs, "ConfigMap", "atlas-elasticsearch")["data"]["elasticsearch.yml"])
    claim = find(es_docs, "PersistentVolumeClaim", "atlas-elasticsearch-snapshots")
    store = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    mounts = {m["name"]: m["mountPath"] for m in container(store, "elasticsearch")["volumeMounts"]}
    volumes = {v["name"]: v for v in pod_spec(store)["volumes"]}

    assert settings["path.repo"] == [SNAPSHOTS_DIR]
    assert claim["metadata"]["annotations"]["helm.sh/resource-policy"] == "keep"
    assert claim["spec"]["resources"]["requests"]["storage"] == "30Gi"
    assert "storageClassName" not in claim["spec"]
    assert mounts["snapshots"] == SNAPSHOTS_DIR
    assert volumes["snapshots"]["persistentVolumeClaim"]["claimName"] == "atlas-elasticsearch-snapshots"
    assert [t["metadata"]["name"] for t in store["spec"]["volumeClaimTemplates"]] == ["data"]

    classed = helm_render(ES_CHART, sets=("global.storageClass=fast-ssd",))
    assert find(classed, "PersistentVolumeClaim", "atlas-elasticsearch-snapshots")["spec"]["storageClassName"] == (
        "fast-ssd"
    )


@pytest.mark.covers(rules=["SNP-01"])
def test__the_chart_s_server_takes_snapshots(server_docs: list[dict[str, Any]]) -> None:
    """The server chart turns them on; the dev server keeps the default, off."""
    envs = env_map(container(find(server_docs, "Deployment", "atlas-server"), "server"))

    assert env_value(envs, "AURELIUS_ATLAS_SERVER_SNAPSHOT_ENABLED") == "true"


@pytest.mark.covers(rules=["SNP-03"])
def test__an_overdue_snapshot_raises_an_alert() -> None:
    """The rule reads the server's gauge: two hours without a success fires; no data, snapshots off, is OK."""
    rules = yaml.safe_load((WORKSPACE / "dev/observability/config/grafana/alerting/rules.yaml").read_text())
    [rule] = [rule for rule in rules["groups"][0]["rules"] if rule["uid"] == "aurelius-atlas-snapshot-overdue"]
    expression, threshold = rule["data"][0]["model"]["expr"], rule["data"][1]["model"]["conditions"][0]

    assert "aurelius_atlas_snapshot_last_success_seconds" in expression
    assert expression.startswith("time() - max(")
    assert threshold["evaluator"] == {"type": "gt", "params": [7200]}
    assert (rule["noDataState"], rule["execErrState"], rule["for"]) == ("OK", "Alerting", "15m")
    assert rule["labels"] == {"severity": "critical", "team": "maintainers"}


@pytest.mark.covers(rules=["SNP-07"])
def test__the_restore_job_runs_the_snapshot_command_while_no_server_runs(server_docs: list[dict[str, Any]]) -> None:
    """Off by default; enabled, only at replicaCount 0, against the Deployment's store, with its labels."""
    assert not [doc for doc in server_docs if doc["kind"] == "Job"]
    assert "replicaCount=0" in helm_render_fails(
        SERVER_CHART, value_files=SERVER_TEST_VALUES, sets=("restore.enabled=true",)
    )

    docs = helm_render(
        SERVER_CHART,
        value_files=SERVER_TEST_VALUES,
        sets=("restore.enabled=true", "replicaCount=0", "restore.snapshot=aurelius-atlas-2026.11.04-10.00-x"),
    )
    job = find(docs, "Job", "atlas-server-restore")
    restore = container(job, "restore")
    deployment = find(docs, "Deployment", "atlas-server")
    envs, served = env_map(restore), env_map(container(deployment, "server"))

    assert restore["command"] == [
        "python",
        "-m",
        "aurelius_atlas_server.snapshots",
        "restore",
        "--replace",
        "--snapshot",
        "aurelius-atlas-2026.11.04-10.00-x",
    ]
    assert restore["image"] == container(deployment, "server")["image"]
    for name in ("HOSTS", "PASSWORD", "CA_CERTS"):
        assert (
            envs[f"AURELIUS_ATLAS_SERVER_ELASTICSEARCH_{name}"] == served[f"AURELIUS_ATLAS_SERVER_ELASTICSEARCH_{name}"]
        )
    assert "AURELIUS_ATLAS_SERVER_AUTH_CLIENT_SECRET" not in envs
    assert (job["spec"]["backoffLimit"], pod_spec(job)["restartPolicy"]) == (0, "Never")
    labels = job["spec"]["template"]["metadata"]["labels"]
    assert (labels["app.kubernetes.io/name"], labels["app.kubernetes.io/instance"]) == ("atlas-server", "atlas")

    newest = helm_render(SERVER_CHART, value_files=SERVER_TEST_VALUES, sets=("restore.enabled=true", "replicaCount=0"))
    assert container(find(newest, "Job", "atlas-server-restore"), "restore")["command"][-1] == "--replace"
