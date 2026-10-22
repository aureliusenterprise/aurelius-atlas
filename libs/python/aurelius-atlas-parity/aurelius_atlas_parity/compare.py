"""The exact comparison of a response body with its expectation (SCN-09, SCN-10, SCN-12; DD-013)."""

import copy
import json
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Any

from aurelius_atlas_parity.path import JsonPath, Location, Segment, Wildcard, format_location

DEVIATION_MATCHES_NOTHING_ERROR = "deviation {id} at {path} matches nothing in the expectation"


class Marker(Enum):
    """Values that stand in for something that is not a JSON value."""

    ABSENT = "(absent)"
    """The field or element is not there."""
    VOLATILE = "(volatile)"
    """The value is not compared (SCN-10)."""


@dataclass(frozen=True)
class Difference:
    """One place where a response differs from its expectation."""

    location: Location
    expected: Any
    actual: Any

    def __str__(self) -> str:
        return f"{format_location(self.location)}: expected {_show(self.expected)}, got {_show(self.actual)}"


def _show(value: Any) -> str:  # noqa: ANN401 - any JSON value
    """A value as JSON; a marker, also one inside an object or array, as its text (``(volatile)``)."""
    if isinstance(value, Marker):
        return value.value
    return json.dumps(value, ensure_ascii=False, default=_marker_text)


def _marker_text(value: object) -> str:
    if isinstance(value, Marker):
        return value.value
    raise TypeError(value)


def _kind(value: Any) -> str:  # noqa: ANN401 - any JSON value
    """The JSON type of a value; booleans are not numbers here, unlike in Python."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    return type(value).__name__


def compare(expected: Any, actual: Any) -> list[Difference]:  # noqa: ANN401 - any JSON value
    """Return every difference between two JSON values (SCN-09).

    Objects must have the same keys, arrays the same length and order, and scalars the same JSON type and
    value. ``Marker.VOLATILE`` equals only itself.
    """
    return list(_compare(expected, actual, ()))


def _compare(expected: Any, actual: Any, location: Location) -> Iterator[Difference]:  # noqa: ANN401
    if isinstance(expected, dict) and isinstance(actual, dict):
        yield from _compare_objects(expected, actual, location)
    elif isinstance(expected, list) and isinstance(actual, list):
        yield from _compare_arrays(expected, actual, location)
    elif _kind(expected) != _kind(actual) or expected != actual:
        yield Difference(location, expected, actual)


def _compare_objects(expected: dict[str, Any], actual: dict[str, Any], location: Location) -> Iterator[Difference]:
    for key, value in expected.items():
        if key in actual:
            yield from _compare(value, actual[key], (*location, key))
        else:
            yield Difference((*location, key), value, Marker.ABSENT)
    for key, value in actual.items():
        if key not in expected:
            yield Difference((*location, key), Marker.ABSENT, value)


def _compare_arrays(expected: list[Any], actual: list[Any], location: Location) -> Iterator[Difference]:
    for index in range(max(len(expected), len(actual))):
        if index >= len(actual):
            yield Difference((*location, index), expected[index], Marker.ABSENT)
        elif index >= len(expected):
            yield Difference((*location, index), Marker.ABSENT, actual[index])
        else:
            yield from _compare(expected[index], actual[index], (*location, index))


def _replace(document: Any, location: Location, value: Any) -> Any:  # noqa: ANN401 - any JSON value
    """Set the value at a location; returns the new document, which is ``value`` itself at the root."""
    if not location:
        return value
    parent = document
    for step in location[:-1]:
        parent = parent[step]
    parent[location[-1]] = value
    return document


def mask_volatile(document: Any, paths: list[JsonPath]) -> Any:  # noqa: ANN401 - any JSON value
    """Return a copy of the document with the value at every match of the paths replaced by ``Marker.VOLATILE``."""
    masked = copy.deepcopy(document)
    for path in paths:
        for location, _ in path.find(masked):
            masked = _replace(masked, location, Marker.VOLATILE)
    return masked


def apply_deviation(
    expected: object,
    *,
    id: str,  # noqa: A002 - the deviation id, as the format names it
    path: JsonPath,
    value: object = None,
    absent: bool = False,
) -> object:
    """Return a copy of the expectation with the Aurelius value, or no value, at the path (SCN-12).

    A key that the expectation does not have is added when a value is given, so a deviation can declare a
    field Aurelius returns and Atlas does not.

    Raises:
        ValueError: The path matches nothing to change in the expectation.
    """
    if not path.segments:
        if absent:
            raise ValueError(DEVIATION_MATCHES_NOTHING_ERROR.format(id=id, path=path.text))
        return copy.deepcopy(value)
    changed = copy.deepcopy(expected)
    last = path.segments[-1]
    touched = False
    for _, parent in path.parent.find(changed):
        touched = _change_children(parent, last, value=value, absent=absent) or touched
    if not touched:
        raise ValueError(DEVIATION_MATCHES_NOTHING_ERROR.format(id=id, path=path.text))
    return changed


def _child_steps(parent: object, last: Segment, *, absent: bool) -> list[str | int]:
    """The keys or indexes of a parent that the last segment of a deviation's path names."""
    if isinstance(parent, dict):
        if isinstance(last, Wildcard):
            return list(parent)
        if not isinstance(last, str) or (absent and last not in parent):
            return []
        return [last]
    if isinstance(parent, list):
        if isinstance(last, Wildcard):
            return list(range(len(parent)))
        if isinstance(last, int) and last < len(parent):
            return [last]
    return []


def _change_children(parent: Any, last: Segment, *, value: object, absent: bool) -> bool:  # noqa: ANN401
    """Set or remove the children of one parent; return whether any changed."""
    steps = _child_steps(parent, last, absent=absent)
    # Remove from the end, so the indexes of a list stay valid.
    for step in reversed(steps):
        if absent:
            del parent[step]
        else:
            parent[step] = copy.deepcopy(value)
    return bool(steps)
