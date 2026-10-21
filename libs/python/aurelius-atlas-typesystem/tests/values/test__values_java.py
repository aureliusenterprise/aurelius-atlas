"""Java's number conversions on Java values held as DD-040 says (VAL-04 to VAL-08)."""

import math
from decimal import Decimal

import pytest
from aurelius_atlas_typesystem import java
from aurelius_atlas_typesystem.java import DOUBLE_MAX, FLOAT_MAX, LONG_MAX, LONG_MIN

M = "aurelius_atlas_typesystem.java"


@pytest.mark.covers(f"{M}.is_number", f"{M}.is_long", rules=["VAL-04"])
def test__a_boolean_is_never_a_number_and_a_long_is_64_bits() -> None:
    """``instanceof Number`` excludes ``Boolean``; Jackson reads an integer beyond 64 bits as a ``BigInteger``."""
    assert [java.is_number(value) for value in (1, 1.5, Decimal(1), True, "1", None)] == [
        True,
        True,
        True,
        False,
        False,
        False,
    ]
    java_boolean = True

    assert java.is_long(LONG_MAX)
    assert not java.is_long(LONG_MAX + 1)
    assert not java.is_long(java_boolean)
    assert not java.is_long(1.0)


@pytest.mark.covers(f"{M}.long_value", rules=["VAL-04", "VAL-08"])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("3.7"), 3),
        (Decimal("-3.7"), -3),
        (-3.7, -3),
        (math.nan, 0),
        (math.inf, LONG_MAX),
        (-1e30, LONG_MIN),
        (2**64 + 5, 5),
        (Decimal(2**63), LONG_MIN),
    ],
)
def test__long_value_truncates_saturates_doubles_and_wraps_big_numbers(value: java.JavaNumber, expected: int) -> None:
    """``Number.longValue``: a double saturates, NaN is 0; a ``BigInteger`` or ``BigDecimal`` wraps to 64 bits."""
    assert java.long_value(value) == expected


@pytest.mark.covers(f"{M}.to_big_integer", rules=["VAL-04", "VAL-06"])
def test__to_big_integer_truncates_and_fails_on_nan() -> None:
    """``AtlasBuiltInTypes.toBigInteger``; ``new BigDecimal("NaN")`` throws."""
    assert (java.to_big_integer(Decimal("-3.9")), java.to_big_integer(2.5e10), java.to_big_integer(7)) == (
        -3,
        25000000000,
        7,
    )
    with pytest.raises(ValueError, match="NaN"):
        java.to_big_integer(math.nan)


@pytest.mark.covers(f"{M}.to_float32", f"{M}.float_value", f"{M}.double_value", rules=["VAL-05"])
def test__floats_are_32_bit_values_held_as_their_shortest_decimal() -> None:
    """``(float)`` narrowing: 0.1 stays ``0.1``; beyond ``Float.MAX_VALUE`` is an infinity."""
    assert (java.to_float32(0.1), java.to_float32(1 / 3), java.to_float32(FLOAT_MAX)) == (0.1, 0.33333334, 3.4028235e38)
    assert java.to_float32(1e39) == math.inf
    assert java.to_float32(-1e39) == -math.inf
    assert math.isnan(java.to_float32(math.nan))
    assert java.float_value(Decimal("0.1")) == 0.1
    assert java.double_value(10**400) == math.inf
    assert java.double_value(-(10**400)) == -math.inf
    assert java.double_value(Decimal("1.5")) == 1.5


@pytest.mark.covers(f"{M}.parse_long", rules=["VAL-04"])
@pytest.mark.parametrize(
    ("text", "expected"),
    [("12", 12), ("+12", 12), ("-0", 0), ("", None), ("1 2", None), (" 1", None), ("\u0661", None)],
)
def test__long_value_of_takes_a_sign_and_ascii_digits(text: str, expected: int | None) -> None:
    """``Long.valueOf(String)``: no spaces, no other digits."""
    assert java.parse_long(text) == expected


@pytest.mark.covers(f"{M}.parse_double", f"{M}.parse_float", rules=["VAL-05"])
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (" 1.5f ", 1.5),
        ("1e3", 1000.0),
        (".5D", 0.5),
        ("5.", 5.0),
        ("0x1.8p1", 3.0),
        ("-Infinity", -math.inf),
        ("1_0", None),
        ("inf", None),
        ("", None),
        ("abcd", None),
    ],
)
def test__double_value_of_reads_java_s_number_text(text: str, expected: float | None) -> None:
    """``Double.valueOf(String)``: trimmed, a suffix, hexadecimal; not Python's ``inf`` or underscores."""
    assert java.parse_double(text) == expected


@pytest.mark.covers(f"{M}.parse_double", f"{M}.parse_float", rules=["VAL-05"])
def test__float_value_of_rounds_to_32_bits() -> None:
    """``Float.valueOf``: NaN is a value; a number beyond the 32-bit range is an infinity."""
    assert java.parse_float("0.1") == 0.1
    assert math.isnan(java.parse_float("NaN") or 0.0)
    assert java.parse_float("1e39") == math.inf
    assert java.parse_float("x") is None
    assert java.parse_double(str(DOUBLE_MAX)) == DOUBLE_MAX


@pytest.mark.covers(f"{M}.parse_big_decimal", f"{M}.big_decimal_value_of", rules=["VAL-07"])
def test__big_decimals_keep_their_digits() -> None:
    """``new BigDecimal(String)`` keeps the scale; ``BigDecimal.valueOf(double)`` reads ``Double.toString``."""
    assert str(java.parse_big_decimal("1.10")) == "1.10"
    assert str(java.parse_big_decimal("-.5e3")) == "-5E+2"
    assert [java.parse_big_decimal(text) for text in ("NaN", "1_0", " 1", "")] == [None, None, None, None]
    assert [str(java.big_decimal_value_of(value)) for value in (5.0, 0.1, 1e7, -1.0)] == [
        "5.0",
        "0.1",
        "1.0E+7",
        "-1.0",
    ]
