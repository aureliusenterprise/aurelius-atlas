"""Data quality for Aurelius Atlas: the closed rule vocabulary, the row-mask engine and the score rollup.

A rule is data: a check kind from a closed vocabulary (:class:`CheckKind`), a dimension
(:class:`Dimension`), and parameters. The library maps a rule to a row mask over a polars DataFrame
(:func:`evaluate`), scores it, rolls results up per dimension (:func:`summarise`), and converts to and
from the shapes the store holds (:func:`rule_from_atlas_attributes`, :func:`result_documents`).
"""

from aurelius_atlas_quality.atlas import (
    ATLAS_TO_KIND,
    RULE_TYPE_NAME,
    SCORE_TYPE_NAME,
    result_documents,
    rule_from_atlas_attributes,
)
from aurelius_atlas_quality.evaluate import RuleResult, evaluate, evaluate_rules
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
    "KINDS",
    "RULE_TYPE_NAME",
    "SCORE_TYPE_NAME",
    "CheckKind",
    "Dimension",
    "DimensionScore",
    "DqRule",
    "KindSpec",
    "QualityRuleError",
    "QualitySummary",
    "RuleResult",
    "evaluate",
    "evaluate_rules",
    "result_documents",
    "rule_from_atlas_attributes",
    "summarise",
]
