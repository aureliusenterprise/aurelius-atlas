"""``DSLVisitor`` and ``GremlinQueryComposer``: the entities a DSL query asks for, as a search query (DD-242).

Atlas's visitor walks the parse tree and its composer writes Gremlin; here one composer walks the syntax tree of
4.3 and writes the filter tree of the basic search (``SearchQuery``), with the name resolution of
``IdentifierHelper.Info`` and ``RegistryBasedLookup``. Semantic errors are collected as Atlas collects them
(DSE-14); a form Aurelius Atlas does not search ends the composition with its reason (DSE-15).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from aurelius_atlas_dsl.atlas_dsl import QueryMetadata
from aurelius_atlas_dsl.dsl_tree import (
    ArithE,
    BoolOperator,
    ComparisonClause,
    CompE,
    Expr,
    FromClause,
    FromExpression,
    HasClause,
    HasTermClause,
    Identifier,
    IsClause,
    Literal,
    LiteralKind,
    Operator,
    Query,
    SingleQrySrc,
    WhereClause,
)
from aurelius_atlas_dsl.dsl_tree import (
    Group as Parenthesised,
)
from aurelius_atlas_model.discovery import Condition
from aurelius_atlas_model.errors import AtlasErrorCode
from aurelius_atlas_model.typedef import ATLAS_TYPE_DATE, IndexType, TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.classification_type import ClassificationType
from aurelius_atlas_typesystem.entity_type import ENTITY_ROOT, EntityType
from aurelius_atlas_typesystem.map_type import MapType
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core import identifier_helper as ih
from aurelius_atlas_core.search_context import ALL_CLASSIFICATIONS, ALL_ENTITY_TYPES, NO_CLASSIFICATIONS
from aurelius_atlas_core.search_fields import KEYWORD, PROPAGATED_TRAIT_NAMES, TRAIT_NAMES, field_name, search_value
from aurelius_atlas_core.search_query import TYPE_NAME_FIELD, Criterion, Filter, Group, SearchQuery, Test

IS_INCOMPLETE = "__isIncomplete"
_NUMERIC = frozenset({"byte", "short", "int", "long", "float", "double", "biginteger", "bigdecimal"})
_ALPHA_NUMERIC = re.compile(r"[a-zA-Z0-9]+")
_ISO8601 = re.compile(r"(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)\.(\d+)Z")
_ISO8601_DATE = re.compile(r"(\d+)-(\d+)-(\d+)")
_TESTS = {
    Operator.EQ: Test.EQ,
    Operator.NEQ: Test.NEQ,
    Operator.LT: Test.LT,
    Operator.LTE: Test.LTE,
    Operator.GT: Test.GT,
    Operator.GTE: Test.GTE,
}
SELECT = "select is not supported yet"
GROUP_BY = "groupby is not supported yet"
REFERRED = "the referred attribute {name} is not supported yet"
CLASSIFICATION_ATTRIBUTE = "classification attributes are not supported yet"
HAS_TERM = "hasTerm is not supported"
IS_A_EXPRESSION = "isa takes a classification name, not an expression"
WHERE_FIRST = "a where clause needs a type or classification before it"
NOT_A_CONDITION = "{text} is not a condition"
ARITHMETIC = "a comparison takes a name and a value, not {text}"
"""The reasons a form is not searched (DSE-15): the first two and the referred and classification attributes until
4.4b (DV-96), the others declared (DV-95)."""
_ANYTHING = Criterion(TYPE_NAME_FIELD, Test.ANYTHING)
_NOTHING = Criterion(TYPE_NAME_FIELD, Test.NOTHING)


class UnsupportedError(Exception):
    """A form of the DSL Aurelius Atlas does not search (DSE-15, DV-95, DV-96)."""


@dataclass(frozen=True)
class _Unknown:
    """``UNKNOWN_TYPE``: the active type after a source that names none."""


_UNKNOWN = _Unknown()
type _Active = EntityType | ClassificationType | str | _Unknown | None
"""The active type: an entity or classification type, ``_CLASSIFIED`` or ``_NOT_CLASSIFIED``, unknown, or none."""


@dataclass(frozen=True)
class _Info:
    """``IdentifierHelper.Info``: a name resolved against the active type."""

    raw: str
    attribute_name: str | None
    attribute: AtlasAttribute | None
    field: str | None
    referred: bool
    classification_attribute: bool

    @property
    def is_primitive(self) -> bool:
        return self.attribute is not None and _is_primitive(self.attribute.attribute_type)


class DslQueryComposer:
    """Composes one query's entity search; ``errors`` holds its semantic errors (DSE-14)."""

    def __init__(self, registry: TypeRegistry, metadata: QueryMetadata, limit: int, offset: int) -> None:
        self._registry = registry
        self._metadata = metadata
        self._limit = limit
        self._offset = offset
        self._active: _Active = None
        self._aliases: dict[str, str] = {}
        self._filters: list[Filter] = []
        self._has_type_source = False
        self.errors: list[str] = []

    def compose(self, query: Query) -> SearchQuery:
        """The search for the entities ``query`` finds (DSE-04 to DSE-12).

        Raises:
            UnsupportedError: For a form Aurelius Atlas does not search (DSE-15).
        """
        if query.select is not None:
            raise UnsupportedError(SELECT)
        if query.group_by is not None:
            raise UnsupportedError(GROUP_BY)
        for source in query.sources:
            self._source(source)
        sort_field, descending = self._order_by(query)
        if self._metadata.has_limit_offset:
            limit, offset = self._metadata.resolved_limit, self._metadata.resolved_offset
        else:
            limit, offset = self._limit, self._offset
        filters = self._filters
        return SearchQuery(
            type_names=None,
            filter=filters[0] if len(filters) == 1 else Group(Condition.AND, tuple(filters)) if filters else None,
            sort_field=sort_field,
            descending=descending,
            offset=offset,
            size=limit,
        )

    def _source(self, source: SingleQrySrc) -> None:
        """``visitFromExpression``, ``visitWhereClause`` and ``visitSingleQrySrc`` (DSE-04, DSE-11)."""
        match source:
            case FromClause(from_expression=from_expression):
                self._from_expression(from_expression)
            case FromExpression():
                self._from_expression(source)
            case WhereClause(expr=expr):
                if self._active is None:
                    raise UnsupportedError(WHERE_FIRST)
                self._add(self._expr(expr, nested=False))
            case Expr():
                if not self._has_type_source:
                    subject = _subject(source.comp_e)
                    if subject is not None:
                        self._add_from(subject.text)
                if self._has_type_source:
                    self._add(self._expr(source, nested=False))

    def _from_expression(self, from_expression: FromExpression) -> None:
        self._add_from(from_expression.source.text)
        if from_expression.alias is not None:
            self._add_alias(from_expression.alias.text)
        if from_expression.where is not None:
            self._add(self._expr(from_expression.where.expr, nested=False))

    def _add(self, found: Filter | None) -> None:
        if found is not None:
            self._filters.append(found)

    def _add_from(self, text: str) -> None:
        """``addFrom``: a type or classification source; a name the active type has is not one (DSE-04, DSE-05)."""
        name = ih.remove_quotes(text)
        if not self._should_register(name):
            attribute = self._attribute(name)
            if attribute is not None and not _is_primitive(attribute.attribute_type):
                raise UnsupportedError(REFERRED.format(name=name))
            return
        self._aliases[name] = name
        if name in {ALL_CLASSIFICATIONS, NO_CLASSIFICATIONS}:
            self._active = name
            self._add(_trait(name))
            return
        found = ENTITY_ROOT if name == ALL_ENTITY_TYPES else self._registry.entity_type(name)
        if found is None:
            found = self._registry.classification_type(name)
        if found is None:
            self._error(AtlasErrorCode.INVALID_DSL_UNKNOWN_TYPE, name)
            self._active = _UNKNOWN
            return
        self._active = found
        if isinstance(found, ClassificationType):
            self._add(_trait(name))
            return
        self._has_type_source = True
        if found is not ENTITY_ROOT:
            self._add(Criterion(TYPE_NAME_FIELD, Test.ANY_OF, frozenset(found.type_and_all_sub_types)))

    def _add_alias(self, alias: str) -> None:
        """``registerAlias``: the alias names the active type; a second of the same name fails (DSE-05)."""
        if alias in self._aliases:
            self._error(AtlasErrorCode.INVALID_DSL_DUPLICATE_ALIAS, alias, self._active_name())
            return
        self._aliases[alias] = self._active_name() or ""

    def _should_register(self, name: str) -> bool:
        """``shouldRegister``: no active type yet, or a name neither the active type nor one of its attributes."""
        return self._active is None or (name != self._active_name() and self._attribute(name) is None)

    def _active_name(self) -> str | None:
        active = self._active
        if isinstance(active, str):
            return active
        return None if active is None or isinstance(active, _Unknown) else str(active.type_name)

    def _attribute(self, name: str | None) -> AtlasAttribute | None:
        """``RegistryBasedLookup.getAttribute`` of the active type: an attribute, also a relationship one."""
        active = self._active
        if isinstance(active, EntityType):
            return active.attribute(name) or (active.relationship_attribute(name) if name else None)
        if isinstance(active, ClassificationType):
            return active.attribute(name)
        return None

    def _expr(self, expr: Expr, *, nested: bool) -> Filter | None:
        """``processExpr``: one condition, or conditions joined left to right as ``processExprRight`` (DSE-11)."""
        if not expr.rights:
            return self._comp_e(expr.comp_e, nested=nested)
        items: list[Filter | None] = [self._comp_e(expr.comp_e, nested=True)]
        previous: BoolOperator | None = None
        for right in expr.rights:
            if previous is not None and right.operator is not previous:
                items = [_joined(previous, items)]
            previous = right.operator
            items.append(self._comp_e(right.comp_e, nested=True))
        return _joined(previous, items)

    def _comp_e(self, comp_e: CompE, *, nested: bool) -> Filter | None:
        match comp_e:
            case ComparisonClause():
                return self._where(comp_e)
            case IsClause(target=Identifier(text=target)):
                if not nested:
                    self._add_from(comp_e.arith_e.text)
                return self._is_a(target)
            case HasClause(identifier=Identifier(text=attribute)):
                if not nested:
                    self._add_from(comp_e.arith_e.text)
                return self._has(attribute)
            case IsClause():
                raise UnsupportedError(IS_A_EXPRESSION)
            case HasTermClause():
                raise UnsupportedError(HAS_TERM)
            case ArithE(multi_e=multi_e, rights=()) if isinstance(multi_e.atom_e, Parenthesised) and not multi_e.rights:
                return self._expr(multi_e.atom_e.expr, nested=nested)
            case _:
                raise UnsupportedError(NOT_A_CONDITION.format(text=comp_e.text))

    def _is_a(self, text: str) -> Filter | None:
        """``addIsA``: entities with the classification, any or none (DSE-10)."""
        if text in {ALL_CLASSIFICATIONS, NO_CLASSIFICATIONS}:
            return _trait(text)
        name = ih.remove_quotes(text)
        known = name.upper() in {ALL_CLASSIFICATIONS, NO_CLASSIFICATIONS} or self._registry.classification_type(name)
        if not known:
            self._error(AtlasErrorCode.INVALID_DSL_UNKNOWN_CLASSIFICATION, name)
            return None
        return _trait(name, named=True)

    def _has(self, text: str) -> Filter | None:
        """``addFromProperty``: entities with a value of a primitive attribute (DSE-10)."""
        info = self._resolve(text)
        if not info.is_primitive:
            self._error(AtlasErrorCode.INVALID_DSL_HAS_PROPERTY, info.raw)
            return None
        return _NOTHING if info.field is None else Criterion(info.field, Test.NOT_NULL)

    def _where(self, comparison: ComparisonClause) -> Filter | None:
        """``addWhere``: an attribute compared with a value (DSE-06 to DSE-09)."""
        lhs = _single(comparison.lhs)
        rhs = _single(comparison.rhs)
        if isinstance(self._active, (ClassificationType, str)):
            self._active = _UNKNOWN
        info = self._resolve(lhs.text)
        if info.classification_attribute:
            raise UnsupportedError(CLASSIFICATION_ATTRIBUTE)
        if info.referred:
            raise UnsupportedError(REFERRED.format(name=info.attribute_name))
        if info.attribute is None:
            self._error(AtlasErrorCode.INVALID_DSL_UNKNOWN_TYPE, info.raw)
            self._error(AtlasErrorCode.INVALID_DSL_QUALIFIED_NAME, info.raw)
            return None
        if not info.is_primitive:
            raise UnsupportedError(REFERRED.format(name=info.attribute_name))
        field = info.field
        if field is None:
            return _NOTHING
        attribute_type = resolved(info.attribute.attribute_type)
        if isinstance(rhs, Literal) and rhs.kind is LiteralKind.VALUE_ARRAY:
            return self._within(field, attribute_type, rhs)
        if info.attribute_name == IS_INCOMPLETE and comparison.operator in {Operator.EQ, Operator.NEQ}:
            return _is_incomplete(field, comparison.operator, rhs.text)
        if comparison.operator is Operator.LIKE:
            return _like(field, info.attribute, rhs.text)
        return self._compare(field, attribute_type, comparison.operator, rhs.text)

    def _compare(self, field: str, attribute_type: AtlasType, operator: Operator, rhs: str) -> Filter | None:
        """``HAS_OPERATOR`` and ``HAS_NOT_OPERATOR`` with the value read as the attribute's type (DSE-06, DSE-07)."""
        element = _element(attribute_type)
        type_name = str(element.type_name)
        string_like = False
        if type_name == ATLAS_TYPE_DATE:
            text = ih.remove_quotes(rhs) if ih.is_quoted(rhs) else rhs
            millis = _java_date_millis(text)
            if millis is None:
                self._error(AtlasErrorCode.INVALID_DSL_INVALID_DATE, text)
                return None
            value: Any = element.get_normalized_value(str(millis))
        else:
            string_like = type_name not in _NUMERIC and not ih.is_true_or_false(rhs)
            value = element.get_normalized_value(ih.remove_quotes(rhs.replace("'", "").replace('"', "")))
        kind = field.partition(".")[0]
        found = None if value is None else search_value(kind, value)
        if found is None:
            return _NOTHING
        test = _TESTS[operator]
        if isinstance(attribute_type, ArrayType) and test is Test.EQ:
            return Criterion(field, Test.ANY_OF, frozenset({found}))
        if test is Test.NEQ and not string_like:
            return Group(Condition.AND, (Criterion(field, Test.NOT_NULL), Criterion(field, Test.NEQ, found)))
        return Criterion(field, test, found)

    def _within(self, field: str, attribute_type: AtlasType, values: Literal) -> Filter:
        """``HAS_OPERATOR`` ``within``: any of a value array's values, read as the attribute's type (DV-91)."""
        element = _element(attribute_type)
        kind = field.partition(".")[0]
        csv = ",".join(values.values).translate(str.maketrans("", "", "[]'\""))
        found = set()
        for text in csv.split(","):
            value = element.get_normalized_value(text)
            converted = None if value is None else search_value(kind, value)
            if converted is not None:
                found.add(converted)
        return Criterion(field, Test.ANY_OF, frozenset(found)) if found else _NOTHING

    def _resolve(self, text: str) -> _Info:
        """``IdentifierHelper.Info``: a name, ``<type>.<attribute>`` or ``<alias>.<attribute>`` (DSE-06)."""
        raw = ih.remove_quotes(text)
        raw = self._aliases.get(raw, raw)
        parts = [part for part in raw.split(".") if part]
        type_name, attribute_name = self._active_name(), None
        referred = classification_attribute = False
        if len(parts) == 2 and self._registry.business_metadata_type(parts[0]) is not None:  # noqa: PLR2004
            parts = [raw]
        if len(parts) == 1:
            type_name, attribute_name = self._aliases.get(parts[0], type_name), parts[0]
        elif len(parts) == 2:  # noqa: PLR2004 - <type>.<attribute>
            if self._attribute(parts[0]) is not None:
                attribute_name, referred = parts[0], True
            else:
                type_name = self._aliases.get(parts[0], parts[0])
                classification_attribute = type_name != self._active_name() and (
                    self._registry.classification_type(type_name) is not None
                )
                attribute_name = parts[1]
        attribute = self._attribute(attribute_name)
        if referred and attribute is not None and _is_primitive(attribute.attribute_type):
            referred = False
        named = self._registry.entity_type(type_name)
        own = named.attribute(attribute_name) if named is not None and attribute is not None else None
        target = own or attribute
        return _Info(
            raw=raw,
            attribute_name=attribute_name,
            attribute=attribute,
            field=None if target is None else field_name(target),
            referred=referred,
            classification_attribute=classification_attribute,
        )

    def _order_by(self, query: Query) -> tuple[str | None, bool]:
        """``addOrderBy``: the sort, entities without a value left out (DSE-12)."""
        order_by = query.order_by
        if order_by is None:
            return None, False
        info = self._resolve(order_by.expr.text.replace("(", "").replace(")", ""))
        if not info.is_primitive or info.field is None:
            self._error(AtlasErrorCode.INVALID_DSL_ORDERBY, info.raw)
            return None, False
        self._filters.append(Criterion(info.field, Test.NOT_NULL))
        descending = order_by.sort_order is not None and order_by.sort_order.lower() == "desc"
        return info.field, descending

    def _error(self, code: AtlasErrorCode, *params: object) -> None:
        self.errors.append(code.message(*params))


def _subject(comp_e: CompE) -> ArithE | None:
    """``inferFromClause``: the subject of an ``isa``, ``is`` or ``has`` that opens a query (DSE-11)."""
    if isinstance(comp_e, (IsClause, HasClause, HasTermClause)):
        return comp_e.arith_e
    return None


def _single(arith_e: ArithE) -> Identifier | Literal:
    """The one name or value of a side of a comparison; arithmetic is not searched (DV-95)."""
    atom = arith_e.multi_e.atom_e
    if arith_e.rights or arith_e.multi_e.rights or isinstance(atom, Parenthesised):
        raise UnsupportedError(ARITHMETIC.format(text=arith_e.text))
    return atom


def _joined(condition: BoolOperator | None, items: Sequence[Filter | None]) -> Group:
    """``addAndClauses``/``addOrClauses``; a condition that composed to nothing holds for every entity."""
    criteria = tuple(_ANYTHING if item is None else item for item in items)
    return Group(Condition.AND if condition is BoolOperator.AND else Condition.OR, criteria)


def _trait(name: str, *, named: bool = False) -> Filter:
    """``TRAIT``, ``ANY_TRAIT`` and ``NO_TRAIT``: attached or propagated, without sub classifications (DSE-04)."""
    if not named and name == ALL_CLASSIFICATIONS:
        return Group(
            Condition.OR, (Criterion(TRAIT_NAMES, Test.NOT_NULL), Criterion(PROPAGATED_TRAIT_NAMES, Test.NOT_NULL))
        )
    if not named and name == NO_CLASSIFICATIONS:
        return Group(
            Condition.AND, (Criterion(TRAIT_NAMES, Test.IS_NULL), Criterion(PROPAGATED_TRAIT_NAMES, Test.IS_NULL))
        )
    names = frozenset({name})
    return Group(
        Condition.OR,
        (Criterion(TRAIT_NAMES, Test.ANY_OF, names), Criterion(PROPAGATED_TRAIT_NAMES, Test.ANY_OF, names)),
    )


def _is_incomplete(field: str, operator: Operator, rhs: str) -> Filter:
    """``addForIsIncompleteClause``: ``1`` or ``true`` incomplete, empty, ``0`` or ``false`` complete (DSE-09)."""
    value = rhs.replace("'", "").replace('"', "")
    incomplete = Criterion(field, Test.EQ, 1)
    complete = Criterion(field, Test.IS_NULL)
    if ih.is_complete_value(value):
        return complete if operator is Operator.EQ else incomplete
    if ih.is_in_complete_value(value):
        return incomplete if operator is Operator.EQ else complete
    number = search_value("long", value)
    if number is None:
        return _NOTHING
    if operator is Operator.EQ:
        return Criterion(field, Test.EQ, number)
    return Group(Condition.AND, (Criterion(field, Test.NOT_NULL), Criterion(field, Test.NEQ, number)))


def _like(field: str, attribute: AtlasAttribute, rhs: str) -> Filter:
    """``STRING_CONTAINS`` or ``TEXT_CONTAINS``: the whole value or one of its words matching (DSE-08, DV-92)."""
    if field.partition(".")[0] != KEYWORD:
        return _NOTHING
    whole = attribute.attribute_def.index_type is IndexType.STRING or not _ALPHA_NUMERIC.fullmatch(
        ih.remove_wildcards(rhs)
    )
    quoted = rhs if ih.is_quoted(rhs) else f"'{rhs}'"
    fixed = ih.get_fixed_reg_ex(quoted)
    pattern = ih.remove_quotes(ih.escape_characters(fixed) if whole else fixed)
    try:
        re.compile(pattern)
    except re.error:
        return _NOTHING
    return Criterion(field, Test.REGEX if whole else Test.WORD_REGEX, pattern)


def _element(attribute_type: AtlasType) -> AtlasType:
    """The type values are read as: an array's or map's element type, else the attribute's."""
    if isinstance(attribute_type, ArrayType):
        return resolved(attribute_type.element_type)
    if isinstance(attribute_type, MapType):
        return resolved(attribute_type.value_type)
    return attribute_type


def _is_primitive(attribute_type: AtlasType) -> bool:
    """``isPrimitive``: a primitive or enum, or an array or map of them."""
    element = _element(resolved(attribute_type))
    return element.category in {TypeCategory.PRIMITIVE, TypeCategory.ENUM}


def _java_date_millis(text: str) -> int | None:
    """``SimpleDateFormat``, lenient, in UTC: ``yyyy-MM-dd'T'HH:mm:ss.SSS'Z'`` then ``yyyy-MM-dd``, of the start
    of ``text``; fields out of range roll over into the next (DSE-06).
    """  # noqa: D205 - one sentence
    found = _ISO8601.match(text) or _ISO8601_DATE.match(text)
    if found is None:
        return None
    fields = [int(group) for group in found.groups()] + [0] * (7 - len(found.groups()))
    year, month, day, hour, minute, second, millis = fields
    try:
        start = datetime(year + (month - 1) // 12, (month - 1) % 12 + 1, 1, tzinfo=UTC)
        moment = start + timedelta(days=day - 1, hours=hour, minutes=minute, seconds=second, milliseconds=millis)
    except ValueError, OverflowError:
        return None
    return int(moment.timestamp() * 1000)
