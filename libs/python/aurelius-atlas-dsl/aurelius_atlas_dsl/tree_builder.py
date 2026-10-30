"""Turns ANTLR's parse tree of a query into the nodes of ``dsl_tree`` (DD-218, DSL-05).

Each function reads one context of ``AtlasDSLParser``: the parts ``DSLVisitor`` reads through the generated
accessors, here by their context class or token type, which pyright can follow. A context that ``parse`` accepted
always has the parts its rule requires.
"""

from antlr4 import ParserRuleContext
from antlr4.tree.Tree import TerminalNodeImpl

from aurelius_atlas_dsl.dsl_tree import (
    ArithE,
    ArithERight,
    AtomE,
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
    Query,
    SelectExpr,
    SelectExpression,
    SingleQrySrc,
    SumClause,
    WhereClause,
)
from aurelius_atlas_dsl.generated.AtlasDSLParser import AtlasDSLParser as P

_OPERATORS = {
    P.K_LT: Operator.LT,
    P.K_LTE: Operator.LTE,
    P.K_EQ: Operator.EQ,
    P.K_NEQ: Operator.NEQ,
    P.K_GT: Operator.GT,
    P.K_GTE: Operator.GTE,
    P.K_LIKE: Operator.LIKE,
}
_LITERAL_TOKENS = {
    P.BOOL: LiteralKind.BOOL,
    P.NUMBER: LiteralKind.NUMBER,
    P.FLOATING_NUMBER: LiteralKind.FLOATING_NUMBER,
    P.ID: LiteralKind.ID,
}


def build_query(ctx: P.QueryContext) -> Query:
    """The ``Query`` of a parsed ``query`` context.

    Args:
        ctx: The context ``AtlasDSLParser.query`` returned without a syntax error.

    Returns:
        Its syntax tree; the query's text ends in ``<EOF>``, as ``getText()`` gives it.
    """
    query_src = _child(ctx, P.QuerySrcContext)
    comma_delimited = _optional(query_src, P.CommaDelimitedQueriesContext)
    delimited = comma_delimited or _child(query_src, P.SpaceDelimitedQueriesContext)
    group_by = _optional(ctx, P.GroupByExpressionContext)
    select = _optional(ctx, P.SelectClauseContext)
    order_by = _optional(ctx, P.OrderByExprContext)
    limit_offset = _optional(ctx, P.LimitOffsetContext)
    return Query(
        sources=tuple(_single_qry_src(src) for src in _children(delimited, P.SingleQrySrcContext)),
        comma_delimited=comma_delimited is not None,
        group_by=_group_by(group_by) if group_by else None,
        select=_select_expr(_child(select, P.SelectExprContext)) if select else None,
        order_by=_order_by(order_by) if order_by else None,
        limit_offset=_limit_offset(limit_offset) if limit_offset else None,
        text=ctx.getText(),
    )


def _single_qry_src(ctx: P.SingleQrySrcContext) -> SingleQrySrc:
    if from_clause := _optional(ctx, P.FromClauseContext):
        return FromClause(_from_expression(_child(from_clause, P.FromExpressionContext)), from_clause.getText())
    if where_clause := _optional(ctx, P.WhereClauseContext):
        return _where_clause(where_clause)
    if from_expression := _optional(ctx, P.FromExpressionContext):
        return _from_expression(from_expression)
    return _expr(_child(ctx, P.ExprContext))


def _from_expression(ctx: P.FromExpressionContext) -> FromExpression:
    from_src = _child(ctx, P.FromSrcContext)
    where_clause = _optional(ctx, P.WhereClauseContext)
    source_ctx = _optional(from_src, P.AliasExprContext) or from_src
    identifiers = [_identifier(identifier) for identifier in _children(source_ctx, P.IdentifierContext)]
    literal = _optional(source_ctx, P.LiteralContext)
    source = _literal(literal) if literal else identifiers.pop(0)
    alias = identifiers[0] if identifiers else None
    return FromExpression(source, alias, _where_clause(where_clause) if where_clause else None, ctx.getText())


def _where_clause(ctx: P.WhereClauseContext) -> WhereClause:
    return WhereClause(_expr(_child(ctx, P.ExprContext)), ctx.getText())


def _group_by(ctx: P.GroupByExpressionContext) -> GroupByExpression:
    return GroupByExpression(_select_expr(_child(ctx, P.SelectExprContext)), ctx.getText())


def _select_expr(ctx: P.SelectExprContext) -> SelectExpr:
    expressions = tuple(
        SelectExpression(
            _expr(_child(expression, P.ExprContext)),
            _identifier(alias) if (alias := _optional(expression, P.IdentifierContext)) else None,
            expression.getText(),
        )
        for expression in _children(ctx, P.SelectExpressionContext)
    )
    return SelectExpr(expressions, ctx.getText())


def _order_by(ctx: P.OrderByExprContext) -> OrderByExpr:
    sort_order = _optional(ctx, P.SortOrderContext)
    return OrderByExpr(_expr(_child(ctx, P.ExprContext)), sort_order.getText() if sort_order else None, ctx.getText())


def _limit_offset(ctx: P.LimitOffsetContext) -> LimitOffset:
    offset = _optional(ctx, P.OffsetClauseContext)
    return LimitOffset(
        _tokens(_child(ctx, P.LimitClauseContext), P.NUMBER)[0],
        _tokens(offset, P.NUMBER)[0] if offset else None,
        ctx.getText(),
    )


def _expr(ctx: P.ExprContext) -> Expr:
    rights = tuple(
        ExprRight(
            BoolOperator.AND if _tokens(right, P.K_AND) else BoolOperator.OR,
            _comp_e(_child(right, P.CompEContext)),
            right.getText(),
        )
        for right in _children(ctx, P.ExprRightContext)
    )
    return Expr(_comp_e(_child(ctx, P.CompEContext)), rights, ctx.getText())


def _comp_e(ctx: P.CompEContext) -> CompE:  # noqa: PLR0911 - one return per alternative of compE
    text = ctx.getText()
    if comparison := _optional(ctx, P.ComparisonClauseContext):
        lhs, rhs = _children(comparison, P.ArithEContext)
        operator = _child(comparison, P.OperatorContext)
        return ComparisonClause(
            _arith_e(lhs), _OPERATORS[_first_terminal(operator).symbol.type], operator.getText(), _arith_e(rhs), text
        )
    if is_clause := _optional(ctx, P.IsClauseContext):
        keyword = (_tokens(is_clause, P.K_ISA) or _tokens(is_clause, P.K_IS))[0]
        return IsClause(_arith_e(_child(is_clause, P.ArithEContext)), keyword, _target(is_clause), text)
    if has_clause := _optional(ctx, P.HasClauseContext):
        return HasClause(
            _arith_e(_child(has_clause, P.ArithEContext)), _identifier(_child(has_clause, P.IdentifierContext)), text
        )
    if has_term := _optional(ctx, P.HasTermClauseContext):
        return HasTermClause(_arith_e(_child(has_term, P.ArithEContext)), _target(has_term), text)
    if _optional(ctx, P.CountClauseContext):
        return CountClause(text)
    if max_clause := _optional(ctx, P.MaxClauseContext):
        return MaxClause(_expr(_child(max_clause, P.ExprContext)), text)
    if min_clause := _optional(ctx, P.MinClauseContext):
        return MinClause(_expr(_child(min_clause, P.ExprContext)), text)
    if sum_clause := _optional(ctx, P.SumClauseContext):
        return SumClause(_expr(_child(sum_clause, P.ExprContext)), text)
    return _arith_e(_child(ctx, P.ArithEContext))


def _target(ctx: P.IsClauseContext | P.HasTermClauseContext) -> Identifier | Expr:
    identifier = _optional(ctx, P.IdentifierContext)
    return _identifier(identifier) if identifier else _expr(_child(ctx, P.ExprContext))


def _arith_e(ctx: P.ArithEContext) -> ArithE:
    rights = tuple(
        ArithERight(_first_terminal(right).getText(), _multi_e(_child(right, P.MultiEContext)), right.getText())
        for right in _children(ctx, P.ArithERightContext)
    )
    return ArithE(_multi_e(_child(ctx, P.MultiEContext)), rights, ctx.getText())


def _multi_e(ctx: P.MultiEContext) -> MultiE:
    rights = tuple(
        MultiERight(_first_terminal(right).getText(), _atom_e(_child(right, P.AtomEContext)), right.getText())
        for right in _children(ctx, P.MultiERightContext)
    )
    return MultiE(_atom_e(_child(ctx, P.AtomEContext)), rights, ctx.getText())


def _atom_e(ctx: P.AtomEContext) -> AtomE:
    if identifier := _optional(ctx, P.IdentifierContext):
        return _identifier(identifier)
    if literal := _optional(ctx, P.LiteralContext):
        return _literal(literal)
    return Group(_expr(_child(ctx, P.ExprContext)), ctx.getText())


def _identifier(ctx: P.IdentifierContext) -> Identifier:
    return Identifier(ctx.getText())


def _literal(ctx: P.LiteralContext) -> Literal:
    if value_array := _optional(ctx, P.ValueArrayContext):
        return Literal(LiteralKind.VALUE_ARRAY, ctx.getText(), tuple(_tokens(value_array, P.ID)))
    return Literal(_LITERAL_TOKENS[_first_terminal(ctx).symbol.type], ctx.getText())


def _children[T: ParserRuleContext](ctx: ParserRuleContext, kind: type[T]) -> list[T]:
    return [child for child in ctx.children or () if isinstance(child, kind)]


def _optional[T: ParserRuleContext](ctx: ParserRuleContext, kind: type[T]) -> T | None:
    return next(iter(_children(ctx, kind)), None)


def _child[T: ParserRuleContext](ctx: ParserRuleContext, kind: type[T]) -> T:
    return _children(ctx, kind)[0]


def _tokens(ctx: ParserRuleContext, token_type: int) -> list[str]:
    return [
        child.getText()
        for child in ctx.children or ()
        if isinstance(child, TerminalNodeImpl) and child.symbol.type == token_type
    ]


def _first_terminal(ctx: ParserRuleContext) -> TerminalNodeImpl:
    return next(child for child in ctx.children or () if isinstance(child, TerminalNodeImpl))
