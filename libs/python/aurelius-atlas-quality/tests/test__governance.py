"""The governance vocabulary and the one-record verdict (GQ-01..GQ-06)."""

import pytest
from aurelius_atlas_quality import (
    GOV_KINDS,
    Dimension,
    GovCheckKind,
    GovRule,
    GovVerdict,
    QualityRuleError,
    evaluate_gov_entity,
)


def rule(
    kind: GovCheckKind = GovCheckKind.ATTRIBUTE_PRESENT,
    attribute: str = "name",
    any_of: list[str] | None = None,
    **messages: str | None,
) -> GovRule:
    """A governance rule of the vocabulary, with the message overrides the test names."""
    return GovRule.from_json(
        {
            "name": "domain has a name",
            "checkKind": kind.value,
            "params": {"attribute": attribute, **({"anyOf": any_of} if any_of else {})},
            **messages,
        }
    )


@pytest.mark.covers("aurelius_atlas_quality.governance.GovRule.from_json", rules=["GQ-01"])
def test__a_rule_is_data_with_a_kind_an_attribute_and_its_messages() -> None:
    """A rule names a kind of the closed vocabulary, one attribute, and the sentences for its verdicts."""
    built = GovRule.from_json(
        {
            "guid": "g-1",
            "name": "domain has a definition",
            "checkKind": "ATTRIBUTE_NOT_EMPTY",
            "params": {"attribute": "definition"},
            "compliantMessage": "This data domain has a definition",
            "nonCompliantMessage": "This data domain should have a definition",
        }
    )
    assert built.guid == "g-1"
    assert built.kind is GovCheckKind.ATTRIBUTE_NOT_EMPTY
    assert built.dimension is Dimension.COMPLETENESS
    assert (built.attribute, built.any_of) == ("definition", ())
    assert built.compliant_message == "This data domain has a definition"
    assert built.non_compliant_message == "This data domain should have a definition"


@pytest.mark.covers("aurelius_atlas_quality.governance.GovRule.from_json", rules=["GQ-01"])
def test__the_rule_carries_no_threshold_and_the_verdict_no_score() -> None:
    """A verdict over one record is boolean: the rule shape takes no threshold, the result holds no score (DD-487)."""
    verdict = evaluate_gov_entity(rule(), {"name": "Finance"})
    assert isinstance(verdict.compliant, bool)
    assert set(GovVerdict.__dataclass_fields__) == {"rule", "compliant", "message"}
    with pytest.raises(QualityRuleError, match="has no parameters \\['threshold'\\]"):
        GovRule.from_json({"checkKind": "ATTRIBUTE_PRESENT", "params": {"attribute": "name", "threshold": 0.5}})


@pytest.mark.covers("aurelius_atlas_quality.governance.GovRule.from_json", rules=["GQ-02"])
def test__an_unknown_kind_names_the_vocabulary() -> None:
    """A kind outside the two is refused, and the error lists what the vocabulary holds."""
    with pytest.raises(QualityRuleError, match="ATTRIBUTE_PRESENT"):
        GovRule.from_json({"checkKind": "COMPLETENESS", "params": {"attribute": "name"}})


@pytest.mark.covers("aurelius_atlas_quality.governance.GovRule.from_json", rules=["GQ-02"])
def test__a_missing_or_unknown_parameter_raises_through_the_same_door() -> None:
    """The parse-time check is DQ-02's: a missing attribute, an unknown parameter, a wrong dimension."""
    with pytest.raises(QualityRuleError, match=r"needs the parameters \['attribute'\]"):
        GovRule.from_json({"checkKind": "ATTRIBUTE_PRESENT", "params": {}})
    with pytest.raises(QualityRuleError, match=r"has no parameters \['column'\]"):
        GovRule.from_json({"checkKind": "ATTRIBUTE_PRESENT", "params": {"attribute": "name", "column": "x"}})
    with pytest.raises(QualityRuleError, match="does not fit check kind"):
        GovRule.from_json(
            {"checkKind": "ATTRIBUTE_PRESENT", "dimension": "UNIQUENESS", "params": {"attribute": "name"}}
        )


@pytest.mark.covers("aurelius_atlas_quality.governance.GovRule.from_json", rules=["GQ-02"])
def test__an_any_of_that_is_not_a_list_raises() -> None:
    """The legacy OR list must be a list of names; a bare string is a shape error, not a name."""
    with pytest.raises(QualityRuleError, match="anyOf must be a list"):
        GovRule.from_json({"checkKind": "ATTRIBUTE_PRESENT", "params": {"attribute": "name", "anyOf": "parentEntity"}})


@pytest.mark.covers("aurelius_atlas_quality.governance.GovRule.from_json", rules=["GQ-03"])
def test__the_governance_vocabulary_holds_two_presence_rows() -> None:
    """Two kinds, both COMPLETENESS, both with required attribute and optional anyOf — the KindSpec shape."""
    assert set(GOV_KINDS) == {GovCheckKind.ATTRIBUTE_PRESENT, GovCheckKind.ATTRIBUTE_NOT_EMPTY}
    for kind, spec in GOV_KINDS.items():
        assert spec.dimension is Dimension.COMPLETENESS, kind
        assert spec.required == frozenset({"attribute"}), kind
        assert spec.optional == frozenset({"anyOf"}), kind
        assert spec.reason, kind


@pytest.mark.covers("aurelius_atlas_quality.governance.evaluate_gov_entity", rules=["GQ-04"])
def test__attribute_present_passes_on_a_value_even_an_empty_one() -> None:
    """Completeness's posture: a present value passes, even the empty string or an empty list."""
    assert evaluate_gov_entity(rule(), {"name": "Finance"}).compliant
    assert evaluate_gov_entity(rule(), {"name": ""}).compliant
    assert evaluate_gov_entity(rule(), {"name": []}).compliant
    assert evaluate_gov_entity(rule(), {"name": False}).compliant
    assert not evaluate_gov_entity(rule(), {"name": None}).compliant
    assert not evaluate_gov_entity(rule(attribute="definition"), {"name": "Finance"}).compliant


@pytest.mark.covers("aurelius_atlas_quality.governance.evaluate_gov_entity", rules=["GQ-04"])
def test__attribute_not_empty_demands_content() -> None:
    """Length's posture: a filled string or collection passes; an empty one, a null, or none fails."""
    not_empty = rule(GovCheckKind.ATTRIBUTE_NOT_EMPTY)
    assert evaluate_gov_entity(not_empty, {"name": "Finance"}).compliant
    assert evaluate_gov_entity(not_empty, {"name": ["x"]}).compliant
    assert evaluate_gov_entity(not_empty, {"name": 0}).compliant  # a present non-collection is content
    assert not evaluate_gov_entity(not_empty, {"name": ""}).compliant
    assert not evaluate_gov_entity(not_empty, {"name": []}).compliant
    assert not evaluate_gov_entity(not_empty, {"name": None}).compliant


@pytest.mark.covers("aurelius_atlas_quality.governance.evaluate_gov_entity", rules=["GQ-05"])
def test__an_attribute_the_record_lacks_fails_and_never_raises() -> None:
    """The legacy scored a missing column zero; an editor draft is always missing something."""
    verdict = evaluate_gov_entity(rule(), {})
    assert not verdict.compliant
    assert verdict.message  # the reason line answers, not an exception


@pytest.mark.covers("aurelius_atlas_quality.governance.evaluate_gov_entity", rules=["GQ-06"])
def test__any_of_passes_when_one_of_the_attributes_passes() -> None:
    """The legacy '|' pair: one pass over the attribute and the anyOf list makes the record compliant."""
    pair = rule(attribute="dataDomain", any_of=["parentEntity"])
    assert evaluate_gov_entity(pair, {"parentEntity": ["p-1"]}).compliant
    assert evaluate_gov_entity(pair, {"dataDomain": "d", "parentEntity": None}).compliant
    assert not evaluate_gov_entity(pair, {"dataDomain": None, "parentEntity": None}).compliant


@pytest.mark.covers("aurelius_atlas_quality.governance.evaluate_gov_entity", rules=["GQ-06"])
def test__the_verdict_shows_the_rule_own_message_or_the_kind_reason() -> None:
    """The rule's stored sentence answers for its verdict; the kind's reason line is the fallback."""
    with_messages = rule(
        compliantMessage="This entity has a name",
        nonCompliantMessage="This entity should have a name",
    )
    assert evaluate_gov_entity(with_messages, {"name": "x"}).message == "This entity has a name"
    assert evaluate_gov_entity(with_messages, {}).message == "This entity should have a name"

    bare = rule()
    assert evaluate_gov_entity(bare, {"name": "x"}).message == GOV_KINDS[GovCheckKind.ATTRIBUTE_PRESENT].reason
    assert evaluate_gov_entity(bare, {}).message == GOV_KINDS[GovCheckKind.ATTRIBUTE_PRESENT].reason
