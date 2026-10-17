import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from aurelius_atlas_trace.config import load_config
from aurelius_atlas_trace.inventory import PublicFunction
from aurelius_atlas_trace.report import (
    JUnitFailure,
    JUnitTotals,
    Report,
    Row,
    Status,
    TestRef,
    build_report,
    function_coverage,
    read_coverage,
    read_junit,
    render_html,
    render_summary,
    status_of,
)
from aurelius_atlas_trace.testing import SampleWorkspace
from aurelius_atlas_trace.trace import Outcome

CODE = """
def passes():
    return 1


def fails():
    return 2


def skipped():
    return 3


def unnamed():
    return 4
"""

TESTS = """
import pytest

import {package}


@pytest.mark.covers("{package}.passes", rules=["ABC-01"])
def test__passes():
    assert {package}.passes() == 1


@pytest.mark.covers("{package}.fails", rules=["ABC-02"])
def test__fails():
    assert {package}.fails() == 0


@pytest.mark.covers("{package}.skipped", rules=["ABC-03"])
@pytest.mark.skip(reason="not today")
def test__skipped():
    pass
"""

E2E = """
import pytest


@pytest.mark.covers(rules=["ABC-04"])
def test__not_run_here():
    pass
"""

SCENARIO_CONFTEST = """
def pytest_itemcollected(item):
    if item.name == "test__passes":
        item.user_properties += [("parity.endpoint", "GET /a"), ("parity.deviation", "DV-01")]
    if item.name == "test__fails":
        item.user_properties += [("parity.endpoint", "GET /a"), ("parity.endpoint", "POST /b")]
"""

RULES = "| ABC-01 | Passes |\n| ABC-02 | Fails |\n| ABC-03 | Skipped |\n| ABC-04 | Not run |\n| ABC-05 | Uncovered |\n"

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="3" failures="1" errors="1" skipped="1">
<testcase classname="tests.test__a" name="test__ok"/>
<testcase classname="tests.test__a" name="test__bad"><failure message="assert 2 == 0"/></testcase>
<testcase classname="tests.test__a" name="test__broken"><error message="fixture failed"/></testcase>
</testsuite></testsuites>
"""


def coverage_xml(source: Path, filename: str, hits: dict[int, int]) -> str:
    """A minimal Cobertura document for one file."""
    lines = "".join(f'<line number="{number}" hits="{count}"/>' for number, count in hits.items())
    return (
        f"<coverage><sources><source>{source}</source></sources><packages><package><classes>"
        f'<class filename="{filename}"><lines>{lines}</lines></class>'
        "</classes></package></packages></coverage>"
    )


@pytest.fixture
def run_workspace(make_workspace: Callable[..., SampleWorkspace]) -> SampleWorkspace:
    """A workspace whose unit tests ran as the CI ``test -c ci`` target runs them; the e2e tests did not run."""
    workspace = make_workspace(code=CODE, tests=TESTS, e2e=E2E, rules=RULES, conftest=SCENARIO_CONFTEST)
    subprocess.run(  # noqa: S603 - fixed arguments
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "-p",
            "no:cacheprovider",
            f"--cov={workspace.package}",
            "--cov-report=xml:coverage.xml",
            "--junitxml=junit.xml",
            "--trace-json=trace.json",
        ],
        cwd=workspace.project,
        capture_output=True,
        check=False,
    )
    return workspace


@pytest.mark.covers("aurelius_atlas_trace.report.status_of", rules=["TRC-14"])
@pytest.mark.parametrize(
    ("outcomes", "expected"),
    [
        ([], Status.UNCOVERED),
        ([None, None], Status.NOT_RUN),
        ([None, Outcome.PASSED], Status.PASSED),
        ([Outcome.PASSED, Outcome.FAILED], Status.FAILED),
        ([Outcome.SKIPPED, None], Status.SKIPPED),
        ([Outcome.SKIPPED, Outcome.PASSED], Status.PASSED),
    ],
)
def test__status_of_distinguishes_not_run_from_uncovered(outcomes: list[Outcome | None], expected: Status) -> None:
    """No naming test is uncovered; naming tests that did not run is not run; any failure fails."""
    assert status_of(outcomes) is expected


@pytest.mark.covers("aurelius_atlas_trace.report.Row.status", rules=["TRC-13"])
def test__row_status_follows_its_tests() -> None:
    """A row's status is the status of its tests' outcomes."""
    row = Row(name="ABC-01", detail="", tests=(TestRef(project="p", nodeid="t", outcome=Outcome.FAILED),))

    assert row.status is Status.FAILED


@pytest.mark.covers("aurelius_atlas_trace.report.read_junit", rules=["TRC-12"])
def test__read_junit_adds_up_suites_and_lists_failures(tmp_path: Path) -> None:
    """Counts come from the suites; failed and erroring cases are listed with their message."""
    (tmp_path / "junit.xml").write_text(JUNIT)
    (tmp_path / "junit-e2e.xml").write_text('<testsuite tests="2" failures="0" errors="0" skipped="0"/>')

    totals = read_junit([tmp_path / "junit.xml", tmp_path / "junit-e2e.xml"])

    assert (totals.tests, totals.failures, totals.errors, totals.skipped) == (5, 1, 1, 1)
    assert totals.failed_cases == [
        JUnitFailure(name="tests.test__a::test__bad", message="assert 2 == 0"),
        JUnitFailure(name="tests.test__a::test__broken", message="fixture failed"),
    ]


@pytest.mark.covers(
    "aurelius_atlas_trace.report.read_coverage", "aurelius_atlas_trace.report.function_coverage", rules=["TRC-13"]
)
def test__function_coverage_counts_measured_lines_in_the_function(tmp_path: Path) -> None:
    """The share of a function's measured body lines that ran, over all files; the ``def`` line does not count."""
    source = tmp_path / "pkg"
    source.mkdir()
    (source / "mod.py").write_text("")
    hits = {1: 1, 2: 0, 3: 1, 4: 0, 10: 1, 11: 0, 12: 0, 20: 1}
    (tmp_path / "a.xml").write_text(coverage_xml(source, "mod.py", hits))
    (tmp_path / "b.xml").write_text(coverage_xml(source, "mod.py", {2: 3}))

    coverage = read_coverage([tmp_path / "a.xml", tmp_path / "b.xml"])
    file = (source / "mod.py").resolve()

    assert function_coverage(PublicFunction("m.f", file, 1, 4), coverage) == pytest.approx(2 / 3)
    assert function_coverage(PublicFunction("m.g", file, 10, 12), coverage) == 0.0
    assert function_coverage(PublicFunction("m.h", file, 20, 22), coverage) is None
    assert function_coverage(PublicFunction("m.j", file, 30, 32), coverage) is None
    assert function_coverage(PublicFunction("m.i", tmp_path / "other.py", 1, 3), coverage) is None


@pytest.mark.covers("aurelius_atlas_trace.report.build_report", rules=["TRC-12", "TRC-13", "TRC-14"])
def test__build_report_joins_results_with_rules_and_functions(run_workspace: SampleWorkspace) -> None:
    """Each rule and function gets its tests and outcomes; tests that did not run show as not run."""
    report = build_report(load_config(run_workspace.root))
    package = run_workspace.package

    assert {row.name: row.status for row in report.rules} == {
        "ABC-01": Status.PASSED,
        "ABC-02": Status.FAILED,
        "ABC-03": Status.SKIPPED,
        "ABC-04": Status.NOT_RUN,
        "ABC-05": Status.UNCOVERED,
    }
    functions = {row.name: row for row in report.functions}
    assert {name: row.status for name, row in functions.items()} == {
        f"{package}.fails": Status.FAILED,
        f"{package}.passes": Status.PASSED,
        f"{package}.skipped": Status.SKIPPED,
        f"{package}.unnamed": Status.UNCOVERED,
    }
    assert functions[f"{package}.passes"].coverage == 1.0
    assert functions[f"{package}.unnamed"].coverage == 0.0
    assert functions[f"{package}.passes"].tests == (
        TestRef(project="sample", nodeid="tests/test__sample.py::test__passes", outcome=Outcome.PASSED),
    )
    assert (report.totals.tests, report.totals.failures, report.totals.skipped) == (3, 1, 1)


@pytest.mark.covers("aurelius_atlas_trace.report.build_report", rules=["SCN-15"])
def test__build_report_has_one_row_per_endpoint(run_workspace: SampleWorkspace) -> None:
    """Scenario tests are grouped by the endpoints they call, with their outcomes and deviations."""
    report = build_report(load_config(run_workspace.root))

    rows = {row.name: row for row in report.endpoints}
    assert list(rows) == ["GET /a", "POST /b"]
    assert rows["GET /a"].status is Status.FAILED
    assert rows["GET /a"].detail == "deviations DV-01"
    assert [test.nodeid for test in rows["GET /a"].tests] == [
        "tests/test__sample.py::test__passes",
        "tests/test__sample.py::test__fails",
    ]
    assert rows["POST /b"].detail == "no deviations"


def sample_report() -> Report:
    """A report with one row of each status that needs attention, and one passing row."""
    passed = TestRef(project="p", nodeid="tests/test__a.py::test__ok", outcome=Outcome.PASSED)
    failed = TestRef(project="p", nodeid="tests/test__a.py::test__bad<x>", outcome=Outcome.FAILED)
    idle = TestRef(project="p", nodeid="e2e/test__b.py::test__later", outcome=None)
    return Report(
        totals=JUnitTotals(
            tests=3, failures=1, errors=0, skipped=0, failed_cases=[JUnitFailure("tests.test__a::test__bad", "boom")]
        ),
        rules=(
            Row(name="ABC-01", detail="0.2 · spec.md", tests=(passed,)),
            Row(name="ABC-02", detail="0.2 · spec.md", tests=(failed,)),
            Row(name="ABC-03", detail="0.2 · spec.md", tests=(idle,)),
            Row(name="ABC-04", detail="0.2 · spec.md", tests=()),
        ),
        functions=(Row(name="m.f", detail="m.py:1", tests=(passed,), coverage=0.5),),
        endpoints=(
            Row(name="GET /api/version", detail="deviations DV-01", tests=(passed,)),
            Row(name="POST /api/entity", detail="no deviations", tests=(failed,)),
        ),
    )


@pytest.mark.covers("aurelius_atlas_trace.report.render_html", rules=["TRC-12", "TRC-13", "TRC-14"])
def test__render_html_is_one_self_contained_page() -> None:
    """The page shows results, rules and functions with statuses, escapes names, and loads nothing."""
    page = render_html(sample_report())

    assert page.startswith("<!doctype html>")
    assert "<script" not in page
    assert "<link" not in page
    assert "src=" not in page
    assert "3 tests: 1 failed" in page
    assert '<td class="not-run">not run</td>' in page
    assert '<td class="uncovered">uncovered</td>' in page
    assert "test__bad&lt;x&gt;" in page
    assert "<td>50%</td>" in page


@pytest.mark.covers("aurelius_atlas_trace.report.render_html", rules=["SCN-15"])
def test__render_html_has_an_endpoint_section() -> None:
    """Endpoints get their own table with statuses and deviations."""
    page = render_html(sample_report())

    assert "<h2>Endpoints (2)</h2>" in page
    assert '<code>GET /api/version</code><div class="detail">deviations DV-01</div>' in page


@pytest.mark.covers("aurelius_atlas_trace.report.render_summary", rules=["TRC-15", "SCN-15"])
def test__render_summary_counts_and_lists_what_needs_attention() -> None:
    """The Markdown summary has counts per status and lists failed and uncovered items and failed tests."""
    summary = render_summary(sample_report())

    assert "| Rules | 1 | 1 | 0 | 1 | 1 |" in summary
    assert "| Functions | 1 | 0 | 0 | 0 | 0 |" in summary
    assert "| Endpoints | 1 | 1 | 0 | 0 | 0 |" in summary
    assert "- endpoint `POST /api/entity`: failed" in summary
    assert "- rule `ABC-02`: failed" in summary
    assert "- rule `ABC-04`: uncovered" in summary
    assert "ABC-03" not in summary
    assert "- test `tests.test__a::test__bad` failed" in summary


@pytest.mark.covers("aurelius_atlas_trace.report.render_summary", rules=["TRC-15"])
def test__render_summary_without_problems_has_no_attention_section() -> None:
    """A clean run has only the counts."""
    report = sample_report()
    clean = Report(totals=JUnitTotals(tests=1), rules=report.rules[:1], functions=report.functions)

    assert "Needs attention" not in render_summary(clean)
