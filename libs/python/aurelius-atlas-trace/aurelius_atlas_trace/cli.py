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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aurelius-atlas-trace", description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(), help="workspace root (default: .)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="fail when a public function or a rule is named by no test")
    report = commands.add_parser("report", help="build the HTML test report from the run's result files")
    report.add_argument("--output", type=Path, required=True, help="HTML file to write")
    report.add_argument("--summary", type=Path, help="also write a Markdown summary here")
    return parser


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
        report = build_report(config)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(render_html(report))
        if arguments.summary is not None:
            arguments.summary.parent.mkdir(parents=True, exist_ok=True)
            arguments.summary.write_text(render_summary(report))
    except (CollectionError, ConfigError, DuplicateRuleError) as error:
        print(error, file=sys.stderr)  # noqa: T201 - command output
        return EXIT_ERROR
    return EXIT_OK
