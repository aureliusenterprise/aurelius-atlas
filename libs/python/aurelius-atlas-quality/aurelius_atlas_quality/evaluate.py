"""Evaluation: a rule over a DataFrame, into a score and the rows it rejects (DQ-04, DQ-05)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import polars as pl

from aurelius_atlas_quality.checks import mask_for
from aurelius_atlas_quality.rule import DqRule


@dataclass(frozen=True)
class RuleResult:
    """The outcome of one rule over one frame: its score, its verdict, and the rejected rows.

    ``score`` is the share of accepted rows, ``None`` for an empty frame — nothing was measured, and a
    score would be invented (the DD-369 posture: render nothing, not zero). ``failed_rows`` holds the
    rows the rule rejected, capped at ``max_failed_rows``, so a caller can bound what it stores.
    """

    rule: DqRule
    score: float | None
    passed: bool
    rows_checked: int
    rows_failed: int
    failed_rows: pl.DataFrame


def evaluate(
    rule: DqRule,
    df: pl.DataFrame,
    *,
    as_of: datetime | None = None,
    max_failed_rows: int = 100,
) -> RuleResult:
    """Run ``rule`` over ``df`` and return its score, verdict, and rejected rows (DQ-04).

    An empty frame has no score: the check runs over no rows, so the rule neither passes nor fails.

    Raises:
        polars.exceptions.ColumnNotFoundError: a parameter names a column the frame does not have.
            The caller decides — the scanner records the rule as ERROR, an API answers 400.
    """
    rows_checked = df.height
    if rows_checked == 0:
        return RuleResult(rule=rule, score=None, passed=False, rows_checked=0, rows_failed=0, failed_rows=df)
    accepted = mask_for(df, rule.kind, rule.params, as_of)
    rejected = df.filter(~accepted)
    rows_failed = rejected.height
    score = (rows_checked - rows_failed) / rows_checked
    return RuleResult(
        rule=rule,
        score=score,
        passed=score >= rule.threshold,
        rows_checked=rows_checked,
        rows_failed=rows_failed,
        failed_rows=rejected.head(max(0, max_failed_rows)),
    )


def evaluate_rules(
    rules: Sequence[DqRule],
    df: pl.DataFrame,
    *,
    as_of: datetime | None = None,
    max_failed_rows: int = 100,
) -> list[RuleResult]:
    """Run every rule over ``df`` in order (DQ-05). A column error still raises; see :func:`evaluate`."""
    return [evaluate(rule, df, as_of=as_of, max_failed_rows=max_failed_rows) for rule in rules]
