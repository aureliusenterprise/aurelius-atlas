"""The governance-verdict answer of the validate-entity API (CL-40 as amended by 12.7; DD-498).

The body ``POST /`` answers since 12.7: the verdicts the app's own engine ran over the draft
(VEV-02) and the rules the vocabulary could not read (VEV-03), stated as models so a caller
parses them and the app's answer is checked against one shape. The four canned cards of the
8.3 mock retire with DV-67 (ADR 061): ``compliant`` is a JSON boolean, not the legacy's
string ``'0'``/``'1'``, and nothing of the legacy ``AppSearchResult`` document survives.

The field names are camelCase, the same house style the card document used; ``verdicts`` is a
flat array and the banner groups it by ``attribute`` (DD-498 — keyed cards and parallel arrays
were refused there).
"""

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class GovernanceVerdict(BaseModel):
    """One ACTIVE governance rule's answer about the draft (VEV-02; CL-40).

    ``compliant`` is a JSON boolean — 12.6's verdict, not the mock's string flag — and
    ``message`` is the verdict line the engine carries: the rule's own sentence for its
    verdict, the kind's reason when the rule stores none (GQ-06).
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid", frozen=True)

    rule_guid: str = Field(alias="ruleGuid", description="The catalogue guid of the rule that answered.")

    rule_name: str = Field(alias="ruleName", description="The rule's name, as the catalogue holds it.")

    attribute: str = Field(description="The entity attribute the rule measures: the banner groups by it.")

    dimension: str = Field(description="The rule's quality dimension, e.g. ``COMPLETENESS``.")

    compliant: StrictBool = Field(description="The verdict: whether the draft passes the rule.")

    message: str = Field(description="The line to show: the rule's own sentence, or the kind's reason.")


class UnreadRule(BaseModel):
    """A rule the vocabulary cannot read — recorded, never executed (VEV-03; CL-40; DV-146)."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid", frozen=True)

    rule_guid: str = Field(alias="ruleGuid", description="The catalogue guid of the unread rule.")

    rule_name: str = Field(alias="ruleName", description="The rule's name, as the catalogue holds it.")

    error: str = Field(description="Why the vocabulary cannot read it, e.g. a stored expression rule.")


class ValidationResponse(BaseModel):
    """The ``POST /`` answer: the verdicts of the ACTIVE rules, and the unread ones (VEV-02/03; CL-40; DD-498)."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid", frozen=True)

    verdicts: list[GovernanceVerdict] = Field(
        default_factory=list,
        description="One verdict per ACTIVE rule the vocabulary could read (VEV-02).",
    )

    unread_rules: list[UnreadRule] = Field(
        alias="unreadRules",
        default_factory=list,
        description="The rules the vocabulary could not read (VEV-03): shown, never executed.",
    )
