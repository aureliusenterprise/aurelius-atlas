"""The pytest plugin: registers ``covers``, validates it at collection and writes the trace file.

Loaded into every pytest run through the ``pytest11`` entry point.
"""

import json
from pathlib import Path

import pytest

from aurelius_atlas_trace.marker import MARKER_HELP, Covers, MarkerError, item_covers
from aurelius_atlas_trace.trace import TRACE_FORMAT_VERSION, Outcome, TracedTest

TRACE_JSON_OPTION = "--trace-json"
INVALID_MARKERS_ERROR = "Invalid covers markers:\n{problems}"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add ``--trace-json``."""
    parser.getgroup("aurelius-atlas-trace").addoption(
        TRACE_JSON_OPTION,
        dest="trace_json",
        metavar="FILE",
        default=None,
        help="write each test's covers markers and outcome to FILE (JSON)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the marker and a recorder for this session."""
    config.addinivalue_line("markers", MARKER_HELP)
    config.pluginmanager.register(TraceRecorder(config), TraceRecorder.NAME)


class TraceRecorder:
    """Collects the markers and outcomes of one pytest session."""

    NAME = "aurelius-atlas-trace-recorder"

    def __init__(self, config: pytest.Config) -> None:
        self._config = config
        self._covers: dict[str, Covers] = {}
        self._properties: dict[str, tuple[tuple[str, str], ...]] = {}
        self._outcomes: dict[str, Outcome] = {}

    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        """Validate every marker before any test runs; one bad marker stops the run (TRC-01 to TRC-03).

        Also keeps each test's ``user_properties`` as they are after collection (SCN-14).

        Raises:
            pytest.UsageError: A test carries an invalid marker; the message names the test and the problem.
        """
        problems: list[str] = []
        for item in items:
            # pytester.getitems() hands collectors through this hook too; only test items have properties.
            properties = getattr(item, "user_properties", ())
            self._properties[item.nodeid] = tuple((str(name), str(value)) for name, value in properties)
            try:
                self._covers[item.nodeid] = item_covers(item)
            except MarkerError as error:
                problems.append(f"  {item.nodeid}: {error}")
        if problems:
            raise pytest.UsageError(INVALID_MARKERS_ERROR.format(problems="\n".join(problems)))

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Fold the setup, call and teardown reports of a test into one outcome."""
        self._outcomes[report.nodeid] = Outcome.combine(self._outcomes.get(report.nodeid), Outcome.of(report))

    def pytest_sessionfinish(self) -> None:
        """Write the trace file when ``--trace-json`` was given (TRC-11)."""
        path = self._config.getoption("trace_json")
        if path is None:
            return
        tests = [
            TracedTest(
                nodeid=nodeid,
                targets=covers.targets,
                rules=covers.rules,
                outcome=self._outcomes.get(nodeid),
                properties=self._properties.get(nodeid, ()),
            )
            for nodeid, covers in self._covers.items()
        ]
        document = {
            "version": TRACE_FORMAT_VERSION,
            "rootdir": str(self._config.rootpath),
            "tests": [test.to_json() for test in tests],
        }
        output = self._config.invocation_params.dir / Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(document, indent=2) + "\n")
