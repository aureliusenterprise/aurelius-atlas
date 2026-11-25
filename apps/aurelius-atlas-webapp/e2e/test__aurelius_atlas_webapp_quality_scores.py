"""E2E: the 7.25c/7.25d/7.25e data-quality scores — the box, the stat, the sorts, the card.

The score source is the scanner's: 12.2 writes one ``m4i_dq_score`` per rule and
dataset, and 14.5's worker round rolls those scores up to the fields, their data
attributes, and every entity of their breadcrumb (ASQ-04, ASQ-05), which 16.1
carries on the view and on every card of the view family (AVS-01). This
scenario seeds the source by hand — its stack starts from an empty store, so
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

Since 7.25e the file holds a second scenario on the shipped corpus instead of a
hand-seeded one: a demo field 12.9 scored — ``FUNC_ORGANIZATION`` — whose rule
cards each print the score their own rule gave that field (DET-65, AVS-13, the
read door's join of VDR-16), with the Dimension and Quality Score sorts DET-66
adds to its box. The shared m4i purge wipes the corpus by design, so that
scenario carries the demo bundle through the server's own import door when the
field has gone; nothing it asserts is hardcoded (DV-207, DD-223).
"""

import json
import re
import secrets
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote, urljoin

import pytest
from conftest import ATLAS_SERVER_HOST_PORT, _goto_app
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


# The demo field 12.9 scores — the one the increment hand-checked (12-9-demo-
# quality-scores/spec.md, the acceptance's by-hand leg). Its GUID is fixed, so
# the box below can be opened without searching for it.
_DEMO_FIELD_GUID = "f86b18e1-7a20-4ba1-a616-09bac4b96a3b"

# 12.9's shipped bundle, read only when the shared purge has taken the corpus
# down (the note under _ensure_demo_field).
_SAMPLE_ZIP = Path(__file__).parents[3] / "data" / "atlas-sample" / "sample_data.zip"


def _import_sample(page: Page, token: str) -> None:
    """Put the shipped demo corpus back through the server's own import door (IMS-01).

    The multipart shape ``docker/import_sample.py`` posts: the bundle as
    ``data``, Atlas's empty ``AtlasImportRequest`` as ``request``. The e2e
    sign-in user is ``aurelius-writer``, who holds ``atlas-admin`` in the
    realm, so ``ADMIN_IMPORT`` passes (AUZ-02). The import is idempotent by
    GUID, so posting it over a store that still holds the corpus is a no-op.

    The call goes to the server's published port rather than the webapp
    origin: the stack's nginx proxies ``/api/`` with its default 60 s read
    timeout, and a bundle import that runs longer than that answers 504
    while the import itself keeps going server-side. The port is the same
    door the proxy fronts (DD-142's readiness probe dials it directly).
    """
    response = page.request.post(
        f"https://localhost:{ATLAS_SERVER_HOST_PORT}/api/atlas/admin/import",
        multipart={
            "request": "{}",
            "data": {
                "name": "sample_data.zip",
                "mimeType": "application/zip",
                "buffer": _SAMPLE_ZIP.read_bytes(),
            },
        },
        headers={"authorization": f"Bearer {token}"},
        # The bundle's 687 entities run past the API context's 30s default.
        timeout=300_000,
    )

    assert response.status == 200, response.text()


def _read_view(page: Page, root_url: str, mint: Callable[[], str], guid: str) -> dict:
    """The view door's answer for one entity, or an empty dict when it holds none (AVS-04)."""
    answer = page.request.get(
        urljoin(root_url, f"/api/aurelius/v1/entity/guid/{guid}"),
        headers={"authorization": f"Bearer {mint()}"},
    )

    return {} if answer.status != 200 else answer.json()


def _ensure_demo_field(page: Page, root_url: str, mint: Callable[[], str], *, timeout: float = 300) -> dict:
    """Read the demo field's view, importing the corpus first when the store lost it.

    The m4i purge the DET scenarios share (``_M4I_PURGE``, DD-223) deletes every
    entity of the field and rule types, which takes the shipped corpus with it —
    and CI's ``nx affected`` runs another suite's purge minutes before this
    scenario. So the field is read first, and only a store that no longer holds
    it ACTIVE is served the bundle. The worker's rounds then land the field's
    card and its joined score rows (AVS-13, VDR-16), which the two waits ride —
    the ASG-06 wait idiom on the derived document, on one shared deadline.

    Returns:
        The view of the field as the read door answers it (AVS-04, AVS-13).
    """
    view = _read_view(page, root_url, mint, _DEMO_FIELD_GUID)
    if view.get("status") != "ACTIVE":
        # The purge deletes softly (DD-059) and an import revives a deleted
        # entity (IMP-04), so the bundle puts the field, its rules and their
        # scores back in one round.
        _import_sample(page, mint())

    deadline = time.monotonic() + timeout
    while True:
        view = _read_view(page, root_url, mint, _DEMO_FIELD_GUID)
        overall = next((row for row in view.get("quality", []) if row["dimension"] == "overall"), {})
        if view.get("ruleScores") and overall.get("count", 0) > 0:
            return view
        assert time.monotonic() < deadline, f"the field never came back scored: {view}"
        time.sleep(2)


def _section_entities(view: dict, attribute: str) -> list[dict]:
    """The opened entity's related entities under one end (AVS-04), as the box seeds them.

    Args:
        view: the view as the read door answers it
        attribute: the relationship attribute the layout seeds on (DET-35)

    Returns:
        The end's entity rows, guid and name (empty when the view holds no such end).
    """
    for section in view.get("sections", []):
        if section["attribute"] == attribute:
            return section.get("entities", [])
    return []


def _percent(value: float) -> str:
    """The percent UIC-37 and the stat print (DET-58, DET-65): whole percents whole, one decimal at most.

    Angular's ``percent: '1.0-1'`` (what `scorePercent` calls), rewritten: the
    raw stored float can carry the sum's tail (94.60000000000001), and the pipe
    rounds it away, so the expectation rounds the same way.
    """
    return f"{value * 100:.1f}".rstrip("0").rstrip(".") + "%"


def _count(value: float) -> str:
    """The rule count as the browser prints it (UIC-37): the store's number, whole percents whole."""
    return str(int(value)) if float(value).is_integer() else str(value)


def _roll_up(view: dict) -> tuple[list[str], str]:
    """The score box's row texts and the stat's percent, off the view's own roll-up.

    The same rows DET-56 draws and the same percent DET-58 prints, derived from
    the view's ``quality`` (AVS-01) instead of pinned: `qualityRows`' fixed
    dimension order, only the dimensions the roll-up counts (DET-64), UIC-37's
    percent to one decimal at most, and the stat's percent (Angular's
    ``percent: '1.0-1'`` of `scorePercent`, whole percents whole).

    Args:
        view: the field's view as the read door answers it

    Returns:
        The box's row texts and the stats bar's value.
    """
    # `QUALITY_DIMENSIONS` and `QUALITY_DIMENSION_LABELS` (DET-56's fixed order
    # and words), and `scorePercent`'s `percent: '1.0-1'` — the whole thing read
    # off the view, so the scenario never pins a demo number.
    dimensions = {row["dimension"]: row for row in view.get("quality", [])}
    overall = dimensions.pop("overall", {})
    words = {
        "accuracy": "Accuracy",
        "completeness": "Completeness",
        "timeliness": "Timeliness",
        "uniqueness": "Uniqueness",
        "validity": "Validity",
    }

    rows = [
        f"{_percent(row['score'])} {word} ({_count(row['count'])})"
        for dimension, word in words.items()
        if (row := dimensions.get(dimension, {})).get("count", 0) > 0
    ]

    return rows, _percent(overall["score"]) if overall.get("count", 0) > 0 else "Unavailable"


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


# impact=major, likelihood=high (7.25e's increment promotion: the joined rule
# scores are a new surface on the field page, and the shipped corpus's roll-up
# is its only proof on a served stack)
@pytest.mark.high
@pytest.mark.covers(rules=["DET-65", "DET-66"])
def test__the_field_page_draws_each_rule_score(
    authenticated: Page, root_url: str, fresh_user_token: Callable[[], str]
) -> None:
    """The field's rules box prints the score of the rule on each card (DET-65, DET-66).

    The shipped corpus instead of a hand-seeded one: the field 12.9 scored
    (`FUNC_ORGANIZATION`), whose rules carry one Accuracy and one Completeness
    score and a third rule the scanner never measured. The read door joins the
    field's own results (ASQ-09, VDR-16, AVS-13) and the box draws each card's
    row — UIC-37's pie, the percent, the dimension lowercased, and no count
    (DET-65) — while the score box above it and the stats bar keep printing the
    roll-up (DET-56, DET-58). The unscored rule stays a card and prints nothing
    extra (DV-207). The box sorts by the same rows DET-66 adds: Relevance, Name,
    Dimension, Quality Score, ascending with the card the field cannot place
    last. Every number is read from the view's own answer, none hardcoded; the
    bundle is re-imported when an earlier purge took it, and no shared service
    restarts (DD-223).
    """
    view = _ensure_demo_field(authenticated, root_url, fresh_user_token)
    rules = _section_entities(view, "dataQuality")
    # The rows the join answers for the field, kept to the rules the box shows —
    # the box can only print a score of a rule it holds a card for.
    scores = {row["rule"]: row for row in view["ruleScores"] if row["rule"] in {rule["guid"] for rule in rules}}
    # The box's cards ride the search door (16.5d, DD-615) and DET-18 quietly
    # drops a relation whose card is missing, so wait the rules' beat before the
    # screen resolves the box.
    _wait_search_cards(authenticated, root_url, fresh_user_token(), [rule["guid"] for rule in rules])
    # The box's cards are the field's rule end (DET-35), and the scored half of
    # them is what DET-65 prints — the scenario needs both a scored and an
    # unscored rule to prove the card never grows a row it has no score for.
    assert len(rules) >= 2, f"the demo field lost its rules end: {rules}"
    assert 0 < len(scores) < len(rules), f"the demo field's scores no longer cover part of its rules: {scores}"

    # The name the screen opens on, the two sorts' expected orders, and the
    # roll-up — all off the door's answer, so the demo's own numbers can move
    # with the bundle without touching this scenario.
    names = {rule["guid"]: rule["name"] for rule in rules}
    _goto_app(authenticated, urljoin(root_url, f"/en-US/search/details/{_DEMO_FIELD_GUID}"))
    expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(view["displayText"])

    box = authenticated.locator("#related-rules")
    expect(box).to_be_visible()
    cards = box.locator("aurelius-atlas-webapp-catalogue-card")
    expect(cards).to_have_count(len(rules))

    # DET-65: each scored card prints its own row — percent, dimension word in
    # lower case, no count — and the rule the field holds no result for prints
    # no block at all. The rows ride the card's own `.aurelius-card-scores`.
    for card in cards.all():
        guid = next(guid for guid, name in names.items() if name == card.locator(".title.is-4 a").inner_text().strip())
        row = scores.get(guid)
        block = card.locator(".aurelius-card-scores")
        if row is None:
            # DV-207: the rule the scanner never measured stays a card and grows
            # no score line of its own.
            expect(block.locator(".quality-dimension")).to_have_count(0)
        else:
            # The row is the card's, joined at view build (DD-865), so its pie
            # is the wait: DET-65 with DET-60, the score the rule gave this
            # field wins over any roll-up, and DET-65 prints no count.
            expect(block.locator("aurelius-atlas-ui-data-quality-pie")).to_have_count(1)
            assert _dimension_texts(block) == [f"{_percent(row['score'])} {row['dimension'].lower()}"]

    # DET-56/DET-58 above it: the roll-up stays the field's own box and percent
    # — the joined rule rows never replace it.
    box_rows, stat_value = _roll_up(view)
    score_box = authenticated.locator("#data-quality")
    expect(score_box.locator(".quality-dimension")).to_have_count(len(box_rows))
    assert _dimension_texts(score_box) == box_rows
    stat = authenticated.locator(
        ".aurelius-details-stats .level-item", has=authenticated.locator('p.heading a[href="#data-quality"]')
    )
    expect(stat.locator("p.title")).to_have_text(stat_value)

    # DET-66: the four options, in the spec's order — the DET-21 pair plus the
    # two rows the join carries.
    select = box.locator("select")
    assert [text.strip() for text in select.locator("option").all_inner_texts()] == [
        "Relevance",
        "Name",
        "Dimension",
        "Quality Score",
    ]

    titles = cards.locator(".title.is-4 a")

    def order(*, key: Callable[[dict], str | float], descending: bool = False) -> list[str]:
        """Wait the box into DET-66's order of the joined rows (the sort's re-render).

        Args:
            key: the dimension word or the score of one row
            descending: the direction button's ask, DET-21's plain reversal

        Returns:
            The rule names in the order the box shows them.
        """
        wanted = _rule_order(names, scores, key=key)
        if descending:
            wanted.reverse()
        for index, name in enumerate(wanted):
            expect(titles.nth(index)).to_have_text(name)
        return [text.strip() for text in titles.all_inner_texts()]

    # DET-66: Dimension orders the cards on the row's word, ascending, with the
    # card the field cannot place taking the last place DET-59 sets.
    select.select_option(label="Dimension")
    order(key=lambda row: row["dimension"].lower())

    # DET-66: Quality Score orders them on the score, ascending, same last place.
    select.select_option(label="Quality Score")
    ascending = order(key=lambda row: row["score"])

    # DET-21: the direction button is the plain reversal of what is on screen.
    box.locator("button.aurelius-card-section-direction").click()
    assert order(key=lambda row: row["score"], descending=True) == list(reversed(ascending))


def _rule_order(names: dict[str, str], scores: dict[str, dict], *, key: Callable[[dict], str | float]) -> list[str]:
    """The DET-66 ascending order of the box's cards, as the store's comparator builds it.

    The sorted value ascending, a card the field places last (DET-59's missing-
    last rule), and every tie falling back to the label order (DET-59's
    tie-break on the display text).

    Args:
        names: the display text of each rule of the box, by GUID
        scores: the joined rule score rows, keyed by rule GUID
        key: the dimension word or the score of one row

    Returns:
        The display texts in the order the box must show them.
    """

    def placed(name: str) -> tuple[int, str | float, str]:
        row = scores.get(next(guid for guid, held in names.items() if held == name))

        return (1, 0, name) if row is None else (0, key(row), name)

    return sorted(names.values(), key=placed)
