"""Which projects, packages and specifications the check covers (TRC-07), read from the root ``pyproject.toml``."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aurelius_atlas_trace.rules import Increment

PYPROJECT = "pyproject.toml"
CONFIG_TABLE = "aurelius-atlas-trace"
TEST_DIRECTORIES = ("tests", "e2e")
"""The test directories of a project, as the Nx Python plugin knows them."""

MISSING_TABLE_ERROR = "{path} has no [tool.{table}] table"
BAD_SETTING_ERROR = "{path}: [tool.{table}] needs 'specs' and 'enforce-from' (N.M): {error}"
NO_DEVIATIONS_ERROR = "{path}: [tool.{table}] deviations: {file} does not exist"
NO_PACKAGE_ERROR = "{project} declares no package in [tool.hatch.build.targets.wheel] packages"


class ConfigError(ValueError):
    """The workspace configuration is missing or incomplete."""


@dataclass(frozen=True)
class Project:
    """An Atlas project: its directory, its importable packages and its test directories."""

    root: Path
    packages: tuple[str, ...]
    test_dirs: tuple[Path, ...]


@dataclass(frozen=True)
class TraceConfig:
    """The check's view of the workspace."""

    workspace: Path
    spec_dir: Path
    enforce_from: Increment
    projects: tuple[Project, ...]
    excluded_subpackages: tuple[str, ...]
    members: tuple[Path, ...]
    """Every uv workspace member, excluded or not: where the report looks for test results."""
    deviations: Path | None = None
    """The deviations table that parity scenarios name their deviations from (SCN-13), if configured."""


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        return tomllib.load(file)


def _project(root: Path) -> Project:
    pyproject = _read_toml(root / PYPROJECT)
    paths = pyproject.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {})
    packages = tuple(paths.get("packages", ()))
    if not packages:
        raise ConfigError(NO_PACKAGE_ERROR.format(project=root.name))
    return Project(
        root=root,
        packages=packages,
        test_dirs=tuple(root / name for name in TEST_DIRECTORIES if (root / name).is_dir()),
    )


def _roots(workspace: Path, members: list[str], excluded: set[str]) -> list[Path]:
    globbed = {root for member in members if member not in excluded for root in workspace.glob(member)}
    return sorted(root for root in globbed if (root / PYPROJECT).is_file())


def load_config(workspace: Path) -> TraceConfig:
    """Read ``[tool.aurelius-atlas-trace]`` and the uv workspace members of the root ``pyproject.toml``.

    The table holds ``specs`` (directory of the specifications), ``enforce-from`` (first increment whose
    rules count), ``exclude-projects`` (workspace members left out, as listed in ``members``) and
    ``exclude-subpackages`` (subpackage names left out of every package, default ``["testing"]``) and
    ``deviations`` (the deviations table, optional).

    Raises:
        ConfigError: The table or one of its settings is missing, or a project declares no package.
    """
    path = workspace / PYPROJECT
    tool = _read_toml(path).get("tool", {})
    table = tool.get(CONFIG_TABLE)
    if table is None:
        raise ConfigError(MISSING_TABLE_ERROR.format(path=path, table=CONFIG_TABLE))

    excluded = set(table.get("exclude-projects", ()))
    members = tool.get("uv", {}).get("workspace", {}).get("members", ())
    try:
        spec_dir = workspace / table["specs"]
        enforce_from = Increment.parse(table["enforce-from"])
    except (KeyError, ValueError) as error:
        raise ConfigError(BAD_SETTING_ERROR.format(path=path, table=CONFIG_TABLE, error=error)) from error
    deviations = workspace / table["deviations"] if "deviations" in table else None
    if deviations is not None and not deviations.is_file():
        raise ConfigError(NO_DEVIATIONS_ERROR.format(path=path, table=CONFIG_TABLE, file=deviations))

    return TraceConfig(
        workspace=workspace,
        spec_dir=spec_dir,
        enforce_from=enforce_from,
        projects=tuple(_project(root) for root in _roots(workspace, members, excluded)),
        excluded_subpackages=tuple(table.get("exclude-subpackages", ("testing",))),
        members=tuple(_roots(workspace, members, set())),
        deviations=deviations,
    )
