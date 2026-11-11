"""The governance-verdict document, as the client lib owns it (CL-40 as amended by 12.7; DD-498).

The document ``POST /`` answers since 12.7 — the flat verdict array and the unread rules,
the browser's contract (VEV-02/03) — stated once so the app's answer and a caller's parse
validate one model. The four canned cards of the 8.3 mock retired with DV-67 (ADR 061).
"""

from typing import Any

import pytest
from aurelius_atlas_validate_entity_client.models import (
    GovernanceVerdict,
    UnreadRule,
    ValidationResponse,
)
from pydantic import ValidationError

VERDICT: dict[str, Any] = {
    "ruleGuid": "rule-1",
    "ruleName": "Name present",
    "attribute": "name",
    "dimension": "COMPLETENESS",
    "compliant": False,
    "message": "This entity is missing a name",
}
ANSWER: dict[str, Any] = {
    "verdicts": [VERDICT, {**VERDICT, "ruleGuid": "rule-2", "compliant": True, "message": "ok"}],
    "unreadRules": [{"ruleGuid": "rule-3", "ruleName": "Legacy expression", "error": "no check kind"}],
}


@pytest.mark.covers(rules=["CL-40"])
def test__the_document_parses_as_the_editor_receives_it() -> None:
    """The flat array and the unread list, camelCase keys (VEV-02/03, DD-498)."""
    response = ValidationResponse.model_validate(ANSWER)

    assert [verdict.compliant for verdict in response.verdicts] == [False, True]
    assert response.verdicts[0].rule_guid == "rule-1"
    assert response.verdicts[0].attribute == "name"
    assert response.unread_rules[0].error == "no check kind"


@pytest.mark.covers(rules=["CL-40"])
def test__compliant_is_a_json_boolean() -> None:
    """12.6's verdict, not the mock's string flag: a string is not the contract (DD-498)."""
    with pytest.raises(ValidationError):
        GovernanceVerdict.model_validate({**VERDICT, "compliant": "0"})


@pytest.mark.covers(rules=["CL-40"])
def test__an_unknown_field_is_a_validation_error() -> None:
    """``extra='forbid'``: a field the app does not answer is not the contract, not silence."""
    with pytest.raises(ValidationError):
        ValidationResponse.model_validate({"verdicts": [], "unreadRules": [], "surprise": 1})


@pytest.mark.covers(rules=["CL-40"])
def test__the_document_is_immutable_once_parsed() -> None:
    """Frozen models: a validated verdict cannot drift from the wire."""
    verdict = GovernanceVerdict.model_validate(VERDICT)

    with pytest.raises(ValidationError):
        verdict.compliant = True


@pytest.mark.covers(rules=["CL-40"])
def test__a_verdict_needs_every_field() -> None:
    """The verdict is exact: a missing line is a validation error (VEV-02)."""
    with pytest.raises(ValidationError):
        GovernanceVerdict.model_validate({"ruleGuid": "rule-1"})


@pytest.mark.covers(rules=["CL-40"])
def test__an_unread_rule_names_its_error() -> None:
    """The unread entry carries the cause: recorded, never executed (VEV-03, DV-146)."""
    unread = UnreadRule.model_validate({"ruleGuid": "r", "ruleName": "n", "error": "no check kind"})

    assert unread.rule_name == "n"
