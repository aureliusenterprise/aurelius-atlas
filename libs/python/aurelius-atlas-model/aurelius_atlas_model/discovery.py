"""Basic search's request and answer: ``SearchParameters``, ``FilterCriteria`` and ``AtlasSearchResult`` (SRC-01).

Ported from Apache Atlas 2.4.0 ``org.apache.atlas.model.discovery`` and ``org.apache.atlas.SortOrder``.
"""

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BeforeValidator, PlainSerializer

from aurelius_atlas_model.base import AtlasModel, JavaBool, JavaInt, OptionalNameSet
from aurelius_atlas_model.instance.entity_header import AtlasEntityHeader


class SortOrder(StrEnum):
    """``org.apache.atlas.SortOrder``."""

    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class Operator(StrEnum):
    """``SearchParameters.Operator``: written as its first symbol, read by any (``fromString``)."""

    LT = "LT"
    GT = "GT"
    LTE = "LTE"
    GTE = "GTE"
    EQ = "EQ"
    NEQ = "NEQ"
    IN = "IN"
    LIKE = "LIKE"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    CONTAINS_ANY = "CONTAINS_ANY"
    CONTAINS_ALL = "CONTAINS_ALL"
    IS_NULL = "IS_NULL"
    NOT_NULL = "NOT_NULL"
    TIME_RANGE = "TIME_RANGE"
    NOT_EMPTY = "NOT_EMPTY"

    @property
    def symbols(self) -> tuple[str, ...]:
        """The symbols it is read by; the first is the one it is written as."""
        return SYMBOLS[self]

    @classmethod
    def from_symbol(cls, symbol: object) -> Operator | None:
        """``fromString``: the operator with the symbol, or None (SRC-01)."""
        if isinstance(symbol, Operator):
            return symbol
        return _BY_SYMBOL.get(symbol) if isinstance(symbol, str) else None


SYMBOLS: dict[Operator, tuple[str, ...]] = {
    Operator.LT: ("<", "lt"),
    Operator.GT: (">", "gt"),
    Operator.LTE: ("<=", "lte"),
    Operator.GTE: (">=", "gte"),
    Operator.EQ: ("=", "eq"),
    Operator.NEQ: ("!=", "neq"),
    Operator.IN: ("in", "IN"),
    Operator.LIKE: ("like", "LIKE"),
    Operator.STARTS_WITH: ("startsWith", "STARTSWITH", "begins_with", "BEGINS_WITH"),
    Operator.ENDS_WITH: ("endsWith", "ENDSWITH", "ends_with", "ENDS_WITH"),
    Operator.CONTAINS: ("contains", "CONTAINS"),
    Operator.NOT_CONTAINS: ("not_contains", "NOT_CONTAINS"),
    Operator.CONTAINS_ANY: ("containsAny", "CONTAINSANY", "contains_any", "CONTAINS_ANY"),
    Operator.CONTAINS_ALL: ("containsAll", "CONTAINSALL", "contains_all", "CONTAINS_ALL"),
    Operator.IS_NULL: ("isNull", "ISNULL", "is_null", "IS_NULL"),
    Operator.NOT_NULL: ("notNull", "NOTNULL", "not_null", "NOT_NULL"),
    Operator.TIME_RANGE: ("timerange", "TIMERANGE", "time_range", "TIME_RANGE"),
    Operator.NOT_EMPTY: ("notEmpty", "NOTEMPTY", "not_empty", "NOT_EMPTY"),
}
"""``Operator``'s symbols, as Java declares them."""

_BY_SYMBOL = {symbol: operator for operator, symbols in SYMBOLS.items() for symbol in symbols}

type OperatorField = Annotated[
    Operator | None,
    BeforeValidator(Operator.from_symbol),
    PlainSerializer(lambda operator: None if operator is None else operator.symbols[0], return_type=str | None),
]
"""An operator read by any symbol, an unknown one as none, and written as its first symbol (SRC-01)."""


class Condition(StrEnum):
    """``FilterCriteria.Condition``."""

    AND = "AND"
    OR = "OR"


class FilterCriteria(AtlasModel):
    """``FilterCriteria``: a condition over criteria, or an attribute, an operator and a value."""

    attribute_name: str | None = None
    operator: OperatorField = None
    attribute_value: str | None = None
    condition: Condition | None = None
    criterion: list[FilterCriteria] | None = None


class SearchParameters(AtlasModel):
    """``SearchParameters``: what a basic search looks for, how its answer is sorted and paged (SRC-01)."""

    query: str | None = None
    type_name: str | None = None
    classification: str | None = None
    relationship_name: str | None = None
    term_name: str | None = None
    sort_by: str | None = None
    exclude_deleted_entities: JavaBool = False
    include_classification_attributes: JavaBool = False
    include_sub_types: Annotated[bool, BeforeValidator(lambda value: True if value is None else value)] = True
    include_sub_classifications: Annotated[bool, BeforeValidator(lambda value: True if value is None else value)] = True
    exclude_header_attributes: JavaBool = False
    limit: JavaInt = 0
    offset: JavaInt = 0
    marker: str | None = None
    entity_filters: FilterCriteria | None = None
    tag_filters: FilterCriteria | None = None
    relationship_filters: FilterCriteria | None = None
    attributes: OptionalNameSet = None
    sort_order: SortOrder | None = None


class AtlasQueryType(StrEnum):
    """``AtlasSearchResult.AtlasQueryType``."""

    DSL = "DSL"
    FULL_TEXT = "FULL_TEXT"
    GREMLIN = "GREMLIN"
    BASIC = "BASIC"
    ATTRIBUTE = "ATTRIBUTE"
    RELATIONSHIP = "RELATIONSHIP"


class AttributeSearchResult(AtlasModel):
    """``AttributeSearchResult``: attribute names and, per entity, their values (SRC-10)."""

    name: list[str] | None = None
    values: list[list[Any]] | None = None


class AtlasSearchResult(AtlasModel):
    """``AtlasSearchResult``: the entities a search found, and how it was asked (SRC-09)."""

    query_type: AtlasQueryType | None = None
    search_parameters: SearchParameters | None = None
    query_text: str | None = None
    type: str | None = None
    classification: str | None = None
    entities: list[AtlasEntityHeader] | None = None
    relations: list[dict[str, Any]] | None = None
    attributes: AttributeSearchResult | None = None
    full_text_result: list[dict[str, Any]] | None = None
    referred_entities: dict[str, AtlasEntityHeader] | None = None
    approximate_count: int = -1
    next_marker: str | None = None

    def add_entity(self, header: AtlasEntityHeader) -> None:
        """``addEntity``: append the header, replacing one of the same GUID."""
        entities = [entity for entity in self.entities or [] if entity.guid != header.guid]
        self.entities = [*entities, header]
