from collections.abc import Callable
from pathlib import Path

import pytest
from aurelius_atlas_trace.config import ConfigError, load_config
from aurelius_atlas_trace.rules import Increment
from aurelius_atlas_trace.testing import SampleWorkspace


@pytest.mark.covers("aurelius_atlas_trace.config.load_config", rules=["TRC-07"])
def test__load_config_checks_every_member_not_excluded(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """Workspace members are Atlas projects unless excluded; their packages and test directories are found."""
    workspace = make_workspace(code="", tests="", e2e="")

    config = load_config(workspace.root)

    (project,) = config.projects
    assert project.root == workspace.project
    assert project.packages == (workspace.package,)
    assert project.test_dirs == (workspace.project / "tests", workspace.project / "e2e")
    assert config.members == (workspace.project, workspace.root / "libs" / "template")
    assert config.spec_dir == workspace.root / "specs"
    assert config.enforce_from == Increment(0, 2)
    assert config.excluded_subpackages == ("testing",)


@pytest.mark.covers("aurelius_atlas_trace.config.load_config", rules=["TRC-07"])
def test__load_config_picks_up_a_new_project(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """A member added to the workspace is checked without touching the trace configuration."""
    workspace = make_workspace(code="", tests="")
    pyproject = workspace.root / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace('"libs/sample",', '"libs/sample", "libs/new",'))
    new = workspace.root / "libs" / "new"
    new.mkdir()
    (new / "pyproject.toml").write_text('[tool.hatch.build.targets.wheel]\npackages = ["new_package"]\n')

    config = load_config(workspace.root)

    assert [project.root.name for project in config.projects] == ["new", "sample"]


@pytest.mark.covers("aurelius_atlas_trace.config.load_config")
@pytest.mark.parametrize(
    ("pyproject", "problem"),
    [
        ("[project]\nname = 'x'\n", r"has no \[tool.aurelius-atlas-trace\] table"),
        ("[tool.aurelius-atlas-trace]\nspecs = 'specs'\n", "needs 'specs' and 'enforce-from'"),
        ("[tool.aurelius-atlas-trace]\nspecs = 'specs'\nenforce-from = 'one'\n", "needs 'specs' and 'enforce-from'"),
        (
            "[tool.uv.workspace]\nmembers = ['lib']\n[tool.aurelius-atlas-trace]\nspecs = 's'\nenforce-from = '0.2'\n",
            "lib declares no package",
        ),
    ],
)
def test__load_config_explains_what_is_missing(tmp_path: Path, pyproject: str, problem: str) -> None:
    """A missing table, setting or package is a ConfigError that says what is missing."""
    (tmp_path / "pyproject.toml").write_text(pyproject)
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "pyproject.toml").write_text("[project]\nname = 'lib'\n")

    with pytest.raises(ConfigError, match=problem):
        load_config(tmp_path)
