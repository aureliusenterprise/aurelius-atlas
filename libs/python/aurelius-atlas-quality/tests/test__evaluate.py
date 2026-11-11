"""Evaluation: the row mask of every kind, the score, the verdict, the rejected rows (DQ-03..05)."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import polars as pl
import pytest
from aurelius_atlas_quality import Dimension, DqRule, evaluate, evaluate_rules
from aurelius_atlas_quality.checks import mask_for
from aurelius_atlas_quality.rule import CheckKind

AS_OF = datetime(2026, 11, 10, 12, tzinfo=UTC)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_BERLIN = ZoneInfo("Europe/Berlin")


def _rule(kind: CheckKind, **params: object) -> DqRule:
    return DqRule(name=kind.value, kind=kind, dimension=Dimension.COMPLETENESS, params=params)


def _accepted(kind: CheckKind, df: pl.DataFrame, **params: object) -> list[bool]:
    return mask_for(df, kind, params, AS_OF).to_list()


def _utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=UTC)


@pytest.mark.covers("aurelius_atlas_quality.evaluate.evaluate", rules=["DQ-04"])
def test__completeness_scores_the_share_of_filled_rows() -> None:
    """The completeness email rule: the score is the non-null share, the verdict reads the threshold."""
    df = pl.DataFrame({"email": ["a@b.c", None, "d@e.f", None, "g@h.i"]})
    rule = _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="email")
    result = evaluate(rule, df)
    assert result.score == pytest.approx(0.6)
    assert not result.passed
    assert (result.rows_checked, result.rows_failed) == (5, 2)

    lenient = DqRule.from_json({"checkKind": "COLUMN_NOT_NULL_RATIO", "params": {"column": "email"}, "threshold": 0.5})
    assert evaluate(lenient, df).passed


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__not_null_ratio_fills_the_mask() -> None:
    """The mask accepts filled rows and rejects nulls for the not-null ratio."""
    df = pl.DataFrame({"email": ["a", None]})
    assert _accepted(CheckKind.COLUMN_NOT_NULL_RATIO, df, column="email") == [True, False]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__row_not_empty_counts_the_filled_columns_of_each_row() -> None:
    """A row passes when enough of its columns are filled; minColumns lowers the bar."""
    df = pl.DataFrame({"name": ["a", None, "c"], "definition": ["d", "e", None]})
    assert _accepted(CheckKind.ROW_NOT_EMPTY, df, columns=["name", "definition"]) == [True, False, False]
    assert _accepted(CheckKind.ROW_NOT_EMPTY, df, columns=["name", "definition"], minColumns=1) == [True, True, True]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__unique_accepts_the_first_value_and_rejects_its_repeats() -> None:
    """The first copy of a value passes, later copies fail, nulls stay accepted."""
    df = pl.DataFrame({"email": ["a@b.c", "x@y.z", "a@b.c", None, None]})
    assert _accepted(CheckKind.COLUMN_UNIQUE_RATIO, df, column="email") == [True, True, False, True, True]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__composite_unique_rejects_the_repeat_of_a_whole_row() -> None:
    """Uniqueness over a column pair fails only when the whole row repeats."""
    df = pl.DataFrame({"a": ["x", "x", "y", None], "b": ["1", "1", "1", "1"]})
    assert _accepted(CheckKind.COLUMN_COMPOSITE_UNIQUE, df, columns=["a", "b"]) == [True, False, True, True]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__regex_accepts_a_match_and_a_null_and_rejects_the_rest() -> None:
    """A matching value and a null pass; text that does not match fails."""
    df = pl.DataFrame({"email": ["a@b.c", "nope", None, "@b.c"]})
    assert _accepted(CheckKind.COLUMN_MATCHES_REGEX, df, column="email", pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$") == [
        True,
        False,
        True,
        False,
    ]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__in_set_reads_a_number_or_a_text_column_against_the_allowed_values() -> None:
    """The set compares as text, so a number column matches number-valued allowed values."""
    df = pl.DataFrame({"eur": [1, 2, 3, None], "cur": ["EUR", "USD", None, "GBP"]})
    assert _accepted(CheckKind.COLUMN_IN_SET, df, column="eur", values=[1, 2]) == [True, True, False, True]
    assert _accepted(CheckKind.COLUMN_IN_SET, df, column="cur", values=["EUR", "USD"]) == [True, True, True, False]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__castable_judges_each_value_as_the_named_type() -> None:
    """The same text column passes or fails per named type: int, float, or date."""
    df = pl.DataFrame({"v": ["123", "12.5", "x", None, "2026-01-02"]})
    assert _accepted(CheckKind.COLUMN_TYPE_CASTABLE, df, column="v", type="int") == [True, False, False, True, False]
    assert _accepted(CheckKind.COLUMN_TYPE_CASTABLE, df, column="v", type="float") == [True, True, False, True, False]
    assert _accepted(CheckKind.COLUMN_TYPE_CASTABLE, df, column="v", type="date") == [False, False, False, True, True]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__castable_accepts_a_numbered_number_and_rejects_the_text_that_is_not_one() -> None:
    """A real number column casts by kind; a text column casts only where the text is a number."""
    df = pl.DataFrame({"n": [1.0, 2.5], "t": ["42", "no"]})
    assert _accepted(CheckKind.COLUMN_TYPE_CASTABLE, df, column="n", type="int") == [False, False]
    assert _accepted(CheckKind.COLUMN_TYPE_CASTABLE, df, column="n", type="float") == [True, True]
    assert _accepted(CheckKind.COLUMN_TYPE_CASTABLE, df, column="t", type="int") == [True, False]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__equals_column_compares_one_column_with_another() -> None:
    """A row passes when the two columns hold the same value; a null in either is accepted."""
    df = pl.DataFrame({"a": ["x", "y", None, "z"], "b": ["x", "Y", "q", None]})
    assert _accepted(CheckKind.COLUMN_EQUALS_COLUMN_RATIO, df, column="a", otherColumn="b") == [
        True,
        False,
        True,
        False,
    ]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__within_range_reads_a_number_and_a_text_number_and_fails_text_that_is_not_one() -> None:
    """Range checking casts to number first, so a text number is judged on its value."""
    numbers = pl.DataFrame({"amount": [10.0, -1.0, None]})
    assert _accepted(CheckKind.COLUMN_WITHIN_RANGE, numbers, column="amount", min=0, max=10) == [
        True,
        False,
        True,
    ]
    text = pl.DataFrame({"amount": ["5", "big"]})
    assert _accepted(CheckKind.COLUMN_WITHIN_RANGE, text, column="amount", min=0, max=10) == [True, False]


def _epoch_ms(times: list[datetime]) -> pl.Series:
    """The times as epoch milliseconds, the shape an Atlas export gives (UTC-stamped, tz-free)."""
    return pl.Series("ts", [int((t - _EPOCH).total_seconds() * 1000) for t in times], dtype=pl.Int64)


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
@pytest.mark.parametrize(
    "column",
    [
        _epoch_ms([_utc(10, 3), _utc(10, 11, 30)]),  # epoch ms (Atlas's shape)
        pl.Series("ts", ["2026-11-10T03:00:00", "2026-11-10T11:30:00"]),  # text, read as UTC
        pl.Series("ts", [_utc(10, 3), _utc(10, 11, 30)]),  # datetime
        pl.Series("ts", [_utc(10, 3).astimezone(_BERLIN), _utc(10, 11, 30).astimezone(_BERLIN)]),  # zoned
    ],
    ids=["epoch-ms", "text", "datetime", "zoned"],
)
def test__freshness_measures_the_age_of_a_row_in_any_time_shape(column: pl.Series) -> None:
    """Rows older than the allowed age fail; rows within it pass — in every time shape the source gives."""
    df = pl.DataFrame({"ts": column})
    accepted = _accepted(CheckKind.ROW_FRESHNESS_MAX_AGE, df, column="ts", maxAgeHours=8)
    assert accepted == [False, True]


@pytest.mark.covers("aurelius_atlas_quality.checks.mask_for", rules=["DQ-03"])
def test__freshness_accepts_a_null_and_rejects_a_column_that_holds_no_time() -> None:
    """A null row is accepted; a filled row whose column holds no time fails (DQ-03)."""
    df = pl.DataFrame({"ts": [1, None]})
    assert _accepted(CheckKind.ROW_FRESHNESS_MAX_AGE, df, column="ts", maxAgeHours=8) == [False, True]
    names = pl.DataFrame({"name": ["a", None]})
    assert _accepted(CheckKind.ROW_FRESHNESS_MAX_AGE, names, column="name", maxAgeHours=8) == [False, True]


@pytest.mark.covers("aurelius_atlas_quality.evaluate.evaluate", rules=["DQ-04"])
def test__an_empty_frame_has_no_score() -> None:
    """Nothing measured, nothing scored: the score is None, and the rule neither passes nor fails (DD-369)."""
    result = evaluate(_rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="a"), pl.DataFrame({"a": []}))
    assert (result.score, result.passed, result.rows_checked) == (None, False, 0)


@pytest.mark.covers("aurelius_atlas_quality.evaluate.evaluate", rules=["DQ-04"])
def test__a_missing_column_raises_for_the_caller_to_record() -> None:
    """The engine answers an unfit rule with a column error; the scanner records the rule as ERROR."""
    df = pl.DataFrame({"email": ["a"]})
    with pytest.raises(pl.exceptions.ColumnNotFoundError):
        evaluate(_rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="missing"), df)


@pytest.mark.covers("aurelius_atlas_quality.evaluate.evaluate", rules=["DQ-04"])
def test__failed_rows_hold_the_rejected_rows_capped_at_the_given_size() -> None:
    """Failed rows carry the rejected rows, capped at max_failed_rows; the count stays full."""
    df = pl.DataFrame({"email": [None] * 10})
    result = evaluate(_rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="email"), df, max_failed_rows=3)
    assert result.rows_failed == 10
    assert result.failed_rows.height == 3


@pytest.mark.covers("aurelius_atlas_quality.evaluate.evaluate_rules", rules=["DQ-05"])
def test__evaluate_rules_runs_each_rule_over_the_same_frame() -> None:
    """Every rule runs over the same frame and each keeps its own score (DQ-05)."""
    df = pl.DataFrame({"email": ["a@b.c", None], "name": ["x", "y"]})
    rules = [
        _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="email"),
        _rule(CheckKind.COLUMN_NOT_NULL_RATIO, column="name"),
    ]
    results = evaluate_rules(rules, df, as_of=AS_OF)
    assert [r.score for r in results] == [0.5, 1.0]
