from collections.abc import Callable
from pathlib import Path

import pytest
from aurelius_atlas_trace.check import (
    CollectionError,
    Findings,
    collect_project,
    find_gaps,
    format_findings,
    inventory,
    run_check,
)
from aurelius_atlas_trace.config import Project, load_config
from aurelius_atlas_trace.inventory import PublicFunction
from aurelius_atlas_trace.rules import Increment, Rule
from aurelius_atlas_trace.testing import SampleWorkspace
from aurelius_atlas_trace.trace import TracedTest

CODE = """
def named():
    return 1


def unnamed():
    return 2
"""

TESTS = """
import pytest

from {package} import named


@pytest.mark.covers("{package}.named", rules=["ABC-01", "ZZZ-99"])
def test__named():
    assert named() == 1
"""

E2E = """
import pytest


@pytest.mark.covers(rules=["ABC-02"])
def test__end_to_end():
    raise AssertionError("must not run during the check")
"""

RULES = "| ABC-01 | Named by a unit test |\n| ABC-02 | Named by an e2e test |\n| ABC-03 | Named by nothing |\n"


@pytest.mark.covers(
    "aurelius_atlas_trace.check.run_check",
    "aurelius_atlas_trace.check.collect_project",
    "aurelius_atlas_trace.check.inventory",
    "aurelius_atlas_trace.check.find_gaps",
    rules=["TRC-09", "TRC-10"],
)
def test__run_check_finds_every_kind_of_gap(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """Unnamed functions, unnamed rules and unknown rule ids are all found, e2e tests included, none run."""
    workspace = make_workspace(code=CODE, tests=TESTS, e2e=E2E, rules=RULES)

    findings = run_check(load_config(workspace.root))

    assert [function.name for function in findings.uncovered_functions] == [f"{workspace.package}.unnamed"]
    assert [rule.id for rule in findings.unchecked_rules] == ["ABC-03"]
    assert findings.unknown_rules == (("tests/test__sample.py::test__named", "ZZZ-99"),)
    assert not findings.ok


@pytest.mark.covers("aurelius_atlas_trace.check.run_check", "aurelius_atlas_trace.check.Findings.ok", rules=["TRC-09"])
def test__run_check_is_ok_when_everything_is_named(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """A workspace where every function and rule is named passes; the template project is ignored."""
    tests = TESTS.replace(', "ZZZ-99"', "").replace('"{package}.named"', '"{package}.named", "{package}.unnamed"')
    workspace = make_workspace(
        code=CODE, tests=tests, e2e=E2E, rules=RULES.replace("| ABC-03 | Named by nothing |\n", "")
    )

    assert run_check(load_config(workspace.root)).ok


@pytest.mark.covers("aurelius_atlas_trace.check.collect_project", rules=["TRC-10"])
def test__collect_project_fails_when_a_test_module_does_not_import(
    make_workspace: Callable[..., SampleWorkspace],
) -> None:
    """A test module that cannot be imported makes its markers unknown, which is an error."""
    workspace = make_workspace(code=CODE, tests="import does_not_exist\n")

    with pytest.raises(CollectionError, match="collecting the tests of sample failed"):
        collect_project(load_config(workspace.root).projects[0])


@pytest.mark.covers("aurelius_atlas_trace.check.collect_project", rules=["TRC-10"])
def test__collect_project_without_tests_has_no_tests(tmp_path: Path) -> None:
    """A project without test directories contributes no markers and no error."""
    project = Project(root=tmp_path, packages=("anything",), test_dirs=())

    assert collect_project(project).tests == ()


@pytest.mark.covers("aurelius_atlas_trace.check.inventory", rules=["TRC-06"])
def test__inventory_covers_every_atlas_project(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """The inventory is the public functions of every Atlas project's packages."""
    workspace = make_workspace(code=CODE, tests="")

    names = [function.name for function in inventory(load_config(workspace.root))]

    assert names == [f"{workspace.package}.named", f"{workspace.package}.unnamed"]


@pytest.mark.covers("aurelius_atlas_trace.check.find_gaps", rules=["TRC-09"])
def test__find_gaps_counts_a_name_from_any_test(tmp_path: Path) -> None:
    """A function or rule named by any one test is covered."""
    function = PublicFunction(name="m.f", file=tmp_path / "m.py", first_line=1, last_line=2)
    rules = {"ABC-01": Rule(id="ABC-01", increment=Increment(0, 2), spec=tmp_path / "0-2-x.md")}
    tests = [
        TracedTest(nodeid="a", targets=("m.f",), rules=()),
        TracedTest(nodeid="b", targets=(), rules=("ABC-01",)),
    ]

    assert find_gaps([function], rules, tests).ok


@pytest.mark.covers("aurelius_atlas_trace.check.format_findings", rules=["TRC-09"])
def test__format_findings_lists_each_gap_with_its_location(tmp_path: Path) -> None:
    """Every gap is one line naming the function, rule or test and where to find it."""
    findings = Findings(
        uncovered_functions=(PublicFunction(name="m.f", file=tmp_path / "m.py", first_line=3, last_line=4),),
        unchecked_rules=(Rule(id="ABC-03", increment=Increment(0, 2), spec=tmp_path / "0-2-x.md"),),
        unknown_rules=(("tests/test__a.py::test__a", "ZZZ-99"),),
    )

    assert format_findings(findings, tmp_path).splitlines() == [
        "Public functions no test names (1):",
        "  m.f  (m.py:3)",
        "Rules no test names (1):",
        "  ABC-03  (0-2-x.md, increment 0.2)",
        "Tests naming a rule no specification defines (1):",
        "  tests/test__a.py::test__a: ZZZ-99",
    ]
    assert format_findings(Findings((), (), ()), tmp_path) == "Every public function and every rule is named by a test."
