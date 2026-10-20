"""The JSON conventions every Atlas model shares: names, nulls, timestamps and Java scalars (DD-020, DD-037).

Used by the typedef models (``typedef``) and the instance models (``instance``) alike.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)


def _read_epoch_millis(value: object) -> object:
    """Read a number or a string of digits as epoch milliseconds; leave other values to Pydantic (DD-022)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return _EPOCH + value * _MILLISECOND
    if isinstance(value, str) and value.isdigit():
        return _EPOCH + int(value) * _MILLISECOND
    return value


def _as_utc(value: datetime) -> datetime:
    """Read a date-time without a zone as UTC, as Jackson's ``StdDateFormat`` does."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _write_epoch_millis(value: datetime) -> int:
    return (value - _EPOCH) // _MILLISECOND


type Timestamp = Annotated[
    datetime,
    BeforeValidator(_read_epoch_millis),
    AfterValidator(_as_utc),
    PlainSerializer(_write_epoch_millis, return_type=int, when_used="json"),
]
"""A ``java.util.Date``: an aware datetime, written as epoch milliseconds (TDM-05)."""


def _null_as(default: object) -> Callable[[object], object]:
    def read(value: object) -> object:
        return default if value is None else value

    return read


type JavaBool = Annotated[bool, BeforeValidator(_null_as(default=False))]
"""A Java ``boolean``: an explicit null reads as false (TDM-10)."""

type JavaInt = Annotated[int, BeforeValidator(_null_as(default=0))]
"""A Java ``int``: an explicit null reads as 0 (TDM-10)."""


def empty_when_null(value: object) -> object:
    """Read a null list as empty: a field Java never leaves null (TDM-06)."""
    return [] if value is None else value


def _unique(names: list[str]) -> list[str]:
    """Keep each name once, in first-seen order (TDM-09, DD-021)."""
    return list(dict.fromkeys(names))


def _unique_or_null(names: list[str] | None) -> list[str] | None:
    return None if names is None else _unique(names)


def null_when_empty[T](values: list[T] | None) -> list[T] | None:
    """Read an empty list as null: a field Java leaves null when empty (TDM-11)."""
    return values or None


type NameSet = Annotated[list[str], BeforeValidator(empty_when_null), AfterValidator(_unique)]
"""A Java ``Set<String>`` that is never null (TDM-06, TDM-09)."""

type OptionalNameSet = Annotated[list[str] | None, AfterValidator(_unique_or_null)]
"""A Java ``Set<String>`` that may be null (TDM-09)."""


class AtlasModel(BaseModel):
    """The JSON conventions of every Atlas model (TDM-01 to TDM-03, TDM-15, DD-020)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
        validate_assignment=True,
        extra="ignore",
        coerce_numbers_to_str=True,
    )

    def to_json(self) -> dict[str, Any]:
        """The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02)."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)
