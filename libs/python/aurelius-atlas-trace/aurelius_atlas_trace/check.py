"""The check: every public function and every rule is named by a test (ADR 049 R1, R2)."""

import subprocess
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from aurelius_atlas_trace.config import Project, TraceConfig
from aurelius_atlas_trace.inventory import PublicFunction, public_functions
from aurelius_atlas_trace.parity import DEVIATION_PROPERTY, read_deviation_ids
from aurelius_atlas_trace.rules import Rule, read_rules
from aurelius_atlas_trace.trace import TracedTest, read_trace_file

# pytest exit codes that mean "collected fine": 0 tests found, or none at all.
_COLLECTED = {0, 5}

COLLECTION_FAILED_ERROR = "collecting the tests of {project} failed (exit code {code}):\n{output}"


class CollectionError(RuntimeError):
    """pytest could not collect a project's tests, so its markers are unknown."""


@dataclass(frozen=True)
class ProjectTests:
    """The collected tests of one project."""

    project: Project
    tests: tuple[TracedTest, ...]


@dataclass(frozen=True)
class Findings:
    """What the check found missing (TRC-09)."""

    uncovered_functions: tuple[PublicFunction, ...]
    unchecked_rules: tuple[Rule, ...]
    unknown_rules: tuple[tuple[str, str], ...]
    """Pairs of (test node id, rule id) for rules that no specification defines."""
    unknown_deviations: tuple[tuple[str, str], ...] = ()
    """Pairs of (test node id, deviation id) for deviations the deviations table does not define (SCN-13)."""

    @property
    def ok(self) -> bool:
        """Whether nothing is missing."""
        return not (self.uncovered_functions or self.unchecked_rules or self.unknown_rules or self.unknown_deviations)


def collect_project(project: Project) -> ProjectTests:
    """Collect a project's tests, without running them, and read their markers (TRC-10).

    Raises:
        CollectionError: pytest failed to collect, for example because a test module does not import.
    """
    if not project.test_dirs:
        return ProjectTests(project=project, tests=())
    with tempfile.TemporaryDirectory() as work_dir:
        trace_file = Path(work_dir) / "trace.json"
        result = subprocess.run(  # noqa: S603 - fixed arguments, no shell
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "-p",
                "no:cacheprovider",
                "--trace-json",
                str(trace_file),
                *(str(path.relative_to(project.root)) for path in project.test_dirs),
            ],
            cwd=project.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode not in _COLLECTED:
            raise CollectionError(
                COLLECTION_FAILED_ERROR.format(
                    project=project.root.name, code=result.returncode, output=result.stdout + result.stderr
                )
            )
        tests = read_trace_file(trace_file).tests if trace_file.exists() else ()
    return ProjectTests(project=project, tests=tests)


def inventory(config: TraceConfig) -> list[PublicFunction]:
    """List the public functions of every Atlas project (TRC-06, TRC-07)."""
    return [
        function
        for project in config.projects
        for package in project.packages
        for function in public_functions(package, config.excluded_subpackages)
    ]


def find_gaps(
    functions: Iterable[PublicFunction],
    rules: dict[str, Rule],
    tests: Iterable[TracedTest],
    deviations: set[str] | None = None,
) -> Findings:
    """Compare what the tests name with the functions and rules that must be named (TRC-09).

    Args:
        functions: The public functions that must be named.
        rules: The rules that must be named, by id.
        tests: The collected tests.
        deviations: The deviation ids scenarios may name (SCN-13); None skips that comparison.
    """
    named_targets: set[str] = set()
    named_rules: set[str] = set()
    unknown: list[tuple[str, str]] = []
    unknown_deviations: list[tuple[str, str]] = []
    for test in tests:
        named_targets.update(test.targets)
        named_rules.update(test.rules)
        unknown.extend((test.nodeid, rule) for rule in test.rules if rule not in rules)
        if deviations is not None:
            unknown_deviations.extend(
                (test.nodeid, deviation)
                for deviation in test.property_values(DEVIATION_PROPERTY)
                if deviation not in deviations
            )
    return Findings(
        uncovered_functions=tuple(function for function in functions if function.name not in named_targets),
        unchecked_rules=tuple(rule for rule in rules.values() if rule.id not in named_rules),
        unknown_rules=tuple(sorted(unknown)),
        unknown_deviations=tuple(sorted(unknown_deviations)),
    )


def run_check(config: TraceConfig) -> Findings:
    """Collect every Atlas project's tests and compare them with its functions and the specified rules."""
    collected = [collect_project(project) for project in config.projects]
    return find_gaps(
        inventory(config),
        read_rules(config.spec_dir, config.enforce_from),
        (test for project_tests in collected for test in project_tests.tests),
        None if config.deviations is None else read_deviation_ids(config.deviations),
    )


def format_findings(findings: Findings, workspace: Path) -> str:
    """Describe the findings for a terminal, one item per line."""
    if findings.ok:
        return "Every public function and every rule is named by a test."
    lines: list[str] = []
    if findings.uncovered_functions:
        lines.append(f"Public functions no test names ({len(findings.uncovered_functions)}):")
        lines.extend(
            f"  {function.name}  ({function.file.relative_to(workspace)}:{function.first_line})"
            for function in findings.uncovered_functions
        )
    if findings.unchecked_rules:
        lines.append(f"Rules no test names ({len(findings.unchecked_rules)}):")
        lines.extend(
            f"  {rule.id}  ({rule.spec.relative_to(workspace)}, increment {rule.increment})"
            for rule in findings.unchecked_rules
        )
    if findings.unknown_rules:
        lines.append(f"Tests naming a rule no specification defines ({len(findings.unknown_rules)}):")
        lines.extend(f"  {nodeid}: {rule}" for nodeid, rule in findings.unknown_rules)
    if findings.unknown_deviations:
        lines.append(
            f"Scenarios naming a deviation the deviations table does not define ({len(findings.unknown_deviations)}):"
        )
        lines.extend(f"  {nodeid}: {deviation}" for nodeid, deviation in findings.unknown_deviations)
    return "\n".join(lines)
