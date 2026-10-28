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
UMBRELLA_CHART = WORKSPACE / "helm"


def _require_helm() -> None:
    if shutil.which("helm") is None:  # pragma: no cover - environment guard
        pytest.skip("helm CLI not on PATH (devcontainer / CI runner feature)")


def helm_render(
    chart: Path,
    *,
    sets: tuple[str, ...] = (),
    value_files: tuple[Path, ...] = (),
) -> list[dict[str, Any]]:
    """Render a chart with ``helm template`` and return its parsed documents.

    Args:
        chart: The chart directory.
        sets: ``--set`` arguments, in order.
        value_files: ``-f`` value files, in order.

    Returns:
        The rendered Kubernetes documents (empty ones dropped).

    Raises:
        AssertionError: The render failed; the helm stderr rides along.
    """
    cmd = ["helm", "template", "atlas", str(chart), "--namespace", "atlas"]
    for values in value_files:
        cmd += ["-f", str(values)]
    for arg in sets:
        cmd += ["--set", arg]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert done.returncode == 0, f"helm render of {chart} failed:\n{done.stderr}"
    return [doc for doc in yaml.safe_load_all(done.stdout) if doc]


def helm_render_fails(chart: Path, *, sets: tuple[str, ...]) -> str:
    """Assert a render fails and return helm's stderr (guard tests)."""
    done = subprocess.run(
        ["helm", "template", "atlas", str(chart), "--namespace", "atlas", *(x for s in sets for x in ("--set", s))],
        capture_output=True,
        text=True,
        check=False,
    )
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
    """The umbrella under its CI test values (CHT-19; issuer + secrets render)."""
    return helm_render(UMBRELLA_CHART, value_files=(UMBRELLA_CHART / "tests/values.test.yaml",))
