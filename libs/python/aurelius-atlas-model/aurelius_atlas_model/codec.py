"""Atlas's JSON: numbers with a fraction read as decimals, decimals and dates written as Jackson writes them.

Atlas's REST mapper reads floats as ``BigDecimal`` (``USE_BIG_DECIMAL_FOR_FLOATS``) and writes a ``BigDecimal``
with its digits and a ``Date`` as epoch milliseconds (VAL-01, DD-039).
"""

import json
import math
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from aurelius_atlas_model.errors import java_string

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)

NOT_JSON_ERROR = "{type} is not a JSON value"


def loads(text: str | bytes) -> Any:  # noqa: ANN401 - any JSON value
    """Read JSON as Jackson does with ``USE_BIG_DECIMAL_FOR_FLOATS``: every float is a ``Decimal`` with its digits.

    Raises:
        ValueError: The text is not JSON.
    """
    return json.loads(text, parse_float=Decimal)


def dumps(value: Any) -> bytes:  # noqa: ANN401 - any value Atlas writes
    """Write ``value`` as Atlas's REST mapper does, compactly, in UTF-8 (VAL-01).

    A ``Decimal`` keeps its digits, a ``datetime`` is epoch milliseconds, NaN and infinities are strings, a
    model is its ``to_json``, and map keys are Java's text of the key.
    """
    return "".join(_write(value)).encode()


def _write(value: Any) -> list[str]:  # noqa: ANN401 - any value Atlas writes
    scalar = _scalar(value)
    if scalar is not None:
        return [scalar]
    if isinstance(value, BaseModel):
        return _write(value.model_dump(mode="python", by_alias=True, exclude_none=True))
    if isinstance(value, Mapping):
        return _object(value)
    if isinstance(value, list | tuple | set | frozenset):
        return _array(value)
    raise TypeError(NOT_JSON_ERROR.format(type=type(value).__name__))


def _scalar(value: Any) -> str | None:  # noqa: ANN401 - any value Atlas writes
    """The JSON text of a scalar, or None for anything else."""
    match value:
        case None | bool() | int() | str():
            return json.dumps(value, ensure_ascii=False)
        case float():
            return _float(value)
        case Decimal():
            return '"NaN"' if value.is_nan() else str(value)
        case datetime():
            return str((value - _EPOCH) // _MILLISECOND)
        case _:
            return None


def _object(value: Mapping[Any, Any]) -> list[str]:
    out = ["{"]
    for index, (key, item) in enumerate(value.items()):
        if index:
            out.append(",")
        out += [json.dumps(java_string(key), ensure_ascii=False), ":", *_write(item)]
    return [*out, "}"]


def _array(value: list[Any] | tuple[Any, ...] | set[Any] | frozenset[Any]) -> list[str]:
    out = ["["]
    for index, item in enumerate(value):
        if index:
            out.append(",")
        out += _write(item)
    return [*out, "]"]


def _float(value: float) -> str:
    """Jackson writes NaN and the infinities as strings (``WRITE_NAN_AS_STRINGS``)."""
    if math.isnan(value):
        return '"NaN"'
    if math.isinf(value):
        return '"Infinity"' if value > 0 else '"-Infinity"'
    return repr(value)
