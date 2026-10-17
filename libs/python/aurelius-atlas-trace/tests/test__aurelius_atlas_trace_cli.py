from collections.abc import Callable

import pytest
from aurelius_atlas_trace.cli import EXIT_ERROR, EXIT_GAPS, EXIT_OK, main
from aurelius_atlas_trace.testing import SampleWorkspace

CODE = "def named():\n    return 1\n"

TESTS = """
import pytest


@pytest.mark.covers("{package}.named", rules=["ABC-01"])
def test__named():
    pass
"""


@pytest.mark.covers("aurelius_atlas_trace.cli.main", rules=["TRC-09"])
def test__main_check_exits_zero_when_everything_is_named(
    make_workspace: Callable[..., SampleWorkspace], capsys: pytest.CaptureFixture[str]
) -> None:
    """``check`` prints the all-clear and exits 0."""
    workspace = make_workspace(code=CODE, tests=TESTS)

    assert main(["--workspace", str(workspace.root), "check"]) == EXIT_OK
    assert "Every public function and every rule is named by a test." in capsys.readouterr().out


@pytest.mark.covers("aurelius_atlas_trace.cli.main", rules=["TRC-09"])
def test__main_check_exits_one_on_gaps(
    make_workspace: Callable[..., SampleWorkspace], capsys: pytest.CaptureFixture[str]
) -> None:
    """``check`` lists the gaps and exits 1."""
    workspace = make_workspace(code=CODE, tests=TESTS, rules="| ABC-01 | Named |\n| ABC-02 | Not named |\n")

    assert main(["--workspace", str(workspace.root), "check"]) == EXIT_GAPS
    assert "ABC-02" in capsys.readouterr().out


@pytest.mark.covers("aurelius_atlas_trace.cli.main")
def test__main_exits_two_when_the_check_cannot_run(
    make_workspace: Callable[..., SampleWorkspace], capsys: pytest.CaptureFixture[str]
) -> None:
    """A test module that does not import is an error, not a gap."""
    workspace = make_workspace(code=CODE, tests="import does_not_exist\n")

    assert main(["--workspace", str(workspace.root), "check"]) == EXIT_ERROR
    assert "collecting the tests of sample failed" in capsys.readouterr().err


@pytest.mark.covers("aurelius_atlas_trace.cli.main", rules=["TRC-12", "TRC-15"])
def test__main_report_writes_the_page_and_the_summary(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """``report`` writes the HTML page and, when asked, the Markdown summary, creating their directories."""
    workspace = make_workspace(code=CODE, tests=TESTS)
    output = workspace.root / "dist" / "test-report" / "index.html"
    summary = workspace.root / "dist" / "test-report" / "summary.md"

    code = main(["--workspace", str(workspace.root), "report", "--output", str(output), "--summary", str(summary)])

    assert code == EXIT_OK
    assert "ABC-01" in output.read_text()
    assert summary.read_text().startswith("## Test report")
