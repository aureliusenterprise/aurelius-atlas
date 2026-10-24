"""Java's number conversions, on Java values held as Python values (DD-040).

A Java ``Integer``, ``Long`` or ``BigInteger`` is an ``int``, a ``BigDecimal`` a ``Decimal``, a ``Double`` a
``float`` and a ``Float`` a ``float`` holding the shortest decimal of its 32-bit value. A ``bool`` is a Java
``Boolean``, never a number. Each function is named after the Java method it ports.
"""

import math
import re
import struct
from datetime import timedelta, timezone, tzinfo
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from functools import cache
from typing import TypeGuard
from zoneinfo import ZoneInfo, available_timezones

from aurelius_atlas_model.errors import java_double_string

BYTE_MIN, BYTE_MAX = -(2**7), 2**7 - 1
SHORT_MIN, SHORT_MAX = -(2**15), 2**15 - 1
INT_MIN, INT_MAX = -(2**31), 2**31 - 1
LONG_MIN, LONG_MAX = -(2**63), 2**63 - 1
"""``Byte``, ``Short``, ``Integer`` and ``Long`` ``MIN_VALUE`` and ``MAX_VALUE``."""
FLOAT_MIN = 1.401298464324817e-45
"""``Float.MIN_VALUE``, the smallest positive ``float``, as a double."""
DOUBLE_MIN = 5e-324
"""``Double.MIN_VALUE``, the smallest positive ``double``."""
FLOAT_MAX = struct.unpack("<f", b"\xff\xff\x7f\x7f")[0]
"""``Float.MAX_VALUE``, exactly, as a double."""
DOUBLE_MAX = 1.7976931348623157e308
"""``Double.MAX_VALUE``."""

_INTEGER_TEXT = re.compile(r"[+-]?[0-9]+")
_BIG_DECIMAL_TEXT = re.compile(r"[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?")
_DOUBLE_TEXT = re.compile(
    r"[+-]?(NaN|Infinity|(([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?)|"
    r"(0[xX]([0-9a-fA-F]+\.?[0-9a-fA-F]*|\.[0-9a-fA-F]+)[pP][+-]?[0-9]+))[fFdD]?"
)

type JavaNumber = int | float | Decimal


def is_number(value: object) -> TypeGuard[JavaNumber]:
    """``value instanceof Number``: an ``int``, ``float`` or ``Decimal``, but not a ``bool``."""
    return isinstance(value, int | float | Decimal) and not isinstance(value, bool)


def is_long(value: object) -> TypeGuard[int]:
    """Whether ``value`` is an integer Jackson reads as an ``Integer`` or a ``Long``, not a ``BigInteger``."""
    return isinstance(value, int) and not isinstance(value, bool) and LONG_MIN <= value <= LONG_MAX


def long_value(value: JavaNumber) -> int:
    """``Number.longValue``: a ``BigInteger`` or ``BigDecimal`` wraps to 64 bits; a double saturates, NaN is 0."""
    if isinstance(value, float):
        if math.isnan(value):
            return 0
        if math.isinf(value):
            return LONG_MAX if value > 0 else LONG_MIN
        return max(LONG_MIN, min(LONG_MAX, int(value)))
    whole = int(value.to_integral_value(rounding=ROUND_DOWN)) if isinstance(value, Decimal) else value
    return (whole - LONG_MIN) % 2**64 + LONG_MIN


def to_big_integer(value: JavaNumber) -> int:
    """``AtlasBuiltInTypes.toBigInteger``: an integer as it is, a decimal or a double truncated toward zero.

    Raises:
        ValueError: A NaN or infinite double, which ``new BigDecimal(String)`` rejects.
    """
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(java_double_string(value))
        return int(Decimal(repr(value)).to_integral_value(rounding=ROUND_DOWN))
    if isinstance(value, Decimal):
        return int(value.to_integral_value(rounding=ROUND_DOWN))
    return value


def to_float32(value: float) -> float:
    """Round a double to Java's ``float`` and hold it as the shortest decimal of the 32-bit value (DD-040).

    A value beyond ``Float.MAX_VALUE`` becomes an infinity, as Java's narrowing conversion does.
    """
    if not math.isfinite(value):
        return value
    single = _single(value)
    if single is None:
        return math.copysign(math.inf, value)
    for digits in range(1, 10):
        shortest = float(f"{single:.{digits}g}")
        if _single(shortest) == single:
            return shortest
    return single  # pragma: no cover - nine significant digits always identify a float


def _single(value: float) -> float | None:
    """The 32-bit float nearest ``value``, or None beyond the 32-bit range."""
    try:
        return struct.unpack("<f", struct.pack("<f", value))[0]
    except OverflowError:
        return None


def float_value(value: JavaNumber) -> float:
    """``Number.floatValue``: the number as Java's ``float`` (an infinity beyond its range)."""
    return to_float32(double_value(value))


def double_value(value: JavaNumber) -> float:
    """``Number.doubleValue``: the number as Java's ``double`` (an infinity beyond its range)."""
    try:
        return float(value)
    except OverflowError:
        return math.inf if value > 0 else -math.inf


def parse_long(text: str) -> int | None:
    """``Long.valueOf(String)`` and its kin: an optional sign and ASCII digits, or None."""
    return int(text) if _INTEGER_TEXT.fullmatch(text) else None


def parse_double(text: str) -> float | None:
    """``Double.valueOf(String)``: trimmed; sign; decimal or hexadecimal; ``NaN``; ``Infinity``; a type suffix."""
    trimmed = text.strip(_JAVA_WHITESPACE)
    if not _DOUBLE_TEXT.fullmatch(trimmed):
        return None
    number = trimmed.rstrip("fFdD") if not trimmed.endswith(("NaN", "Infinity")) else trimmed
    if "x" in number.lower():
        return float.fromhex(number)
    return float(number.replace("Infinity", "inf"))


def parse_float(text: str) -> float | None:
    """``Float.valueOf(String)``: as ``parse_double``, rounded to Java's ``float``."""
    parsed = parse_double(text)
    return None if parsed is None else to_float32(parsed)


def parse_big_decimal(text: str) -> Decimal | None:
    """``new BigDecimal(String)``: sign, digits with an optional point, an optional exponent; else None."""
    if not _BIG_DECIMAL_TEXT.fullmatch(text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:  # pragma: no cover - the pattern admits only what Decimal reads
        return None


def big_decimal_value_of(value: float) -> Decimal:
    """``BigDecimal.valueOf(double)``: the decimal of ``Double.toString`` (``5`` becomes ``5.0``)."""
    return Decimal(java_double_string(value))


_JAVA_WHITESPACE = "".join(chr(code) for code in range(0x21))
"""What ``String.trim`` removes: every character up to the space."""


SHORT_ZONE_IDS = {
    "ACT": "Australia/Darwin",
    "AET": "Australia/Sydney",
    "AGT": "America/Argentina/Buenos_Aires",
    "ART": "Africa/Cairo",
    "AST": "America/Anchorage",
    "BET": "America/Sao_Paulo",
    "BST": "Asia/Dhaka",
    "CAT": "Africa/Harare",
    "CNT": "America/St_Johns",
    "CST": "America/Chicago",
    "CTT": "Asia/Shanghai",
    "EAT": "Africa/Addis_Ababa",
    "ECT": "Europe/Paris",
    "IET": "America/Indiana/Indianapolis",
    "IST": "Asia/Kolkata",
    "JST": "Asia/Tokyo",
    "MIT": "Pacific/Apia",
    "NET": "Asia/Yerevan",
    "NST": "Pacific/Auckland",
    "PLT": "Asia/Karachi",
    "PNT": "America/Phoenix",
    "PRT": "America/Puerto_Rico",
    "PST": "America/Los_Angeles",
    "SST": "Pacific/Guadalcanal",
    "VST": "Asia/Ho_Chi_Minh",
}
"""Java's legacy three-letter time zone ids that the tz database lacks, and the zones Java maps them to
(``ZoneId.SHORT_IDS``)."""

_CUSTOM_ZONE = re.compile(r"GMT([+-])([0-9]{1,2})(?::([0-9]{2}))?|GMT([+-])([0-9]{3,4})")
_MAX_OFFSET_HOURS = 23
_MAX_OFFSET_MINUTES = 59


def time_zone(zone_id: str) -> tzinfo | None:
    """``TimeZone.getTimeZone(id)``, or None for an id Java does not know (EVL-07, DD-042).

    Java knows tz database zones, its legacy short ids and custom ``GMT±h[h][[:]mm]`` offsets, and answers any other id
    with ``GMT``.
    """
    if zone_id in _tz_database():
        return ZoneInfo(zone_id)
    if zone_id in SHORT_ZONE_IDS:
        return ZoneInfo(SHORT_ZONE_IDS[zone_id])
    match = _CUSTOM_ZONE.fullmatch(zone_id)
    if match is None:
        return None
    if match[1] is not None:
        sign, hours, minutes = match[1], int(match[2]), int(match[3] or 0)
    else:
        sign, digits = match[4], int(match[5])
        hours, minutes = divmod(digits, 100)
    if hours > _MAX_OFFSET_HOURS or minutes > _MAX_OFFSET_MINUTES:
        return None
    offset = timedelta(hours=hours, minutes=minutes)
    return timezone(-offset if sign == "-" else offset)


def is_valid_time_zone(zone_id: str) -> bool:
    """``AtlasClassificationType.isValidTimeZone``: ``GMT``, or an id ``TimeZone`` resolves to another zone."""
    return zone_id == "GMT" or time_zone(zone_id) is not None


@cache
def _tz_database() -> frozenset[str]:
    return frozenset(available_timezones())
