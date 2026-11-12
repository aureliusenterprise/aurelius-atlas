"""E2E: the governance verdicts, live over the real catalogue (VEV-01..04, VE-03/04).

The suite drives the deployed app on the stack of ``e2e/docker-compose.yaml``: the app
reads its rules from a real Atlas server on the dev store, as its own service identity
(VEV-04), while the caller's token — the browser's own, minted for ``aurelius`` (DV-75) —
verifies at the gate and stops there. Rules are seeded through that same catalogue as
the dev writer and hard-deleted after (DD-223).

Every test names its rules with one ``zz<run>`` word: the dev store is shared with the
other suites and the m4i sample corpus, so the assertions are keyed by the seeded rules'
guids and never count the whole answer — a foreign rule of the shared store rides the
verdicts too, and that is not this suite's failure (the scanner's precedent).
"""

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

import httpx2 as httpx
import pytest
from aurelius_atlas_validate_entity_client import ValidateEntityClient
from aurelius_atlas_validate_entity_client.models import ValidationResponse

type SeedRules = Callable[[list[dict[str, Any]]], Awaitable[dict[str, str]]]
"""The ``seed_rules`` seeder: rule attribute dicts in, ``{temp index: real guid}`` out."""

NO_KIND_ERROR = "dqcheckkind"
"""The unread cause of a stored expression rule: the vocabulary names no kind (DV-146)."""


@pytest.fixture()
def run() -> str:
    """One word making this test's names unique in the shared store (DD-223)."""
    return uuid4().hex[:10]


def _draft(run: str) -> dict[str, Any]:
    """The editor draft the rules run over (VEV-01): only its ``attributes`` are read."""
    return {
        "typeName": "m4i_dataset",
        "guid": "-1",
        "attributes": {
            "name": f"zz{run} draft",
            "qualifiedName": f"zz{run}.draft",
            "domain": "finance",
        },
    }


def _present_rule(run: str, attribute: str) -> dict[str, Any]:
    """An ACTIVE ATTRIBUTE_PRESENT rule over ``attribute``, with the corpus's stored sentences."""
    return {
        "name": f"zz{run}.{attribute}-present",
        "qualifiedName": f"zz{run}.{attribute}-present",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": attribute,
        "qualityDimension": "COMPLETENESS",
        "compliantMessage": f"zz{run} the draft carries a {attribute}",
        "nonCompliantMessage": f"zz{run} the draft carries no {attribute}",
    }


@pytest.mark.critical
@pytest.mark.covers("aurelius_atlas_validate_entity.routes.validate.build_router", rules=["VE-03"])
async def test__a_missing_token_is_rejected(anonymous_client: httpx.AsyncClient) -> None:
    """``POST /`` without a bearer is the gate's 401, before any rule is read (VE-03, DV-75)."""
    response = await anonymous_client.post("/", json=_draft("noauth"))

    assert response.status_code == 401


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_validate_entity.verdicts.VerdictEngine.evaluate_draft",
    "aurelius_atlas_validate_entity.verdicts.VerdictEngine._read",
    rules=["VEV-02", "VEV-03"],
)
async def test__the_draft_answers_with_the_seeded_rules_verdicts(
    api: ValidateEntityClient, seed_rules: SeedRules, run: str
) -> None:
    """Two seeded ACTIVE rules answer the draft live: one compliant, one not (VEV-02).

    The draft carries ``name`` and nothing else, so the presence rule over ``name`` is
    compliant with its own stored sentence and the not-empty rule over ``description``
    is not, with its refusal sentence (GQ-06). The rules are found by their real guids —
    the server assigns them, the suite saves the assignments — so a foreign rule of the
    shared store rides the answer unnoticed (DD-223).
    """
    guids = await seed_rules(
        [
            _present_rule(run, "name"),
            {
                "name": f"zz{run}.description-empty",
                "qualifiedName": f"zz{run}.description-empty",
                "active": True,
                "dqcheckkind": "ATTRIBUTE_NOT_EMPTY",
                "dqattribute": "description",
                "qualityDimension": "COMPLETENESS",
                "compliantMessage": f"zz{run} the draft describes the dataset",
                "nonCompliantMessage": f"zz{run} the draft has no description",
            },
        ]
    )

    answer: ValidationResponse = await api.validate(_draft(run))

    by_guid = {verdict.rule_guid: verdict for verdict in answer.verdicts}
    compliant = by_guid[guids["0"]]
    assert compliant.compliant is True
    assert compliant.message == f"zz{run} the draft carries a name"
    assert compliant.attribute == "name"
    assert compliant.dimension == "COMPLETENESS"
    refusal = by_guid[guids["1"]]
    assert refusal.compliant is False
    assert refusal.message == f"zz{run} the draft has no description"
    assert refusal.rule_name == f"zz{run}.description-empty"


@pytest.mark.critical
@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine._read", rules=["VEV-03"])
async def test__an_inactive_rule_needs_no_verdict_and_an_expression_rule_is_unread(
    api: ValidateEntityClient, seed_rules: SeedRules, run: str
) -> None:
    """The walk skips the inactive rule and records the expression rule unread (VEV-03, DV-146).

    The inactive rule would pass over this draft, so its absence is the assertion; the
    stored expression rule names no ``dqcheckkind``, so the vocabulary cannot read it —
    it travels as an unread entry with the cause, never executed.
    """
    guids = await seed_rules(
        [
            {**_present_rule(run, "name"), "active": False},
            {
                "name": f"zz{run}.legacy-expression",
                "qualifiedName": f"zz{run}.legacy-expression",
                "active": True,
                "expression": "d.name != null",
                "qualityDimension": "COMPLETENESS",
            },
        ]
    )

    answer = await api.validate(_draft(run))

    assert guids["0"] not in {verdict.rule_guid for verdict in answer.verdicts}
    unread = {entry.rule_guid: entry for entry in answer.unread_rules}
    assert NO_KIND_ERROR in unread[guids["1"]].error
    assert unread[guids["1"]].rule_name == f"zz{run}.legacy-expression"


@pytest.mark.critical
@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VEV-01"])
async def test__a_body_that_is_not_json_is_400_in_the_atlas_error_body(client: httpx.AsyncClient) -> None:
    """A body the app cannot parse is VEV-01's 400, in the Atlas error body (DV-79's posture)."""
    response = await client.post(
        "/",
        content=b"not json {",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "ATLAS-400-00-029"


@pytest.mark.critical
@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-04"])
async def test__liveness_needs_no_token(anonymous_client: httpx.AsyncClient) -> None:
    """The container healthcheck answers 204, anonymous, on the deployed container (VE-04)."""
    response = await anonymous_client.get("/liveness")

    assert response.status_code == 204
