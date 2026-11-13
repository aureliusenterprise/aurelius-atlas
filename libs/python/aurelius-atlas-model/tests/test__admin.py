"""The administrative answers' JSON (ADM-01, ADM-02, ADM-05), read from ``AdminResource``.

The version and status maps are written inline in Apache Atlas 2.4.0; the session object is built field by
field there, so its keys keep their Java names — the dotted settings names included — in the order written.
"""

import pytest
from aurelius_atlas_model.admin import AtlasServiceStatus, AtlasSessionProfile, AtlasVersionInfo

SESSION_KEYS = [
    "atlas.rest-csrf.enabled",
    "atlas.rest-csrf.browser-useragents-regex",
    "atlas.rest-csrf.methods-to-ignore",
    "atlas.rest-csrf.custom-header",
    "atlas.ui.editable.entity.types",
    "atlas.ui.default.version",
    "atlas.ui.date.timezone.format.enabled",
    "atlas.ui.date.format",
    "atlas.debug.metrics.enabled",
    "atlas.tasks.enabled",
    "atlas.tasks.ui.tab.enabled",
    "atlas.lineage.on.demand.enabled",
    "atlas.lineage.on.demand.default.node.count",
    "atlas.relationship.search.enabled",
    "atlas.entity.update.allowed",
    "atlas.entity.create.allowed",
    "userName",
    "groups",
    "timezones",
    "_csrfToken",
]
"""The keys of ``admin/session`` in the order ``AdminResource`` writes them (ADM-05)."""


@pytest.mark.covers(rules=["ADM-01"])
def test__the_version_writes_the_four_capitalized_names() -> None:
    """``AtlasVersion.asMap()``: ``Version``, ``Revision``, ``Name`` and ``Description`` (DV-03)."""
    info = AtlasVersionInfo.model_validate(
        {"version": "7.30.0", "revision": "abc123", "name": "aurelius-atlas", "description": "on Elasticsearch"}
    )

    assert info.to_json() == {
        "Version": "7.30.0",
        "Revision": "abc123",
        "Name": "aurelius-atlas",
        "Description": "on Elasticsearch",
    }


@pytest.mark.covers(rules=["ADM-02"])
def test__the_status_defaults_to_active() -> None:
    """The only service state needs no argument: ``{"Status": "ACTIVE"}``."""
    assert AtlasServiceStatus().to_json() == {"Status": "ACTIVE"}


@pytest.mark.covers(rules=["ADM-05"])
def test__the_session_writes_every_setting_at_its_atlas_default() -> None:
    """Every key in Java's order, the settings under their ``atlas.`` names, the CSRF and time zones empty."""
    session = AtlasSessionProfile()

    assert list(session.to_json()) == SESSION_KEYS
    assert session.to_json()["atlas.rest-csrf.methods-to-ignore"] == "GET,OPTIONS,HEAD,TRACE"
    assert session.to_json()["atlas.lineage.on.demand.default.node.count"] == 3
    assert session.to_json()["atlas.entity.update.allowed"] is False


@pytest.mark.covers(rules=["ADM-05"])
def test__the_session_keeps_a_null_user_name_on_the_wire() -> None:
    """Unlike the other models no key drops out: a request without a user answers ``userName`` null."""
    session = AtlasSessionProfile()

    assert session.to_json()["userName"] is None
    session.user_name = "admin"
    session.groups = ["ADMIN"]
    assert session.to_json()["userName"] == "admin"
    assert session.to_json()["groups"] == ["ADMIN"]
