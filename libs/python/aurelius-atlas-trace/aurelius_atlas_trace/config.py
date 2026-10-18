"""Which projects, packages and specifications the check covers (TRC-07), read from the root ``pyproject.toml``."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aurelius_atlas_trace.rules import Increment

PYPROJECT = "pyproject.toml"
PROJECT_FILE = "project.json"
CONFIG_TABLE = "aurelius-atlas-trace"
TEST_DIRECTORIES = ("tests", "e2e")
"""The test directories of a project, as the Nx Python plugin knows them."""

SKIPPED_DIRS = frozenset(
    {".git", ".nx", ".venv", "__pycache__", "build", "coverage", "dist", "node_modules", "site", "tmp"}
)
"""Directories the project search never enters: outputs, caches and dependencies, which hold no Nx projects."""

MISSING_TABLE_ERROR = "{path} has no [tool.{table}] table"
BAD_SETTING_ERROR = "{path}: [tool.{table}] needs 'specs' and 'enforce-from' (N.M): {error}"
NO_DEVIATIONS_ERROR = "{path}: [tool.{table}] deviations: {file} does not exist"


class ConfigError(ValueError):
    """The workspace configuration is missing or incomplete."""


@dataclass(frozen=True)
class Project:
    """An Atlas project: its directory, its importable packages and its test directories."""

    root: Path
    packages: tuple[str, ...]
    """The importable packages to inventory; empty for a project that ships no Python, such as a container image."""

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
    """Every Nx project, excluded or not: where the report looks for test results."""
    deviations: Path | None = None
    """The deviations table that parity scenarios name their deviations from (SCN-13), if configured."""


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        return tomllib.load(file)


def _project(root: Path) -> Project:
    packages: tuple[str, ...] = ()
    pyproject = root / PYPROJECT
    if pyproject.is_file():
        tool = _read_toml(pyproject).get("tool", {})
        wheel = tool.get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {})
        packages = tuple(wheel.get("packages", ()))
    return Project(
        root=root,
        packages=packages,
        test_dirs=tuple(root / name for name in TEST_DIRECTORIES if (root / name).is_dir()),
    )


def _roots(workspace: Path, excluded: set[str], *, apply_exclusions: bool) -> list[Path]:
    """Every directory with a project.json, optionally without the excluded ones (TRC-07)."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(workspace):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIPPED_DIRS)
        if PROJECT_FILE not in filenames:
            continue
        root = Path(dirpath)
        if apply_exclusions and root.relative_to(workspace).as_posix() in excluded:
            continue
        found.append(root)
    return sorted(found)


def load_config(workspace: Path) -> TraceConfig:
    """Read ``[tool.aurelius-atlas-trace]`` from the root ``pyproject.toml`` and discover the projects (TRC-07).

    An Atlas project is an Nx project: every directory with a ``project.json``, except those
    ``exclude-projects`` leaves out. A project without a ``pyproject.toml`` ships no Python, so it
    contributes no functions to the inventory; its tests are still collected, so the rules they name
    count (DD-035). The table holds ``specs`` (directory of the specifications), ``enforce-from``
    (first increment whose rules count), ``exclude-projects`` (project directories left out, relative
    to the workspace), ``exclude-subpackages`` (subpackage names left out of every package, default
    ``["testing"]``) and ``deviations`` (the deviations table, optional).

    Raises:
        ConfigError: The table or one of its settings is missing.
    """
    path = workspace / PYPROJECT
    tool = _read_toml(path).get("tool", {})
    table = tool.get(CONFIG_TABLE)
    if table is None:
        raise ConfigError(MISSING_TABLE_ERROR.format(path=path, table=CONFIG_TABLE))

    excluded = set(table.get("exclude-projects", ()))
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
        projects=tuple(_project(root) for root in _roots(workspace, excluded, apply_exclusions=True)),
        excluded_subpackages=tuple(table.get("exclude-subpackages", ("testing",))),
        members=tuple(_roots(workspace, excluded, apply_exclusions=False)),
        deviations=deviations,
    )
