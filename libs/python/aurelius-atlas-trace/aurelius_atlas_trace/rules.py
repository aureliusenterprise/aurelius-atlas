"""The rules of the increment specifications: what R2 of ADR 049 says must be named by a test (TRC-08)."""

import re
from dataclasses import dataclass
from pathlib import Path

from aurelius_atlas_trace.marker import RULE_ID_PATTERN

SPEC_FILE_PATTERN = re.compile(r"(\d+)-(\d+)-[a-z0-9-]+\.md")
"""A specification file: ``N-M-slug.md`` for increment N.M."""

_RULE_ROW_PATTERN = re.compile(rf"^\|\s*({RULE_ID_PATTERN.pattern})\s*\|")

DUPLICATE_RULE_ERROR = "rule {rule} is defined in both {first} and {second}"


class DuplicateRuleError(ValueError):
    """Two specifications, or two rows of one, define the same rule id."""


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


def read_rules(spec_dir: Path, enforce_from: Increment) -> dict[str, Rule]:
    """Read the rule ids of every specification from increment ``enforce_from`` on (TRC-08).

    A rule is a table row whose first cell is a rule id. Files that are not named ``N-M-slug.md`` (the
    template, the index) are ignored.

    Args:
        spec_dir: The directory of the increment specifications.
        enforce_from: The first increment whose rules count.

    Returns:
        The rules by id.

    Raises:
        DuplicateRuleError: A rule id is defined twice.
    """
    rules: dict[str, Rule] = {}
    for spec in sorted(spec_dir.glob("*.md")):
        match = SPEC_FILE_PATTERN.fullmatch(spec.name)
        if match is None:
            continue
        increment = Increment(int(match[1]), int(match[2]))
        if increment < enforce_from:
            continue
        for line in spec.read_text().splitlines():
            row = _RULE_ROW_PATTERN.match(line)
            if row is None:
                continue
            rule_id = row[1]
            if rule_id in rules:
                raise DuplicateRuleError(
                    DUPLICATE_RULE_ERROR.format(rule=rule_id, first=rules[rule_id].spec.name, second=spec.name)
                )
            rules[rule_id] = Rule(id=rule_id, increment=increment, spec=spec)
    return rules
