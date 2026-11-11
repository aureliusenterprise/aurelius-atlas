"""E2E: the 7.27 rules editor — the create/edit circle of a vocabulary rule.

A rule is an entity like any other (DD-483): the generic create door opens
the drawer, ``Data Quality`` rides its type picker, and the pencil on the
rule's page edits it. The drawer builds the form from the server's
vocabulary, named in human words (EDT-31) with the threshold as a slider
beside the number (EDT-32); its Save checks the draft with 12.5's validate
endpoint before the POST (EDT-28). The rule's own page lists the fields it
applies to (DET-38) and the field's rules box shows the rule (DET-35). The
scenarios ride the served stack: browser -> nginx -> server, seeded fields
from the shared m4i mini-graph, self-cleaned by the shared m4i purge (DD-223).
"""

import json
import re
import secrets
from collections.abc import Callable
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Locator, Page, expect
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


def _open_quality_create(authenticated: Page, root_url: str) -> Locator:
    """Open the generic create door and pick Data Quality (DD-483).

    The hero `+`, the type from the picker, DD-330's create route — returns
    the drawer.
    """
    authenticated.goto(urljoin(root_url, "/en-US/search/browse"))
    authenticated.locator("button.aurelius-create-entity").click()
    drawer = authenticated.locator(".aurelius-drawer")
    expect(drawer).to_contain_text("Create new entity")
    authenticated.locator(".aurelius-editor-picker select").select_option(label="Data Quality")
    expect(authenticated).to_have_url(re.compile(r"\(drawer:create/m4i_data_quality\)$"))

    return drawer


def _pick_field(authenticated: Page, field_name: str) -> None:
    """Take the named field in the rule's `fields` picker (EDT-13's pick).

    The picker's prefix search finds the row and the click attaches the
    chip — the picker's own e2e idiom.
    """
    block = authenticated.locator(".aurelius-editor-relationship[data-field='fields']")
    block.locator(".aurelius-relationship-input").fill(field_name)
    row = block.locator('[role="option"]').filter(has_text=field_name)
    expect(row).to_be_visible(timeout=10_000)
    row.click()
    expect(block.locator(".aurelius-relationship-chip")).to_have_count(1)


def _drive_threshold_pair(authenticated: Page, rest: str) -> None:
    """Drive the EDT-32 threshold pair from its resting value `rest`.

    The box names the current percent; typing moves the slider; a percent
    outside the served bounds stores the nearer bound, shown once the field
    is left (the pair's shared clamp); dragging the slider fills the box with
    the same threshold as a percent. Ends at 0.75.
    """
    expect(authenticated.locator("#editor-threshold")).to_have_value(rest)
    authenticated.locator("#editor-threshold").fill("90")
    expect(authenticated.locator("#editor-threshold-slider")).to_have_value("0.9")
    authenticated.locator("#editor-threshold").fill("150")
    authenticated.locator("#editor-threshold").blur()
    expect(authenticated.locator("#editor-threshold")).to_have_value("100")
    authenticated.locator("#editor-threshold").fill("-5")
    authenticated.locator("#editor-threshold").blur()
    expect(authenticated.locator("#editor-threshold")).to_have_value("0")
    authenticated.locator("#editor-threshold").fill("90")
    authenticated.locator("#editor-threshold-slider").fill("0.75")
    expect(authenticated.locator("#editor-threshold")).to_have_value("75")


@pytest.mark.covers(rules=["EDT-25", "EDT-26", "EDT-28", "EDT-30", "EDT-31", "EDT-32", "DET-35", "DET-38"])
def test__the_generic_door_creates_a_rule(
    authenticated: Page, root_url: str, fresh_user_token: Callable[[], str]
) -> None:
    """Data Quality rides the generic door and its Save checks first, then lands (EDT-25/26/28/30/31/32).

    A rule enters like every other entity (DD-483): the hero `+`, ``Data
    Quality`` from the type picker, DD-330's route — and the field's rules
    box carries no door of its own. The form is built from the server's
    vocabulary (EDT-30) and speaks in human words (EDT-31): the kind row
    reads "Not empty", and picking it reveals the kind's description above
    the localized dimension. The threshold pair (EDT-32): typing the number
    moves the slider, dragging the slider fills the number. The `fields`
    picker takes the seeded field by hand (EDT-13). Save asks validate first
    — the watched answer names the kind — and only then the POST lands on
    the new rule's page, which lists the field it applies to (DET-38), while
    the field's own box shows the rule (DET-35).
    """
    run = secrets.token_hex(4)
    rule_name = f"zz{run}rule"
    guids = _seed_m4i_mini_graph(authenticated, root_url, fresh_user_token(), run)
    field_guid = guids["field"]

    try:
        # DD-483: the field page's rules box carries no create button at all
        # — the generic door below is the door.
        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{field_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}field")
        expect(authenticated.locator("button.aurelius-details-create-rule")).to_have_count(0)

        # EDT-25/DD-483: the generic create door with Data Quality chosen.
        drawer = _open_quality_create(authenticated, root_url)

        # EDT-30/EDT-25/EDT-31: the vocabulary form arrives from the
        # server's kinds, each labelled by its human name — the raw engine
        # name is never offered. Pick the kind by its human name.
        kind_select = authenticated.locator(".aurelius-quality-kind select")
        expect(kind_select).to_be_visible()
        expect(kind_select.locator('option:has-text("COLUMN_NOT_NULL_RATIO")')).to_have_count(0)
        kind_select.select_option(label="Not empty")

        # EDT-31: the kind's description appears above the localized
        # dimension, both read-only.
        expect(authenticated.locator(".aurelius-quality-kind-description")).to_have_text(
            "One column carries a value in at least part of the rows."
        )
        expect(authenticated.locator(".aurelius-quality-dimension-value")).to_have_text("Completeness")

        # EDT-26: the chosen kind's own parameter joins the form.
        authenticated.locator("#editor-name").fill(rule_name)
        authenticated.locator("#editor-dqcolumn").fill("total")

        # EDT-32: the threshold pair, one value — driven from the default 100
        # (typing, clamping, dragging) and left at 0.75.
        _drive_threshold_pair(authenticated, "100")

        # EDT-13: the `fields` picker takes the seeded field by hand.
        _pick_field(authenticated, f"zz{run}field")

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

        # The pair's 0.75 is what the engine reads (EDT-32).
        stored = authenticated.request.get(
            urljoin(root_url, f"/api/atlas/v2/entity/guid/{rule_guid}"),
            headers={"authorization": f"Bearer {fresh_user_token()}"},
        )
        assert stored.status == 200, stored.text()
        assert stored.json()["entity"]["attributes"]["threshold"] == 0.75

        # DET-38: the rule's own page lists the field it applies to — the
        # Fields box seeds from the `fields` end the picker wrote (the edge
        # is a near-real-time record, wait its read first, CLS-12).
        _wait_entity_read(
            authenticated,
            root_url,
            fresh_user_token(),
            rule_guid,
            predicate=lambda entity: _active_edge(entity, "fields", field_guid),
        )
        authenticated.reload()
        rule_page = authenticated.locator("#related-fields")
        expect(rule_page.locator(".aurelius-card-section-count")).to_contain_text("1 result(s)")
        expect(rule_page).to_contain_text(f"zz{run}field")

        # DET-35's read from the other end: one card in the field's box.
        _wait_entity_read(
            authenticated,
            root_url,
            fresh_user_token(),
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
    (DET-35's shape, the engine's own read of it): the generic pencil on the
    rule's page reopens the quality form seeded from the entity — the name,
    the localized dimension (EDT-31), its parameter, `active` checked, and
    the threshold pair resting at the stored 1.0 (EDT-29, EDT-27, EDT-32).
    The column parameter is retyped, the slider dragged to 0.5, and `active`
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
        # kind's localized dimension and its parameter line up, active is
        # checked, and the stored 1.0 rests both halves of the pair
        # (EDT-27, EDT-31, EDT-32).
        expect(authenticated.locator("#editor-name")).to_have_value(rule_name)
        expect(authenticated.locator(".aurelius-quality-dimension-value")).to_have_text("Completeness")
        expect(authenticated.locator("#editor-dqcolumn")).to_have_value("total")
        expect(authenticated.locator("#editor-threshold")).to_have_value("100")
        expect(authenticated.locator("#editor-threshold-slider")).to_have_value("1")
        active = authenticated.locator(".aurelius-quality-active input")
        expect(active).to_be_checked()

        # EDT-27's round-trip: the slider to 0.5, deactivated, the parameter
        # retyped — validate first again (EDT-28), then the store keeps
        # exactly what the form said.
        authenticated.locator("#editor-dqcolumn").fill("quantity")
        authenticated.locator("#editor-threshold-slider").fill("0.5")
        expect(authenticated.locator("#editor-threshold")).to_have_value("50")
        # EDT-32's clamp again on the edit side: an over-bound percent rests
        # at the bound, then the slider brings the pair back to 0.5.
        authenticated.locator("#editor-threshold").fill("900")
        authenticated.locator("#editor-threshold").blur()
        expect(authenticated.locator("#editor-threshold")).to_have_value("100")
        authenticated.locator("#editor-threshold-slider").fill("0.5")
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
