"""E2E: the 7.29 person details page — responsibilities, grouped stats, rule box.

The tenth layout (DET-39..DET-43): a person page with no description box,
four headed stat boxes counting the five responsibility ends (DET-40,
DD-519), the one merged Governance Responsibilities box (DET-41, DV-154 —
the five ends, not the retired App Search query), and the Governance
Quality Rules box listing the type's rules with their live verdicts
(DET-42, DV-155 — the basic-search prefix joined to 12.7's
``/validate-entity/`` answers). The scenarios ride the served stack:
browser -> nginx -> server, and the deployed validate-entity app reading
with its cache at zero; self-cleaned like the other m4i suites (DD-223).
"""

import json
import re
import secrets
from urllib.parse import urljoin

import pytest
from conftest import _goto_app
from playwright.sync_api import Page, expect
from test__aurelius_atlas_webapp import (
    _delete_entity,
    _purge_type,
    _seed_gov_rule,
    _wait_entity_read,
)

# The shared dev store is never cleaned between runs, so the m4i purge list
# the DET tests share applies here too (the quality-rules suite's scope,
# minus the types this page never seeds).
_M4I_PURGE = [
    "m4i_person",
    "m4i_data_domain",
    "m4i_data_entity",
    "m4i_data_attribute",
]


def _seed_person(page: Page, root_url: str, token: str, run: str, *, with_graph: bool) -> tuple[str, dict[str, str]]:
    """Seed one person (and, on request, its five responsibility ends) in one bulk create.

    The ends ride ``relationshipAttributes`` naming the request's own
    temporary guids (REL-11, the mini-graph's idiom). Names are single
    ``zz<run>`` tokens so every assertion can be word-exact on the shared
    store. Returns the person's guid and the name map.
    """
    names = {
        "person": f"zz{run}person",
        "domain": f"zz{run}dom",
        "owned_entity": f"zz{run}owne",
        "owned_attribute": f"zz{run}owna",
        "stewarded_entity": f"zz{run}stwe",
        "stewarded_attribute": f"zz{run}stwa",
    }

    def entity(temp_guid: str, type_name: str, key: str, **extra: object) -> dict:
        body: dict = {
            "typeName": type_name,
            "guid": temp_guid,
            "attributes": {"qualifiedName": names[key], "name": names[key]},
        }
        body.update(extra)
        return body

    person: dict = entity("-0", "m4i_person", "person")
    entities: list[dict] = [person]
    if with_graph:
        person["relationshipAttributes"] = {
            "domainLead": [{"guid": "-1", "typeName": "m4i_data_domain"}],
            "businessOwnerEntity": [{"guid": "-2", "typeName": "m4i_data_entity"}],
            "businessOwnerAttribute": [{"guid": "-3", "typeName": "m4i_data_attribute"}],
            "stewardEntity": [{"guid": "-4", "typeName": "m4i_data_entity"}],
            "stewardAttribute": [{"guid": "-5", "typeName": "m4i_data_attribute"}],
        }
        entities += [
            entity("-1", "m4i_data_domain", "domain"),
            entity("-2", "m4i_data_entity", "owned_entity"),
            entity("-3", "m4i_data_attribute", "owned_attribute"),
            entity("-4", "m4i_data_entity", "stewarded_entity"),
            entity("-5", "m4i_data_attribute", "stewarded_attribute"),
        ]

    response = page.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps({"entities": entities}),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert response.status == 200, response.text()

    assignments = response.json()["guidAssignments"]

    return assignments["-0"], names


def _person_stat(page: Page, group_heading: str, label: str) -> str:
    """The grouped stats bar's count under one heading's label (DET-40)."""
    box = page.locator(".aurelius-details-stats-group").filter(has=page.get_by_text(group_heading, exact=True)).first
    item = box.locator(".level-item").filter(has_text=label).first

    return item.locator("p.title").inner_text().strip()


@pytest.mark.critical
@pytest.mark.covers(rules=["DET-39", "DET-40", "DET-41", "DET-43"])
def test__the_person_page_draws_roles_and_counts(authenticated: Page, root_url: str, user_token: str) -> None:
    """The tenth layout: no description box, four stat boxes, the merged roles box (DET-39..DET-41, DET-43).

    The legacy person page's anatomy over seeded relationships: the five
    ends merge into one Governance Responsibilities box (the retired
    ``derivedperson`` query has no port, DV-154), the four headed boxes
    count those ends per the seed rule (one deduped ACTIVE entry each),
    and the screen draws neither the description box nor a People box the
    legacy page never carried. Self-cleaned.
    """
    run = secrets.token_hex(4)
    guid, names = _seed_person(authenticated, root_url, user_token, run, with_graph=True)
    ends = ["domainLead", "businessOwnerEntity", "businessOwnerAttribute", "stewardEntity", "stewardAttribute"]

    try:
        # The ends are assembled by searching the edge documents: wait until
        # the person reads all five (the editor's propagation-retry idiom).
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            guid,
            predicate=lambda entity: all(entity.get("relationshipAttributes", {}).get(key) for key in ends),
        )

        _goto_app(authenticated, urljoin(root_url, f"/en-US/search/details/{guid}"))

        # DET-39: the description box is absent — the one layout without it.
        expect(authenticated.locator("#description-details")).to_have_count(0)
        # DET-40: the grouped bar replaced the flat one: four headed boxes.
        expect(authenticated.locator(".aurelius-details-stats-group")).to_have_count(4)
        expect(authenticated.locator(".aurelius-details-stats")).to_have_count(0)
        # No People box either (DET-23's layouts are the domain/entity/attribute).
        expect(authenticated.locator("#people-details")).to_have_count(0)

        # DET-40: the legacy order and the per-end counts (one end each;
        # Other counts the properties, none yet — the person carries no
        # attribute the filter lets through).
        # The headings render uppercase (Bulma's text-transform), so they are
        # compared case-folded (the stats-bar idiom in the sibling suite).
        headings = [
            (box.locator("p.heading").first.inner_text() or "").strip().casefold()
            for box in authenticated.locator(".aurelius-details-stats-group").all()
        ]
        assert headings == ["domain lead", "data owner", "data steward", "other"]
        assert _person_stat(authenticated, "Domain Lead", "Data Domains") == "1"
        assert _person_stat(authenticated, "Data Owner", "Data Entities") == "1"
        assert _person_stat(authenticated, "Data Owner", "Data Attributes") == "1"
        assert _person_stat(authenticated, "Data Steward", "Data Entities") == "1"
        assert _person_stat(authenticated, "Data Steward", "Data Attributes") == "1"
        assert _person_stat(authenticated, "Other", "Properties") == "0"

        # DET-41: the five ends merge into one box, deduped by guid — the
        # ProcessOwner end the legacy box never lists is absent (DV-154)
        # because no seed names it here and the layout seeds only five.
        roles = authenticated.locator("#governance-roles")
        # Name the count element: while the ends load, the box carries its own
        # "Loading …" placeholders as h6 too, which a bare h6 locator resolves
        # alongside the count and fails strict mode under load.
        expect(roles.locator("h6.aurelius-card-section-count")).to_have_text("5 result(s)")
        expect(roles.locator(".title.is-4 a")).to_have_text(
            [
                names["domain"],
                names["owned_entity"],
                names["owned_attribute"],
                names["stewarded_entity"],
                names["stewarded_attribute"],
            ]
        )

        # DET-43: the nav's three entries, the legacy order — and no
        # Description entry, since the page draws no such box to reach.
        expect(authenticated.locator(".aurelius-details-nav .menu-list a")).to_have_text(
            ["Governance Responsibilities", "Governance Quality Rules", "Properties"]
        )

        # DET-25/DV-156: a heading is a router jump — the screen stays, the
        # address names the box. Scroll only: no facet filter rides it.
        authenticated.locator(".aurelius-details-stats-group").first.locator("p.heading a").click()
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{guid}#governance-roles$"))
        expect(roles.locator(".title.is-4 a")).to_have_count(5)  # still unfiltered
    finally:
        _delete_entity(authenticated, root_url, user_token, guid)
        for type_name in _M4I_PURGE:
            _purge_type(authenticated, root_url, user_token, type_name)


@pytest.mark.critical
@pytest.mark.covers(rules=["DET-42"])
def test__the_person_page_shows_the_quality_rules_with_verdicts(
    authenticated: Page, root_url: str, user_token: str
) -> None:
    """The #gov-quality box lists the type's rules and flips the verdict line (DET-42, DV-155).

    The deployed chain: the box searches the ACTIVE ``m4i_gov_data_quality``
    rules whose ``qualifiedName`` starts ``m4i_person--`` (the rule→type
    prefix), and paints each row's icon from 12.7's live answer over the
    opened person (the validate-entity app, its cache at zero). A person
    without the checked attribute rides the warning icon; saving the
    attribute through the API and reopening flips it to success — the
    Other stat counting the new property on the way (DET-40). Lines are
    keyed by this run's sentences: the shared store's corpus rules ride the
    box too, and counting them is not this test's business (DD-223). Self-cleaned.
    """
    run = secrets.token_hex(4)
    guid, names = _seed_person(authenticated, root_url, user_token, run, with_graph=False)
    rule_name = f"zz{run}email"
    description = f"zz{run} the person carries an email address"
    rule_guid = _seed_gov_rule(
        authenticated,
        root_url,
        user_token,
        {
            "name": rule_name,
            "qualifiedName": f"m4i_person--{rule_name}",
            "active": "true",
            "dqcheckkind": "ATTRIBUTE_PRESENT",
            "dqattribute": "email",
            "qualityDimension": "COMPLETENESS",
            "ruleDescription": description,
            "compliantMessage": f"zz{run} the email is there",
            "nonCompliantMessage": f"zz{run} the email is missing",
        },
    )

    try:
        _wait_entity_read(authenticated, root_url, user_token, guid, predicate=bool)

        _goto_app(authenticated, urljoin(root_url, f"/en-US/search/details/{guid}"))

        box = authenticated.locator("#gov-quality")
        expect(box.locator("h2")).to_have_text("Governance Quality Rules")

        # DET-42: the run's rule draws its card — name as the title, the
        # stored description line, and the warning icon of a refusal
        # (the person has no email yet).
        card = box.locator("aurelius-atlas-ui-entity-card", has_text=rule_name)
        expect(card).to_be_visible()
        expect(card.locator(".aurelius-gov-quality-description")).to_have_text(description)
        expect(card.locator(".aurelius-gov-quality-verdict .icon.has-text-warning")).to_have_count(1)
        expect(card.locator(".aurelius-gov-quality-verdict .icon.has-text-success")).to_have_count(0)

        # The verdict is live: save the email the rule asks for, reopen.
        updated = authenticated.request.post(
            urljoin(root_url, "/api/atlas/v2/entity"),
            data=json.dumps(
                {
                    "entity": {
                        "guid": guid,
                        "typeName": "m4i_person",
                        "attributes": {
                            "name": names["person"],
                            "qualifiedName": names["person"],
                            "email": "ada@example.com",
                        },
                    }
                }
            ),
            headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
        )
        assert updated.status == 200, updated.text()
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            guid,
            predicate=lambda entity: entity.get("attributes", {}).get("email"),
        )

        authenticated.reload()

        card = box.locator("aurelius-atlas-ui-entity-card", has_text=rule_name)
        expect(card.locator(".aurelius-gov-quality-verdict .icon.has-text-success")).to_have_count(1)
        expect(card.locator(".aurelius-gov-quality-verdict .icon.has-text-warning")).to_have_count(0)
        # The dimension word, titlecased — the legacy card's `| titlecase`.
        expect(card.locator(".aurelius-gov-quality-dimension")).to_have_text("Completeness")

        # DET-40: the Other box counts the new property the table shows.
        expect(authenticated.locator("#properties-details")).to_contain_text("email")
        assert _person_stat(authenticated, "Other", "Properties") == "1"
    finally:
        _delete_entity(authenticated, root_url, user_token, guid)
        _delete_entity(authenticated, root_url, user_token, rule_guid)
        for type_name in _M4I_PURGE:
            _purge_type(authenticated, root_url, user_token, type_name)
