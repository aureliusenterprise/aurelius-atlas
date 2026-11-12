"""The Atlas glue: rules read from stored entities, results written as score documents (DQ-07, DQ-08)."""

import polars as pl
import pytest
from aurelius_atlas_quality import (
    SCORE_TYPE_NAME,
    CheckKind,
    Dimension,
    DqRule,
    GovCheckKind,
    QualityRuleError,
    evaluate_rules,
    result_documents,
    rule_from_atlas_attributes,
    rule_from_gov_attributes,
    summarise,
)
from aurelius_atlas_quality.atlas import gov_expression_params


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_atlas_attributes", rules=["DQ-07"])
def test__a_new_vocabulary_rule_reads_from_its_dq_attributes() -> None:
    """A rule entity of the new vocabulary names its kind and parameters under the dq attributes."""
    rule = rule_from_atlas_attributes(
        {
            "guid": "g-1",
            "name": {"raw": "email completeness"},
            "dataqualityruledimension": {"raw": "COMPLETENESS"},
            "dqcheckkind": "COLUMN_NOT_NULL_RATIO",
            "dqcolumn": "email",
            "threshold": 0.98,
        }
    )
    assert rule.guid == "g-1"
    assert rule.name == "email completeness"
    assert rule.kind is CheckKind.COLUMN_NOT_NULL_RATIO
    assert rule.dimension is Dimension.COMPLETENESS
    assert rule.params == {"column": "email"}
    assert rule.threshold == 0.98


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_atlas_attributes", rules=["DQ-07"])
@pytest.mark.parametrize(
    ("operator", "kind"),
    [("NOTNULL", CheckKind.COLUMN_NOT_NULL_RATIO), ("UNIQUE", CheckKind.COLUMN_UNIQUE_RATIO)],
)
def test__a_legacy_rule_pair_maps_to_its_kind_and_its_column(operator: str, kind: CheckKind) -> None:
    """The shapes the deployed corpus carries read without re-authoring (DV-146)."""
    rule = rule_from_atlas_attributes(
        {
            "guid": "g-2",
            "name": "email rule",
            "dataqualityruledimension": "COMPLETENESS" if operator == "NOTNULL" else "UNIQUENESS",
            "dataqualitytype": "attribute",
            "dataqualityoperator": operator,
            "columnname": "email",
        }
    )
    assert (rule.kind, rule.params) == (kind, {"column": "email"})


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_atlas_attributes", rules=["DQ-07"])
def test__a_legacy_regex_rule_reads_its_pattern_and_a_legacy_enum_rule_its_allowed_values() -> None:
    """The legacy REGEX pattern and the legacy comma-split ENUM list reach the new parameters."""
    regex_rule = rule_from_atlas_attributes(
        {
            "name": "email shape",
            "dataqualityruledimension": "VALIDITY",
            "dataqualitytype": "attribute",
            "dataqualityoperator": "REGEX",
            "columnname": "email",
            "regularexpression": r"^[^@]+@[^@]+\.[^@]+$",
        }
    )
    assert regex_rule.params == {"column": "email", "pattern": r"^[^@]+@[^@]+\.[^@]+$"}

    enum_rule = rule_from_atlas_attributes(
        {
            "name": "currency",
            "dataqualityruledimension": "VALIDITY",
            "dataqualitytype": "attribute",
            "dataqualityoperator": "ENUM",
            "columnname": "currency",
            "allowedvalues": "EUR, USD ,GBP,",
        }
    )
    assert enum_rule.params == {"column": "currency", "values": ["EUR", "USD", "GBP"]}


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_atlas_attributes", rules=["DQ-07"])
def test__a_rule_the_vocabulary_cannot_hold_raises_for_the_scanner_to_record() -> None:
    """The legacy free-text expression has no kind: the error names the rule's pair, for re-authoring."""
    with pytest.raises(QualityRuleError, match="attribute/FLINK"):
        rule_from_atlas_attributes(
            {"name": "old one", "dataqualitytype": "attribute", "dataqualityoperator": "FLINK"},
        )


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_atlas_attributes", rules=["DQ-07"])
def test__a_rule_missing_its_parameter_raises_through_the_vocabulary_check() -> None:
    """A new-vocabulary rule without its column fails the same parse-time check (DQ-02)."""
    with pytest.raises(QualityRuleError, match=r"needs the parameters \['column'\]"):
        rule_from_atlas_attributes(
            {"name": "no column", "dqcheckkind": "COLUMN_NOT_NULL_RATIO"},
        )


@pytest.mark.covers("aurelius_atlas_quality.atlas.result_documents", rules=["DQ-08"])
def test__a_run_writes_one_document_per_rule_and_the_overall_one() -> None:
    """The documents carry the score, the verdict, the row counts, and the ids a reader needs (DQ-08)."""
    rules = [
        DqRule(
            "email complete",
            CheckKind.COLUMN_NOT_NULL_RATIO,
            Dimension.COMPLETENESS,
            {"column": "email"},
            guid="g-1",
        ),
        DqRule(
            "email valid",
            CheckKind.COLUMN_IN_SET,
            Dimension.VALIDITY,
            {"column": "email", "values": ["a@b.c"]},
            guid="g-2",
        ),
    ]
    df = pl.DataFrame({"email": ["a@b.c", None]})
    results = evaluate_rules(rules, df)
    documents = result_documents(
        results, summarise(results), dataset_guid="ds-1", run_id="r-1", run_at_ms=1_700_000_000_000
    )

    rule_documents = [d for d in documents if d["ruleGuid"]]
    assert len(rule_documents) == 2
    complete = next(d for d in rule_documents if d["ruleGuid"] == "g-1")
    assert complete["typeName"] == SCORE_TYPE_NAME
    assert complete["datasetGuid"] == "ds-1"
    assert complete["runId"] == "r-1"
    assert complete["dimension"] == "COMPLETENESS"
    assert complete["checkKind"] == "COLUMN_NOT_NULL_RATIO"
    assert complete["score"] == 0.5
    assert complete["rowsChecked"] == 2
    assert complete["rowsFailed"] == 1
    assert complete["runAtMs"] == 1_700_000_000_000

    (overall,) = [d for d in documents if d["ruleGuid"] is None]
    assert overall["score"] == pytest.approx(0.75)
    assert overall["dimensions"] == {"COMPLETENESS": 0.5, "VALIDITY": 1.0}


@pytest.mark.covers("aurelius_atlas_quality.atlas.result_documents", rules=["DQ-08"])
def test__an_unscored_rule_writes_nothing() -> None:
    """An empty frame scores nothing and stores nothing: no rule row, and no overall row (DD-369)."""
    rules = [DqRule("a", CheckKind.COLUMN_NOT_NULL_RATIO, Dimension.COMPLETENESS, {"column": "a"})]
    results = evaluate_rules(rules, pl.DataFrame({"a": []}))
    documents = result_documents(results, summarise(results), dataset_guid="ds-1", run_id="r-1", run_at_ms=1)
    assert documents == []


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_gov_attributes", rules=["GQ-07"])
def test__a_gov_rule_reads_from_its_dq_attributes_and_its_messages() -> None:
    """A stored governance rule of the vocabulary reads bare or raw-wrapped, with both messages."""
    rule = rule_from_gov_attributes(
        {
            "guid": "gv-1",
            "name": {"raw": "Data domain has a name"},
            "qualityDimension": {"raw": "completeness"},
            "dqcheckkind": "ATTRIBUTE_NOT_EMPTY",
            "dqattribute": "name",
            "compliantMessage": "This data domain has a name",
            "noncompliantMessage": "This data domain should have a name",
        }
    )
    assert rule.guid == "gv-1"
    assert rule.name == "Data domain has a name"
    assert rule.kind is GovCheckKind.ATTRIBUTE_NOT_EMPTY
    assert rule.dimension is Dimension.COMPLETENESS  # the corpus's lowercase dimension reads upper
    assert (rule.attribute, rule.any_of) == ("name", ())
    assert rule.compliant_message == "This data domain has a name"
    assert rule.non_compliant_message == "This data domain should have a name"


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_gov_attributes", rules=["GQ-07"])
def test__a_gov_rule_reads_its_any_of_list_and_the_camel_message_spelling() -> None:
    """The one OR pair of the corpus reads, and the webapp's camelCase spelling works too."""
    rule = rule_from_gov_attributes(
        {
            "name": "domain or parent",
            "dqcheckkind": "ATTRIBUTE_PRESENT",
            "dqattribute": "dataDomain",
            "dqanyOf": ["parentEntity"],
            "nonCompliantMessage": "This entity needs a data domain or a parent entity",
        }
    )
    assert rule.any_of == ("parentEntity",)
    assert rule.non_compliant_message == "This entity needs a data domain or a parent entity"


@pytest.mark.covers("aurelius_atlas_quality.atlas.gov_expression_params", rules=["ASG-02"])
@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("completeness('name')", (GovCheckKind.ATTRIBUTE_PRESENT, "name", [])),
        ("length('datasets', 1)", (GovCheckKind.ATTRIBUTE_NOT_EMPTY, "datasets", [])),
        (
            "length('dataDomain', 1) | length('parentEntity', 1)",
            (GovCheckKind.ATTRIBUTE_NOT_EMPTY, "dataDomain", ["parentEntity"]),
        ),
        (" completeness( 'name' ) ", (GovCheckKind.ATTRIBUTE_PRESENT, "name", [])),
    ],
)
def test__an_expression_of_the_two_forms_reads_as_a_kind_an_attribute_and_any_of(
    expression: str, expected: tuple[GovCheckKind, str, list[str]]
) -> None:
    """Each form, and the corpus's ``|`` pair: the first part's name the attribute, the others' ``anyOf``."""
    assert gov_expression_params(expression) == expected


@pytest.mark.covers("aurelius_atlas_quality.atlas.gov_expression_params", rules=["ASG-02"])
@pytest.mark.parametrize(
    "expression",
    [
        None,
        "",
        "length('name', 2)",
        "completeness('name') | length('datasets', 1)",
        "uniqueness('qualifiedName')",
        "conditional_value('target_relationship_type', 'source_typename', {'m4i_field_assignment':'m4i_field'})",
        "completeness('name'); import os",
        "completeness('name') |",
    ],
)
def test__any_other_expression_reads_as_no_rule(expression: str | None) -> None:
    """Another count, a mix of the forms, another function, trailing code or an empty part: unread (DV-146)."""
    with pytest.raises(QualityRuleError, match="re-authoring"):
        gov_expression_params(expression)


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_gov_attributes", rules=["GQ-07", "ASG-02"])
def test__a_stored_expression_rule_reads_from_its_expression() -> None:
    """The legacy rule carries an expression and no dqcheckkind: its form gives the kind and attributes."""
    rule = rule_from_gov_attributes(
        {
            "guid": "gv-2",
            "name": "legacy domain",
            "expression": "length('dataDomain', 1) | length('parentEntity', 1)",
            "qualityDimension": "completeness",
            "nonCompliantMessage": "This data entity needs a data domain or a parent entity",
        }
    )
    assert (rule.kind, rule.attribute, rule.any_of) == (
        GovCheckKind.ATTRIBUTE_NOT_EMPTY,
        "dataDomain",
        ("parentEntity",),
    )
    assert rule.non_compliant_message == "This data entity needs a data domain or a parent entity"


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_gov_attributes", rules=["GQ-07", "ASG-02"])
def test__a_vocabulary_rule_ignores_its_expression() -> None:
    """With ``dqcheckkind`` the vocabulary attributes decide; an expression beside them is never read."""
    rule = rule_from_gov_attributes(
        {"dqcheckkind": "ATTRIBUTE_PRESENT", "dqattribute": "definition", "expression": "length('name', 1)"}
    )
    assert (rule.kind, rule.attribute) == (GovCheckKind.ATTRIBUTE_PRESENT, "definition")


@pytest.mark.covers("aurelius_atlas_quality.atlas.rule_from_gov_attributes", rules=["GQ-07"])
def test__a_stored_expression_rule_of_another_shape_raises() -> None:
    """An expression of neither form is never executed: the error names re-authoring (DV-146)."""
    with pytest.raises(QualityRuleError, match="re-authoring"):
        rule_from_gov_attributes({"name": "unique", "expression": "uniqueness('qualifiedName')"})
