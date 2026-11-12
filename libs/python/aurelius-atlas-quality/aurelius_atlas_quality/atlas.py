"""The Atlas glue: rules read from stored entities, results written as score documents.

This module converts; it holds no I/O. :func:`rule_from_atlas_attributes` reads a stored
``m4i_data_quality`` rule's attributes into a :class:`~aurelius_atlas_quality.rule.DqRule`,
:func:`rule_from_gov_attributes` reads a stored ``m4i_gov_data_quality`` rule's attributes into a
:class:`~aurelius_atlas_quality.governance.GovRule`, and :func:`result_documents` renders a run's
results as the documents a scanner writes to the store (DQ-07, DQ-08, GQ-07).
"""

import re
from collections.abc import Mapping, Sequence
from typing import Any

from aurelius_atlas_quality.evaluate import RuleResult
from aurelius_atlas_quality.governance import GovCheckKind, GovRule
from aurelius_atlas_quality.rule import CheckKind, DqRule, QualityRuleError
from aurelius_atlas_quality.score import QualitySummary

RULE_TYPE_NAME = "m4i_data_quality"
"""The Atlas entity type that carries a data-quality rule."""

GOV_RULE_TYPE_NAME = "m4i_gov_data_quality"
"""The Atlas entity type that carries a governance-quality rule (GQ-07)."""

SCORE_TYPE_NAME = "m4i_dq_score"
"""The document type a scanner writes for one rule's score over one dataset."""

ATLAS_TO_KIND: Mapping[tuple[str, str], CheckKind] = {
    ("attribute", "NOTNULL"): CheckKind.COLUMN_NOT_NULL_RATIO,
    ("attribute", "UNIQUE"): CheckKind.COLUMN_UNIQUE_RATIO,
    ("attribute", "REGEX"): CheckKind.COLUMN_MATCHES_REGEX,
    ("attribute", "ENUM"): CheckKind.COLUMN_IN_SET,
}
"""The legacy rule shapes this port reads: ``dataqualitytype`` and ``dataqualityoperator`` to a kind.

A rule stored by the legacy application carries that pair. A rule of the new vocabulary names its
kind under ``dqcheckkind`` instead, and has no legacy twin.
"""


def rule_from_atlas_attributes(attributes: Mapping[str, Any]) -> DqRule:
    """Build a rule from the attributes of an ``m4i_data_quality`` entity (DQ-07).

    ``attributes`` may carry the entity's ``guid``; it travels onto the rule and onto its documents.
    The attributes are read under the legacy names — ``name``, ``dataqualityruledimension",
    ``dataqualitytype``, ``dataqualityoperator``, ``columnname``, ``regularexpression``,
    ``allowedvalues``, ``threshold`` — and under the new names ``dqcheckkind``, ``dqcolumn``, and the
    ``dq``-prefixed parameters. Each value is read bare or as the webapp's ``{"raw": ...}`` wrapper.
    A legacy pair maps through :data:`ATLAS_TO_KIND` and takes its parameters from the legacy
    attributes; a rule of the vocabulary names its kind and parameters directly.

    Raises:
        aurelius_atlas_quality.rule.QualityRuleError: the entity names no kind this port knows, or a
            parameter is missing. The scanner records such a rule as ERROR — the legacy-expression case.
    """
    plain = {key: _raw(value) for key, value in attributes.items()}
    if plain.get("dqcheckkind"):
        return _rule_of_vocabulary(plain)
    return _rule_of_legacy(plain)


def _rule_of_vocabulary(plain: Mapping[str, Any]) -> DqRule:
    params: dict[str, Any] = {"column": plain.get("dqcolumn") or plain.get("columnname")}
    for name in (
        "pattern",
        "values",
        "columns",
        "otherColumn",
        "type",
        "min",
        "max",
        "maxAgeHours",
        "minColumns",
    ):
        if plain.get(f"dq{name}") is not None:
            params[name] = plain[f"dq{name}"]
    return _parse(plain, plain["dqcheckkind"], params)


_UNKNOWN_PAIR_ERROR = "the rule pair {pair} is not in the vocabulary; known pairs: {known}"


def _rule_of_legacy(plain: Mapping[str, Any]) -> DqRule:
    pair = (str(plain.get("dataqualitytype") or ""), str(plain.get("dataqualityoperator") or ""))
    kind = ATLAS_TO_KIND.get(pair)
    if kind is None:
        known = ", ".join(sorted("/".join(parts) for parts in ATLAS_TO_KIND))
        raise QualityRuleError(_UNKNOWN_PAIR_ERROR.format(pair="/".join(pair), known=known))
    params: dict[str, Any] = {"column": plain.get("columnname") or plain.get("dqcolumn")}
    if kind is CheckKind.COLUMN_MATCHES_REGEX:
        params["pattern"] = plain.get("regularexpression")
    if kind is CheckKind.COLUMN_IN_SET:
        params["values"] = _split(plain.get("allowedvalues"))
    return _parse(plain, kind.value, params)


def _parse(plain: Mapping[str, Any], kind: str, params: Mapping[str, Any]) -> DqRule:
    return DqRule.from_json(
        {
            "guid": plain.get("guid"),
            "name": plain.get("name", ""),
            "checkKind": kind,
            "dimension": plain.get("dataqualityruledimension"),
            "params": {k: v for k, v in params.items() if v is not None},
            "threshold": plain.get("threshold", 1.0),
        }
    )


_GOV_NO_KIND_ERROR = "the rule names no 'dqcheckkind': a stored expression rule needs re-authoring (DV-146)"

_GOV_FORMS = {
    GovCheckKind.ATTRIBUTE_PRESENT: re.compile(r"\s*completeness\(\s*'([^']+)'\s*\)\s*"),
    GovCheckKind.ATTRIBUTE_NOT_EMPTY: re.compile(r"\s*length\(\s*'([^']+)'\s*,\s*1\s*\)\s*"),
}
"""The corpus's two expression forms and the kinds they read as: not null, at least one (ASG-02, DD-533)."""


def gov_expression_params(expression: Any) -> tuple[GovCheckKind, str, list[str]]:  # noqa: ANN401 - a stored value
    """The kind, attribute and ``anyOf`` a stored governance expression reads as (ASG-02, DD-533).

    The expression is one part, or several joined by ``|``, each ``completeness('<name>')`` or each
    ``length('<name>', 1)``: the first part's name is the attribute, the others' the ``anyOf``. The text is
    matched whole, never evaluated.

    Raises:
        aurelius_atlas_quality.rule.QualityRuleError: no expression, or one of another shape, a mix of the two
            forms among them (DV-146).
    """
    parts = expression.split("|") if isinstance(expression, str) and expression.strip() else []
    for kind, form in _GOV_FORMS.items():
        matches = [form.fullmatch(part) for part in parts]
        if parts and all(matches):
            first, *others = [match.group(1) for match in matches if match is not None]
            return kind, first, others
    raise QualityRuleError(_GOV_NO_KIND_ERROR)


def rule_from_gov_attributes(attributes: Mapping[str, Any]) -> GovRule:
    """Build a governance rule from the attributes of an ``m4i_gov_data_quality`` entity (GQ-07).

    ``attributes`` may carry the entity's ``guid``; it travels onto the rule. The rule reads under the
    vocabulary names — ``dqcheckkind``, ``dqattribute``, ``dqanyOf`` — plus ``name``,
    ``qualityDimension``, and the rule's messages: ``compliantMessage`` and ``nonCompliantMessage``,
    the corpus's lowercase ``noncompliantMessage`` spelling read as the fallback. Each value is read
    bare or as the webapp's ``{"raw": ...}`` wrapper.

    A rule with no ``dqcheckkind`` — a stored expression rule, the legacy shape — reads from its
    ``expression`` when that is one of the corpus's two forms (:func:`gov_expression_params`, ASG-02,
    DD-533); any other expression raises: the caller records it, nothing executes it (DV-146).

    Raises:
        aurelius_atlas_quality.rule.QualityRuleError: the entity names no kind of the governance
            vocabulary nor an expression of the two forms, or a parameter is missing or malformed (GQ-02).
    """
    plain = {key: _raw(value) for key, value in attributes.items()}
    kind = plain.get("dqcheckkind")
    if kind:
        attribute, any_of = plain.get("dqattribute"), plain.get("dqanyOf")
    else:
        kind, attribute, any_of = gov_expression_params(plain.get("expression"))
    return GovRule.from_json(
        {
            "guid": plain.get("guid"),
            "name": plain.get("name", ""),
            "checkKind": kind,
            "dimension": plain.get("qualityDimension"),
            "params": {
                "attribute": attribute,
                **({"anyOf": any_of} if any_of is not None else {}),
            },
            "compliantMessage": plain.get("compliantMessage"),
            "nonCompliantMessage": plain.get("nonCompliantMessage") or plain.get("noncompliantMessage"),
        }
    )


def _split(raw: Any) -> Any:  # noqa: ANN401 - the attribute is a comma-separated string or a JSON list
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    return raw


def _raw(value: Any) -> Any:  # noqa: ANN401 - the store hands back {"raw": ...} wrappers or bare JSON
    """A stored attribute value as its bare JSON: the webapp reads attributes as ``{raw: ...}``."""
    if isinstance(value, Mapping) and set(value) == {"raw"}:
        return value["raw"]
    return value


def result_documents(
    results: Sequence[RuleResult],
    summary: QualitySummary,
    *,
    dataset_guid: str,
    run_id: str,
    run_at_ms: int,
) -> list[dict[str, Any]]:
    """The score documents of one run: one per scoring rule, plus the dataset's overall document (DQ-08).

    Each rule document carries the kind, dimension, score, verdict, and row counts with the run id, so
    the store can pick the newest row per rule. The overall document has ``ruleGuid`` null and the
    summary's per-dimension scores. Rules without a score (an empty frame) produce nothing (DD-369).
    """
    documents: list[dict[str, Any]] = [
        {
            "typeName": SCORE_TYPE_NAME,
            "ruleGuid": result.rule.guid,
            "datasetGuid": dataset_guid,
            "runId": run_id,
            "runAtMs": run_at_ms,
            "dimension": result.rule.dimension.value,
            "checkKind": result.rule.kind.value,
            "score": result.score,
            "passed": result.passed,
            "rowsChecked": result.rows_checked,
            "rowsFailed": result.rows_failed,
        }
        for result in results
        if result.score is not None
    ]
    if summary.score is not None:
        documents.append(
            {
                "typeName": SCORE_TYPE_NAME,
                "ruleGuid": None,
                "datasetGuid": dataset_guid,
                "runId": run_id,
                "runAtMs": run_at_ms,
                "dimension": None,
                "checkKind": None,
                "score": summary.score,
                "passed": None,
                "rowsChecked": sum(r.rows_checked for r in results),
                "rowsFailed": sum(r.rows_failed for r in results),
                "dimensions": {d.dimension.value: d.score for d in summary.dimensions},
            }
        )
    return documents
