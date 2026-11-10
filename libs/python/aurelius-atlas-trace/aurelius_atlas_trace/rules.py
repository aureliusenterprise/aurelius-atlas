"""The rules of the increment specifications: what R2 of ADR 049 says must be named by a test (TRC-08)."""

import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from aurelius_atlas_trace.marker import RULE_ID_PATTERN

SPEC_FILE_PATTERN = re.compile(r"(\d+)-(\d+)-[a-z0-9-]+\.md")
"""A specification file in the old layout: ``N-M-slug.md`` for increment N.M."""

SPEC_FILE_NAME = "spec.md"
"""A specification in the per-project layout: ``<project>/specs/N-M-slug/spec.md`` for increment N.M."""

INCREMENT_DIR_PATTERN = re.compile(r"(\d+)-(\d+)([a-z]?)(?:-[a-z0-9-]+)?")
"""The name of an increment directory: ``N-M-slug``, the minor carrying an optional letter (``7-4a-search``)."""

PRUNE_DIRECTORIES = frozenset(
    {".git", ".venv", ".tox", "node_modules", "__pycache__", "dist", "site", "coverage", "tmp"}
)
"""Project directories the search for specifications never enters.

The scratch tree (``tmp/``, where local spikes and merge sandboxes live) holds
stale copies of whole spec trees; entering it reports rules that no live spec
has (the 7.24 trace run's DTM-08 conflict came from a copy under ``tmp/``).
"""

_RULE_ROW_PATTERN = re.compile(rf"^\|\s*({RULE_ID_PATTERN.pattern})\s*\|")

DUPLICATE_RULE_ERROR = "rule {rule} is defined in both {first} and {second}"
CONFLICTING_RULE_ERROR = "rule {rule} is {first_row} in {first} and {second_row} in {second}"


class DuplicateRuleError(ValueError):
    """Two specifications of different increments define the same rule id, or one increment's files disagree."""


@dataclass(frozen=True, order=True)
class Increment:
    """An increment number such as 0.2, ordered numerically."""

    major: int
    minor: int

    @classmethod
    def parse(cls, text: str) -> Increment:
        """Read ``N.M``.

        Raises:
            ValueError: The text is not two dot-separated numbers.
        """
        major, minor = text.split(".")
        return cls(int(major), int(minor))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True)
class Rule:
    """A rule id and the specification that defines it."""

    id: str
    increment: Increment
    spec: Path


def _display(spec: Path) -> str:
    """Name a specification file for an error message; ``spec.md`` needs its increment directory."""
    return f"{spec.parent.name}/{spec.name}" if spec.name == SPEC_FILE_NAME else spec.name


def _spec_files(root: Path) -> Iterator[tuple[Path, Increment]]:
    """Every specification under a root: ``<dir>/spec.md`` of an ``N-M-slug`` directory, or ``N-M-slug.md``."""
    for directory, names, files in os.walk(root):
        names[:] = sorted(name for name in names if name not in PRUNE_DIRECTORIES)
        here = Path(directory)
        if (directory_match := INCREMENT_DIR_PATTERN.fullmatch(here.name)) and SPEC_FILE_NAME in files:
            yield here / SPEC_FILE_NAME, Increment(int(directory_match[1]), int(directory_match[2]))
        for name in sorted(files):
            if (file_match := SPEC_FILE_PATTERN.fullmatch(name)) is not None:
                yield here / name, Increment(int(file_match[1]), int(file_match[2]))


def _normalize(row: str) -> str:
    """A rule row compared across files of one increment: the cells, with spacing ignored.

    Relative path prefixes are stripped: the parts of a multi-project increment hold the same
    shared row at different tree depths, so a link's `../` count differs while the rule does not.
    """
    while "../" in row:
        row = row.replace("../", "")
    return "|".join(cell.strip() for cell in row.split("|"))


def read_rules(spec_roots: Iterable[Path], enforce_from: Increment) -> dict[str, Rule]:
    """Read the rule ids of every specification from increment ``enforce_from`` on (TRC-08).

    A rule is a table row whose first cell is a rule id. A specification is either a ``spec.md`` in an
    ``N-M-slug`` directory below one of the roots, or a file named ``N-M-slug.md``; other files (the
    template, the index) are ignored and the search never enters ``PRUNE_DIRECTORIES``. Several files
    can define the rules of one increment — the parts of a multi-project increment restate their
    scope — so a repeated id within one increment is one source of truth, and only rows that disagree
    are an error.

    Args:
        spec_roots: Directories to search for specifications, each a project or the old spec directory.
        enforce_from: The first increment whose rules count.

    Returns:
        The rules by id.

    Raises:
        DuplicateRuleError: A rule id is defined by two increments, or two files of one increment
            define it with different rows.
    """
    definitions: dict[str, list[tuple[Increment, Path, str]]] = {}
    specs = sorted(((spec, increment) for root in spec_roots for spec, increment in _spec_files(root)))
    for spec, increment in specs:
        if increment < enforce_from:
            continue
        for line in spec.read_text().splitlines():
            if (row := _RULE_ROW_PATTERN.match(line)) is not None:
                definitions.setdefault(row[1], []).append((increment, spec, _normalize(line)))

    rules: dict[str, Rule] = {}
    for rule_id, found in definitions.items():
        first, rest = found[0], found[1:]
        if rest and any(increment != first[0] for increment, _, _ in rest):
            other = next(found for found in rest if found[0] != first[0])
            raise DuplicateRuleError(
                DUPLICATE_RULE_ERROR.format(rule=rule_id, first=_display(first[1]), second=_display(other[1]))
            )
        if len({row for _, _, row in found}) > 1:
            raise DuplicateRuleError(
                CONFLICTING_RULE_ERROR.format(
                    rule=rule_id,
                    first_row=first[2],
                    first=_display(first[1]),
                    second_row=rest[0][2],
                    second=_display(rest[0][1]),
                )
            )
        increment, spec, _ = first
        rules[rule_id] = Rule(id=rule_id, increment=increment, spec=spec)
    return rules
