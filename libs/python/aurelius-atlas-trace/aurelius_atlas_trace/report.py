"""The test report: results, coverage and traceability of one run on one page (ADR 049 R3)."""

import html
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from aurelius_atlas_trace.check import ProjectTests, collect_project, inventory
from aurelius_atlas_trace.config import TraceConfig
from aurelius_atlas_trace.inventory import PublicFunction
from aurelius_atlas_trace.parity import DEVIATION_PROPERTY, ENDPOINT_PROPERTY
from aurelius_atlas_trace.rules import Rule, read_rules
from aurelius_atlas_trace.trace import Outcome, read_trace_file

JUNIT_GLOB = "junit*.xml"
COVERAGE_GLOB = "coverage.xml"
TRACE_GLOB = "trace*.json"
"""File names the report reads from each project directory, where the Nx test targets write them."""


class Status(StrEnum):
    """The state of a rule or function in this run (TRC-13, TRC-14)."""

    FAILED = "failed"
    UNCOVERED = "uncovered"
    NOT_RUN = "not run"
    SKIPPED = "skipped"
    PASSED = "passed"


def status_of(outcomes: Sequence[Outcome | None]) -> Status:
    """Summarise the outcomes of the tests naming one rule or function; None is a test that did not run."""
    if not outcomes:
        return Status.UNCOVERED
    ran = [outcome for outcome in outcomes if outcome is not None]
    if not ran:
        return Status.NOT_RUN
    if Outcome.FAILED in ran:
        return Status.FAILED
    if all(outcome is Outcome.SKIPPED for outcome in ran):
        return Status.SKIPPED
    return Status.PASSED


@dataclass(frozen=True)
class TestRef:
    """A test that names a rule or function, and its outcome in this run."""

    __test__ = False  # not a pytest test class

    project: str
    nodeid: str
    outcome: Outcome | None


@dataclass(frozen=True)
class Row:
    """One rule or function with its tests."""

    name: str
    detail: str
    tests: tuple[TestRef, ...]
    coverage: float | None = None

    @property
    def status(self) -> Status:
        """The row's status over its tests."""
        return status_of([test.outcome for test in self.tests])


@dataclass(frozen=True)
class JUnitFailure:
    """A failed or erroring test case from a JUnit file."""

    name: str
    message: str


@dataclass
class JUnitTotals:
    """Test counts over every JUnit file of the run."""

    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    failed_cases: list[JUnitFailure] = field(default_factory=list)


@dataclass(frozen=True)
class Report:
    """Everything the page and the summary show."""

    totals: JUnitTotals
    rules: tuple[Row, ...]
    functions: tuple[Row, ...]
    endpoints: tuple[Row, ...] = ()
    """One row per endpoint that parity scenarios call (SCN-15)."""


def read_junit(paths: Iterable[Path]) -> JUnitTotals:
    """Add up JUnit XML files and list their failed and erroring test cases."""
    totals = JUnitTotals()
    for path in paths:
        root = ET.parse(path).getroot()  # noqa: S314 - the run's own output
        suites = [root] if root.tag == "testsuite" else root.iter("testsuite")
        for suite in suites:
            totals.tests += int(suite.get("tests", 0))
            totals.failures += int(suite.get("failures", 0))
            totals.errors += int(suite.get("errors", 0))
            totals.skipped += int(suite.get("skipped", 0))
            totals.failed_cases.extend(
                failure for case in suite.iter("testcase") if (failure := _failure(case)) is not None
            )
    return totals


def _failure(case: ET.Element) -> JUnitFailure | None:
    problem = case.find("failure")
    if problem is None:
        problem = case.find("error")
    if problem is None:
        return None
    return JUnitFailure(name=f"{case.get('classname', '')}::{case.get('name', '')}", message=problem.get("message", ""))


def read_coverage(paths: Iterable[Path]) -> dict[Path, dict[int, int]]:
    """Read Cobertura XML files into hits per line per absolute source file."""
    lines_by_file: dict[Path, dict[int, int]] = {}
    for path in paths:
        root = ET.parse(path).getroot()  # noqa: S314 - the run's own output
        sources = [Path(source.text or "") for source in root.iter("source")] or [path.parent]
        for cls in root.iter("class"):
            filename = cls.get("filename", "")
            candidates = [(source / filename) for source in sources]
            file = next((candidate for candidate in candidates if candidate.exists()), candidates[0]).resolve()
            hits = lines_by_file.setdefault(file, {})
            for line in cls.iter("line"):
                number = int(line.get("number", 0))
                hits[number] = max(hits.get(number, 0), int(line.get("hits", 0)))
    return lines_by_file


def function_coverage(function: PublicFunction, coverage: dict[Path, dict[int, int]]) -> float | None:
    """Return the share of a function's measured body lines that ran, or None when coverage did not measure it.

    The first measured line is the ``def`` statement (with its decorators), which runs when the module is
    imported, so it is left out: a function no test calls has 0%, not a share for its signature.
    """
    hits = coverage.get(function.file)
    if hits is None:
        return None
    measured = sorted(
        (number, count) for number, count in hits.items() if function.first_line <= number <= function.last_line
    )
    body = [count for _, count in measured[1:]]
    if not body:
        return None
    return sum(1 for count in body if count > 0) / len(body)


def build_report(config: TraceConfig) -> Report:
    """Collect every Atlas project's tests and join them with the results the run left in the workspace."""
    collected = [collect_project(project) for project in config.projects]
    outcomes: dict[tuple[Path, str], Outcome | None] = {}
    for member in config.members:
        for trace_path in sorted(member.glob(TRACE_GLOB)):
            trace = read_trace_file(trace_path)
            for test in trace.tests:
                outcomes[trace.rootdir.resolve(), test.nodeid] = test.outcome

    coverage = read_coverage(path for member in config.members for path in sorted(member.glob(COVERAGE_GLOB)))
    rules = read_rules(config.spec_dir, config.enforce_from)
    return Report(
        totals=read_junit(path for member in config.members for path in sorted(member.glob(JUNIT_GLOB))),
        rules=tuple(_rule_rows(rules.values(), collected, outcomes, config.workspace)),
        functions=tuple(_function_rows(inventory(config), collected, outcomes, coverage, config.workspace)),
        endpoints=tuple(_endpoint_rows(collected, outcomes)),
    )


def _refs(
    collected: Iterable[ProjectTests],
    outcomes: dict[tuple[Path, str], Outcome | None],
    *,
    rule: str | None = None,
    target: str | None = None,
) -> tuple[TestRef, ...]:
    return tuple(
        TestRef(
            project=project_tests.project.root.name,
            nodeid=test.nodeid,
            outcome=outcomes.get((project_tests.trace_rootdir.resolve(), test.nodeid)),
        )
        for project_tests in collected
        for test in project_tests.tests
        if (rule is not None and rule in test.rules) or (target is not None and target in test.targets)
    )


def _endpoint_rows(
    collected: Sequence[ProjectTests], outcomes: dict[tuple[Path, str], Outcome | None]
) -> Iterable[Row]:
    """One row per endpoint, in name order, with the scenario tests calling it and their deviations (SCN-15)."""
    endpoints: dict[str, list[TestRef]] = {}
    deviations: dict[str, set[str]] = {}
    for project_tests in collected:
        root = project_tests.project.root
        for test in project_tests.tests:
            for endpoint in test.property_values(ENDPOINT_PROPERTY):
                endpoints.setdefault(endpoint, []).append(
                    TestRef(
                        project=root.name,
                        nodeid=test.nodeid,
                        outcome=outcomes.get((project_tests.trace_rootdir.resolve(), test.nodeid)),
                    )
                )
                deviations.setdefault(endpoint, set()).update(test.property_values(DEVIATION_PROPERTY))
    for endpoint in sorted(endpoints):
        ids = sorted(deviations[endpoint])
        detail = f"deviations {', '.join(ids)}" if ids else "no deviations"
        yield Row(name=endpoint, detail=detail, tests=tuple(endpoints[endpoint]))


def _rule_rows(
    rules: Iterable[Rule],
    collected: Sequence[ProjectTests],
    outcomes: dict[tuple[Path, str], Outcome | None],
    workspace: Path,
) -> Iterable[Row]:
    for rule in rules:
        detail = f"{rule.increment} · {rule.spec.relative_to(workspace)}"
        yield Row(name=rule.id, detail=detail, tests=_refs(collected, outcomes, rule=rule.id))


def _function_rows(
    functions: Iterable[PublicFunction],
    collected: Sequence[ProjectTests],
    outcomes: dict[tuple[Path, str], Outcome | None],
    coverage: dict[Path, dict[int, int]],
    workspace: Path,
) -> Iterable[Row]:
    for function in functions:
        detail = f"{function.file.relative_to(workspace)}:{function.first_line}"
        yield Row(
            name=function.name,
            detail=detail,
            tests=_refs(collected, outcomes, target=function.name),
            coverage=function_coverage(function, coverage),
        )


def _counts(rows: Iterable[Row]) -> dict[Status, int]:
    counts = dict.fromkeys(Status, 0)
    for row in rows:
        counts[row.status] += 1
    return counts


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def render_summary(report: Report) -> str:
    """Render the Markdown summary CI appends to the run page (TRC-15)."""
    totals = report.totals
    lines = [
        "## Test report",
        "",
        f"**Tests:** {totals.tests} run, {totals.failures + totals.errors} failed, {totals.skipped} skipped",
        "",
        "| | Passed | Failed | Skipped | Not run | Uncovered |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for title, rows in (("Rules", report.rules), ("Endpoints", report.endpoints), ("Functions", report.functions)):
        counts = _counts(rows)
        lines.append(
            f"| {title} | {counts[Status.PASSED]} | {counts[Status.FAILED]} | {counts[Status.SKIPPED]} "
            f"| {counts[Status.NOT_RUN]} | {counts[Status.UNCOVERED]} |"
        )
    problems = [
        f"- {kind} `{row.name}`: {row.status}"
        for kind, rows in (("rule", report.rules), ("endpoint", report.endpoints), ("function", report.functions))
        for row in rows
        if row.status in {Status.FAILED, Status.UNCOVERED}
    ]
    problems.extend(f"- test `{case.name}` failed" for case in totals.failed_cases)
    if problems:
        lines += ["", "### Needs attention", "", *problems]
    return "\n".join(lines) + "\n"


_STYLE = """
:root { --bg: #ffffff; --fg: #1f2328; --muted: #59636e; --line: #d1d9e0; --head: #f6f8fa;
  --passed: #1a7f37; --failed: #cf222e; --skipped: #9a6700; --idle: #59636e; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #0d1117; --fg: #e6edf3; --muted: #9198a1; --line: #3d444d; --head: #151b23;
    --passed: #3fb950; --failed: #f85149; --skipped: #d29922; --idle: #9198a1; } }
body { background: var(--bg); color: var(--fg); font: 14px/1.5 system-ui, sans-serif; margin: 0 auto;
  padding: 16px; max-width: 1200px; }
h1 { font-size: 1.5em; } h2 { font-size: 1.2em; margin-top: 2em; }
table { border-collapse: collapse; width: 100%; } th, td { border-bottom: 1px solid var(--line);
  padding: 4px 8px; text-align: left; vertical-align: top; } th { background: var(--head); }
code, .detail { font-family: ui-monospace, monospace; font-size: 0.9em; } .detail { color: var(--muted); }
.passed { color: var(--passed); } .failed, .uncovered { color: var(--failed); font-weight: 600; }
.skipped { color: var(--skipped); } .not-run, .none { color: var(--idle); }
ul { margin: 0; padding-left: 1.2em; } .wrap { overflow-x: auto; }
"""


def _status_cell(status: Status) -> str:
    return f'<td class="{status.value.replace(" ", "-")}">{status.value}</td>'


def _tests_cell(tests: Iterable[TestRef]) -> str:
    items = [
        f"<li><code>{html.escape(test.project)}/{html.escape(test.nodeid)}</code> "
        f'<span class="{"not-run" if test.outcome is None else test.outcome.value}">'
        f"{'not run' if test.outcome is None else test.outcome.value}</span></li>"
        for test in tests
    ]
    return f"<td><ul>{''.join(items)}</ul></td>" if items else '<td class="none">none</td>'


def _table(title: str, rows: Sequence[Row], *, with_coverage: bool) -> str:
    counts = ", ".join(f"{count} {status.value}" for status, count in _counts(rows).items() if count)
    head = "<th>Name</th><th>Status</th>" + ("<th>Lines run</th>" if with_coverage else "") + "<th>Tests</th>"
    body = "".join(
        f'<tr><td><code>{html.escape(row.name)}</code><div class="detail">{html.escape(row.detail)}</div></td>'
        + _status_cell(row.status)
        + (f"<td>{_percent(row.coverage)}</td>" if with_coverage else "")
        + _tests_cell(row.tests)
        + "</tr>"
        for row in rows
    )
    return (
        f"<h2>{html.escape(title)} ({len(rows)})</h2><p>{html.escape(counts) or 'none'}</p>"
        f'<div class="wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    )


def render_html(report: Report, title: str = "Test report") -> str:
    """Render the report as one self-contained HTML page (TRC-12 to TRC-14)."""
    totals = report.totals
    failed = "".join(
        f"<li><code>{html.escape(case.name)}</code> — {html.escape(case.message)}</li>" for case in totals.failed_cases
    )
    results = (
        f"<p>{totals.tests} tests: {totals.failures} failed, {totals.errors} errors, {totals.skipped} skipped.</p>"
        + (f"<ul>{failed}</ul>" if failed else "")
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{_STYLE}</style></head><body>"
        f"<h1>{html.escape(title)}</h1><h2>Results</h2>{results}"
        + _table("Rules", report.rules, with_coverage=False)
        + _table("Endpoints", report.endpoints, with_coverage=False)
        + _table("Public functions", report.functions, with_coverage=True)
        + "</body></html>\n"
    )
