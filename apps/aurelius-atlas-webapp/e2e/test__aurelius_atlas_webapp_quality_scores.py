"""E2E: the 7.25c/7.25d data-quality scores — the box, the stat, the sort, the card.

The score source is the scanner's: 12.2 writes one ``m4i_dq_score`` per rule and
dataset, and 14.5's worker round rolls those scores up to the fields, their data
attributes, and every entity of their breadcrumb (ASQ-04, ASQ-05), which 16.1
carries on the view and on every card of the view family (AVS-01). This
scenario seeds the source by hand — the sample catalogue carries no scores, so
the roll-up is the thing under test, not the scanner — and rides the served
stack: browser -> nginx -> server. It opens a scored dataset, reads the score
box's rows and the stats bar's percent (DET-56, DET-58), sorts the Fields box by
Completeness (DET-59), and reads the score block on a card of that box
(DET-60) and, since 7.25d, on the results row too (DET-61 as amended); every
score surface prints only the dimensions that have rules, never a 0-count row
(DET-64). A second, un-scored dataset answers the placeholder and the word
(DET-56, DET-58, DET-63). The totals land through the worker's round, so the
wait is on the door's card, not the seed's answer (the ASG-06 idiom);
self-cleaned by the shared m4i purge, scores first (DD-223).
"""

import json
import re
import secrets
import time
from collections.abc import Callable
from urllib.parse import quote, urljoin

import pytest
from playwright.sync_api import Locator, Page, expect
from test__aurelius_atlas_webapp import (
    _active_edge,
    _purge_type,
    _seed_entities,
    _seed_m4i_mini_graph,
    _wait_entity_read,
    _wait_search_cards,
)

# The shared dev store is never cleaned between runs, so the m4i purge list the
# DET tests share applies here too, with the scores' own type.
_M4I_PURGE = [
    "m4i_dq_score",
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

SCORE_TYPE = "m4i_dq_score"
"""The scanner's score entities (12.2, DQS-06) — what the roll-up reads."""


def _seed_field_on_dataset(page: Page, root_url: str, token: str, run: str, dataset_guid: str, key: str) -> str:
    """Seed a second field onto the dataset's Fields end (the DET-59 sort's rival).

    The edge is the dataset's own ``fields`` relationship seeded from the field
    side (the shared-record posture of REL-11): the dataset's read and the
    App Search document list the field either way. The field's end is
    ``datasets`` at SINGLE cardinality (``m4i_field_assignment``), so the
    reference is one object, not a list — like the mini-graph's ``system`` end.
    """
    name = f"zz{run}{key}"
    response = page.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps(
            {
                "entities": [
                    {
                        "typeName": "m4i_field",
                        "guid": "-0",
                        "attributes": {"qualifiedName": name, "name": name},
                        "relationshipAttributes": {"datasets": {"guid": dataset_guid, "typeName": "m4i_dataset"}},
                    }
                ]
            }
        ),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert response.status == 200, response.text()

    return response.json()["guidAssignments"]["-0"]


def _seed_score_rule(page: Page, root_url: str, token: str, run: str, key: str, field_guid: str) -> str:
    """Seed one ACTIVE completeness rule over ``field_guid``.

    The score roll-up reads the dimension off the rule (ASQ-04), so every rule
    here stamps ``COMPLETENESS`` and the scores differ only by their value. It
    also requires the rule's ``active`` flag set: the attribute defaults to
    ``false`` when a seed omits it, and ``_active_rule`` skips a rule that is
    not active (DD-532) — unlike the DET-35 rules-box seed, which only shows
    the rule and never rolls a score up.
    """
    name = f"zz{run}{key}"
    response = page.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps(
            {
                "entities": [
                    {
                        "typeName": "m4i_data_quality",
                        "guid": "-0",
                        "attributes": {
                            "qualifiedName": name,
                            "name": name,
                            "id": int(run[:6], 16),
                            "active": True,
                            "qualityDimension": "COMPLETENESS",
                            "ruleDescription": f"zz{run} the {key} field carries a value.",
                        },
                        "relationshipAttributes": {"fields": [{"guid": field_guid, "typeName": "m4i_field"}]},
                    }
                ]
            }
        ),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert response.status == 200, response.text()

    return response.json()["guidAssignments"]["-0"]


def _seed_score(page: Page, root_url: str, token: str, dataset_guid: str, rule_guid: str, score: float) -> str:
    """Store one PASS score as the scanner's write stores it (12.2, DQS-06, DQS-07).

    The key is ``{dataset}/{rule}`` and the qualified name hangs under
    ``dq-score/``, exactly as ``records.score_entity`` builds it; only the
    scanner's extract (the rows behind the value) is replaced by the number.
    """
    key = f"{dataset_guid}/{rule_guid}"
    response = page.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps(
            {
                "entities": [
                    {
                        "typeName": SCORE_TYPE,
                        "guid": "-0",
                        "attributes": {
                            "qualifiedName": f"dq-score/{key}",
                            "scoreKey": key,
                            "datasetGuid": dataset_guid,
                            "ruleGuid": rule_guid,
                            "verdict": "PASS",
                            "score": score,
                        },
                    }
                ]
            }
        ),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert response.status == 200, response.text()

    return response.json()["guidAssignments"]["-0"]


def _wait_card_quality(
    page: Page,
    root_url: str,
    mint: Callable[[], str],
    guid: str,
    *,
    overall_count: float,
    score: float,
    timeout: float = 120,
) -> None:
    """Ask the search door until ``guid``'s card carries the overall roll-up (bounded, AVS-01).

    The totals land through the worker's quality round — not the score's seed
    answer (ASQ-07) — so every score assertion waits the door first, the ASG-06
    verdict-wait idiom on the score totals. The wait can outlive the dev
    realm's 60s token, so it mints through ``fresh_user_token`` per attempt.
    """
    deadline = time.monotonic() + timeout
    while True:
        answer = page.request.post(
            urljoin(root_url, "/api/aurelius/v1/search"),
            data=json.dumps({"filters": {"guid": [guid]}, "limit": 1}),
            headers={"content-type": "application/json", "authorization": f"Bearer {mint()}"},
        ).json()
        rows = {row["dimension"]: row for card in answer.get("cards", []) for row in card.get("quality", [])}
        overall = rows.get("overall", {})
        if overall.get("count") == overall_count and overall.get("score") == pytest.approx(score, abs=0.001):
            return
        assert time.monotonic() < deadline, f"the door never rolled the totals up on {guid}: held {overall}"
        time.sleep(2)


def _dimension_texts(scope: Locator) -> list[str]:
    r"""The scope's UIC-37 row texts with every run of whitespace collapsed.

    UIC-37 joins the percent, the dimension word and the count with
    ``&nbsp;`` — Playwright keeps those as-is, so the rows are compared with
    ``\s+`` collapsed, the DET-44 chrome suite's idiom.
    """
    return [re.sub(r"\s+", " ", text).strip() for text in scope.locator(".quality-dimension").all_inner_texts()]


def _seed_score_source(
    page: Page, root_url: str, token: str, run: str, dataset_guid: str, field_guid: str
) -> tuple[str, list[tuple[str, str]]]:
    """Store the roll-up's source over the mini-graph's dataset (12.2's write shape).

    A second field joins the dataset, a completeness rule hangs off each field
    (ASQ-04 reads the dimension off the rule), and the scanner's PASS scores
    say 0.5 and 0.9 — the rival pair DET-59 sorts on. Returns the new field's
    guid beside the (field, rule) pairs the waits ride.
    """
    field2_guid = _seed_field_on_dataset(page, root_url, token, run, dataset_guid, "field2")
    pairs: list[tuple[str, str]] = []
    for key, scored_guid, score in [("rule1", field_guid, 0.5), ("rule2", field2_guid, 0.9)]:
        rule_guid = _seed_score_rule(page, root_url, token, run, key, scored_guid)
        _seed_score(page, root_url, token, dataset_guid, rule_guid, score)
        pairs.append((scored_guid, rule_guid))
    return field2_guid, pairs


def _score_box_and_stat(page: Page, *, scored: bool, run: str) -> None:
    """The box's rows (or rest) and the stats bar's value (or word), with the nav entry (DET-56, DET-58).

    On the scored dataset: only the dimension that has rules (DET-64 leaves
    the four 0-count dimensions off the box), UIC-37's pie, the
    stats bar's overall percent after the consumers, and the side
    navigation's entry beside the governance box's. On the twin: the
    placeholder, no rows, and the word.
    """
    box = page.locator("#data-quality")
    expect(box).to_be_visible()
    expect(box.locator("h2")).to_have_text("Data Quality")
    if scored:
        assert _dimension_texts(box) == ["70% Completeness (2)"]
        expect(box.locator("aurelius-atlas-ui-data-quality-pie")).to_have_count(1)
        value = "70%"
    else:
        expect(box.locator("p.aurelius-quality-not-available")).to_have_text("No data quality results available")
        expect(box.locator(".quality-dimension")).to_have_count(0)
        value = "Unavailable"
    stat = page.locator(".aurelius-details-stats .level-item", has=page.locator('p.heading a[href="#data-quality"]'))
    expect(stat.locator("p.title")).to_have_text(value)
    nav_labels = [text.strip() for text in page.locator(".aurelius-details-nav .menu-list a").all_inner_texts()]
    assert "Data Quality" in nav_labels, f"the nav lost the score entry for zz{run}"
    assert nav_labels.index("Data Quality") == nav_labels.index("Governance Quality Rules") - 1


def _drives_the_score_sort(page: Page, run: str) -> None:
    """The Fields box's dimension sorts and the card's score block (DET-59, DET-60).

    The options carry the five dimensions after the pair; Completeness
    orders the cards by their own score row, ascending low-first (DET-21's
    comparator), and the direction button reverses it; the first card
    prints its own fixed-order block. The titles are read exactly — the
    0.5 field's name is the 0.9 one's prefix, so containment could not
    tell them apart.
    """
    fields_box = page.locator("#related-fields")
    expect(fields_box).to_be_visible()
    options = [text.strip() for text in fields_box.locator("select option").all_inner_texts()]
    assert options == ["Relevance", "Name", "Accuracy", "Completeness", "Timeliness", "Uniqueness", "Validity"]
    titles = fields_box.locator("aurelius-atlas-webapp-catalogue-card .title.is-4 a")
    cards = fields_box.locator("aurelius-atlas-webapp-catalogue-card")
    expect(cards).to_have_count(2)
    fields_box.locator("select").select_option(label="Completeness")
    expect(titles.nth(0)).to_have_text(f"zz{run}field")
    expect(titles.nth(1)).to_have_text(f"zz{run}field2")
    fields_box.locator("button.aurelius-card-section-direction").click()
    expect(titles.nth(0)).to_have_text(f"zz{run}field2")
    expect(titles.nth(1)).to_have_text(f"zz{run}field")
    # DET-60 as amended, DET-64: the block of the card now on top — the 0.9
    # field's own roll-up, with only the dimension that has rules.
    assert _dimension_texts(cards.nth(0).locator(".aurelius-card-scores")) == ["90% Completeness (1)"]


# impact=major, likelihood=high (the score surfaces are new furniture with the
# roll-up's worker timing under them; the only proof of DET-56/58/59/60/61 on
# real data)
@pytest.mark.high
@pytest.mark.covers(rules=["DET-56", "DET-58", "DET-59", "DET-60", "DET-61", "DET-64"])
def test__the_dataset_page_draws_the_data_quality_scores(
    authenticated: Page, root_url: str, fresh_user_token: Callable[[], str]
) -> None:
    """The score box, the stat, the Completeness sort, and the card block on a scored dataset (DET-56..DET-61).

    The mini-graph, then the score source: a second field joins the dataset, a
    completeness rule hangs off each field, and the scanner's scores say 0.5 and
    0.9. The worker's round rolls them up (ASQ-04, ASQ-05) — the dataset's own
    overall is the two fields' sums, 0.7 over 2 — and the door carries that on
    the dataset, its fields, and the cards. The dataset page then draws the
    five-row box in the fixed order with the held 0-count rows (DET-56), the
    stats bar's percent and its nav entry in the legacy place (DET-58), the
    Fields box sorted by Completeness putting the 0.9 field first (DET-59), and
    the score block on each card of that box (DET-60 as amended) — every one of
    them the scored dimensions only, never a 0-count row (DET-64). The
    un-scored twin dataset answers the placeholder and the word (DET-56,
    DET-58, DET-63), and the scored one's results row prints the same block it
    carries in a details section (DET-61 as amended). Self-cleaned;
    no shared service restarts (DD-223).
    """
    run = secrets.token_hex(4)
    token = fresh_user_token()
    guids = _seed_m4i_mini_graph(authenticated, root_url, token, run)
    dataset_guid = guids["dataset"]
    field_guid = guids["field"]
    field2_guid, rule_pairs = _seed_score_source(authenticated, root_url, token, run, dataset_guid, field_guid)
    # The empty twin: the same layout, no scores (DET-63's negative half).
    empty = _seed_entities(authenticated, root_url, token, "m4i_dataset", [f"zz{run}empty"])

    try:
        # The rules' edges are separate records the read searches (the CLS-12
        # race, DET-35's idiom), and the roll-up reads the fields' documents —
        # wait both beats before the screen, so the quality round has already
        # found documents derived with their dataset join.
        for scored_guid, rule_guid in rule_pairs:
            _wait_entity_read(
                authenticated,
                root_url,
                fresh_user_token(),
                scored_guid,
                predicate=lambda entity, guid=rule_guid: _active_edge(entity, "dataQuality", guid),
            )
        _wait_search_cards(authenticated, root_url, fresh_user_token(), [field_guid, field2_guid, dataset_guid])

        # The totals arrive through the worker's round (ASQ-07), so wait the
        # roll-up itself: the dataset's overall is the two fields' sums,
        # 1.4 over 2 = 0.7. The wait carries the mint factory (its poll can
        # outlive the 60s dev token).
        _wait_card_quality(authenticated, root_url, fresh_user_token, dataset_guid, overall_count=2, score=0.7)
        _wait_card_quality(authenticated, root_url, fresh_user_token, field2_guid, overall_count=1, score=0.9)

        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{dataset_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}warehouse")
        _score_box_and_stat(authenticated, scored=True, run=run)

        # DET-59/DET-60: the Fields box's dimension sorts and the cards' blocks.
        _drives_the_score_sort(authenticated, run)

        # DET-61 as amended (DD-860): the same scored dataset as a results row
        # prints its block — the data decides, not the mount site — and DET-64
        # keeps it to the dimension that has rules.
        authenticated.goto(urljoin(root_url, f"/en-US/search/results?query={quote(f'zz{run}warehouse')}"))
        rows = authenticated.locator(".result-row")
        # The fresh seeds search asynchronously (the store's refresh lags the
        # seed answer), so the row count waits like the totals above do.
        expect(rows).to_have_count(1, timeout=30_000)
        expect(rows.first).to_contain_text(f"zz{run}warehouse")
        block = rows.first.locator(".aurelius-card-scores")
        expect(block).to_be_visible()
        assert _dimension_texts(block) == ["70% Completeness (2)"]

        # DET-56/DET-58/DET-63, the negative half: the un-scored twin answers
        # the placeholder and the word — no rows, no percent.
        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{empty['-0']}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}empty")
        _score_box_and_stat(authenticated, scored=False, run=run)
    finally:
        for type_name in _M4I_PURGE:
            # The factory, not one minted token: the delete retries on the
            # worker's late writes can run past the dev realm's 60s.
            _purge_type(authenticated, root_url, fresh_user_token, type_name)
