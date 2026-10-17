"""A sample workspace on disk, for tests of the check and the report.

Note:
    Test infrastructure: like every ``testing`` module, it is outside the traceability check (DD-010).
"""

import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT_PYPROJECT = """
[tool.uv.workspace]
members = ["libs/sample", "libs/template"]

[tool.aurelius-atlas-trace]
enforce-from = "0.2"
exclude-projects = ["libs/template"]
specs = "specs"
deviations = "deviations.md"
"""

PROJECT_PYPROJECT = """
[tool.hatch.build.targets.wheel]
packages = ["{package}"]

[tool.pytest.ini_options]
pythonpath = ["."]
"""


@dataclass(frozen=True)
class SampleWorkspace:
    """A workspace with one Atlas project, one excluded template project, specifications and a deviations table."""

    root: Path
    package: str

    @property
    def project(self) -> Path:
        """The Atlas project's directory."""
        return self.root / "libs" / "sample"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip())


def build_sample_workspace(  # noqa: PLR0913 - one keyword per part of the workspace
    root: Path,
    package: str,
    *,
    code: str,
    tests: str,
    rules: str = "| ABC-01 | A rule |\n",
    e2e: str | None = None,
    conftest: str | None = None,
) -> SampleWorkspace:
    """Write a sample workspace; ``{package}`` in the snippets is replaced by the package name.

    Args:
        root: The workspace directory to create.
        package: The Atlas project's package name.
        code: The package's ``__init__.py``.
        tests: The project's ``tests/test__sample.py``.
        rules: Rule table rows of the 0.2 specification.
        e2e: The project's ``e2e/test__sample_e2e.py``, if any.
        conftest: The project's ``tests/conftest.py``, if any.

    Returns:
        The workspace. Its project directory must be on ``sys.path`` for the inventory to import the package.
    """
    workspace = SampleWorkspace(root=root, package=package)
    _write(root / "pyproject.toml", ROOT_PYPROJECT)
    _write(workspace.project / "pyproject.toml", PROJECT_PYPROJECT.replace("{package}", package))
    _write(workspace.project / package / "__init__.py", code.replace("{package}", package))
    _write(workspace.project / "tests" / "test__sample.py", tests.replace("{package}", package))
    if conftest is not None:
        _write(workspace.project / "tests" / "conftest.py", conftest.replace("{package}", package))
    if e2e is not None:
        _write(workspace.project / "e2e" / "test__sample_e2e.py", e2e.replace("{package}", package))
    _write(root / "libs" / "template" / "pyproject.toml", "[project]\nname = 'template'\n")
    _write(root / "specs" / "0-1-old.md", "| OLD-01 | Before the check |\n")
    _write(root / "specs" / "0-2-sample.md", "| Id | Rule |\n| --- | --- |\n" + rules)
    _write(root / "specs" / "template.md", "| XYZ-01 | Not a specification |\n")
    _write(root / "deviations.md", "| # | Area |\n| --- | --- |\n| DV-01 | Sample |\n")
    return workspace
