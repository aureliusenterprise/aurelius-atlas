"""The rule vocabulary and its parse-time validation (DQ-01, DQ-02)."""

import pytest
from aurelius_atlas_quality import KINDS, CheckKind, Dimension, DqRule, KindSpec, QualityRuleError


def _blob(**overrides: object) -> dict:
    blob: dict = {
        "name": "email completeness",
        "checkKind": "COLUMN_NOT_NULL_RATIO",
        "params": {"column": "email"},
    }
    blob.update(overrides)
    return blob


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-01"])
def test__dq_rule_from_json_reads_a_completeness_rule() -> None:
    """A rule reads its kind, its own dimension, its parameters and the default threshold."""
    rule = DqRule.from_json(_blob())
    assert rule.kind is CheckKind.COLUMN_NOT_NULL_RATIO
    assert rule.dimension is Dimension.COMPLETENESS
    assert rule.params == {"column": "email"}
    assert rule.threshold == 1.0
    assert rule.guid is None


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-01"])
def test__dq_rule_from_json_keeps_the_guid_and_threshold_of_the_stored_rule() -> None:
    """A stored rule keeps its guid and its threshold; a fresh one has neither."""
    rule = DqRule.from_json(_blob(guid="3f1a", threshold=0.98))
    assert (rule.guid, rule.threshold) == ("3f1a", 0.98)


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-01"])
@pytest.mark.parametrize("dimension", ["completeness", "COMPLETENESS"])
def test__dq_rule_from_json_accepts_the_dimension_in_either_case(dimension: str) -> None:
    """The stored dimension is case-insensitive, like the kind."""
    assert DqRule.from_json(_blob(dimension=dimension)).dimension is Dimension.COMPLETENESS


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-01"])
def test__every_kind_of_the_vocabulary_names_its_dimension_and_parameters() -> None:
    """The vocabulary is closed: every kind carries a dimension, and its parameter shape."""
    assert len(KINDS) == 10
    for spec in KINDS.values():
        assert isinstance(spec, KindSpec)
        assert spec.required
        assert spec.required.isdisjoint(spec.optional)
        assert spec.reason
        assert isinstance(spec.dimension, Dimension)


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-02"])
def test__from_json_rejects_a_kind_outside_the_vocabulary() -> None:
    """An unknown kind is refused, and the error names the vocabulary the rule could have used."""
    with pytest.raises(QualityRuleError, match="unknown check kind"):
        DqRule.from_json(_blob(checkKind="PYTHON_EVAL"))
    with pytest.raises(QualityRuleError, match="COLUMN_WITHIN_RANGE"):
        DqRule.from_json(_blob(checkKind="PYTHON_EVAL"))


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-02"])
def test__from_json_rejects_a_missing_kind() -> None:
    """A blob without a kind is not a rule at all."""
    with pytest.raises(QualityRuleError, match="no 'checkKind'"):
        DqRule.from_json({"params": {"column": "email"}})


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-02"])
def test__from_json_rejects_a_dimension_the_kind_cannot_measure() -> None:
    """A dimension that disagrees with the kind is a mistake, not a choice (DQ-02)."""
    with pytest.raises(QualityRuleError, match="does not fit check kind"):
        DqRule.from_json(_blob(dimension="UNIQUENESS"))


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-02"])
def test__from_json_rejects_an_unknown_dimension() -> None:
    """A dimension outside the five named ones is refused like an unknown kind."""
    with pytest.raises(QualityRuleError, match="unknown dimension"):
        DqRule.from_json(_blob(dimension="BEAUTY"))


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-02"])
def test__from_json_rejects_a_missing_parameter_and_names_it() -> None:
    """A missing required parameter is refused at parse time, naming the parameter."""
    with pytest.raises(QualityRuleError, match=r"needs the parameters \['column'\]"):
        DqRule.from_json({"checkKind": "COLUMN_NOT_NULL_RATIO", "params": {}})


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-02"])
def test__from_json_rejects_a_parameter_the_kind_does_not_know() -> None:
    """An unknown parameter is refused too, so typos never pass silently."""
    with pytest.raises(QualityRuleError, match=r"has no parameters \['pattern'\]"):
        DqRule.from_json(_blob(params={"column": "email", "pattern": "x"}))


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-02"])
@pytest.mark.parametrize("threshold", ["-0.1", "1.5", "almost"])
def test__from_json_rejects_a_threshold_that_is_not_a_ratio(threshold: object) -> None:
    """The threshold must be a number between 0 and 1 (DQ-02)."""
    with pytest.raises(QualityRuleError, match="threshold"):
        DqRule.from_json(_blob(threshold=threshold))


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-02"])
def test__from_json_rejects_a_castable_type_outside_the_named_types() -> None:
    """A COLUMN_TYPE_CASTABLE rule must name a type the engine can cast to, at parse time."""
    with pytest.raises(QualityRuleError, match="unknown type"):
        DqRule.from_json(
            {
                "checkKind": "COLUMN_TYPE_CASTABLE",
                "params": {"column": "v", "type": "boolean"},
            }
        )


@pytest.mark.covers("aurelius_atlas_quality.rule.DqRule.from_json", rules=["DQ-01"])
def test__from_json_reads_a_row_rule_and_its_optional_parameter() -> None:
    """A row rule reads its column list and its optional minimum."""
    rule = DqRule.from_json(
        {
            "checkKind": "ROW_NOT_EMPTY",
            "params": {"columns": ["name", "definition"], "minColumns": 1},
        }
    )
    assert rule.kind is CheckKind.ROW_NOT_EMPTY
    assert rule.dimension is Dimension.COMPLETENESS
    assert rule.name == "ROW_NOT_EMPTY"
