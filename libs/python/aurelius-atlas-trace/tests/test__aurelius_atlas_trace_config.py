from collections.abc import Callable
from pathlib import Path

import pytest
from aurelius_atlas_trace.config import ConfigError, load_config
from aurelius_atlas_trace.rules import Increment
from aurelius_atlas_trace.testing import SampleWorkspace


@pytest.mark.covers("aurelius_atlas_trace.config.load_config", rules=["TRC-07"])
def test__load_config_checks_every_project_not_excluded(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """Nx projects are Atlas projects unless excluded; their packages and test directories are found."""
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
    assert config.deviations == workspace.root / "deviations.md"


@pytest.mark.covers("aurelius_atlas_trace.config.load_config", rules=["SCN-13"])
def test__load_config_reads_an_optional_deviations_table(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """Without the setting there is no table; a configured table that does not exist is an error."""
    workspace = make_workspace(code="", tests="")
    pyproject = workspace.root / "pyproject.toml"
    text = pyproject.read_text()

    pyproject.write_text(text.replace('deviations = "deviations.md"\n', ""))
    assert load_config(workspace.root).deviations is None

    pyproject.write_text(text.replace('"deviations.md"', '"missing.md"'))
    with pytest.raises(ConfigError, match=r"deviations: .*missing\.md does not exist"):
        load_config(workspace.root)


@pytest.mark.covers("aurelius_atlas_trace.config.load_config", rules=["TRC-07"])
def test__load_config_picks_up_a_new_project(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """A directory with a project.json is checked without touching the trace configuration."""
    workspace = make_workspace(code="", tests="")
    new = workspace.root / "libs" / "new"
    new.mkdir()
    (new / "project.json").write_text("{}\n")

    config = load_config(workspace.root)

    assert [project.root.name for project in config.projects] == ["new", "sample"]


@pytest.mark.covers("aurelius_atlas_trace.config.load_config", rules=["TRC-07"])
def test__load_config_includes_a_project_without_python(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """A project without a pyproject.toml ships no package; its tests are still collected (DD-035)."""
    workspace = make_workspace(code="", tests="")
    image = workspace.root / "libs" / "image"
    (image / "e2e").mkdir(parents=True)
    (image / "project.json").write_text("{}\n")

    config = load_config(workspace.root)

    discovered = {project.root.name: project for project in config.projects}
    assert discovered["image"].packages == ()
    assert discovered["image"].test_dirs == (image / "e2e",)


@pytest.mark.covers("aurelius_atlas_trace.config.load_config")
@pytest.mark.parametrize(
    ("pyproject", "problem"),
    [
        ("[project]\nname = 'x'\n", r"has no \[tool.aurelius-atlas-trace\] table"),
        ("[tool.aurelius-atlas-trace]\nspecs = 'specs'\n", "needs 'specs' and 'enforce-from'"),
        ("[tool.aurelius-atlas-trace]\nspecs = 'specs'\nenforce-from = 'one'\n", "needs 'specs' and 'enforce-from'"),
    ],
)
def test__load_config_explains_what_is_missing(tmp_path: Path, pyproject: str, problem: str) -> None:
    """A missing table or setting is a ConfigError that says what is missing."""
    (tmp_path / "pyproject.toml").write_text(pyproject)
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "pyproject.toml").write_text("[project]\nname = 'lib'\n")

    with pytest.raises(ConfigError, match=problem):
        load_config(tmp_path)
