"""``biginteger`` and ``bigdecimal`` (VAL-06, VAL-07, VAL-15).

Read from ``TestAtlasBigIntegerType`` and ``TestAtlasBigDecimalType`` of Atlas 2.4.0, the Java values held as
DD-040 says.
"""

import math
from decimal import Decimal

import pytest
from aurelius_atlas_typesystem.builtin import BigDecimalType, BigIntegerType

ONES = [1, 1, 1, 1, 1.0, 1.0, 1, Decimal(1), "1"]
"""``Byte``, ``Short``, ``Integer``, ``Long``, ``Float``, ``Double``, ``BigInteger``, ``BigDecimal`` 1 and ``"1"``."""
MINUS_ONES = [-1, -1, -1, -1, -1.0, -1.0, -1, Decimal(-1), "-1"]
BIG_INTEGER = "aurelius_atlas_typesystem.builtin.big_integer_type.BigIntegerType"
BIG_DECIMAL = "aurelius_atlas_typesystem.builtin.big_decimal_type.BigDecimalType"
INVALID = ["", "12ab", "abcd", "-12ab", True]


@pytest.mark.covers(
    f"{BIG_INTEGER}.create_default_value",
    f"{BIG_INTEGER}.is_valid_value",
    f"{BIG_INTEGER}.get_normalized_value",
    rules=["VAL-06", "VAL-15"],
)
def test__big_integers_truncate_numbers_and_numeric_text() -> None:
    """Every 1 is 1, every -1 is -1; a decimal string is read as a ``BigDecimal`` and truncated."""
    big = BigIntegerType()

    assert big.create_default_value() == 0
    assert [big.get_normalized_value(value) for value in ONES] == [1] * len(ONES)
    assert [big.get_normalized_value(value) for value in MINUS_ONES] == [-1] * len(MINUS_ONES)
    assert (big.get_normalized_value("-2.9e1"), big.get_normalized_value(10**30)) == (-29, 10**30)
    assert big.get_normalized_value(1e30) == 2**63 - 1
    assert big.is_valid_value(None)
    assert not any(big.is_valid_value(value) for value in INVALID)


@pytest.mark.covers(
    f"{BIG_DECIMAL}.create_default_value",
    f"{BIG_DECIMAL}.is_valid_value",
    f"{BIG_DECIMAL}.get_normalized_value",
    rules=["VAL-07", "VAL-15"],
)
def test__big_decimals_keep_digits_and_take_other_numbers_through_double() -> None:
    """``TestAtlasBigDecimalType``: every 1 except a ``BigInteger`` normalises to ``BigDecimal.valueOf(1.0)``.

    A ``BigInteger`` 1 normalises to ``1``; JSON never gives one that small (DD-040), so the Python ``int`` 1 is
    an ``Integer`` and gives ``1.0``. A ``BigInteger`` beyond ``long`` keeps every digit.
    """
    big = BigDecimalType()
    ones = [1, 1, 1, 1, 1.0, 1.0, Decimal("1.0"), "1.0"]

    assert big.create_default_value() == Decimal(0)
    assert [str(big.get_normalized_value(value)) for value in ones] == ["1.0"] * len(ones)
    assert [str(big.get_normalized_value(-value if not isinstance(value, str) else "-1.0")) for value in ones] == [
        "-1.0"
    ] * len(ones)
    assert str(big.get_normalized_value(0)) == "0"
    assert str(big.get_normalized_value(0.0)) == "0.0"
    assert str(big.get_normalized_value(2**70)) == str(2**70)
    assert str(big.get_normalized_value(Decimal("1.10"))) == "1.10"
    assert (str(big.get_normalized_value(12345678)), str(big.get_normalized_value(10**7))) == ("12345678", "1.0E+7")
    assert big.is_valid_value(math.nan)
    assert all(big.is_valid_value(value) for value in (None, 1, 1.5, Decimal(1)))
    assert not any(big.is_valid_value(value) for value in INVALID)
    with pytest.raises(ValueError, match="NaN"):
        big.get_normalized_value(math.nan)
