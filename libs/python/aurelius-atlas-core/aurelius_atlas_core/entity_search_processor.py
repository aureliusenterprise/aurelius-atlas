"""``EntitySearchProcessor``: an entity search as a query of the entity documents (SRC-05 to SRC-08, DD-089).

Atlas's ``EntitySearchProcessor`` with the filter handling of ``SearchProcessor`` (``processSearchAttributes``,
``processDateRange``, ``processPipeSeperatedSystemAttribute``, ``toInMemoryPredicate``) and the predicates of
``SearchPredicateUtil``, which decide what a filter means; the query is answered by the entity documents.
"""

import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.discovery import Condition, FilterCriteria, Operator, SortOrder
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    ATLAS_TYPE_BIGDECIMAL,
    ATLAS_TYPE_BIGINTEGER,
    ATLAS_TYPE_BOOLEAN,
    ATLAS_TYPE_BYTE,
    ATLAS_TYPE_DATE,
    ATLAS_TYPE_DOUBLE,
    ATLAS_TYPE_FLOAT,
    ATLAS_TYPE_INT,
    ATLAS_TYPE_LONG,
    ATLAS_TYPE_SHORT,
)
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.struct_type import StructType

from aurelius_atlas_core.classification_search_processor import ClassificationSearchProcessor
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.search_context import MARKER_END, SearchContext
from aurelius_atlas_core.search_fields import BOOLEAN, KEYWORD, LABEL_DELIMITER, LONG, field_name
from aurelius_atlas_core.search_query import Criterion, Filter, Group, SearchQuery, Test
from aurelius_atlas_core.stored_entity import StoredEntity

INVALID_VALUE = "Invalid value {value} for attribute {name}"
RANGE_DELIMITER = ","
IS_INCOMPLETE = "__isIncomplete"
PIPE_SEPARATED = ("__labels", "__customAttributes", "__classificationNames", "__propagatedClassificationNames")
"""``isPipeSeparatedSystemAttribute``: system attributes Atlas keeps as ``|a|b|``."""
CUSTOM_ATTRIBUTES = "__customAttributes"

_COMPARISONS = {
    Operator.LT: Test.LT,
    Operator.LTE: Test.LTE,
    Operator.GT: Test.GT,
    Operator.GTE: Test.GTE,
    Operator.EQ: Test.EQ,
    Operator.NEQ: Test.NEQ,
}
_STRING_TESTS = {
    Operator.STARTS_WITH: Test.STARTS_WITH,
    Operator.ENDS_WITH: Test.ENDS_WITH,
    Operator.CONTAINS: Test.CONTAINS,
    Operator.LIKE: Test.CONTAINS,  # DV-43: getLIKEPredicateGenerator is a contains
    Operator.NOT_CONTAINS: Test.NOT_CONTAINS,
}
_PRESENCE = {Operator.IS_NULL: Test.IS_NULL, Operator.NOT_NULL: Test.NOT_NULL, Operator.NOT_EMPTY: Test.NOT_EMPTY}
_INTEGRAL = {
    ATLAS_TYPE_BYTE: 2**7,
    ATLAS_TYPE_SHORT: 2**15,
    ATLAS_TYPE_INT: 2**31,
    ATLAS_TYPE_LONG: 2**63,
    ATLAS_TYPE_DATE: 2**63,
}
_FLOATING = (ATLAS_TYPE_FLOAT, ATLAS_TYPE_DOUBLE, ATLAS_TYPE_BIGDECIMAL, ATLAS_TYPE_BIGINTEGER)
_DIGITS = re.compile(r"[+-]?\d+")


class EntitySearchProcessor:
    """The entities of a search's context, paged; ``clock`` is now in epoch milliseconds, for named time ranges."""

    def __init__(self, context: SearchContext, clock: Callable[[], int], facets: tuple[str, ...] = ()) -> None:
        self._context = context
        self._clock = clock
        self._facets = facets
        self.facets: dict[str, list[tuple[str, int]]] = {}
        """The values of the search fields ``facets`` names over every matching entity, once executed (DD-093)."""
        self.result_count = -1
        """``getResultCount``: how many entities match in all, once executed."""
        self.next_offset: int | None = None
        """The offset of the next page when paging by marker; ``-1`` after the last."""

    async def query(self, store: EntityStore) -> SearchQuery:
        """The search as a query of the entity documents, with its classifications' criterion (DD-089, DD-090).

        Raises:
            AtlasError: ``BAD_REQUEST`` for a filter value that is not of its attribute's type (DV-46).
        """
        parameters = self._context.parameters
        entities: Sequence[StructType] = self._context.entity_types
        filters = SearchFilters(self._clock)
        classifications = await ClassificationSearchProcessor(self._context, filters).criterion(store)
        first = self._context.first_type
        sort_attribute = None if first is None or not parameters.sort_by else first.attribute(parameters.sort_by)
        sort_field = None if sort_attribute is None else field_name(sort_attribute)
        marker = self._context.marker
        return SearchQuery(
            type_names=self._context.type_names,
            active_only=parameters.exclude_deleted_entities,
            filter=_all_of(filters.filter(parameters.entity_filters, entities), classifications),
            sort_field=sort_field,
            descending=parameters.sort_order is SortOrder.DESCENDING,
            offset=parameters.offset if marker is None else marker,
            size=parameters.limit,
            text=self._context.text,
            facets=self._facets,
        )

    async def execute(self, store: EntityStore) -> list[StoredEntity]:
        """``execute``: the page of matching entities; with a marker, also the next page's offset (SRC-07, SRC-08)."""
        query = await self.query(store)
        hits = await store.search(query)
        found, self.result_count, self.facets = hits.entities, hits.total, hits.facets
        if self._context.has_tag_filters:
            self.result_count = -1  # ClassificationSearchProcessor.getResultCount without an entity index query
        if self._context.marker is not None:
            self.next_offset = MARKER_END if len(found) < query.size else query.offset + len(found)
        return found


class SearchFilters:
    """Filters as search query criteria; ``clock`` is now in epoch milliseconds, for named time ranges."""

    def __init__(self, clock: Callable[[], int]) -> None:
        self._clock = clock

    def filter(self, criteria: FilterCriteria | None, types: Sequence[StructType]) -> Filter | None:
        """A filter on attributes of ``types``, criteria without a predicate left out, as ``toInMemoryPredicate``
        builds it; a criterion on an attribute several types define matches any of them (SRC-05, CSR-03).
        """  # noqa: D205 - one sentence
        if criteria is None:
            return None
        if criteria.condition is not None and criteria.criterion:
            children = [found for child in criteria.criterion if (found := self.filter(child, types)) is not None]
            return Group(criteria.condition, tuple(children)) if children else None
        if not criteria.attribute_name:
            return None
        criteria_of_types: dict[Criterion, None] = {}
        for struct_type in types:
            found = self._criterion(struct_type, criteria)
            if found is not None:
                criteria_of_types[found] = None
        tests = list(criteria_of_types)
        if not tests:
            return None
        return tests[0] if len(tests) == 1 else Group(Condition.OR, tuple(tests))

    def _criterion(self, struct_type: StructType, criteria: FilterCriteria) -> Criterion | None:
        name = str(criteria.attribute_name)
        attribute = struct_type.attribute(name)
        field = None if attribute is None else field_name(attribute)
        operator, value = criteria.operator, criteria.attribute_value
        if attribute is None or field is None or operator is None:
            return None
        if name == IS_INCOMPLETE:
            operator, value = _incomplete(operator, value)
        if name in PIPE_SEPARATED:
            operator, value = _pipe_separated(name, operator, value)
        return self._test(attribute, field, operator, value)

    def _test(  # noqa: PLR0911 - one predicate per operator
        self, attribute: AtlasAttribute, field: str, operator: Operator, value: str | None
    ) -> Criterion | None:
        kind = field.partition(".")[0]
        array = isinstance(attribute.attribute_type, ArrayType)
        if operator in _PRESENCE:
            return Criterion(field, _PRESENCE[operator], array=array)
        if operator in {Operator.CONTAINS_ANY, Operator.CONTAINS_ALL}:
            return None  # no predicate, no index expression
        if operator is Operator.IN:
            return Criterion(field, Test.NOTHING)
        if array:
            return _array_test(field, kind, operator, value)
        if operator in _STRING_TESTS:
            if kind != KEYWORD or value is None:
                return Criterion(field, Test.NOTHING)
            return Criterion(field, _STRING_TESTS[operator], value)
        if operator is Operator.TIME_RANGE:
            if kind != LONG or not value:
                return Criterion(field, Test.NOTHING)
            start, end = self._time_range(attribute, value)
            return Criterion(field, Test.RANGE, start, end)
        if not value or (kind == BOOLEAN and operator not in {Operator.EQ, Operator.NEQ}):
            return Criterion(field, Test.NOTHING)
        return Criterion(field, _COMPARISONS[operator], _parsed(attribute, value))

    def _time_range(self, attribute: AtlasAttribute, value: str) -> tuple[int, int]:
        """``processDateRange``: a named range in UTC (DV-44), else ``<start>,<end>`` (SRC-06)."""
        named = date_range(value, datetime.fromtimestamp(self._clock() / 1000, UTC))
        if named is not None:
            return named
        parts = value.split(RANGE_DELIMITER)
        if len(parts) != 2:  # noqa: PLR2004 - a start and an end
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, INVALID_VALUE.format(value=value, name=attribute.name))
        return _parsed(attribute, parts[0]), _parsed(attribute, parts[1])


def _all_of(*filters: Filter | None) -> Filter | None:
    present = tuple(found for found in filters if found is not None)
    if not present:
        return None
    return present[0] if len(present) == 1 else Group(Condition.AND, present)


def _array_test(field: str, kind: str, operator: Operator, value: str | None) -> Criterion:
    """An array holds the request's value as given: only a string array can hold it (``attrClass`` ``List``)."""
    holdable = value is not None and kind == KEYWORD
    if operator is Operator.CONTAINS and holdable:
        return Criterion(field, Test.CONTAINS, value, array=True)
    if operator is Operator.NOT_CONTAINS:
        return Criterion(field, Test.NOT_CONTAINS, value, array=True) if holdable else Criterion(field, Test.ANYTHING)
    return Criterion(field, Test.NOTHING)


def _incomplete(operator: Operator, value: str | None) -> tuple[Operator, str | None]:
    """``processSearchAttributes`` on ``__isIncomplete``: complete entities have none (SRC-06)."""
    complete = value is None or value == "0" or value.lower() == "false"
    if operator is Operator.EQ:
        return (Operator.IS_NULL, value) if complete else (Operator.EQ, "1")
    if operator is Operator.NEQ:
        return (Operator.EQ, "1") if complete else (Operator.IS_NULL, value)
    if operator is Operator.NOT_NULL:
        return Operator.EQ, "1"
    return operator, value


def _pipe_separated(  # noqa: PLR0911 - one rewrite per operator
    name: str, operator: Operator, value: str | None
) -> tuple[Operator, str | None]:
    """``processPipeSeperatedSystemAttribute``: an element of ``|a|b|`` (SRC-06)."""
    if value is None:
        return operator, value
    if operator is Operator.STARTS_WITH:
        return Operator.CONTAINS, LABEL_DELIMITER + value
    if operator is Operator.ENDS_WITH:
        return Operator.CONTAINS, value + LABEL_DELIMITER
    if operator is Operator.EQ:
        return Operator.CONTAINS, LABEL_DELIMITER + value + LABEL_DELIMITER
    if operator is Operator.NEQ:
        return Operator.NOT_CONTAINS, LABEL_DELIMITER + value + LABEL_DELIMITER
    if operator in {Operator.CONTAINS, Operator.NOT_CONTAINS} and name == CUSTOM_ATTRIBUTES:
        key, separator, given = value.partition("=")
        if separator:
            return operator, f"{codec.dumps(key).decode()}:{codec.dumps(given).decode()}"
    return operator, value


def _parsed(attribute: AtlasAttribute, value: str) -> Any:  # noqa: ANN401 - a value of the attribute's type
    """``toInMemoryPredicate``'s parsing: the value as the attribute's type.

    Raises:
        AtlasError: ``BAD_REQUEST`` for one that is not (DV-46).
    """
    type_name = str(attribute.attribute_type.type_name)
    invalid = AtlasError(AtlasErrorCode.BAD_REQUEST, INVALID_VALUE.format(value=value, name=attribute.name))
    if type_name in _INTEGRAL:
        bound = _INTEGRAL[type_name]
        if not _DIGITS.fullmatch(value) or not -bound <= int(value) < bound:
            raise invalid
        return int(value)
    if type_name in _FLOATING:
        try:
            return float(value)
        except ValueError as error:
            raise invalid from error
    if type_name == ATLAS_TYPE_BOOLEAN:
        return value.lower() == "true"
    return value


def date_range(name: str, now: datetime) -> tuple[int, int] | None:
    """``processDateRange``'s named ranges from ``now``, in UTC, as epoch milliseconds, both ends included (DV-44)."""
    today = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    month = today.replace(day=1)
    ranges: dict[str, tuple[datetime, datetime]] = {
        "TODAY": (today, today + timedelta(days=1)),
        "YESTERDAY": (today - timedelta(days=1), today),
        "LAST_7_DAYS": (today - timedelta(days=6), today + timedelta(days=1)),
        "LAST_30_DAYS": (today - timedelta(days=29), today + timedelta(days=1)),
        "THIS_MONTH": (month, _months(month, 1)),
        "LAST_MONTH": (_months(month, -1), month),
        "THIS_QUARTER": (_months(month, -1), _months(month, 2)),
        "LAST_QUARTER": (_months(month, -4), _months(month, -1)),
        "LAST_3_MONTHS": (_months(month, -3), month),
        "LAST_6_MONTHS": (_months(month, -6), month),
        "LAST_12_MONTHS": (_months(month, -12), month),
        "THIS_YEAR": (month.replace(month=1), month.replace(year=month.year + 1, month=1)),
        "LAST_YEAR": (month.replace(year=month.year - 1, month=1), month.replace(month=1)),
    }
    if name not in ranges:
        return None
    start, end = ranges[name]
    return _millis(start), _millis(end) - 1


def _months(first: datetime, months: int) -> datetime:
    """The first day of the month ``months`` from the month of ``first``."""
    index = first.year * 12 + first.month - 1 + months
    return first.replace(year=index // 12, month=index % 12 + 1)


def _millis(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)
