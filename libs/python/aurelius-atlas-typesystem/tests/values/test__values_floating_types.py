"""``float`` and ``double`` (VAL-05, VAL-15).

Read from ``TestAtlasFloatType``, ``TestAtlasDoubleType`` and ``TestAtlasBuiltInTypesFloatDouble`` of Atlas
2.4.0, the Java values held as DD-040 says.
"""

import math
from decimal import Decimal

import pytest
from aurelius_atlas_typesystem.builtin import DoubleType, FloatType
from aurelius_atlas_typesystem.java import (
    BYTE_MAX,
    BYTE_MIN,
    DOUBLE_MAX,
    DOUBLE_MIN,
    FLOAT_MAX,
    FLOAT_MIN,
    INT_MAX,
    INT_MIN,
    LONG_MAX,
    LONG_MIN,
)

ONES = [1, 1, 1, 1, 1.0, 1.0, 1, Decimal(1), "1"]
"""``Byte``, ``Short``, ``Integer``, ``Long``, ``Float``, ``Double``, ``BigInteger``, ``BigDecimal`` 1 and ``"1"``."""
MINUS_ONES = [-1, -1, -1, -1, -1.0, -1.0, -1, Decimal(-1), "-1"]
M = "aurelius_atlas_typesystem.builtin.floating_type.FloatingType"
TEXT_INVALID = ["", "12ab", "abcd", "-12ab", True]


@pytest.mark.covers(
    f"{M}.create_default_value", f"{M}.is_valid_value", f"{M}.get_normalized_value", rules=["VAL-05", "VAL-15"]
)
def test__float_holds_numbers_within_float_max_as_32_bit_values() -> None:
    """``TestAtlasFloatType``: ``Double.MAX_VALUE`` and the infinities are invalid; ``Long.MAX_VALUE`` is not."""
    floats = FloatType()
    limits = [BYTE_MIN, BYTE_MAX, INT_MIN, INT_MAX, LONG_MIN, LONG_MAX, FLOAT_MIN, FLOAT_MAX, DOUBLE_MIN, -FLOAT_MAX]

    assert floats.create_default_value() == 0.0
    assert [floats.get_normalized_value(value) for value in ONES] == [1.0] * len(ONES)
    assert [floats.get_normalized_value(value) for value in MINUS_ONES] == [-1.0] * len(MINUS_ONES)
    assert all(floats.is_valid_value(value) for value in [None, *limits])
    assert floats.get_normalized_value(INT_MAX) == 2147483600.0
    assert floats.get_normalized_value(DOUBLE_MIN) == 0.0
    for value in [*TEXT_INVALID, FLOAT_MAX * 2, -FLOAT_MAX * 2, DOUBLE_MAX, -DOUBLE_MAX, math.nan, "1e39"]:
        assert not floats.is_valid_value(value), value


@pytest.mark.covers(f"{M}.get_normalized_value", rules=["VAL-05"])
def test__float_keeps_the_shortest_decimal_and_reads_java_number_text() -> None:
    """``Float.valueOf``: ``0.1`` stays ``0.1``; NaN text is a value; decimals beyond a double are invalid (DV-11)."""
    floats = FloatType()

    assert (floats.get_normalized_value(Decimal("0.1")), floats.get_normalized_value("1.5f")) == (0.1, 1.5)
    assert math.isnan(floats.get_normalized_value("NaN") or 0.0)
    assert floats.get_normalized_value(Decimal("3.5E+38")) is None
    assert floats.get_normalized_value(Decimal("1E+400")) is None
    assert floats.get_normalized_value(10**400) is None


@pytest.mark.covers(
    f"{M}.create_default_value", f"{M}.is_valid_value", f"{M}.get_normalized_value", rules=["VAL-05", "VAL-15"]
)
def test__double_holds_numbers_within_double_max() -> None:
    """``TestAtlasDoubleType``: every limit is valid; twice ``Double.MAX_VALUE``, an infinity, is not."""
    doubles = DoubleType()
    limits = [LONG_MIN, LONG_MAX, FLOAT_MIN, FLOAT_MAX, DOUBLE_MIN, DOUBLE_MAX, -DOUBLE_MAX, -FLOAT_MAX]

    assert doubles.create_default_value() == 0.0
    assert [doubles.get_normalized_value(value) for value in ONES] == [1.0] * len(ONES)
    assert [doubles.get_normalized_value(value) for value in MINUS_ONES] == [-1.0] * len(MINUS_ONES)
    assert [doubles.get_normalized_value(value) for value in limits] == [float(value) for value in limits]
    for value in [*TEXT_INVALID, math.inf, -math.inf, Decimal("2E+308"), 10**400, "1e400"]:
        assert not doubles.is_valid_value(value), value
    assert math.isnan(doubles.get_normalized_value(math.nan) or 0.0)


@pytest.mark.covers(f"{M}.are_equal_values", rules=["VAL-05"])
def test__floating_values_are_equal_within_epsilon() -> None:
    """``areEqualValues``: within 1e-8 after normalising; ``TestAtlasBuiltInTypesFloatDouble``."""
    floats, doubles = FloatType(), DoubleType()

    assert floats.are_equal_values(Decimal("0.1"), "0.1", None)
    assert doubles.are_equal_values(1.0, 1.0 + 1e-9, None)
    assert not doubles.are_equal_values(1.0, 1.0 + 1e-7, None)
    assert floats.are_equal_values(None, None, None)
    assert not floats.are_equal_values(None, 1, None)
    assert not doubles.are_equal_values("x", 1, None)
