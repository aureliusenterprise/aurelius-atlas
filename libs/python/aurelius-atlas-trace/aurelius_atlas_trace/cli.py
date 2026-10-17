"""The ``aurelius-atlas-trace`` command: ``check`` and ``report``."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from aurelius_atlas_trace.check import CollectionError, format_findings, run_check
from aurelius_atlas_trace.config import ConfigError, load_config
from aurelius_atlas_trace.report import build_report, render_html, render_summary
from aurelius_atlas_trace.rules import DuplicateRuleError

EXIT_OK = 0
EXIT_GAPS = 1
EXIT_ERROR = 2

OUTSIDE_WORKSPACE_ERROR = "{path} is outside the workspace {workspace}; the report is written inside it"


class OutsideWorkspaceError(ValueError):
    """An output file of ``report`` would be written outside the workspace."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aurelius-atlas-trace", description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(), help="workspace root (default: .)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="fail when a public function or a rule is named by no test")
    report = commands.add_parser("report", help="build the HTML test report from the run's result files")
    report.add_argument("--output", type=Path, required=True, help="HTML file to write")
    report.add_argument("--summary", type=Path, help="also write a Markdown summary here")
    return parser


def _inside(workspace: Path, path: Path) -> Path:
    """Return the resolved path, refusing one that leaves the workspace (TRC-12)."""
    resolved = path.resolve()
    if not resolved.is_relative_to(workspace):
        raise OutsideWorkspaceError(OUTSIDE_WORKSPACE_ERROR.format(path=resolved, workspace=workspace))
    return resolved


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command; return 0 when all is named, 1 for gaps, 2 when the check cannot run (TRC-09).

    Args:
        argv: The arguments after the program name; defaults to ``sys.argv[1:]``.
    """
    arguments = _parser().parse_args(argv)
    workspace = arguments.workspace.resolve()
    try:
        config = load_config(workspace)
        if arguments.command == "check":
            findings = run_check(config)
            print(format_findings(findings, workspace))  # noqa: T201 - command output
            return EXIT_OK if findings.ok else EXIT_GAPS
        output = _inside(workspace, arguments.output)
        summary = None if arguments.summary is None else _inside(workspace, arguments.summary)
        report = build_report(config)
        _write(output, render_html(report))
        if summary is not None:
            _write(summary, render_summary(report))
    except (CollectionError, ConfigError, DuplicateRuleError, OutsideWorkspaceError) as error:
        print(error, file=sys.stderr)  # noqa: T201 - command output
        return EXIT_ERROR
    return EXIT_OK
