"""Paths into a JSON document: the JSONPath subset ``$``, ``.name``, ``['name']``, ``[n]`` and ``[*]`` (SCN-07)."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

type Location = tuple[str | int, ...]
"""Where one value sits in a document: the keys and indexes leading to it."""

_SEGMENT = re.compile(r"\.(?P<name>[A-Za-z_][\w-]*)|\['(?P<quoted>[^']*)'\]|\[(?P<index>\d+)\]|(?P<wildcard>\[\*\])")

NOT_A_PATH_ERROR = "{text!r} is not a path: it must start with '$' and continue with .name, ['name'], [n] or [*]"


class PathError(ValueError):
    """A path is not in the supported JSONPath subset."""


@dataclass(frozen=True)
class Wildcard:
    """``[*]``: every element of an array or every value of an object."""


type Segment = str | int | Wildcard


@dataclass(frozen=True)
class JsonPath:
    """A parsed path: the segments after ``$``."""

    text: str
    segments: tuple[Segment, ...]

    def find(self, document: Any) -> list[tuple[Location, Any]]:  # noqa: ANN401 - any JSON value
        """Return the location and value of every match in the document, in document order."""
        return list(_find(document, self.segments, ()))

    @property
    def parent(self) -> JsonPath:
        """The path without its last segment; the root's parent is the root."""
        return JsonPath(text=self.text, segments=self.segments[:-1])


def parse_path(text: str) -> JsonPath:
    """Parse a path such as ``$.entities[*].guid``.

    Raises:
        PathError: The text is not in the supported subset.
    """
    if not text.startswith("$"):
        raise PathError(NOT_A_PATH_ERROR.format(text=text))
    segments: list[Segment] = []
    position = 1
    while position < len(text):
        match = _SEGMENT.match(text, position)
        if match is None:
            raise PathError(NOT_A_PATH_ERROR.format(text=text))
        if match["wildcard"]:
            segments.append(Wildcard())
        elif match["index"] is not None:
            segments.append(int(match["index"]))
        else:
            segments.append(match["name"] if match["name"] is not None else match["quoted"])
        position = match.end()
    return JsonPath(text=text, segments=tuple(segments))


def format_location(location: Location) -> str:
    """Write a location as a path, for messages: ``$.entities[0].guid``."""
    parts = ["$"]
    for step in location:
        if isinstance(step, int):
            parts.append(f"[{step}]")
        elif re.fullmatch(r"[A-Za-z_][\w-]*", step):
            parts.append(f".{step}")
        else:
            parts.append(f"['{step}']")
    return "".join(parts)


def _find(value: Any, segments: tuple[Segment, ...], location: Location) -> Iterator[tuple[Location, Any]]:  # noqa: ANN401
    if not segments:
        yield location, value
        return
    head, rest = segments[0], segments[1:]
    if isinstance(head, Wildcard):
        children: list[tuple[str | int, Any]] = []
        if isinstance(value, dict):
            children = list(value.items())
        elif isinstance(value, list):
            children = list(enumerate(value))
        for step, child in children:
            yield from _find(child, rest, (*location, step))
    elif isinstance(head, int):
        if isinstance(value, list) and head < len(value):
            yield from _find(value[head], rest, (*location, head))
    elif isinstance(value, dict) and head in value:
        yield from _find(value[head], rest, (*location, head))
