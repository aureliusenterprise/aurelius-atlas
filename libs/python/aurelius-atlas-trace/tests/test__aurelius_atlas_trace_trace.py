import json
from pathlib import Path

import pytest
from aurelius_atlas_trace.trace import TRACE_FORMAT_VERSION, Outcome, TracedTest, read_trace_file


class Phase:
    """The two attributes of a ``TestReport`` that ``Outcome.of`` reads."""

    def __init__(self, *, failed: bool = False, skipped: bool = False) -> None:
        self.failed = failed
        self.skipped = skipped


@pytest.mark.covers("aurelius_atlas_trace.trace.Outcome.of")
@pytest.mark.parametrize(
    ("phase", "expected"),
    [(Phase(), Outcome.PASSED), (Phase(failed=True), Outcome.FAILED), (Phase(skipped=True), Outcome.SKIPPED)],
)
def test__outcome_of_a_phase(phase: Phase, expected: Outcome) -> None:
    """A phase report maps to passed, failed or skipped."""
    assert Outcome.of(phase) is expected  # pyright: ignore[reportArgumentType] - duck-typed report


@pytest.mark.covers("aurelius_atlas_trace.trace.Outcome.combine")
@pytest.mark.parametrize(
    ("current", "phase", "expected"),
    [
        (None, Outcome.PASSED, Outcome.PASSED),
        (Outcome.PASSED, Outcome.SKIPPED, Outcome.SKIPPED),
        (Outcome.SKIPPED, Outcome.PASSED, Outcome.SKIPPED),
        (Outcome.FAILED, Outcome.PASSED, Outcome.FAILED),
        (Outcome.PASSED, Outcome.FAILED, Outcome.FAILED),
    ],
)
def test__outcome_combine_lets_failure_win(current: Outcome | None, phase: Outcome, expected: Outcome) -> None:
    """Any failing phase fails the test; a skip outranks a pass."""
    assert Outcome.combine(current, phase) is expected


@pytest.mark.covers(
    "aurelius_atlas_trace.trace.TracedTest.to_json",
    "aurelius_atlas_trace.trace.TracedTest.from_json",
    "aurelius_atlas_trace.trace.read_trace_file",
    rules=["TRC-11"],
)
def test__traced_tests_round_trip_through_a_trace_file(tmp_path: Path) -> None:
    """What the plugin writes, the reader reads back, including tests that did not run."""
    tests = (
        TracedTest(nodeid="tests/test__a.py::test__a", targets=("m.f",), rules=("ABC-01",), outcome=Outcome.FAILED),
        TracedTest(nodeid="tests/test__a.py::test__b", targets=(), rules=("ABC-02",)),
    )
    path = tmp_path / "trace.json"
    document = {"version": TRACE_FORMAT_VERSION, "rootdir": str(tmp_path), "tests": [t.to_json() for t in tests]}
    path.write_text(json.dumps(document))

    trace = read_trace_file(path)

    assert trace.rootdir == tmp_path
    assert trace.tests == tests


@pytest.mark.covers("aurelius_atlas_trace.trace.read_trace_file")
def test__read_trace_file_rejects_an_unknown_version(tmp_path: Path) -> None:
    """A file from another format version is refused rather than misread."""
    path = tmp_path / "trace.json"
    path.write_text(json.dumps({"version": 99, "rootdir": ".", "tests": []}))

    with pytest.raises(ValueError, match="trace format version 99 is not supported"):
        read_trace_file(path)
