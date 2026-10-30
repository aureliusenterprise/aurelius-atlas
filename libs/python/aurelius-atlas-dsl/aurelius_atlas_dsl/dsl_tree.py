"""The Atlas DSL's parse tree as typed, immutable nodes (DD-218).

One node per rule of ``AtlasDSLParser.g4`` that ``DSLVisitor`` reads, named after it; a rule that only chooses
(``literal``, ``atomE``, ``compE``, ``fromSrc``, ``singleQrySrc``) is the union of its alternatives, and
``querySrc``, ``selectClause``, ``limitClause`` and ``offsetClause`` are folded into their parent. Every node keeps
``text``, the rule's ``getText()``: its tokens joined without the spaces and comments the lexer skipped (DSL-05).
"""

from dataclasses import dataclass
from enum import Enum


class LiteralKind(Enum):
    """Which token or rule a ``literal`` is."""

    BOOL = "BOOL"
    NUMBER = "NUMBER"
    FLOATING_NUMBER = "FLOATING_NUMBER"
    ID = "ID"
    VALUE_ARRAY = "valueArray"


class Operator(Enum):
    """A comparison's ``operator``; the node keeps the spelling it was written with besides."""

    LT = "K_LT"
    LTE = "K_LTE"
    EQ = "K_EQ"
    NEQ = "K_NEQ"
    GT = "K_GT"
    GTE = "K_GTE"
    LIKE = "K_LIKE"


class BoolOperator(Enum):
    """The connective of an ``exprRight``."""

    AND = "K_AND"
    OR = "K_OR"


@dataclass(frozen=True)
class Identifier:
    """``identifier``: one ``ID`` token, quotes and dots included."""

    text: str


@dataclass(frozen=True)
class Literal:
    """``literal``; ``values`` are the ``ID`` texts of a ``valueArray``, empty for the other kinds."""

    kind: LiteralKind
    text: str
    values: tuple[str, ...] = ()


@dataclass(frozen=True)
class Group:
    """The ``( expr )`` alternative of ``atomE``."""

    expr: Expr
    text: str


type AtomE = Identifier | Literal | Group


@dataclass(frozen=True)
class MultiERight:
    """``multiERight``: ``*`` or ``/`` and an operand."""

    operator: str
    atom_e: AtomE
    text: str


@dataclass(frozen=True)
class MultiE:
    """``multiE``: an operand and the products after it."""

    atom_e: AtomE
    rights: tuple[MultiERight, ...]
    text: str


@dataclass(frozen=True)
class ArithERight:
    """``arithERight``: ``+`` or ``-`` and a product."""

    operator: str
    multi_e: MultiE
    text: str


@dataclass(frozen=True)
class ArithE:
    """``arithE``: a product and the sums after it."""

    multi_e: MultiE
    rights: tuple[ArithERight, ...]
    text: str


@dataclass(frozen=True)
class ComparisonClause:
    """``comparisonClause``; ``operator_text`` is the operator as written (``<`` or ``lt``, any case)."""

    lhs: ArithE
    operator: Operator
    operator_text: str
    rhs: ArithE
    text: str


@dataclass(frozen=True)
class IsClause:
    """``isClause``: ``isa`` or ``is`` (``keyword``, as written) and a classification."""

    arith_e: ArithE
    keyword: str
    target: Identifier | Expr
    text: str


@dataclass(frozen=True)
class HasClause:
    """``hasClause``: an attribute the entity has a value of."""

    arith_e: ArithE
    identifier: Identifier
    text: str


@dataclass(frozen=True)
class HasTermClause:
    """``hasTermClause``: a glossary term assigned to the entity."""

    arith_e: ArithE
    target: Identifier | Expr
    text: str


@dataclass(frozen=True)
class CountClause:
    """``countClause``: ``count()``."""

    text: str


@dataclass(frozen=True)
class MaxClause:
    """``maxClause``: ``max( expr )``."""

    expr: Expr
    text: str


@dataclass(frozen=True)
class MinClause:
    """``minClause``: ``min( expr )``."""

    expr: Expr
    text: str


@dataclass(frozen=True)
class SumClause:
    """``sumClause``: ``sum( expr )``."""

    expr: Expr
    text: str


type CompE = (
    ComparisonClause | IsClause | HasClause | ArithE | CountClause | MaxClause | MinClause | SumClause | HasTermClause
)


@dataclass(frozen=True)
class ExprRight:
    """``exprRight``: ``and`` or ``or`` and the next condition."""

    operator: BoolOperator
    comp_e: CompE
    text: str


@dataclass(frozen=True)
class Expr:
    """``expr``: conditions joined left to right, without precedence between ``and`` and ``or``."""

    comp_e: CompE
    rights: tuple[ExprRight, ...]
    text: str


@dataclass(frozen=True)
class SelectExpression:
    """``selectExpression``: an expression and its ``as`` label."""

    expr: Expr
    alias: Identifier | None
    text: str


@dataclass(frozen=True)
class SelectExpr:
    """``selectExpr``: the expressions of a ``select`` or a ``groupby``."""

    expressions: tuple[SelectExpression, ...]
    text: str


@dataclass(frozen=True)
class WhereClause:
    """``whereClause``."""

    expr: Expr
    text: str


@dataclass(frozen=True)
class FromExpression:
    """``fromExpression``: its ``fromSrc``, as ``source`` and the ``alias`` of an ``aliasExpr``, and its where."""

    source: Identifier | Literal
    alias: Identifier | None
    where: WhereClause | None
    text: str


@dataclass(frozen=True)
class FromClause:
    """``fromClause``: ``from`` and a ``fromExpression``."""

    from_expression: FromExpression
    text: str


type SingleQrySrc = FromClause | WhereClause | FromExpression | Expr


@dataclass(frozen=True)
class GroupByExpression:
    """``groupByExpression``: ``groupby( selectExpr )``."""

    select_expr: SelectExpr
    text: str


@dataclass(frozen=True)
class OrderByExpr:
    """``orderByExpr``; ``sort_order`` is ``asc`` or ``desc`` as written, ``None`` without one."""

    expr: Expr
    sort_order: str | None
    text: str


@dataclass(frozen=True)
class LimitOffset:
    """``limitOffset``: the ``NUMBER`` texts of ``limit`` and ``offset``."""

    limit: str
    offset: str | None
    text: str


@dataclass(frozen=True)
class Query:
    """``query``: its sources (``comma_delimited`` when ``querySrc`` is ``commaDelimitedQueries``) and clauses."""

    sources: tuple[SingleQrySrc, ...]
    comma_delimited: bool
    group_by: GroupByExpression | None
    select: SelectExpr | None
    order_by: OrderByExpr | None
    limit_offset: LimitOffset | None
    text: str
