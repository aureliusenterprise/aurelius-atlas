from collections.abc import Callable

import pytest
from aurelius_atlas_trace.inventory import public_functions
from aurelius_atlas_trace.testing import SampleWorkspace

CODE = """
from json import dumps


def public():
    return 1


def _private():
    return 2


class Thing:
    def method(self):
        return 3

    def _hidden(self):
        return 4

    @property
    def prop(self):
        return 5

    @staticmethod
    def static():
        return 6

    @classmethod
    def factory(cls):
        return cls()


class Child(Thing):
    def own(self):
        return 7


class _Internal:
    def method(self):
        return 8
"""


@pytest.mark.covers("aurelius_atlas_trace.inventory.public_functions", rules=["TRC-06"])
def test__public_functions_lists_functions_methods_and_properties(
    make_workspace: Callable[..., SampleWorkspace],
) -> None:
    """Public functions, methods, properties, static and class methods are listed once, where defined."""
    workspace = make_workspace(code=CODE, tests="")
    package = workspace.package

    names = [function.name for function in public_functions(package)]

    assert names == [
        f"{package}.Child.own",
        f"{package}.Thing.factory",
        f"{package}.Thing.method",
        f"{package}.Thing.prop",
        f"{package}.Thing.static",
        f"{package}.public",
    ]


@pytest.mark.covers("aurelius_atlas_trace.inventory.public_functions", rules=["TRC-06"])
def test__public_functions_skip_private_and_excluded_subpackages(
    make_workspace: Callable[..., SampleWorkspace],
) -> None:
    """Modules starting with ``_`` and subpackages such as ``testing`` are left out at any depth."""
    workspace = make_workspace(code="", tests="")
    root = workspace.project / workspace.package
    for relative in ("api.py", "_private.py", "testing/__init__.py", "sub/__init__.py", "sub/testing/helpers.py"):
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text("def function():\n    pass\n")

    names = [function.name for function in public_functions(workspace.package, ("testing",))]

    assert names == [f"{workspace.package}.api.function", f"{workspace.package}.sub.function"]


@pytest.mark.covers("aurelius_atlas_trace.inventory.public_functions", rules=["TRC-06"])
def test__public_functions_know_where_each_function_is(make_workspace: Callable[..., SampleWorkspace]) -> None:
    """Each function carries its file and line range, which the report uses for coverage."""
    workspace = make_workspace(
        code="def first():\n    return 1\n\n\ndef second():\n    x = 1\n    return x\n", tests=""
    )

    first, second = public_functions(workspace.package)

    assert first.file == (workspace.project / workspace.package / "__init__.py").resolve()
    assert (first.first_line, first.last_line) == (1, 2)
    assert (second.first_line, second.last_line) == (5, 7)
