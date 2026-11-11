"""The build side of the vocabulary: how each check kind masks a DataFrame (DQ-03)."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import polars as pl

from aurelius_atlas_quality.rule import CASTABLE_TYPES, CheckKind, QualityRuleError

__all__ = ["mask_for"]

_INT_DTYPES = frozenset({pl.Int64, pl.Int32, pl.Int16, pl.Int8, pl.UInt64, pl.UInt32, pl.UInt16, pl.UInt8})

_CASTS: Mapping[str, Any] = {
    "int": pl.Int64,
    "integer": pl.Int64,
    "long": pl.Int64,
    "float": pl.Float64,
    "double": pl.Float64,
    "date": pl.Date,
    "datetime": pl.Datetime("us"),
}
"""The type names a :attr:`CheckKind.COLUMN_TYPE_CASTABLE` rule may name, as polars data types."""


def _passing(col: pl.Expr, mask: pl.Expr) -> pl.Expr:
    """Accept a row the check cannot judge: a null holds no violation (DQ-03).

    A null mask over a filled value is a violation: the check could not make the value pass.
    """
    return mask.fill_null(value=False) | col.is_null()


def _matches_regex(_df: pl.DataFrame, params: Mapping[str, Any], _as_of: datetime) -> pl.Expr:
    column: str = params["column"]
    found = pl.col(column).cast(pl.String, strict=False).str.contains(params["pattern"])
    return _passing(pl.col(column), found)


def _in_set(_df: pl.DataFrame, params: Mapping[str, Any], _as_of: datetime) -> pl.Expr:
    """The rows whose value is one of the allowed ones.

    The column and the set both read as text, so a number column matches number values and a text
    column matches text values (DQ-03).
    """
    column = params["column"]
    values = [str(value) for value in params["values"]]
    return _passing(pl.col(column), pl.col(column).cast(pl.String, strict=False).is_in(values))


_UNKNOWN_CAST_ERROR = "unknown type {type!r}; the castable types are {types}"


def _castable(_df: pl.DataFrame, params: Mapping[str, Any], _as_of: datetime) -> pl.Expr:
    """The rows whose value reads as the named type.

    polars's strict-to-null string conversions are the judge, over the value cast to text. A value of
    the named type always reads back as itself.
    """
    column = params["column"]
    dtype = _cast_of(params["type"])
    text = pl.col(column).cast(pl.String, strict=False)
    if dtype in _INT_DTYPES:
        parsed = text.str.to_integer(strict=False)
    elif dtype in (pl.Float64, pl.Float32):
        parsed = text.cast(dtype, strict=False)  # polars parses float text on the cast, not on a parser
    elif dtype == pl.Date:
        parsed = text.str.to_date(strict=False)
    else:
        parsed = text.str.to_datetime(strict=False)
    return _passing(pl.col(column), parsed.is_not_null())


def _cast_of(type_name: str) -> pl.DataType:
    key = str(type_name).lower()
    if key not in CASTABLE_TYPES:
        raise QualityRuleError(_UNKNOWN_CAST_ERROR.format(type=type_name, types=sorted(CASTABLE_TYPES)))
    return _CASTS[key]


def _equals_column(_df: pl.DataFrame, params: Mapping[str, Any], _as_of: datetime) -> pl.Expr:
    left, right = params["column"], params["otherColumn"]
    return _passing(pl.col(left), pl.col(left) == pl.col(right))


def _within_range(_df: pl.DataFrame, params: Mapping[str, Any], _as_of: datetime) -> pl.Expr:
    column = params["column"]
    value = pl.col(column).cast(pl.Float64, strict=False)
    return _passing(pl.col(column), value.is_between(float(params["min"]), float(params["max"])))


def _row_not_empty(_df: pl.DataFrame, params: Mapping[str, Any], _as_of: datetime) -> pl.Expr:
    columns: list[str] = list(params["columns"])
    filled = pl.sum_horizontal(pl.col(columns).is_not_null())
    return filled >= int(params.get("minColumns", len(columns)))


def _unique(_df: pl.DataFrame, params: Mapping[str, Any], _as_of: datetime) -> pl.Expr:
    columns: list[str] = list(params["columns"])
    every_filled = pl.all_horizontal(pl.col(columns).is_not_null())
    first = pl.col(columns[0]).cum_count().over(columns)
    return ~(every_filled & (first > 1))


def _freshness(df: pl.DataFrame, params: Mapping[str, Any], as_of: datetime) -> pl.Expr:
    column = params["column"]
    max_age = pl.duration(hours=float(params["maxAgeHours"]))
    age = pl.lit(as_of, pl.Datetime("us")) - _as_datetime(pl.col(column), df.schema[column])
    return _passing(pl.col(column), age <= max_age)


def _as_datetime(col: pl.Expr, dtype: pl.DataType) -> pl.Expr:
    """A column as a naive UTC timestamp.

    A number reads as epoch milliseconds (Atlas's shape); a zoned datetime converts to UTC first. A
    naive datetime, a date or a text value reads as the time it is, already UTC. A column of no
    time-like type casts to nothing, so every filled row fails.
    """
    if isinstance(dtype, pl.Datetime):
        if dtype.time_zone:
            return col.dt.convert_time_zone("UTC").dt.replace_time_zone(None)
        return col
    if dtype == pl.Date:
        return col.cast(pl.Datetime("us"))
    if dtype in _INT_DTYPES:
        return pl.from_epoch(col, time_unit="ms")
    if dtype == pl.Utf8:
        return col.str.to_datetime(strict=False)
    return col.cast(pl.Datetime("us"), strict=False)


_BUILDERS: Mapping[CheckKind, Any] = {
    CheckKind.COLUMN_NOT_NULL_RATIO: lambda _df, params, _as_of: pl.col(params["column"]).is_not_null(),
    CheckKind.ROW_NOT_EMPTY: _row_not_empty,
    CheckKind.COLUMN_UNIQUE_RATIO: lambda _df, params, _as_of: _unique(_df, {"columns": [params["column"]]}, _as_of),
    CheckKind.COLUMN_COMPOSITE_UNIQUE: _unique,
    CheckKind.COLUMN_MATCHES_REGEX: _matches_regex,
    CheckKind.COLUMN_IN_SET: _in_set,
    CheckKind.COLUMN_TYPE_CASTABLE: _castable,
    CheckKind.COLUMN_EQUALS_COLUMN_RATIO: _equals_column,
    CheckKind.COLUMN_WITHIN_RANGE: _within_range,
    CheckKind.ROW_FRESHNESS_MAX_AGE: _freshness,
}


def mask_for(df: pl.DataFrame, kind: CheckKind, params: Mapping[str, Any], as_of: datetime | None = None) -> pl.Series:
    """The boolean mask of the rows the rule accepts, over ``df`` (DQ-03).

    ``as_of`` is the run time, in UTC: a naive value reads as UTC, and a zoned one converts. The
    freshness kind measures ages against it; the default is now.

    Raises:
        polars.exceptions.ColumnNotFoundError: a parameter names a column the frame does not have.
    """
    build = _BUILDERS[kind]
    moment = as_of or datetime.now(UTC)
    moment = moment.astimezone(UTC).replace(tzinfo=None) if moment.tzinfo else moment
    expr = build(df, params, moment)
    return df.select(expr.alias("__pass"))["__pass"]
