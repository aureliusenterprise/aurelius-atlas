"""``AtlasBuiltInTypes.AtlasDateType`` (VAL-08)."""

import re
from datetime import UTC, datetime, timedelta

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import ATLAS_TYPE_DATE

from aurelius_atlas_typesystem.builtin.builtin_type import BuiltInType
from aurelius_atlas_typesystem.java import is_number, long_value, parse_long

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)
_SERIALIZED_DATE = re.compile(r"([0-9]+)-([0-9]+)-([0-9]+)T([0-9]+):([0-9]+):([0-9]+)\.([0-9]+)Z")
"""``yyyy-MM-dd'T'HH:mm:ss.SSS'Z'`` as a lenient ``SimpleDateFormat`` reads it: any number of digits per field."""
_MONTHS = 12


class DateType(BuiltInType):
    """``date``: a number of milliseconds since the epoch, or a date in Atlas's serialized format, in UTC."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_DATE)

    def create_default_value(self) -> datetime:
        """The epoch."""
        return EPOCH

    def is_valid_value(self, value: object) -> bool:
        """Null, a date, a number or the empty string; otherwise a value that normalises."""
        if value is None or isinstance(value, datetime) or is_number(value) or value == "":
            return True
        return self.get_normalized_value(value) is not None

    def get_normalized_value(self, value: object) -> datetime | None:
        """A date as it is; a number's ``longValue`` in milliseconds; a string parsed leniently, else as a long."""
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, datetime):
            return value
        if is_number(value):
            return _from_millis(long_value(value))
        text = java_string(value)
        parsed = _parse_serialized(text)
        if parsed is not None:
            return parsed
        millis = parse_long(text)
        return None if millis is None else _from_millis(millis)


def _from_millis(millis: int) -> datetime | None:
    """``new Date(millis)``; None beyond the dates Python holds."""
    try:
        return EPOCH + millis * _MILLISECOND
    except OverflowError:
        return None


def _parse_serialized(text: str) -> datetime | None:
    """``SimpleDateFormat.parse`` of the serialized format, lenient: fields roll over, trailing text is ignored.

    ``SSS`` reads its digits as a number of milliseconds, so ``.5`` is 5 ms.
    """
    match = _SERIALIZED_DATE.match(text)
    if match is None:
        return None
    year, month, day, hour, minute, second, millis = (int(field) for field in match.groups())
    try:
        start = datetime(year + (month - 1) // _MONTHS, (month - 1) % _MONTHS + 1, 1, tzinfo=UTC)
        return start + timedelta(days=day - 1, hours=hour, minutes=minute, seconds=second, milliseconds=millis)
    except OverflowError, ValueError:
        return None
