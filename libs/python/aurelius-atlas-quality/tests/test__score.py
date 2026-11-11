"""The score rollup: per-dimension means and the overall score (DQ-06)."""

import polars as pl
import pytest
from aurelius_atlas_quality import Dimension, DqRule, QualitySummary, evaluate_rules, summarise
from aurelius_atlas_quality.rule import KINDS, CheckKind


def _rule(kind: CheckKind, **params: object) -> DqRule:
    return DqRule(name=kind.value, kind=kind, dimension=KINDS[kind].dimension, params=params)


def _summary(df: pl.DataFrame, *rules: DqRule) -> QualitySummary:
    return summarise(evaluate_rules(list(rules), df))


@pytest.mark.covers("aurelius_atlas_quality.score.summarise", rules=["DQ-06"])
def test__a_dimension_scores_the_mean_of_its_rules() -> None:
    """Two completeness rules of 0.5 and 1.0 make the dimension 0.75, counted as two rules (DQ-06)."""
    df = pl.DataFrame({"a": ["x", None], "b": ["y", "z"]})
    summary = _summary(
        df,
        _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="a"),
        _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="b"),
    )
    (completeness,) = summary.dimensions
    assert completeness.dimension is Dimension.COMPLETENESS
    assert (completeness.score, completeness.count) == (0.75, 2)
    assert summary.score == 0.75


@pytest.mark.covers("aurelius_atlas_quality.score.summarise", rules=["DQ-06"])
def test__the_overall_score_is_the_mean_of_the_dimensions() -> None:
    """Completeness 0.5 and uniqueness 1.0 give an overall of 0.75: each dimension weighs once."""
    df = pl.DataFrame({"a": ["x", None], "k": ["one", "two"]})
    summary = _summary(
        df,
        _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="a"),
        _rule(CheckKind.COLUMN_UNIQUE_RATIO, column="k"),
    )
    assert summary.score == 0.75
    assert [(d.dimension.value, d.score, d.count) for d in summary.dimensions] == [
        ("COMPLETENESS", 0.5, 1),
        ("UNIQUENESS", 1.0, 1),
    ]


@pytest.mark.covers("aurelius_atlas_quality.score.summarise", rules=["DQ-06"])
def test__many_rules_of_one_dimension_weigh_once_between_them() -> None:
    """Three completeness rules at 1.0 and one timeliness rule at 0.0 give 0.5, not 0.75."""
    df = pl.DataFrame({"a": ["x"], "b": ["y"], "c": ["z"], "t": ["2020-01-01"]})
    summary = _summary(
        df,
        _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="a"),
        _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="b"),
        _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="c"),
        _rule(CheckKind.ROW_FRESHNESS_MAX_AGE, column="t", maxAgeHours=1),
    )
    assert summary.score == 0.5


@pytest.mark.covers("aurelius_atlas_quality.score.summarise", rules=["DQ-06"])
def test__an_unmeasured_dimension_is_absent_and_never_zero() -> None:
    """A dimension no rule scored says nothing: it is missing, not present at zero (DD-369)."""
    summary = _summary(pl.DataFrame({"a": ["x"]}), _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="a"))
    assert [d.dimension for d in summary.dimensions] == [Dimension.COMPLETENESS]


@pytest.mark.covers("aurelius_atlas_quality.score.summarise", rules=["DQ-06"])
def test__nothing_scoring_gives_no_score_at_all() -> None:
    """An empty frame never scores, so the summary holds no number (DD-369)."""
    summary = _summary(pl.DataFrame({"a": []}), _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="a"))
    assert summary.score is None
    assert summary.dimensions == ()


@pytest.mark.covers("aurelius_atlas_quality.score.summarise", rules=["DQ-06"])
def test__dimensions_are_listed_in_a_stable_order() -> None:
    """The dimensions come out in a fixed order, whatever order the rules went in."""
    df = pl.DataFrame({"a": ["x"], "k": ["u"], "e": ["a@b.c"], "t": ["x"]})
    summary = _summary(
        df,
        _rule(CheckKind.COLUMN_MATCHES_REGEX, column="e", pattern="."),
        _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="a"),
        _rule(CheckKind.COLUMN_UNIQUE_RATIO, column="k"),
        _rule(CheckKind.COLUMN_EQUALS_COLUMN_RATIO, column="t", otherColumn="t"),
    )
    assert [d.dimension.value for d in summary.dimensions] == ["ACCURACY", "COMPLETENESS", "UNIQUENESS", "VALIDITY"]
