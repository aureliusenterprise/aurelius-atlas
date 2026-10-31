"""Fixtures for the chart-contract suite (DD-253): one render per chart, shared.

The suite renders with the ``helm`` CLI — a chart is a YAML generator and the
contract it owes is the rendered manifest, so the manifest is what gets
asserted. ``helm`` ships in the devcontainer and the CI runner (the charts
gate, CHT-06); without it every test here skips rather than fails.

No cluster, no registry, no SOPS key: the renders use only the charts' own
defaults (helm.ts renders the charts bare the same way) plus the value
combinations each rule names. Umbrella renders depend on the component-chart
tarballs (``helm/charts/`` is gitignored), so the session fixture refreshes
them with ``helm dependency update`` first — the suite is self-contained.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKSPACE = Path(__file__).resolve().parents[1]
ES_CHART = WORKSPACE / "dev/elasticsearch/helm"
KC_CHART = WORKSPACE / "dev/keycloak/helm"
SERVER_CHART = WORKSPACE / "apps/aurelius-atlas-server/helm"
WEBAPP_CHART = WORKSPACE / "apps/aurelius-atlas-webapp/helm"
AUX_CHARTS = {
    "data2model": WORKSPACE / "apps/aurelius-atlas-data2model/helm",
    "lineage-model": WORKSPACE / "apps/aurelius-atlas-lineage-model/helm",
    "validate-entity": WORKSPACE / "apps/aurelius-atlas-validate-entity/helm",
}
OBS_CHART = WORKSPACE / "dev/observability/helm"
UMBRELLA_CHART = WORKSPACE / "helm"

# The ingest-client roster (CHT-87..90, DD-277): the otel-* clients the prod
# realm asset spells one ${OTEL_<ID>_CLIENT_SECRET} placeholder for each,
# mirrored by the KC chart's atlas-keycloak.otelClients helper and the
# umbrella's per-client Secret keys. Both suites pin their copies against
# this list (roster drift guard); the asset itself is the source of truth.
OTEL_CLIENT_IDS = (
    "otel-atlas-server",
    "otel-data2model",
    "otel-elasticsearch",
    "otel-keycloak",
    "otel-lineage-model",
    "otel-postgres",
    "otel-validate-entity",
)

# The committed third-party digests (CHT-93, DD-278): the nine distinct dhi.io
# pins the chart values carry. Chart suites assert their own renders against
# this map; ``tools/images/chart_digests.py --check`` is the registry-side
# twin, and the umbrella guard (CHT-97) knows these repos as the legal
# digest-pinned set. Keep in sync with the values files — the drift guard
# workflow fails on divergence from the registry, these tests on divergence
# from here.
PINNED = {
    "dhi.io/elasticsearch": "sha256:18afc55bce2fdae289c80580769dfc27161ce24d7dc9e6727f8124ee61d0c375",
    "dhi.io/keycloak": "sha256:d585d342ea3b9b2aa5b8f3216e88fa04f2eb1846d6986caa4227a6a887296bf6",
    "dhi.io/postgres": "sha256:c075241e0b60eca5cb40e61484feb582b17bd756e8c48a482d93321607a332ce",
    "dhi.io/opentelemetry-collector": "sha256:79de5a3a0319b189dfb428d3fa36a39b8d83ee6605e106089ce78153f7f5ac6e",
    "dhi.io/curl": "sha256:229a580c4b21bffe98970883ae1c11248e82390454e5fec79109132f4b774862",
    "dhi.io/prometheus": "sha256:585a54e52b97d4400aaa4c7ef9470add072362b236cd7fb4e8aacdd371121109",
    "dhi.io/loki": "sha256:4e7325c57c492c02e8944b22cf0c80299a49d657eced3ed9f56853a01f622a41",
    "dhi.io/tempo": "sha256:e6355af759ed371adca5b1fc76303b9eb7db3da15739ba76def54a3f336734c8",
    "dhi.io/grafana": "sha256:3524a4af20d6485671f0576084ee16b35a276fa2e7a490f02c95e46e18778384",
}


def pinned_ref(repository: str) -> str:
    """The full immutable reference a stock render must carry (CHT-93)."""
    return f"{repository}@{PINNED[repository]}"


def _require_helm() -> None:
    if shutil.which("helm") is None:  # pragma: no cover - environment guard
        pytest.skip("helm CLI not on PATH (devcontainer / CI runner feature)")


def helm_render(
    chart: Path,
    *,
    release: str = "atlas",
    sets: tuple[str, ...] = (),
    value_files: tuple[Path, ...] = (),
) -> list[dict[str, Any]]:
    """Render a chart with ``helm template`` and return its parsed documents.

    Args:
        chart: The chart directory.
        release: The release name (``atlas`` by default; the CHT-70 join pins
            both the prefix-equal and the prefixed spellings).
        sets: ``--set`` arguments, in order.
        value_files: ``-f`` value files, in order.

    Returns:
        The rendered Kubernetes documents (empty ones dropped).

    Raises:
        AssertionError: The render failed; the helm stderr rides along.
    """
    cmd = ["helm", "template", release, str(chart), "--namespace", "atlas"]
    for values in value_files:
        cmd += ["-f", str(values)]
    for arg in sets:
        cmd += ["--set", arg]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert done.returncode == 0, f"helm render of {chart} failed:\n{done.stderr}"
    return [doc for doc in yaml.safe_load_all(done.stdout) if doc]


def helm_render_fails(chart: Path, *, sets: tuple[str, ...] = (), value_files: tuple[Path, ...] = ()) -> str:
    """Assert a render fails and return helm's stderr (guard tests)."""
    cmd = ["helm", "template", "atlas", str(chart), "--namespace", "atlas"]
    for values in value_files:
        cmd += ["-f", str(values)]
    for arg in sets:
        cmd += ["--set", arg]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert done.returncode != 0, f"expected a failing render for {sets}, got success"
    return done.stderr


def find(docs: list[dict[str, Any]], kind: str, name: str) -> dict[str, Any]:
    """The one document of kind/name; fail with an inventory."""
    matches = [d for d in docs if d["kind"] == kind and d["metadata"]["name"] == name]
    inventory = ", ".join(f"{d['kind']}/{d['metadata']['name']}" for d in docs)
    assert len(matches) == 1, f"expected exactly one {kind} {name!r} in: {inventory}"
    return matches[0]


def find_all(docs: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    """Every document of a kind."""
    return [d for d in docs if d["kind"] == kind]


def names(docs: list[dict[str, Any]], kind: str) -> set[str]:
    """The names of every document of a kind."""
    return {d["metadata"]["name"] for d in docs if d["kind"] == kind}


def pod_spec(doc: dict[str, Any]) -> dict[str, Any]:
    """The pod template spec of a workload document."""
    return doc["spec"]["template"]["spec"]


def container(doc: dict[str, Any], name: str) -> dict[str, Any]:
    """A named container of a workload document."""
    containers = pod_spec(doc)["containers"]
    matches = [c for c in containers if c["name"] == name]
    assert len(matches) == 1, f"no container {name!r} in {[c['name'] for c in containers]}"
    return matches[0]


def env_map(container: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The container's env as name to env-var mapping (values stay nested)."""
    return {e["name"]: e for e in container.get("env", [])}


def env_value(envs: dict[str, dict[str, Any]], name: str) -> str:
    """A plain (non-secret) env value; fail when the var is a secret ref."""
    env = envs[name]
    assert "value" in env, f"{name} is not a literal value: {env}"
    return env["value"]


def peer_labels(name: str, instance: str = "atlas", component: str | None = None) -> dict[str, str]:
    """The matchLabels a NetworkPolicy peer selector carries for a workload's pods.

    The CHT-70 join: a pod's name label is its chart-name constant (or,
    for fullname-derived workloads like the pullers, the fullname-qualified
    name) and its instance label is the release.
    """
    labels = {"app.kubernetes.io/name": name, "app.kubernetes.io/instance": instance}
    if component:
        labels["app.kubernetes.io/component"] = component
    return labels


def policy_peers_by_port(docs: list[dict[str, Any]], name: str) -> dict[int, set[str]]:
    """A NetworkPolicy's pod-peer name labels per port (namespace peers omitted).

    Args:
        docs: A render's documents.
        name: The NetworkPolicy's metadata name.

    Returns:
        Port to the set of peer pod name labels allowed to it.
    """
    doc = find(docs, "NetworkPolicy", name)
    out: dict[int, set[str]] = {}
    for rule in doc["spec"].get("ingress", []):
        peers = {
            e["podSelector"]["matchLabels"]["app.kubernetes.io/name"]
            for e in rule.get("from", [])
            if "podSelector" in e
        }
        for port in rule.get("ports", []):
            out[port["port"]] = peers
    return out


@pytest.fixture(scope="session", autouse=True)
def _helm_ready() -> None:
    """Skip the suite without helm; refresh the umbrella's component tarballs."""
    _require_helm()
    done = subprocess.run(["helm", "dep", "update", str(UMBRELLA_CHART)], capture_output=True, text=True, check=False)
    assert done.returncode == 0, f"helm dependency update failed:\n{done.stderr}"


@pytest.fixture(scope="session")
def es_docs() -> list[dict[str, Any]]:
    """The store chart at its defaults (the bare render, CHT-10..15)."""
    return helm_render(ES_CHART)


@pytest.fixture(scope="session")
def kc_docs() -> list[dict[str, Any]]:
    """The Keycloak chart at its defaults, bundled database (CHT-16/17)."""
    return helm_render(KC_CHART)


@pytest.fixture(scope="session")
def umbrella_docs() -> list[dict[str, Any]]:
    """The umbrella under its CI test values (CHT-19; issuer, secrets, edge)."""
    return helm_render(UMBRELLA_CHART, value_files=(UMBRELLA_CHART / "tests/values.test.yaml",))


@pytest.fixture(scope="session")
def server_docs() -> list[dict[str, Any]]:
    """The server chart under its CI test values (CHT-20..22)."""
    return helm_render(SERVER_CHART, value_files=(SERVER_CHART / "tests/values.test.yaml",))


@pytest.fixture(scope="session")
def webapp_docs() -> list[dict[str, Any]]:
    """The webapp chart under its CI test values (CHT-23..26)."""
    return helm_render(WEBAPP_CHART, value_files=(WEBAPP_CHART / "tests/values.test.yaml",))


@pytest.fixture(scope="session")
def obs_docs() -> list[dict[str, Any]]:
    """The observability chart under its CI test values (CHT-33..44)."""
    return helm_render(OBS_CHART, value_files=(OBS_CHART / "tests/values.test.yaml",))
