"""E2E: the 7.27 rules editor — the create/edit circle of a vocabulary rule.

The field page's rules box gains a `+` (DET-37); it opens the editor drawer
with the rule type fixed and the field already picked (EDT-25, EDT-30). The
drawer builds the form from the server's vocabulary: the kind Select, the
kind's own parameters, `active`, and `threshold` (EDT-26, EDT-27). Its Save
checks the draft with 12.5's validate endpoint before the POST (EDT-28). The
scenarios ride the served stack: browser -> nginx -> server, seeded fields
from the shared m4i mini-graph, self-cleaned by the shared m4i purge (DD-223).
"""

import json
import re
import secrets
from collections.abc import Callable
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Page, expect
from test__aurelius_atlas_webapp import (
    _active_edge,
    _open_editor_from_details,
    _purge_type,
    _seed_m4i_mini_graph,
    _wait_entity_read,
)

# The shared dev store is never cleaned between runs, so the m4i purge list
# the DET tests share applies here too, with the rules type 7.24 added.
_M4I_PURGE = [
    "m4i_data_quality",
    "m4i_data_entity",
    "m4i_data_attribute",
    "m4i_data_domain",
    "m4i_field",
    "m4i_system",
    "m4i_generic_process",
    "m4i_dataset",
    "m4i_person",
]

# 12.5's validate route, watched to prove the save checked before it wrote.
_VALIDATE_URL = "/api/aurelius/v1/quality/rules/validate"


@pytest.mark.covers(rules=["EDT-25", "EDT-26", "EDT-28", "EDT-30", "DET-37"])
def test__the_field_rules_box_creates_a_rule(
    authenticated: Page, root_url: str, fresh_user_token: Callable[[], str]
) -> None:
    """The `+` opens the kind form and its Save checks first, then lands (DET-37, EDT-25/26/28/30).

    Open the seeded field and click the rules box's `+` (atlas-write
    granted): the drawer opens at create with the rule type fixed — DD-330's
    route, no type picker round — and the field already carried into the
    `fields` picker as a chip (EDT-13's pick shape, DET-37's seed). The form
    is built from the server's vocabulary (EDT-30): choose kind
    ``COLUMN_NOT_NULL_RATIO``, name the rule, type its one parameter
    (EDT-26). Save asks validate first — the watched answer names the kind —
    and only then the POST lands on the new rule's details (EDT-28). The
    rule stands as one card in the field's box (DET-35's read), so the box's
    own `+` delivered a rule the box can show.
    """
    run = secrets.token_hex(4)
    rule_name = f"zz{run}rule"
    guids = _seed_m4i_mini_graph(authenticated, root_url, fresh_user_token(), run)
    field_guid = guids["field"]

    try:
        # DET-37: the field page's rules box carries the create `+`.
        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{field_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}field")
        plus = authenticated.locator("#related-rules button.aurelius-details-create-rule")
        expect(plus).to_be_visible()
        expect(plus).to_have_attribute("aria-label", "Create new entity")

        # DET-37: the `+` opens the drawer at create with the type fixed.
        plus.click()
        drawer = authenticated.locator(".aurelius-drawer")
        expect(drawer).to_be_visible()
        expect(authenticated).to_have_url(re.compile(r"\(drawer:create/m4i_data_quality"))

        # EDT-30/EDT-25: the vocabulary form arrives from the server's
        # kinds, and DET-37's pick seeded the fields picker with this
        # field's chip (EDT-13's shape, named by the query's label).
        kind_select = authenticated.locator(".aurelius-quality-kind select")
        expect(kind_select).to_be_visible()
        fields_box = authenticated.locator(".aurelius-editor-relationship[data-field='fields']")
        expect(fields_box.locator(".aurelius-relationship-chip")).to_contain_text(f"zz{run}field")

        # EDT-26: the chosen kind's own parameter joins the form, with the
        # kind's dimension beside it as read-only text (EDT-25).
        kind_select.select_option(label="COLUMN_NOT_NULL_RATIO")
        expect(authenticated.locator(".aurelius-quality-dimension-value")).to_have_text("COMPLETENESS")
        authenticated.locator("#editor-name").fill(rule_name)
        authenticated.locator("#editor-dqcolumn").fill("total")

        # EDT-28: Save checks the draft with validate first — the watched
        # answer names the chosen kind — and only then the POST lands. The
        # validate response arrives before the POST round trip finishes, so
        # the wait holds until the landing URL names the new rule.
        with authenticated.expect_response(lambda r: _VALIDATE_URL in r.url) as checked:
            drawer.locator("button.aurelius-editor-save").click()
        assert checked.value.json() == {"valid": True, "kind": "COLUMN_NOT_NULL_RATIO", "dimension": "COMPLETENESS"}
        expect(authenticated).to_have_url(re.compile(r"/en-US/search/details/[0-9a-f-]+$"))
        expect(authenticated.locator(".aurelius-drawer")).to_have_count(0)
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(rule_name)
        landing = re.search(r"/details/([^/?#]+)", authenticated.url)
        assert landing is not None
        rule_guid = landing.group(1)

        # DET-35's read: one card in the field's box (the edge is a
        # near-real-time record — wait the field's read first, CLS-12).
        user_token = fresh_user_token()
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            field_guid,
            predicate=lambda entity: _active_edge(entity, "dataQuality", rule_guid),
        )
        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{field_guid}"))
        section = authenticated.locator("#related-rules")
        expect(section.locator(".aurelius-card-section-count")).to_contain_text("1 result(s)")
        expect(section).to_contain_text(rule_name)
    finally:
        for type_name in _M4I_PURGE:
            _purge_type(authenticated, root_url, fresh_user_token(), type_name)


@pytest.mark.covers(rules=["EDT-27", "EDT-28", "EDT-29"])
def test__the_editor_edits_a_stored_rule(
    authenticated: Page, root_url: str, fresh_user_token: Callable[[], str]
) -> None:
    """The pencil reopens a stored rule and its Save keeps exactly the form (EDT-27/28/29).

    The edit half of the circle on a vocabulary rule seeded through the API
    (DET-35's shape, the engine's own read of it): the pencil reopens the
    quality form seeded from the entity — the name, the kind's dimension as
    read-only text, its parameter, `active` checked, and the engine's
    default threshold at the stored 1.0 (EDT-29, EDT-27). The column
    parameter is retyped and the threshold set to 0.5 with `active`
    cleared; the watched validate answer proves the checked-before-write
    rule held again (EDT-28), and the store answers exactly what the form
    said — what saves is what the engine reads.
    """
    run = secrets.token_hex(4)
    rule_name = f"zz{run}rule"
    guids = _seed_m4i_mini_graph(authenticated, root_url, fresh_user_token(), run)
    field_guid = guids["field"]
    user_token = fresh_user_token()

    rule = authenticated.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps(
            {
                "entities": [
                    {
                        "typeName": "m4i_data_quality",
                        "guid": "-0",
                        "attributes": {
                            "qualifiedName": rule_name,
                            "name": rule_name,
                            # `id` is a mandatory INT attribute of the rule type.
                            "id": int(run[:6], 16),
                            "dqcheckkind": "COLUMN_NOT_NULL_RATIO",
                            "dqcolumn": "total",
                            # EWR-09 materializes an absent double/boolean to
                            # 0.0/false, so a rule at the engine's defaults
                            # stores them: threshold 1.0, active.
                            "threshold": 1.0,
                            "active": True,
                        },
                        "relationshipAttributes": {"fields": [{"guid": field_guid, "typeName": "m4i_field"}]},
                    }
                ]
            }
        ),
        headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
    )
    assert rule.status == 200, rule.text()
    rule_guid = rule.json()["guidAssignments"]["-0"]

    try:
        user_token = fresh_user_token()

        # The drawer reads once (CLS-12's race): wait the rule's read
        # carries its `fields` edge before opening the pencil.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            rule_guid,
            predicate=lambda entity: _active_edge(entity, "fields", field_guid),
        )
        _open_editor_from_details(authenticated, root_url, rule_guid)

        # EDT-29: the quality form opens seeded from the stored rule — the
        # kind's dimension and its parameter line up, active is checked, and
        # the absent threshold shows the engine's default (1.0, EDT-27).
        expect(authenticated.locator("#editor-name")).to_have_value(rule_name)
        expect(authenticated.locator(".aurelius-quality-dimension-value")).to_have_text("COMPLETENESS")
        expect(authenticated.locator("#editor-dqcolumn")).to_have_value("total")
        expect(authenticated.locator("#editor-threshold")).to_have_value(re.compile(r"^1(\.0)?$"))
        active = authenticated.locator(".aurelius-quality-active input")
        expect(active).to_be_checked()

        # EDT-27's round-trip: threshold 0.5, deactivated, the parameter
        # retyped — validate first again (EDT-28), then the store keeps
        # exactly what the form said.
        authenticated.locator("#editor-dqcolumn").fill("quantity")
        authenticated.locator("#editor-threshold").fill("0.5")
        active.uncheck()
        drawer = authenticated.locator(".aurelius-drawer")
        with authenticated.expect_response(lambda r: _VALIDATE_URL in r.url) as checked:
            drawer.locator("button.aurelius-editor-save").click()
        assert checked.value.json()["valid"] is True
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{rule_guid}$"))
        expect(authenticated.locator(".aurelius-drawer")).to_have_count(0)

        stored = authenticated.request.get(
            urljoin(root_url, f"/api/atlas/v2/entity/guid/{rule_guid}"),
            headers={"authorization": f"Bearer {fresh_user_token()}"},
        )
        assert stored.status == 200, stored.text()
        attributes = stored.json()["entity"]["attributes"]
        assert attributes["name"] == rule_name
        assert attributes["dqcheckkind"] == "COLUMN_NOT_NULL_RATIO"
        assert attributes["dqcolumn"] == "quantity"
        assert attributes["threshold"] == 0.5
        assert attributes["active"] is False
    finally:
        for type_name in _M4I_PURGE:
            _purge_type(authenticated, root_url, fresh_user_token(), type_name)
