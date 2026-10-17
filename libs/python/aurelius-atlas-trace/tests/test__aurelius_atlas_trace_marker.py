import json
import textwrap
from pathlib import Path

import pytest
from aurelius_atlas_trace import Covers, MarkerError, canonical_name, resolve_target
from aurelius_atlas_trace.marker import item_covers, parse_marker, underlying_function
from aurelius_atlas_trace.trace import Outcome, TracedTest, read_trace_file

SAMPLE_MODULE = """
import functools


def plain():
    pass


def decorated_with_wraps(function):
    @functools.wraps(function)
    def wrapper():
        return function()

    return wrapper


@decorated_with_wraps
def wrapped():
    pass


class Thing:
    VALUE = 1

    def method(self):
        pass

    @property
    def prop(self):
        return 1

    @staticmethod
    def static():
        pass

    @classmethod
    def factory(cls):
        return cls()
"""


@pytest.fixture
def sample_module(pytester: pytest.Pytester) -> str:
    """A module named ``covered`` on the path, with every kind of target."""
    pytester.makepyfile(covered=SAMPLE_MODULE)
    pytester.syspathinsert()
    return "covered"


def run_tests(pytester: pytest.Pytester, source: str, *args: str) -> pytest.RunResult:
    """Run a test file in a subprocess, so the module under test is imported fresh."""
    pytester.makepyfile(test__sample=textwrap.dedent(source))
    return pytester.runpytest_subprocess(*args)


@pytest.mark.covers("aurelius_atlas_trace.plugin.pytest_configure", rules=["TRC-01"])
def test__covers_marker_is_registered(pytester: pytest.Pytester) -> None:
    """The marker is known to pytest, so ``--strict-markers`` accepts it."""
    result = pytester.runpytest_subprocess("--markers")

    result.stdout.fnmatch_lines(["@pytest.mark.covers(*targets, rules=[[]...[]]):*"])


@pytest.mark.covers(
    "aurelius_atlas_trace.plugin.TraceRecorder.pytest_collection_modifyitems",
    "aurelius_atlas_trace.marker.parse_marker",
    rules=["TRC-01"],
)
def test__covers_marker_without_target_or_rule_stops_the_run(pytester: pytest.Pytester) -> None:
    """An empty marker is an error before any test runs."""
    result = run_tests(
        pytester,
        """
        import pytest

        @pytest.mark.covers()
        def test__nothing():
            pass
        """,
    )

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*test__sample.py::test__nothing: covers() needs at least one target or rule*"])


@pytest.mark.covers("aurelius_atlas_trace.marker.resolve_target", rules=["TRC-02"])
@pytest.mark.parametrize(
    ("target", "problem"),
    [
        ("covered.missing", "'covered.missing' does not import"),
        ("not_a_module.function", "'not_a_module.function' does not import"),
        ("covered.Thing", "'covered.Thing' is not a function, method or property"),
        ("covered.Thing.VALUE", "'covered.Thing.VALUE' is not a function, method or property"),
    ],
)
def test__covers_marker_with_a_bad_target_names_it(
    pytester: pytest.Pytester, sample_module: str, target: str, problem: str
) -> None:
    """A target that does not import, or is not a function, stops the run and is named."""
    result = run_tests(
        pytester,
        f"""
        import pytest

        @pytest.mark.covers("{target}")
        def test__bad():
            pass
        """,
    )

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines([f"*test__bad: {problem}*"])
    assert sample_module


@pytest.mark.covers("aurelius_atlas_trace.marker.parse_marker", rules=["TRC-03"])
@pytest.mark.parametrize("rule", ["abc-01", "ABC-1", "ABCDEF-01", "ABC-0001", "ABC01"])
def test__covers_marker_rejects_malformed_rule_ids(pytester: pytest.Pytester, rule: str) -> None:
    """Rule ids are XXX-NN; anything else stops the run."""
    result = run_tests(
        pytester,
        f"""
        import pytest

        @pytest.mark.covers(rules=["{rule}"])
        def test__bad():
            pass
        """,
    )

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines([f"*'{rule}' is not a rule id of the form XXX-NN*"])


@pytest.mark.covers("aurelius_atlas_trace.marker.parse_marker", rules=["TRC-01"])
@pytest.mark.parametrize(
    ("arguments", "problem"),
    [
        ('rules="ABC-01"', "covers(rules=...) takes a list of rule ids"),
        ('rule=["ABC-01"]', "covers() takes only the keyword 'rules', got rule"),
        ("42", "covers() takes dotted paths and rule ids as strings, got 42"),
    ],
)
def test__covers_marker_rejects_malformed_arguments(pytester: pytest.Pytester, arguments: str, problem: str) -> None:
    """Rules come as a list, under ``rules`` only, and everything is a string."""
    result = run_tests(
        pytester,
        f"""
        import pytest

        @pytest.mark.covers({arguments})
        def test__bad():
            pass
        """,
    )

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines([f"*{problem}*"])


@pytest.mark.covers(
    "aurelius_atlas_trace.marker.canonical_name",
    "aurelius_atlas_trace.marker.underlying_function",
    "aurelius_atlas_trace.marker.resolve_target",
    rules=["TRC-02", "TRC-04"],
)
@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("covered.plain", "covered.plain"),
        ("covered.wrapped", "covered.wrapped"),
        ("covered.Thing.method", "covered.Thing.method"),
        ("covered.Thing.prop", "covered.Thing.prop"),
        ("covered.Thing.static", "covered.Thing.static"),
        ("covered.Thing.factory", "covered.Thing.factory"),
    ],
)
def test__resolve_target_names_every_kind_of_function_by_its_definition(
    sample_module: str, path: str, expected: str
) -> None:
    """Functions, decorated functions, methods, properties, static and class methods all resolve."""
    assert resolve_target(path) == expected
    assert sample_module


@pytest.mark.covers("aurelius_atlas_trace.marker.resolve_target", rules=["TRC-04"])
def test__resolve_target_follows_re_exports_to_the_definition() -> None:
    """A name re-exported by a package resolves to its defining module."""
    assert resolve_target("aurelius_atlas_trace.resolve_target") == "aurelius_atlas_trace.marker.resolve_target"
    assert canonical_name(resolve_target) == "aurelius_atlas_trace.marker.resolve_target"


@pytest.mark.covers("aurelius_atlas_trace.marker.underlying_function", "aurelius_atlas_trace.marker.canonical_name")
def test__canonical_name_is_none_for_anything_but_a_function() -> None:
    """Classes, instances and modules have no canonical function name."""
    assert canonical_name(Covers) is None
    assert canonical_name(Covers()) is None
    assert canonical_name(json) is None
    assert underlying_function(42) is None


@pytest.mark.covers("aurelius_atlas_trace.marker.parse_marker")
def test__parse_marker_resolves_targets_and_keeps_rules() -> None:
    """A valid marker becomes canonical targets and its rule ids."""
    mark = pytest.mark.covers("aurelius_atlas_trace.resolve_target", rules=["ABC-01", "DE-123"]).mark

    assert parse_marker(mark) == Covers(
        targets=("aurelius_atlas_trace.marker.resolve_target",), rules=("ABC-01", "DE-123")
    )


@pytest.mark.covers("aurelius_atlas_trace.marker.parse_marker")
def test__parse_marker_raises_marker_error() -> None:
    """Invalid markers raise MarkerError, which the plugin reports."""
    with pytest.raises(MarkerError):
        parse_marker(pytest.mark.covers().mark)


@pytest.mark.covers(
    "aurelius_atlas_trace.marker.item_covers",
    "aurelius_atlas_trace.plugin.pytest_addoption",
    "aurelius_atlas_trace.plugin.TraceRecorder.pytest_sessionfinish",
    rules=["TRC-05", "TRC-11"],
)
def test__markers_at_every_level_combine(pytester: pytest.Pytester) -> None:
    """Module, class and test markers all apply to a test, and the trace file has their union."""
    result = run_tests(
        pytester,
        """
        import pytest

        pytestmark = pytest.mark.covers(rules=["MOD-01"])

        @pytest.mark.covers(rules=["CLS-01"])
        class TestThing:
            @pytest.mark.covers("aurelius_atlas_trace.resolve_target", rules=["FUN-01"])
            def test__one(self):
                pass

            def test__two(self):
                pass
        """,
        "--trace-json",
        "out/trace.json",
    )

    assert result.ret == pytest.ExitCode.OK
    trace = read_trace_file(pytester.path / "out" / "trace.json")
    assert trace.rootdir == pytester.path
    assert set(trace.tests) == {
        TracedTest(
            nodeid="test__sample.py::TestThing::test__one",
            targets=("aurelius_atlas_trace.marker.resolve_target",),
            rules=("CLS-01", "FUN-01", "MOD-01"),
            outcome=Outcome.PASSED,
        ),
        TracedTest(
            nodeid="test__sample.py::TestThing::test__two",
            targets=(),
            rules=("CLS-01", "MOD-01"),
            outcome=Outcome.PASSED,
        ),
    }


@pytest.mark.covers("aurelius_atlas_trace.marker.item_covers", rules=["TRC-05"])
def test__item_covers_merges_duplicates(pytester: pytest.Pytester) -> None:
    """The same target or rule named at two levels counts once."""
    pytester.makepyprojecttoml('[tool.pytest.ini_options]\nasyncio_default_fixture_loop_scope = "function"\n')
    pytester.makepyfile(
        test__sample="""
        import pytest

        pytestmark = pytest.mark.covers("aurelius_atlas_trace.resolve_target", rules=["ABC-01"])

        @pytest.mark.covers("aurelius_atlas_trace.marker.resolve_target", rules=["ABC-01"])
        def test__one():
            pass
        """,
    )
    (item,) = pytester.getitems(pytester.path / "test__sample.py")

    assert item_covers(item) == Covers(targets=("aurelius_atlas_trace.marker.resolve_target",), rules=("ABC-01",))


@pytest.mark.covers(
    "aurelius_atlas_trace.plugin.TraceRecorder.pytest_runtest_logreport",
    "aurelius_atlas_trace.plugin.TraceRecorder.pytest_sessionfinish",
    rules=["TRC-11"],
)
def test__trace_file_records_each_outcome(pytester: pytest.Pytester) -> None:
    """Passed, failed (also in setup or teardown), skipped and unmarked tests are all recorded."""
    result = run_tests(
        pytester,
        """
        import pytest

        @pytest.fixture
        def broken_teardown():
            yield
            raise RuntimeError

        @pytest.mark.covers(rules=["ABC-01"])
        def test__passes():
            pass

        @pytest.mark.covers(rules=["ABC-02"])
        def test__fails():
            raise AssertionError

        @pytest.mark.covers(rules=["ABC-03"])
        def test__teardown_fails(broken_teardown):
            pass

        @pytest.mark.covers(rules=["ABC-04"])
        @pytest.mark.skip(reason="not today")
        def test__skipped():
            pass

        def test__unmarked():
            pass
        """,
        "--trace-json",
        str(pytester.path / "trace.json"),
    )

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    outcomes = {
        test.nodeid.split("::")[1]: test.outcome for test in read_trace_file(pytester.path / "trace.json").tests
    }
    assert outcomes == {
        "test__passes": Outcome.PASSED,
        "test__fails": Outcome.FAILED,
        "test__teardown_fails": Outcome.FAILED,
        "test__skipped": Outcome.SKIPPED,
        "test__unmarked": Outcome.PASSED,
    }


@pytest.mark.covers("aurelius_atlas_trace.plugin.TraceRecorder.pytest_sessionfinish", rules=["TRC-11"])
def test__without_trace_json_nothing_is_written(pytester: pytest.Pytester) -> None:
    """A run without ``--trace-json`` writes no file."""
    result = run_tests(
        pytester,
        """
        import pytest

        @pytest.mark.covers(rules=["ABC-01"])
        def test__passes():
            pass
        """,
    )

    assert result.ret == pytest.ExitCode.OK
    assert list(Path(pytester.path).glob("*.json")) == []


@pytest.mark.covers(rules=["TRC-11"])
def test__collect_only_records_tests_without_outcomes(pytester: pytest.Pytester) -> None:
    """Collecting without running writes the markers with no outcome."""
    result = run_tests(
        pytester,
        """
        import pytest

        @pytest.mark.covers(rules=["ABC-01"])
        def test__passes():
            pass
        """,
        "--collect-only",
        "--trace-json",
        "trace.json",
    )

    assert result.ret == pytest.ExitCode.OK
    (test,) = read_trace_file(pytester.path / "trace.json").tests
    assert test.outcome is None
    assert test.rules == ("ABC-01",)


@pytest.mark.covers("aurelius_atlas_trace.plugin.TraceRecorder.pytest_collection_modifyitems", rules=["SCN-14"])
def test__trace_file_records_user_properties_at_collection(pytester: pytest.Pytester) -> None:
    """Properties a plugin adds while collecting reach the trace file; values become strings."""
    pytester.makeconftest(
        """
        def pytest_itemcollected(item):
            item.user_properties.extend([("kind", "sample"), ("count", 2)])
        """
    )
    result = run_tests(
        pytester,
        """
        def test__one():
            pass
        """,
        "--trace-json",
        "trace.json",
    )

    assert result.ret == pytest.ExitCode.OK
    (test,) = read_trace_file(pytester.path / "trace.json").tests
    assert test.properties == (("kind", "sample"), ("count", "2"))
