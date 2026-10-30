"""The syntax tree of a parsed query: every alternative and its ``getText()`` (DSL-05).

Read from ``AtlasDSLParser.g4`` of Apache Atlas 2.4.0 and the parts of it ``DSLVisitor`` reads; queries from
``GremlinQueryComposerTest`` and ``DSLQueriesTest`` where they show a rule.
"""

import pytest
from aurelius_atlas_dsl.atlas_dsl import parse
from aurelius_atlas_dsl.dsl_tree import (
    ArithE,
    ArithERight,
    BoolOperator,
    ComparisonClause,
    CompE,
    CountClause,
    Expr,
    ExprRight,
    FromClause,
    FromExpression,
    Group,
    GroupByExpression,
    HasClause,
    HasTermClause,
    Identifier,
    IsClause,
    LimitOffset,
    Literal,
    LiteralKind,
    MaxClause,
    MinClause,
    MultiE,
    MultiERight,
    Operator,
    OrderByExpr,
    SelectExpression,
    SumClause,
    WhereClause,
)

COVERS = pytest.mark.covers("aurelius_atlas_dsl.tree_builder.build_query", rules=["DSL-05"])


def _arith(text: str, atom: Identifier | Literal | Group | None = None) -> ArithE:
    """An ``arithE`` of one operand."""
    atom_e = atom or Identifier(text)
    return ArithE(MultiE(atom_e, (), text), (), text)


def _expr(comp_e: CompE, text: str) -> Expr:
    """An ``expr`` of one condition."""
    return Expr(comp_e, (), text)


def _only_expr(query: str) -> Expr:
    source = parse(query).sources[0]
    assert isinstance(source, Expr)
    return source


@COVERS
def test__a_from_clause_keeps_from_apart_from_a_bare_source() -> None:
    """``from DB`` is a ``fromClause``; ``DB`` alone a ``fromExpression``."""
    with_from = parse("from DB").sources[0]
    bare = parse("DB").sources[0]
    assert with_from == FromClause(FromExpression(Identifier("DB"), None, None, "DB"), "fromDB")
    assert bare == FromExpression(Identifier("DB"), None, None, "DB")


@COVERS
def test__an_alias_names_the_source() -> None:
    """``aliasExpr``: the source and the identifier after ``as``."""
    source = parse("DB as d select d").sources[0]
    assert source == FromExpression(Identifier("DB"), Identifier("d"), None, "DBasd")


@COVERS
def test__an_alias_of_a_literal_keeps_the_literal_as_source() -> None:
    """A ``literal`` source of an ``aliasExpr`` is the source, its only identifier the alias."""
    source = parse("1 as d").sources[0]
    assert source == FromExpression(Literal(LiteralKind.NUMBER, "1"), Identifier("d"), None, "1asd")


@COVERS
def test__a_where_without_a_source_is_a_where_clause() -> None:
    """``singleQrySrc`` may be a ``whereClause`` alone."""
    source = parse("where a = 1").sources[0]
    comparison = ComparisonClause(_arith("a"), Operator.EQ, "=", _arith("1", Literal(LiteralKind.NUMBER, "1")), "a=1")
    assert source == WhereClause(_expr(comparison, "a=1"), "wherea=1")


@COVERS
def test__sources_record_whether_commas_delimit_them() -> None:
    """``commaDelimitedQueries`` or ``spaceDelimitedQueries``; ANTLR reads a single source as comma delimited."""
    comma = parse("hive_table as t, sd, hive_column as c")
    space = parse("hive_table hive_column")
    assert (comma.comma_delimited, [s.text for s in comma.sources]) == (True, ["hive_tableast", "sd", "hive_columnasc"])
    assert (space.comma_delimited, [s.text for s in space.sources]) == (False, ["hive_table", "hive_column"])
    assert parse("hive_table").comma_delimited is True


@COVERS
def test__conditions_are_joined_left_to_right() -> None:
    """``expr``: the first condition and each ``exprRight`` in order, ``and``/``or`` as written in any case."""
    where = parse("t where a = 1 AND b = 2 or c = 3").sources[0]
    assert isinstance(where, FromExpression)
    assert where.where is not None
    expr = where.where.expr
    assert [right.operator for right in expr.rights] == [BoolOperator.AND, BoolOperator.OR]
    assert [right.text for right in expr.rights] == ["ANDb=2", "orc=3"]
    assert isinstance(expr.rights[0], ExprRight)
    assert expr.text == "a=1ANDb=2orc=3"


@COVERS
@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("<", Operator.LT),
        ("lte", Operator.LTE),
        ("=", Operator.EQ),
        ("neq", Operator.NEQ),
        (">", Operator.GT),
        (">=", Operator.GTE),
        ("like", Operator.LIKE),
    ],
)
def test__a_comparison_keeps_its_operator_and_spelling(operator: str, expected: Operator) -> None:
    """Every ``operator`` token, with its text as written (``DSLVisitor`` upper-cases that text)."""
    where = parse(f"t where a {operator} 'x'").sources[0]
    assert isinstance(where, FromExpression)
    assert where.where is not None
    comparison = where.where.expr.comp_e
    assert isinstance(comparison, ComparisonClause)
    assert (comparison.operator, comparison.operator_text) == (expected, operator)


@COVERS
def test__arithmetic_keeps_its_operands_and_operators() -> None:
    """``arithE`` and ``multiE``: operands and the ``+ - * /`` between them; parentheses are a ``Group``."""
    expr = _only_expr("a + b * (c - d) / e")
    arith = expr.comp_e
    assert isinstance(arith, ArithE)
    assert arith.multi_e == MultiE(Identifier("a"), (), "a")
    (right,) = arith.rights
    assert isinstance(right, ArithERight)
    assert right.operator == "+"
    product = right.multi_e
    assert [r.operator for r in product.rights] == ["*", "/"]
    assert isinstance(product.rights[0], MultiERight)
    group = product.rights[0].atom_e
    assert isinstance(group, Group)
    assert group.text == "(c-d)"
    assert group.expr.text == "c-d"


@COVERS
@pytest.mark.parametrize(("keyword", "query"), [("isa", "Table isa Dimension"), ("IS", "Table IS Dimension")])
def test__an_is_clause_keeps_its_keyword_and_classification(keyword: str, query: str) -> None:
    """``isClause`` with ``isa`` or ``is`` as written, and an identifier target."""
    is_clause = _only_expr(query).comp_e
    assert is_clause == IsClause(_arith("Table"), keyword, Identifier("Dimension"), f"Table{keyword}Dimension")


@COVERS
def test__has_and_has_term_clauses() -> None:
    """``hasClause`` names an attribute; ``hasTermClause`` a term."""
    has = _only_expr("Table has name").comp_e
    has_term = _only_expr('Table hasTerm "sales@glossary"').comp_e
    assert has == HasClause(_arith("Table"), Identifier("name"), "Tablehasname")
    assert has_term == HasTermClause(_arith("Table"), Identifier('"sales@glossary"'), 'TablehasTerm"sales@glossary"')


@COVERS
def test__the_select_clause_keeps_aggregates_and_labels() -> None:
    """``selectExpr``: each ``selectExpression``, its ``as`` label, ``count()``, ``max``, ``min``, ``sum``."""
    query = parse("from Person select count() as 'count', max(age), min(age), sum(Person.age) as s, name")
    assert query.select is not None
    expressions = query.select.expressions
    assert expressions[0] == SelectExpression(
        _expr(CountClause("count()"), "count()"), Identifier("'count'"), "count()as'count'"
    )
    age = _expr(_arith("age"), "age")
    assert expressions[1].expr.comp_e == MaxClause(age, "max(age)")
    assert expressions[2].expr.comp_e == MinClause(age, "min(age)")
    assert expressions[3].expr.comp_e == SumClause(_expr(_arith("Person.age"), "Person.age"), "sum(Person.age)")
    assert expressions[3].alias == Identifier("s")
    assert expressions[4].alias is None
    assert query.select.text == "count()as'count',max(age),min(age),sum(Person.age)ass,name"


@COVERS
def test__group_by_order_by_limit_and_offset() -> None:
    """``groupByExpression``, ``orderByExpr`` with its sort order as written, ``limitOffset``."""
    query = parse("from DB groupby (owner) select owner orderby (owner) DESC limit 10 offset 1")
    assert query.group_by is not None
    assert isinstance(query.group_by, GroupByExpression)
    assert query.group_by.text == "groupby(owner)"
    assert query.group_by.select_expr.text == "owner"
    assert query.order_by is not None
    assert (query.order_by.sort_order, query.order_by.expr.text) == ("DESC", "(owner)")
    assert query.limit_offset == LimitOffset("10", "1", "limit10offset1")


@COVERS
def test__an_order_by_without_sort_order() -> None:
    """Without ``asc`` or ``desc`` the sort order is ``None``; a limit without offset has none."""
    query = parse("from DB orderby name limit 5")
    assert query.order_by == OrderByExpr(_expr(_arith("name"), "name"), None, "orderbyname")
    assert query.limit_offset == LimitOffset("5", None, "limit5")


@COVERS
@pytest.mark.parametrize(
    ("value", "kind"),
    [
        ("true", LiteralKind.BOOL),
        ("FALSE", LiteralKind.BOOL),
        ("42", LiteralKind.NUMBER),
        ("1e5", LiteralKind.NUMBER),
        ("13364.5", LiteralKind.FLOATING_NUMBER),
        ("['a','b']", LiteralKind.VALUE_ARRAY),
    ],
)
def test__literals_keep_their_kind_and_text(value: str, kind: LiteralKind) -> None:
    """``literal``: ``BOOL``, ``NUMBER``, ``FLOATING_NUMBER`` and ``valueArray``; a lone ``ID`` is an identifier."""
    where = parse(f"t where a = {value}").sources[0]
    assert isinstance(where, FromExpression)
    assert where.where is not None
    comparison = where.where.expr.comp_e
    assert isinstance(comparison, ComparisonClause)
    literal = comparison.rhs.multi_e.atom_e
    assert isinstance(literal, Literal)
    assert (literal.kind, literal.text) == (kind, value)


@COVERS
def test__the_query_text_is_its_tokens_joined_up_to_eof() -> None:
    """``query.getText()``: tokens without what was skipped, and ANTLR's ``<EOF>``."""
    assert parse("hive_db  where name = 'x' -- note").text == "hive_dbwherename='x'<EOF>"
