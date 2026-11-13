"""The JSON conventions every Atlas model shares: names, nulls, timestamps and Java scalars (DD-020, DD-037).

Used by the typedef models (``typedef``) and the instance models (``instance``) alike.
"""

import itertools
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, PlainSerializer, ValidationInfo
from pydantic.alias_generators import to_camel

from aurelius_atlas_model.errors import ATLAS_REQUEST, validate_body_guid


def is_atlas_request(context: object) -> bool:
    """Whether a validation reads a request body, so the body-only rules of the models apply (DV-162).

    The server's body readers pass ``{ATLAS_REQUEST: True}`` as Pydantic's context. Internal code and
    response building validate without a context, where those rules stay silent and any GUID text passes.
    """
    return isinstance(context, Mapping) and bool(context.get(ATLAS_REQUEST))


def _body_guid(value: str | None, info: ValidationInfo) -> str | None:
    if is_atlas_request(info.context):
        validate_body_guid(value)
    return value


def _body_guid_key(value: str, info: ValidationInfo) -> str:
    if is_atlas_request(info.context):
        validate_body_guid(value)
    return value


type BodyGuid = Annotated[str | None, AfterValidator(_body_guid)]
"""A GUID a request body may name, or none: a placeholder or UUID text, checked only as a request (DV-162).

The models of the create and update bodies read their GUIDs as this type, so a request may name an entity
of the same request by a placeholder (``-1``) or a stored one by UUID text. Java takes any text; the rule
is a deliberate move away from it (DV-161, DV-162).
"""

type BodyGuidText = Annotated[str, AfterValidator(_body_guid_key)]
"""A GUID a request body names where Java's field holds no null: a map key or a list element (DV-162).

The rule is ``BodyGuid``'s; only the null differs, as it does in the Java field.
"""

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)


_NEXT_ID = itertools.count(time.monotonic_ns())


def new_model_guid() -> str:
    """``AtlasBaseModelObject.init``: a new object's GUID, ``-`` and the next internal id (GLS-01, SVS-01)."""
    return f"-{next(_NEXT_ID) + 1}"


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
    PlainSerializer(_write_epoch_millis, return_type=int),
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
    """The base of every Atlas model.

    Java camelCase aliases, lenient input (extra keys ignored, numbers coerce to strings),
    and validation on assignment — the Jackson conventions of the Java models (TDM-01 to TDM-03, TDM-15, DD-020).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
        validate_assignment=True,
        extra="ignore",
        coerce_numbers_to_str=True,
    )

    def to_json(self) -> dict[str, Any]:
        """The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

        Untyped values keep their Python types (``Decimal``, ``datetime``) for ``codec.dumps`` (VAL-01, DD-039).
        """
        return self.model_dump(mode="python", by_alias=True, exclude_none=True)
