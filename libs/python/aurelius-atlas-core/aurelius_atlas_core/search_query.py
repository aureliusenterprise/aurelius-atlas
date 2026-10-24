"""``SearchQuery``: a basic search as the entity documents answer it, and its meaning on one entity (DD-089).

What Atlas spreads over an index query, a graph query and in-memory predicates is one query here: the types, the
state, a filter tree over search fields (DD-088) with Atlas's predicates (SRC-05), the sort and the page. The
Elasticsearch documents translate it; ``matches`` states it for one entity's search fields, as the in-memory
documents and the tests read it.
"""

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from aurelius_atlas_model.discovery import Condition

from aurelius_atlas_core.search_fields import KEYWORD, LONG

TYPE_NAME_FIELD = f"{KEYWORD}.__typeName"
STATE_FIELD = f"{KEYWORD}.__state"
GUID_FIELD = f"{KEYWORD}.__guid"
CREATE_TIME_FIELD = f"{LONG}.__timestamp"
ACTIVE = "ACTIVE"


class Test(StrEnum):
    """What a criterion tests of a field's value (``SearchPredicateUtil``'s predicates)."""

    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    EQ = "EQ"
    NEQ = "NEQ"
    """Not equal, or no value."""
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    CONTAINS = "CONTAINS"
    """A string containing the value; an array holding it."""
    NOT_CONTAINS = "NOT_CONTAINS"
    """No value, a string not containing it, an array not holding it."""
    IS_NULL = "IS_NULL"
    NOT_NULL = "NOT_NULL"
    NOT_EMPTY = "NOT_EMPTY"
    RANGE = "RANGE"
    """Between two values, both included."""
    NOTHING = "NOTHING"
    """Matches no entity (``ALWAYS_FALSE``)."""
    ANYTHING = "ANYTHING"
    """Matches every entity: a predicate that holds for any value."""
    ANY_OF = "ANY_OF"
    """A value, or an array element, among the values (``CONTAINS_ANY``)."""
    MATCHES = "MATCHES"
    """A value, or an array element, matching a pattern, ``*`` any characters, ignoring case (CSR-02)."""


@dataclass(frozen=True)
class Criterion:
    """A test of one search field; ``array`` when the attribute holds arrays."""

    field: str
    test: Test
    value: Any = None
    value2: Any = None
    array: bool = False


@dataclass(frozen=True)
class Group:
    """``AND`` or ``OR`` over criteria and groups, none of them empty."""

    condition: Condition
    criteria: tuple[Criterion | Group, ...]


type Filter = Criterion | Group


@dataclass(frozen=True)
class SearchQuery:
    """The entities of ``type_names`` (all for None), only ``ACTIVE`` ones with ``active_only``, matching ``filter``.

    Sorted by ``sort_field`` (descending with ``descending``, entities without a value last), then by creation
    time and GUID; ``size`` of them from ``offset``.
    """

    type_names: frozenset[str] | None
    active_only: bool = False
    filter: Filter | None = None
    sort_field: str | None = None
    descending: bool = False
    offset: int = 0
    size: int = 100
    tie_break: tuple[str, ...] = field(default=(CREATE_TIME_FIELD, GUID_FIELD))


def selects(query: SearchQuery, fields: Mapping[str, Any]) -> bool:
    """Whether an entity with these search fields is one of the query's, before sort and paging."""
    if query.type_names is not None and fields.get(TYPE_NAME_FIELD) not in query.type_names:
        return False
    if query.active_only and fields.get(STATE_FIELD) != ACTIVE:
        return False
    return query.filter is None or matches(query.filter, fields)


def matches(node: Filter, fields: Mapping[str, Any]) -> bool:
    """Whether search fields meet a filter: Atlas's in-memory predicates (SRC-05, SRC-06)."""
    if isinstance(node, Group):
        results = (matches(child, fields) for child in node.criteria)
        return all(results) if node.condition is Condition.AND else any(results)
    return _test(node, fields.get(node.field))


def _test(criterion: Criterion, value: Any) -> bool:  # noqa: ANN401, C901, PLR0911, PLR0912 - one predicate per test
    test, expected = criterion.test, criterion.value
    if test is Test.NOTHING:
        return False
    if test is Test.ANYTHING:
        return True
    if test in {Test.ANY_OF, Test.MATCHES}:
        return _any_item(test, value, expected)
    if test is Test.IS_NULL:
        return value is None
    if test is Test.NOT_NULL:
        return value is not None
    if test is Test.NOT_EMPTY:
        return value is not None and value not in ("", [])
    if test is Test.NEQ:
        return value is None or value != expected
    if test is Test.NOT_CONTAINS:
        return value is None or not _contains(value, expected, array=criterion.array)
    if value is None:
        return False
    if test is Test.CONTAINS:
        return _contains(value, expected, array=criterion.array)
    if test is Test.STARTS_WITH:
        return isinstance(value, str) and value.startswith(expected)
    if test is Test.ENDS_WITH:
        return isinstance(value, str) and value.endswith(expected)
    if test is Test.RANGE:
        return expected <= value <= criterion.value2
    return _compare(test, value, expected)


def _any_item(test: Test, value: Any, expected: Any) -> bool:  # noqa: ANN401 - a field's value
    """``ANY_OF`` and ``MATCHES``: of a value, or of any element of an array."""
    items = value if isinstance(value, list) else [] if value is None else [value]
    if test is Test.ANY_OF:
        return any(item in expected for item in items)
    pattern = wildcard_pattern(expected)
    return any(isinstance(item, str) and pattern.fullmatch(item) is not None for item in items)


def wildcard_pattern(pattern: str) -> re.Pattern[str]:
    """``getRegexString``'s pattern of one name: ``*`` any characters, the rest as it is, ignoring case."""
    return re.compile(".*".join(re.escape(part) for part in pattern.split("*")), re.IGNORECASE | re.DOTALL)


def _contains(value: Any, expected: Any, *, array: bool) -> bool:  # noqa: ANN401 - a field's value
    if array:
        return isinstance(value, Collection) and expected in value
    return isinstance(value, str) and expected in value


def _compare(test: Test, value: Any, expected: Any) -> bool:  # noqa: ANN401 - a field's value
    if test is Test.EQ:
        return value == expected
    if test is Test.LT:
        return value < expected
    if test is Test.LTE:
        return value <= expected
    if test is Test.GT:
        return value > expected
    return value >= expected
