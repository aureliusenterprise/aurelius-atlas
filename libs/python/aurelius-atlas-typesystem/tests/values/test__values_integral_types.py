"""``byte``, ``short``, ``int`` and ``long`` (VAL-04, VAL-15).

Read from ``TestAtlas{Byte,Short,Int,Long}Type`` of Atlas 2.4.0, the Java values held as DD-040 says.
"""

import math
from decimal import Decimal

import pytest
from aurelius_atlas_typesystem.builtin import ByteType, IntType, LongType, ShortType
from aurelius_atlas_typesystem.builtin.integral_type import IntegralType
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
    SHORT_MAX,
    SHORT_MIN,
)

ONES = [1, 1, 1, 1, 1.0, 1.0, 1, Decimal(1), "1"]
"""``Byte``, ``Short``, ``Integer``, ``Long``, ``Float``, ``Double``, ``BigInteger``, ``BigDecimal`` 1 and ``"1"``."""
MINUS_ONES = [-1, -1, -1, -1, -1.0, -1.0, -1, Decimal(-1), "-1"]
M = "aurelius_atlas_typesystem.builtin.integral_type.IntegralType"
COMMON_INVALID = ["", "12ab", "abcd", "-12ab", FLOAT_MAX, DOUBLE_MAX, -FLOAT_MAX, -DOUBLE_MAX, True]
CASES = [
    (ByteType(), [BYTE_MIN, BYTE_MAX], [BYTE_MIN - 1, BYTE_MAX + 1, SHORT_MIN, SHORT_MAX, INT_MIN, INT_MAX, LONG_MIN]),
    (ShortType(), [BYTE_MIN, SHORT_MIN, SHORT_MAX], [SHORT_MIN - 1, SHORT_MAX + 1, INT_MIN, INT_MAX, LONG_MAX]),
    (IntType(), [SHORT_MIN, INT_MIN, INT_MAX], [INT_MIN - 1, INT_MAX + 1, LONG_MIN, LONG_MAX]),
    (LongType(), [INT_MIN, LONG_MIN, LONG_MAX], [LONG_MIN - 1, LONG_MAX + 1]),
]


@pytest.mark.covers(
    f"{M}.create_default_value", f"{M}.is_valid_value", f"{M}.get_normalized_value", rules=["VAL-04", "VAL-15"]
)
@pytest.mark.parametrize(("integral", "limits", "out_of_range"), CASES, ids=["byte", "short", "int", "long"])
def test__numbers_in_range_and_digit_strings_normalise_to_their_integer(
    integral: IntegralType, limits: list[int], out_of_range: list[int]
) -> None:
    """The valid, limit, negative and invalid values of Atlas's tests; ``Float.MIN_VALUE`` truncates to 0."""
    assert integral.create_default_value() == 0
    assert [integral.get_normalized_value(value) for value in ONES] == [1] * len(ONES)
    assert [integral.get_normalized_value(value) for value in MINUS_ONES] == [-1] * len(MINUS_ONES)
    assert [integral.get_normalized_value(value) for value in limits] == limits
    for tiny in (FLOAT_MIN, DOUBLE_MIN, -FLOAT_MIN, -DOUBLE_MIN):
        assert integral.get_normalized_value(tiny) == 0
    assert integral.is_valid_value(None)
    assert integral.get_normalized_value(None) is None
    for value in [*COMMON_INVALID, *out_of_range]:
        assert not integral.is_valid_value(value), value
        assert integral.get_normalized_value(value) is None, value


@pytest.mark.covers(f"{M}.get_normalized_value", rules=["VAL-04"])
def test__a_decimal_truncates_toward_zero_after_the_range_check_on_its_integer_part() -> None:
    """``isValidRange`` checks ``toBigInteger``, then ``intValue`` narrows: 127.9 is a byte, 128.1 is not."""
    assert ByteType().get_normalized_value(Decimal("127.9")) == BYTE_MAX
    assert ByteType().get_normalized_value(Decimal("-128.9")) == BYTE_MIN
    assert ByteType().get_normalized_value(Decimal("128.1")) is None
    assert IntType().get_normalized_value(3.99) == 3
    assert IntType().get_normalized_value(math.nan) == 0


@pytest.mark.covers(f"{M}.get_normalized_value", rules=["VAL-04"])
def test__long_checks_a_double_exactly() -> None:
    """``AtlasLongType.isValidRange`` uses ``toBigInteger`` of ``Double.toString``, which fails on NaN.

    ``-2^63`` as a double reads as ``-9.223372036854776E18``, just outside the range, so Java rejects it too.
    """
    assert LongType().get_normalized_value(-1e18) == -(10**18)
    assert LongType().get_normalized_value(-(2.0**63)) is None
    assert LongType().get_normalized_value(2.0**63) is None
    with pytest.raises(ValueError, match="NaN"):
        LongType().get_normalized_value(math.nan)
