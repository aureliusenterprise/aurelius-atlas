"""The public functions of a package: what R1 of ADR 049 says must be named by a test (TRC-06)."""

import importlib
import inspect
import pkgutil
from collections.abc import Collection, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from aurelius_atlas_trace.marker import underlying_function


@dataclass(frozen=True)
class PublicFunction:
    """A public function, method or property getter, and where its source lives."""

    name: str
    file: Path
    first_line: int
    last_line: int


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _modules(package: str, excluded_subpackages: Collection[str]) -> Iterator[ModuleType]:
    root = importlib.import_module(package)
    yield root
    for info in pkgutil.walk_packages(root.__path__, prefix=f"{package}."):
        relative = info.name.removeprefix(f"{package}.").split(".")
        if all(_is_public(part) and part not in excluded_subpackages for part in relative):
            yield importlib.import_module(info.name)


def _functions_defined_in(module: ModuleType) -> Iterator[object]:
    for name, obj in vars(module).items():
        if not _is_public(name) or getattr(obj, "__module__", None) != module.__name__:
            continue
        if inspect.isfunction(obj):
            yield obj
        elif inspect.isclass(obj):
            yield from (member for attribute, member in vars(obj).items() if _is_public(attribute))


def _describe(obj: object) -> PublicFunction | None:
    function = underlying_function(obj)
    if function is None:
        return None
    lines, first_line = inspect.getsourcelines(function)
    return PublicFunction(
        name=f"{function.__module__}.{function.__qualname__}",
        file=Path(inspect.getfile(function)).resolve(),
        first_line=first_line,
        last_line=first_line + len(lines) - 1,
    )


def public_functions(package: str, excluded_subpackages: Collection[str] = ("testing",)) -> list[PublicFunction]:
    """List the public functions, methods and properties defined in a package (TRC-06).

    A name is public when no part of its path starts with ``_``. Functions imported into a module are listed
    where they are defined, and inherited methods are not listed again.

    Args:
        package: The importable package name.
        excluded_subpackages: Subpackage names left out at any depth, such as test helpers.

    Returns:
        The functions, sorted by name.
    """
    found: dict[str, PublicFunction] = {}
    for module in _modules(package, excluded_subpackages):
        for obj in _functions_defined_in(module):
            function = _describe(obj)
            if function is not None:
                found[function.name] = function
    return sorted(found.values(), key=lambda function: function.name)
