"""The exact comparison of a response body with its expectation (SCN-09, SCN-10, SCN-12; DD-013)."""

import copy
import json
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Any

from aurelius_atlas_parity.path import JsonPath, Location, Wildcard, format_location

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
    if isinstance(value, Marker):
        return value.value
    return json.dumps(value, ensure_ascii=False)


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


def apply_deviation(  # noqa: C901 - one branch per kind of last segment
    expected: Any,  # noqa: ANN401 - any JSON value
    *,
    id: str,  # noqa: A002 - the deviation id, as the format names it
    path: JsonPath,
    value: Any = None,  # noqa: ANN401 - any JSON value
    absent: bool = False,
) -> Any:  # noqa: ANN401 - any JSON value
    """Return a copy of the expectation with the Aurelius value, or no value, at the path (SCN-12).

    A key that the expectation does not have is added when a value is given, so a deviation can declare a
    field Aurelius returns and Atlas does not.

    Raises:
        ValueError: The path matches nothing to change in the expectation.
    """
    changed = copy.deepcopy(expected)
    if not path.segments:
        if absent:
            raise ValueError(DEVIATION_MATCHES_NOTHING_ERROR.format(id=id, path=path.text))
        return value
    last = path.segments[-1]
    touched = False
    for _, parent in path.parent.find(changed):
        if isinstance(parent, dict):
            keys = list(parent) if isinstance(last, Wildcard) else [last] if isinstance(last, str) else []
            for key in keys:
                if absent and key in parent:
                    del parent[key]
                    touched = True
                elif not absent:
                    parent[key] = copy.deepcopy(value)
                    touched = True
        elif isinstance(parent, list):
            indexes = (
                range(len(parent))
                if isinstance(last, Wildcard)
                else [last]
                if isinstance(last, int) and last < len(parent)
                else []
            )
            for index in sorted(indexes, reverse=True):
                if absent:
                    del parent[index]
                else:
                    parent[index] = copy.deepcopy(value)
                touched = True
    if not touched:
        raise ValueError(DEVIATION_MATCHES_NOTHING_ERROR.format(id=id, path=path.text))
    return changed
