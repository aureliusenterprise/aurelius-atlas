"""The criticality classification of every e2e test (the CI test tiers, DD-401).

Every end-to-end test names one of the four criticality levels — ``critical``,
``high``, ``medium`` or ``low`` — in its own decorators, one scenario at a
time, and the guard fails when one names none or names two. A level below
``critical`` shows the risk pair that earned it in a comment beside the marker
(``impact=<severe|major|minor>, likelihood=<high|medium|low>``, plus an
override note when the cost ceiling or an increment promotion applies). The
module ``pytestmark`` carries no level: a file that mixes scenarios of
different risk must not send them all to the same cadence. The guide, the
matrix and the cadences are the plan's:
``docs/architecture/platform/ci-test-tiers-plan.md``. The suite is offline: it
reads the e2e trees, it never runs them.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

from conftest import WORKSPACE

LEVELS: Final = frozenset({"critical", "high", "medium", "low"})
TOP_LEVEL: Final = "critical"
E2E_GLOBS: Final = ("apps/*/e2e", "libs/python/*/e2e")


def _e2e_files() -> list[Path]:
    return sorted({path for pattern in E2E_GLOBS for path in WORKSPACE.glob(f"{pattern}/test__*.py")})


def _own_levels(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """The level markers written on one test function itself."""
    levels = set()
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Attribute) and target.attr in LEVELS:
            levels.add(target.attr)
    return levels


def test__no_module_pytestmark_carries_a_level() -> None:
    """The level belongs to the scenario: a module-wide marker is a classification bug."""
    problems: list[str] = []
    for file in _e2e_files():
        tree = ast.parse(file.read_text())
        for statement in tree.body:
            targets: list[ast.expr] = (
                list(statement.targets)
                if isinstance(statement, ast.Assign)
                else ([statement.target] if isinstance(statement, ast.AnnAssign) else [])
            )
            if not any(isinstance(target, ast.Name) and target.id == "pytestmark" for target in targets):
                continue
            if any(node.attr in LEVELS for node in ast.walk(statement) if isinstance(node, ast.Attribute)):
                problems.append(f"{file.relative_to(WORKSPACE)}:{statement.lineno}")
    assert not problems, "e2e modules whose pytestmark carries a level:\n" + "\n".join(problems)


def _test_functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test__")
    ]


def _has_pair(text: str) -> bool:
    return "impact=" in text and "likelihood=" in text


def _decorator_window(source_lines: list[str], node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """The lines at and above the decorator stack, where the pair comment sits."""
    start = min((decorator.lineno for decorator in node.decorator_list), default=node.lineno)
    return "\n".join(source_lines[max(start - 1 - 8, 0) : start - 1])


def test__every_e2e_test_carries_a_criticality_level() -> None:
    """No e2e test runs uncatalogued: each names exactly one level."""
    problems: list[str] = []
    files = _e2e_files()
    assert files, "the guard found no e2e trees, so it proves nothing"
    for file in files:
        tree = ast.parse(file.read_text())
        for node in _test_functions(tree):
            levels = _own_levels(node)
            if len(levels) != 1:
                shown = ", ".join(sorted(levels)) or "none"
                problems.append(f"{file.relative_to(WORKSPACE)}::{node.name}: {shown}")
    assert not problems, "e2e tests without exactly one criticality marker:\n" + "\n".join(problems)


def test__a_level_below_critical_shows_its_score_pair() -> None:
    """A level below the top carries the matrix answer beside its marker."""
    problems: list[str] = []
    for file in _e2e_files():
        source_lines = file.read_text().splitlines()
        tree = ast.parse("\n".join(source_lines))
        for node in _test_functions(tree):
            levels = _own_levels(node)
            if len(levels) != 1 or TOP_LEVEL in levels:
                continue
            # The pair sits beside the decorator that carries the level.
            if not _has_pair(_decorator_window(source_lines, node)):
                problems.append(f"{file.relative_to(WORKSPACE)}::{node.name}")
    assert not problems, "e2e tests below critical without an impact/likelihood pair:\n" + "\n".join(problems)
