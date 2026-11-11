"""Data quality for Aurelius Atlas: the closed rule vocabularies, the row-mask engine and the score rollup.

A rule is data: a check kind from a closed vocabulary (:class:`CheckKind` for a dataset's rows,
:class:`GovCheckKind` for one catalogue record), a dimension (:class:`Dimension`), and parameters.
The library maps a dataset rule to a row mask over a polars DataFrame (:func:`evaluate`), scores it,
rolls results up per dimension (:func:`summarise`), answers a governance rule as a boolean verdict
over one record (:func:`evaluate_gov_entity`), and converts to and from the shapes the store holds
(:func:`rule_from_atlas_attributes`, :func:`rule_from_gov_attributes`, :func:`result_documents`).
"""

from aurelius_atlas_quality.atlas import (
    ATLAS_TO_KIND,
    GOV_RULE_TYPE_NAME,
    RULE_TYPE_NAME,
    SCORE_TYPE_NAME,
    result_documents,
    rule_from_atlas_attributes,
    rule_from_gov_attributes,
)
from aurelius_atlas_quality.evaluate import RuleResult, evaluate, evaluate_rules
from aurelius_atlas_quality.governance import (
    GOV_KINDS,
    GovCheckKind,
    GovRule,
    GovVerdict,
    evaluate_gov_entity,
)
from aurelius_atlas_quality.rule import (
    CASTABLE_TYPES,
    KINDS,
    CheckKind,
    Dimension,
    DqRule,
    KindSpec,
    QualityRuleError,
)
from aurelius_atlas_quality.score import DimensionScore, QualitySummary, summarise

__all__ = [
    "ATLAS_TO_KIND",
    "CASTABLE_TYPES",
    "GOV_KINDS",
    "GOV_RULE_TYPE_NAME",
    "KINDS",
    "RULE_TYPE_NAME",
    "SCORE_TYPE_NAME",
    "CheckKind",
    "Dimension",
    "DimensionScore",
    "DqRule",
    "GovCheckKind",
    "GovRule",
    "GovVerdict",
    "KindSpec",
    "QualityRuleError",
    "QualitySummary",
    "RuleResult",
    "evaluate",
    "evaluate_gov_entity",
    "evaluate_rules",
    "result_documents",
    "rule_from_atlas_attributes",
    "rule_from_gov_attributes",
    "summarise",
]
