"""The trace file: each test's markers and outcome, as the plugin writes it (TRC-11)."""

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import pytest

TRACE_FORMAT_VERSION = 1

UNSUPPORTED_VERSION_ERROR = "{path}: trace format version {version} is not supported"


class Outcome(StrEnum):
    """The outcome of one test, over its setup, call and teardown."""

    PASSED = "passed"
    SKIPPED = "skipped"
    FAILED = "failed"

    @classmethod
    def of(cls, report: pytest.TestReport) -> Outcome:
        """Return the outcome of one phase report."""
        if report.failed:
            return cls.FAILED
        if report.skipped:
            return cls.SKIPPED
        return cls.PASSED

    @classmethod
    def combine(cls, current: Outcome | None, phase: Outcome) -> Outcome:
        """Fold a phase into the outcome so far: any failure fails the test, a skip outranks a pass."""
        order = [cls.PASSED, cls.SKIPPED, cls.FAILED]
        if current is None:
            return phase
        return max(current, phase, key=order.index)


@dataclass(frozen=True)
class TracedTest:
    """One collected test: its node id, what it names, how it ended (None when it did not run), and its properties.

    The properties are the test's ``user_properties`` at collection, as name and value pairs (SCN-14).
    """

    nodeid: str
    targets: tuple[str, ...]
    rules: tuple[str, ...]
    outcome: Outcome | None = None
    properties: tuple[tuple[str, str], ...] = ()

    def property_values(self, name: str) -> tuple[str, ...]:
        """Return the values of every property with this name, in order."""
        return tuple(value for key, value in self.properties if key == name)

    def to_json(self) -> dict[str, Any]:
        """Return the JSON form of this test."""
        return {
            "nodeid": self.nodeid,
            "targets": list(self.targets),
            "rules": list(self.rules),
            "outcome": None if self.outcome is None else self.outcome.value,
            "properties": [list(pair) for pair in self.properties],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> TracedTest:
        """Read a test from its JSON form."""
        outcome = data.get("outcome")
        return cls(
            nodeid=data["nodeid"],
            targets=tuple(data.get("targets", ())),
            rules=tuple(data.get("rules", ())),
            outcome=None if outcome is None else Outcome(outcome),
            properties=tuple((str(name), str(value)) for name, value in data.get("properties", ())),
        )


@dataclass(frozen=True)
class TraceFile:
    """The content of one trace file: the pytest root directory and its tests."""

    rootdir: Path
    tests: tuple[TracedTest, ...]


def read_trace_file(path: Path) -> TraceFile:
    """Read a trace file written by ``--trace-json``.

    Raises:
        ValueError: The file has a format version this reader does not know.
    """
    document = json.loads(path.read_text())
    version = document.get("version")
    if version != TRACE_FORMAT_VERSION:
        raise ValueError(UNSUPPORTED_VERSION_ERROR.format(path=path, version=version))
    return TraceFile(
        rootdir=Path(document["rootdir"]),
        tests=tuple(TracedTest.from_json(test) for test in document["tests"]),
    )
