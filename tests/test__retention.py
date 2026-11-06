"""Lifetimes contract suite (RET-01 to RET-07, 6.4d, ADR 025).

Every store the stacks keep on disk has a stated lifetime, written where a person
asking "why do you still have this?" reads it: the Data Archiving page. Each
lifetime the system enforces is configured once and stated the same in dev and
in the chart: the metrics' in Prometheus's flag, the logs' in Loki's compactor,
the traces' in Tempo's override, the alert history's in Grafana's env, the
identity events' in the production realm, the entity audits' in the server's
aging settings. A new volume without a row on the page fails the suite (R6).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import KC_CHART, OBS_CHART, WORKSPACE, container, env_map, env_value, find

LIFETIMES_PAGE = WORKSPACE / "docs/architecture/data-lifecycle-management/data-archiving.md"
OBSERVABILITY = WORKSPACE / "dev/observability"
THIRTY_DAYS_IN_SECONDS = 30 * 24 * 3600


def _compose(stack: Path) -> dict[str, Any]:
    return yaml.safe_load((stack / "docker-compose.yaml").read_text())


def _environment(service: dict[str, Any]) -> dict[str, str]:
    """A compose service's ``environment``, list or mapping."""
    environment = service.get("environment") or {}
    if isinstance(environment, list):
        return dict(item.split("=", 1) for item in environment)
    return {key: str(value) for key, value in environment.items()}


def _chart_values() -> dict[str, Any]:
    return yaml.safe_load((OBS_CHART / "values.yaml").read_text())


@pytest.mark.covers(rules=["RET-01"])
def test__every_dev_volume_has_a_stated_lifetime() -> None:
    """Each named volume of a dev stack is a row of the lifetimes page, as ``dev/<stack>:<volume>``."""
    page = LIFETIMES_PAGE.read_text()
    volumes = [
        f"{compose.parent.relative_to(WORKSPACE)}:{volume}"
        for compose in sorted(WORKSPACE.glob("dev/*/docker-compose.yaml"))
        for volume in (yaml.safe_load(compose.read_text()).get("volumes") or {})
    ]

    assert volumes, "no dev volumes found"
    assert [volume for volume in volumes if f"`{volume}`" not in page] == []


@pytest.mark.covers(rules=["RET-02"])
def test__metrics_are_kept_fifteen_days_in_dev_and_the_chart(obs_docs: list[dict[str, Any]]) -> None:
    """Prometheus's retention flag: stated in the compose, the chart's default, rendered into its args."""
    flag = "--storage.tsdb.retention.time=15d"
    rendered = container(find(obs_docs, "Deployment", "atlas-observability-prometheus"), "prometheus")

    assert flag in _compose(OBSERVABILITY)["services"]["prometheus"]["command"]
    assert _chart_values()["prometheus"]["retention"] == "15d"
    assert flag in rendered["args"]


@pytest.mark.covers(rules=["RET-03"])
def test__logs_are_deleted_after_thirty_days() -> None:
    """Loki's compactor enforces the retention, for every stream; the chart's copy is the same file (CHT-39)."""
    config = yaml.safe_load((OBSERVABILITY / "config/loki.yaml").read_text())

    assert config["compactor"]["retention_enabled"] is True
    assert config["compactor"]["delete_request_store"] == "filesystem"
    assert config["limits_config"]["retention_period"] == "720h"
    assert (OBS_CHART / "files/loki.yaml").read_bytes() == (OBSERVABILITY / "config/loki.yaml").read_bytes()


@pytest.mark.covers(rules=["RET-04"])
def test__traces_are_deleted_after_seven_days() -> None:
    """Tempo's default per-tenant override; the chart's copy is the same file (CHT-39)."""
    config = yaml.safe_load((OBSERVABILITY / "config/tempo.yaml").read_text())

    assert config["overrides"]["defaults"]["compaction"]["block_retention"] == "168h"
    assert (OBS_CHART / "files/tempo.yaml").read_bytes() == (OBSERVABILITY / "config/tempo.yaml").read_bytes()


@pytest.mark.covers(rules=["RET-05"])
def test__alert_history_is_deleted_after_thirty_days(obs_docs: list[dict[str, Any]]) -> None:
    """Grafana's alert state history: the same max age in the compose and the chart's rendered env."""
    variable = "GF_UNIFIED_ALERTING_STATE_HISTORY_ANNOTATIONS_MAX_AGE"
    compose = _environment(_compose(OBSERVABILITY)["services"]["grafana"])
    envs = env_map(container(find(obs_docs, "Deployment", "atlas-observability-grafana"), "grafana"))

    assert compose[variable] == "30d"
    assert _chart_values()["grafana"]["alerting"]["historyMaxAge"] == "30d"
    assert env_value(envs, variable) == "30d"


@pytest.mark.covers(rules=["RET-06"])
def test__the_production_realm_keeps_its_events_thirty_days() -> None:
    """Login events and admin events are recorded, and expire after 30 days."""
    realm = json.loads((KC_CHART / "files/aurelius-atlas.json").read_text())

    assert (realm["eventsEnabled"], realm["eventsExpiration"]) == (True, THIRTY_DAYS_IN_SECONDS)
    assert realm["adminEventsEnabled"] is True
    assert realm["attributes"]["adminEventsExpiration"] == str(THIRTY_DAYS_IN_SECONDS)


@pytest.mark.covers(rules=["RET-07"])
def test__the_chart_ages_entity_audits_out_daily(server_docs: list[dict[str, Any]]) -> None:
    """Atlas's aging on, at its 90-day default TTL, swept every day."""
    envs = env_map(container(find(server_docs, "Deployment", "atlas-server"), "server"))

    assert env_value(envs, "AURELIUS_ATLAS_SERVER_AUDIT_AGING_ENABLED") == "true"
    assert env_value(envs, "AURELIUS_ATLAS_SERVER_AUDIT_DEFAULT_AGEOUT_TTL_IN_DAYS") == "90"
    assert env_value(envs, "AURELIUS_ATLAS_SERVER_AUDIT_AGING_SCHEDULER_FREQUENCY_IN_DAYS") == "1"
