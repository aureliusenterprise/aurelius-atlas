"""E2E: the 7.25b governance rule page — the counts, the chart, and the two verdict boxes.

A rule of the governance kind opens the legacy's verdict page (DET-50): a
three-heading stats bar, a Compliance Chart, and one card box per verdict, fed
by the verdicts door (16.5i, VDR-14, ADR 071) over the verdicts the worker's
round wrote (ASG-06). The dataset the rule judges and the two rules ride a
run-scoped type: only that type's rules judge it, so the counts on the shared
dev store are this run's alone (the VCF-19 suite's isolation idiom). The
scenario waits on the verdicts door itself — the verdicts land through the
worker's round, not the seed's answer — and self-cleans, types last (DD-223).
"""

import json
import re
import secrets
import time
from collections.abc import Callable
from urllib.parse import urljoin

import pytest
from conftest import _goto_app
from playwright.sync_api import Page, expect
from test__aurelius_atlas_webapp import (
    _delete_entity,
    _purge_and_drop_types,
    _seed_entities,
    _seed_gov_rule,
    _wait_search_cards,
)


def _wait_rule_verdicts(
    page: Page, root_url: str, token: str, rule_guid: str, *, compliant: bool, timeout: float = 90
) -> None:
    """Ask the verdicts door until the rule's rows carry a verdict of ``compliant`` (bounded, ASG-06).

    The worker's round — not the seed's answer — writes the verdicts, so a
    page opened right after a seed can still read empty and the screen never
    re-reads (one door call per arrival, DD-850). The wait replays the door
    the screen itself rides until it holds this run's verdict, the
    propagation-retry idiom of ``_wait_search_cards`` on the verdict index.
    """
    deadline = time.monotonic() + timeout
    while True:
        answer = page.request.post(
            urljoin(root_url, "/api/aurelius/v1/rule/verdicts"),
            data=json.dumps({"rule": rule_guid}),
            headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
        ).json()
        found = [verdict for verdict in answer.get("verdicts", []) if verdict.get("compliant") is compliant]
        if found:
            return
        assert time.monotonic() < deadline, f"the verdicts door never answered compliant={compliant} for {rule_guid}"
        time.sleep(2)


def _rule_stat(page: Page, index: int) -> str:
    """The rule page's flat stats count by position (DET-50 pins the order)."""
    return page.locator(".aurelius-details-stats .level-item").nth(index).locator("p.title").inner_text().strip()


def _seed_run_type(page: Page, root_url: str, token: str, type_name: str) -> None:
    """Create the run's DataSet subtype through the typedefs door.

    The type rides ``DataSet`` like the VCF-19 suite's run types, so the seed
    needs only the two mandatory attributes — and only this type's rules judge
    its entities (ASG-02), which keeps the page's counts this run's alone.
    """
    seeded = page.request.post(
        urljoin(root_url, "/api/atlas/v2/types/typedefs"),
        data=json.dumps({"entityDefs": [{"name": type_name, "superTypes": ["DataSet"], "attributeDefs": []}]}),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert seeded.status == 200, seeded.text()


def _rule_chart(page: Page, score: str) -> None:
    """DET-54's chart box: its title, the legend's legacy order, and the pie at the score."""
    chart = page.locator(".aurelius-details-compliance-chart")
    expect(chart.locator("h2")).to_have_text("Compliance Chart")
    expect(chart.locator(".aurelius-details-legend-row")).to_have_text(["Non-compliant", "Compliant"])
    expect(chart.locator("aurelius-atlas-ui-data-quality-pie")).to_have_attribute("title", score)


def _seed_verdict_rules(page: Page, root_url: str, token: str, data_type: str, run: str) -> tuple[str, str, str, str]:
    """Seed the run's two ACTIVE readable rules over ``data_type`` (VEV-02, ASG-02).

    The name-present rule judges the run's dataset a pass (it carries a name);
    the description-filled one a refusal (the seed never sets a description).
    Returns the two GUIDs beside the two names the page shows.
    """
    names = {"named": f"zz{run}named", "described": f"zz{run}described"}

    def attributes(key: str, kind: str, attribute: str) -> dict[str, str]:
        return {
            "name": names[key],
            "qualifiedName": f"{data_type}--{names[key]}",
            "active": "true",
            "qualityDimension": "COMPLETENESS",
            "dqcheckkind": kind,
            "dqattribute": attribute,
            "ruleType": "COLUMN",
            "compliantMessage": f"zz{run} the {key} check passes",
            "nonCompliantMessage": f"zz{run} the {key} check fails",
        }

    pass_guid = _seed_gov_rule(page, root_url, token, attributes("named", "ATTRIBUTE_PRESENT", "name"))
    refuse_guid = _seed_gov_rule(page, root_url, token, attributes("described", "ATTRIBUTE_NOT_EMPTY", "description"))

    return pass_guid, refuse_guid, names["named"], names["described"]


# impact=major, likelihood=medium (a young page whose verdicts land through the worker's round)
@pytest.mark.medium
@pytest.mark.covers(rules=["DET-50", "DET-51", "DET-52", "DET-53", "DET-54", "VDR-15"])
def test__the_rule_page_draws_the_chart_and_the_two_verdict_boxes(
    authenticated: Page, root_url: str, fresh_user_token: Callable[[], str]
) -> None:
    """The verdict page of a judged rule: 1/0 counts, score 0, one card in the left box (DET-50..DET-54).

    The browser rides the served stack over the verdicts the worker's round
    wrote: a run-scoped dataset carries a name but no description, so it
    passes the name-present rule and refuses the description-filled one. The
    refused rule's page opens its legacy content — the three stats, the pie
    at score 0, the dataset's card alone in the Non-compliant box, an empty
    Compliant box, and the three-entry nav whose Compliant entry jumps to
    ``#related-compliants``. The passing rule's page turns the page around:
    ``0 / 1``, score 100, the card in the right box. The browser phase
    outlasts the dev realm's 60s token, so every call mints its own (the
    quality-rules suite's idiom). Self-cleaned, types last (ENS-09).
    """
    run = secrets.token_hex(4)
    data_type = f"m4i_{run}_rulepage"
    name = f"zz{run}rulepage"

    _seed_run_type(authenticated, root_url, fresh_user_token(), data_type)
    guids = _seed_entities(authenticated, root_url, fresh_user_token(), data_type, [name])
    guid = guids["-0"]
    pass_guid, refuse_guid, passed_rule, refused_rule = _seed_verdict_rules(
        authenticated, root_url, fresh_user_token(), data_type, run
    )

    try:
        # The card in the left box rides the search door (DET-53, VCF-05):
        # wait its beat, so DET-18 never drops a card still being indexed.
        _wait_search_cards(authenticated, root_url, fresh_user_token(), [guid])
        # The verdicts themselves land through the worker's round (ASG-06):
        # wait the door the screen rides, for each rule's own verdict.
        _wait_rule_verdicts(authenticated, root_url, fresh_user_token(), refuse_guid, compliant=False)
        _wait_rule_verdicts(authenticated, root_url, fresh_user_token(), pass_guid, compliant=True)

        # The refused rule's page (DET-50): the layout dispatch's direct hit,
        # the rule's own name in the title.
        _goto_app(authenticated, urljoin(root_url, f"/en-US/search/details/{refuse_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(refused_rule)

        # DET-52: the three stats in the legacy order — one refusal, no pass,
        # and the Properties stat counting the rendered property rows as every
        # other layout does (DET-24): the number itself is not this page's rule.
        assert _rule_stat(authenticated, 0) == "1"
        assert _rule_stat(authenticated, 1) == "0"
        assert _rule_stat(authenticated, 2).isdigit()

        # DET-54: the chart box between the stats and the boxes — the pie at score 0.
        _rule_chart(authenticated, "0%")

        # DET-53: the Non-compliant box holds the dataset's card, the
        # Compliant box stays empty — both over the shared chrome's count line.
        non_compliants = authenticated.locator("#related-non-compliants")
        expect(non_compliants.locator("h2")).to_have_text("Non-compliant")
        expect(non_compliants.locator("h6.aurelius-card-section-count")).to_have_text("1 result(s)")
        expect(non_compliants.locator(".title.is-4 a")).to_have_text([name])
        compliants = authenticated.locator("#related-compliants")
        expect(compliants.locator("h2")).to_have_text("Compliant")
        expect(compliants.locator("h6.aurelius-card-section-count")).to_have_text("0 result(s)")
        expect(compliants.locator("aurelius-atlas-ui-entity-card")).to_have_count(0)

        # DET-50: the nav carries the three entries in the legacy order, and
        # DET-25's scroll holds: the Compliant entry names the box in the
        # address and the screen stays on the rule.
        nav = authenticated.locator(".aurelius-details-nav")
        expect(nav.locator(".menu-list a")).to_have_text(["Non-compliant", "Compliant", "Properties"])
        nav.locator("button").click()
        nav.get_by_role("link", name="Compliant", exact=True).click()
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{refuse_guid}#related-compliants$"))
        expect(compliants).to_be_visible()

        # The passing rule's page turns the page around (DET-51, DET-52):
        # 0 / 1 and a full pie, the card in the right box.
        _goto_app(authenticated, urljoin(root_url, f"/en-US/search/details/{pass_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(passed_rule)
        assert _rule_stat(authenticated, 0) == "0"
        assert _rule_stat(authenticated, 1) == "1"
        _rule_chart(authenticated, "100%")
        expect(authenticated.locator("#related-non-compliants")).to_contain_text("0 result(s)")
        expect(authenticated.locator("#related-compliants").locator(".title.is-4 a")).to_have_text([name])
    finally:
        _delete_entity(authenticated, root_url, fresh_user_token(), guid)
        _delete_entity(authenticated, root_url, fresh_user_token(), pass_guid)
        _delete_entity(authenticated, root_url, fresh_user_token(), refuse_guid)
        # The run type goes last: ENS-09 keeps it while an entity of it exists
        # in any state, so the purge inside precedes the typedef delete.
        _purge_and_drop_types(authenticated, root_url, fresh_user_token(), [data_type], [data_type])
