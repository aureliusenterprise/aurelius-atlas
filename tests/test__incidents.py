"""Incident contract suite (INC-01 to INC-04; 6.4f, ADR 041).

Every alert rule has its steps on the Incident Management page and links them; every incident and rehearsal
leaves a record in the shape the page names, listed where a responder finds it.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
import yaml
from conftest import WORKSPACE, find

RULES = WORKSPACE / "dev/observability/config/grafana/alerting/rules.yaml"
RESILIENCE = WORKSPACE / "docs/architecture/platform/resilience"
RUNBOOK = RESILIENCE / "incident-management.md"
INCIDENTS = RESILIENCE / "incidents"
STEPS = ("**Means.**", "**Check first.**", "**Mitigate.**", "**Escalate.**")
RECORD_SECTIONS = ("## Summary", "## Timeline", "## Actions", "## Cause", "## Follow-ups")


def _rules() -> list[dict[str, Any]]:
    return yaml.safe_load(RULES.read_text())["groups"][0]["rules"]


def _sections(page: str) -> dict[str, str]:
    """Each ``###`` section of the page by its anchor, ``{ #anchor }``, with its text up to the next heading."""
    found = re.split(r"^### .*\{ #([a-z0-9-]+) \}$", page, flags=re.MULTILINE)
    return {found[i]: re.split(r"^#{2,3} ", found[i + 1], flags=re.MULTILINE)[0] for i in range(1, len(found), 2)}


@pytest.mark.covers(rules=["INC-01"])
def test__every_alert_has_its_steps_on_the_runbook_page() -> None:
    """A section anchored by each rule's uid, with what it means, the first checks, the mitigation, the escalation."""
    sections = _sections(RUNBOOK.read_text())
    uids = [rule["uid"] for rule in _rules()]

    assert sorted(sections) == sorted(uids)
    assert {uid: [step for step in STEPS if step not in sections[uid]] for uid in uids} == {uid: [] for uid in uids}


@pytest.mark.covers(rules=["INC-02"])
def test__every_alert_links_its_section_on_the_published_docs() -> None:
    """``runbook_url`` is the published page, ``#`` the rule's uid."""
    site = re.search(r"^site_url: (\S+)$", (WORKSPACE / "mkdocs.yaml").read_text(), re.MULTILINE)[1]  # type: ignore[index]
    page = f"{site}/architecture/platform/resilience/incident-management/"

    assert {rule["uid"]: rule["annotations"]["runbook_url"] for rule in _rules()} == {
        rule["uid"]: f"{page}#{rule['uid']}" for rule in _rules()
    }


@pytest.mark.covers(rules=["INC-03"])
def test__every_record_has_the_five_sections_and_is_listed() -> None:
    """Named by date and slug, the sections in order, on the index and in the navigation."""
    records = sorted(path for path in INCIDENTS.glob("*.md") if path.name != "index.md")
    index = (INCIDENTS / "index.md").read_text()
    navigation = (WORKSPACE / "mkdocs.yaml").read_text()

    assert records, "no incident records"
    for record in records:
        text = record.read_text()
        positions = [text.find(section) for section in RECORD_SECTIONS]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md", record.name), record.name
        assert -1 not in positions, record.name
        assert positions == sorted(positions), record.name
        assert f"]({record.name})" in index, record.name
        assert f"architecture/platform/resilience/incidents/{record.name}" in navigation, record.name


@pytest.mark.covers(rules=["INC-04"])
def test__a_stopped_producer_s_series_drops_after_two_minutes(obs_docs: list[dict[str, Any]]) -> None:
    """The collector's Prometheus exporter, in dev and in the chart's rendered config."""
    dev = yaml.safe_load((WORKSPACE / "dev/observability/config/otel-collector.yaml").read_text())
    chart = yaml.safe_load(find(obs_docs, "ConfigMap", "atlas-observability")["data"]["config.yaml"])

    assert dev["exporters"]["prometheus"]["metric_expiration"] == "2m"
    assert chart["exporters"]["prometheus"]["metric_expiration"] == "2m"
