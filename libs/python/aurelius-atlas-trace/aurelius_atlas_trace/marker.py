"""The ``covers`` marker: what a test names, validated against the code it names."""

import importlib
import inspect
import re
from collections.abc import Iterable
from dataclasses import dataclass
from types import FunctionType

import pytest

MARKER_NAME = "covers"

MARKER_HELP = (
    f"{MARKER_NAME}(*targets, rules=[...]): the functions (dotted import paths) and the specification "
    "rules (XXX-NN) this test checks"
)

RULE_ID_PATTERN = re.compile(r"[A-Z]{2,5}-\d{2,3}")
"""A rule id: 2-5 capital letters, a hyphen, 2-3 digits (TRC-03)."""

EMPTY_MARKER_ERROR = "covers() needs at least one target or rule"
NOT_A_STRING_ERROR = "covers() takes dotted paths and rule ids as strings, got {value!r}"
RULES_NOT_A_LIST_ERROR = "covers(rules=...) takes a list of rule ids, got {value!r}"
UNKNOWN_KEYWORD_ERROR = "covers() takes only the keyword 'rules', got {names}"
BAD_RULE_ID_ERROR = "{rule!r} is not a rule id of the form XXX-NN"
UNRESOLVED_TARGET_ERROR = "{path!r} does not import"
NOT_A_FUNCTION_ERROR = "{path!r} is not a function, method or property"


class MarkerError(ValueError):
    """A ``covers`` marker names something that is not a function or not a rule id."""


@dataclass(frozen=True)
class Covers:
    """What a test names: canonical function names and rule ids."""

    targets: tuple[str, ...] = ()
    rules: tuple[str, ...] = ()


def underlying_function(obj: object) -> FunctionType | None:
    """Return the plain function behind a function, method, static or class method or property getter.

    Returns:
        The undecorated function, or None when the object is none of these.
    """
    if isinstance(obj, property):
        obj = obj.fget
    if isinstance(obj, staticmethod | classmethod):
        obj = obj.__func__
    if callable(obj):
        obj = inspect.unwrap(obj)
    return obj if isinstance(obj, FunctionType) else None


def canonical_name(obj: object) -> str | None:
    """Return the defining ``module.qualname`` of a function, method or property, or None for anything else.

    Properties are named by their getter, so ``Store.is_open`` names the same function whether it is reached
    through the class or a re-exporting package (TRC-04).
    """
    function = underlying_function(obj)
    return None if function is None else f"{function.__module__}.{function.__qualname__}"


def resolve_target(path: str) -> str:
    """Import a dotted path and return the canonical name of the function it names.

    Args:
        path: A dotted import path such as ``package.module.Class.method``.

    Returns:
        The ``module.qualname`` where the function is defined.

    Raises:
        MarkerError: The path does not import, or names something other than a function, method or property.
    """
    parts = path.split(".")
    for split in range(len(parts) - 1, 0, -1):
        try:
            obj: object = importlib.import_module(".".join(parts[:split]))
        except ImportError:
            continue
        try:
            for attribute in parts[split:]:
                # Class attributes are read from the class body, so properties stay properties.
                obj = inspect.getattr_static(obj, attribute) if inspect.isclass(obj) else getattr(obj, attribute)
        except AttributeError:
            break
        name = canonical_name(obj)
        if name is None:
            raise MarkerError(NOT_A_FUNCTION_ERROR.format(path=path))
        return name
    raise MarkerError(UNRESOLVED_TARGET_ERROR.format(path=path))


def _strings(values: Iterable[object]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise MarkerError(NOT_A_STRING_ERROR.format(value=value))
        result.append(value)
    return tuple(result)


def parse_marker(mark: pytest.Mark) -> Covers:
    """Validate one ``covers`` marker and resolve its targets (TRC-01 to TRC-04).

    Args:
        mark: The marker as pytest collected it.

    Returns:
        The canonical targets and the rule ids it names.

    Raises:
        MarkerError: The marker is empty, or a target or rule id is invalid.
    """
    unknown = sorted(set(mark.kwargs) - {"rules"})
    if unknown:
        raise MarkerError(UNKNOWN_KEYWORD_ERROR.format(names=", ".join(unknown)))
    rules_value = mark.kwargs.get("rules", ())
    if isinstance(rules_value, str) or not isinstance(rules_value, list | tuple):
        raise MarkerError(RULES_NOT_A_LIST_ERROR.format(value=rules_value))

    paths = _strings(mark.args)
    rules = _strings(rules_value)
    if not paths and not rules:
        raise MarkerError(EMPTY_MARKER_ERROR)
    for rule in rules:
        if RULE_ID_PATTERN.fullmatch(rule) is None:
            raise MarkerError(BAD_RULE_ID_ERROR.format(rule=rule))

    return Covers(targets=tuple(resolve_target(path) for path in paths), rules=rules)


def item_covers(item: pytest.Item) -> Covers:
    """Combine every ``covers`` marker that applies to a test, at any level (TRC-05).

    Raises:
        MarkerError: One of the markers is invalid.
    """
    targets: dict[str, None] = {}
    rules: dict[str, None] = {}
    for mark in item.iter_markers(MARKER_NAME):
        covers = parse_marker(mark)
        targets.update(dict.fromkeys(covers.targets))
        rules.update(dict.fromkeys(covers.rules))
    return Covers(targets=tuple(sorted(targets)), rules=tuple(sorted(rules)))
