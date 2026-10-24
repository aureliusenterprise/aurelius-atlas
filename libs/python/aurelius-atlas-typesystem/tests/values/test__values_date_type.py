"""``date`` (VAL-08, VAL-15).

Read from ``TestAtlasDateType`` of Atlas 2.4.0 and ``AtlasBaseTypeDef``'s ``SERIALIZED_DATE_FORMAT_STR``.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from aurelius_atlas_typesystem.builtin import DateType
from aurelius_atlas_typesystem.builtin.date_type import EPOCH

ONES = [1, 1, 1, 1, 1.0, 1.0, 1, Decimal(1), "1"]
"""``Byte``, ``Short``, ``Integer``, ``Long``, ``Float``, ``Double``, ``BigInteger``, ``BigDecimal`` 1 and ``"1"``."""
MINUS_ONES = [-1, -1, -1, -1, -1.0, -1.0, -1, Decimal(-1), "-1"]
M = "aurelius_atlas_typesystem.builtin.date_type.DateType"
MS = timedelta(milliseconds=1)


@pytest.mark.covers(
    f"{M}.create_default_value", f"{M}.is_valid_value", f"{M}.get_normalized_value", rules=["VAL-08", "VAL-15"]
)
def test__numbers_are_milliseconds_since_the_epoch() -> None:
    """Every 1 is ``new Date(1)``, every -1 ``new Date(-1)``; the empty string is valid but has no date."""
    dates = DateType()
    now = datetime(2026, 10, 21, 12, 30, 15, 123000, tzinfo=UTC)

    assert dates.create_default_value() == EPOCH
    assert [dates.get_normalized_value(value) for value in ONES] == [EPOCH + MS] * len(ONES)
    assert [dates.get_normalized_value(value) for value in MINUS_ONES] == [EPOCH - MS] * len(MINUS_ONES)
    assert dates.get_normalized_value(now) is now
    assert dates.get_normalized_value("2026-10-21T12:30:15.123Z") == now
    assert (dates.is_valid_value(""), dates.get_normalized_value("")) == (True, None)
    assert all(dates.is_valid_value(value) for value in (None, now, 1.5, Decimal(1)))
    for value in ("12ab", "abcd", "-12ab", True):
        assert not dates.is_valid_value(value)
        assert dates.get_normalized_value(value) is None


@pytest.mark.covers(f"{M}.get_normalized_value", rules=["VAL-08"])
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-13-01T00:00:00.000Z", datetime(2027, 1, 1, tzinfo=UTC)),
        ("2026-01-32T25:61:00.000Z", datetime(2026, 2, 2, 2, 1, tzinfo=UTC)),
        ("2026-01-01T00:00:00.5Z", datetime(2026, 1, 1, tzinfo=UTC) + 5 * MS),
        ("2026-01-01T00:00:00.000Zand more", datetime(2026, 1, 1, tzinfo=UTC)),
        ("2026-01-01T00:00:00Z", None),
        ("0-01-01T00:00:00.000Z", None),
    ],
)
def test__serialized_dates_are_read_leniently_in_utc(text: str, expected: datetime | None) -> None:
    """A lenient ``SimpleDateFormat``: fields roll over, ``SSS`` counts milliseconds, trailing text is ignored."""
    assert DateType().get_normalized_value(text) == expected


@pytest.mark.covers(f"{M}.get_normalized_value", rules=["VAL-08"])
def test__a_date_python_cannot_hold_is_invalid() -> None:
    """Beyond years 1 to 9999 (DV-12)."""
    assert DateType().get_normalized_value(10**18) is None
