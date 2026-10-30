"""``AtlasDSL``: a DSL query parsed by Atlas's grammar, and what its clauses ask for.

``parse`` is ``AtlasDSL.Parser#parse`` with its ``Validator``; ``QueryMetadata`` is ``AtlasDSL.QueryMetadata``.
The translation to a search (``AtlasDSL.Translator``) is increment 4.4's.
"""

import re
from dataclasses import dataclass
from typing import Self, override

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

from aurelius_atlas_dsl.dsl_tree import Query
from aurelius_atlas_dsl.generated.AtlasDSLLexer import AtlasDSLLexer
from aurelius_atlas_dsl.generated.AtlasDSLParser import AtlasDSLParser
from aurelius_atlas_dsl.tree_builder import build_query

_JAVA_INT = re.compile(r"[+-]?[0-9]+")
_INT_MIN = -(2**31)
_INT_MAX = 2**31 - 1


class _Validator(ErrorListener):
    """``AtlasDSL.Validator``: remembers the parser's last syntax error."""

    def __init__(self) -> None:
        self.error_msg: str | None = None

    @override
    def syntaxError(  # ANTLR's ErrorListener method
        self,
        recognizer: object,
        offendingSymbol: object,
        line: int,
        column: int,
        msg: str,
        e: object,
    ) -> None:
        self.error_msg = msg


def parse(query: str) -> Query:
    """Parse a DSL query by Atlas's grammar (DSL-01 to DSL-03).

    Args:
        query: The query as the client sent it.

    Returns:
        The query's syntax tree (DSL-05).

    Raises:
        AtlasError: ``INVALID_DSL_QUERY`` with ANTLR's message of the last syntax error (DSL-04), or naming a
            limit or offset Java cannot read as an ``int`` (DSL-07, DV-83).
    """
    lexer = AtlasDSLLexer(InputStream(query))
    lexer.removeErrorListeners()  # DSL-02: Atlas leaves the lexer's errors to the console
    parser = AtlasDSLParser(CommonTokenStream(lexer))
    parser.removeErrorListeners()
    validator = _Validator()
    parser.addErrorListener(validator)
    context = parser.query()
    if validator.error_msg is not None:
        raise AtlasError(AtlasErrorCode.INVALID_DSL_QUERY, query, validator.error_msg)
    tree = build_query(context)
    if tree.limit_offset is not None:
        for number in (tree.limit_offset.limit, tree.limit_offset.offset):
            if number is not None and _parse_int(number) is None:
                raise AtlasError(AtlasErrorCode.INVALID_DSL_QUERY, query, f'For input string: "{number}"')
    return tree


def _parse_int(text: str) -> int | None:
    """Java's ``Integer.parseInt`` of a ``NUMBER`` token, ``None`` where it throws."""
    if not _JAVA_INT.fullmatch(text):
        return None
    value = int(text)
    return value if _INT_MIN <= value <= _INT_MAX else None


@dataclass(frozen=True)
class QueryMetadata:
    """``AtlasDSL.QueryMetadata``: the clauses a query has, and its limit and offset (DSL-06)."""

    has_select: bool
    has_group_by: bool
    has_order_by: bool
    has_limit_offset: bool
    resolved_limit: int
    resolved_offset: int

    @classmethod
    def of(cls, query: Query) -> Self:
        """The metadata of a query ``parse`` returned.

        Args:
            query: The parsed query.

        Returns:
            Its clauses; the limit and offset 0 where the query has none.
        """
        limit_offset = query.limit_offset
        limit = offset = 0
        if limit_offset is not None:
            limit = _parse_int(limit_offset.limit) or 0
            offset = _parse_int(limit_offset.offset or "0") or 0
        return cls(
            has_select=query.select is not None,
            has_group_by=query.group_by is not None,
            has_order_by=query.order_by is not None,
            has_limit_offset=limit_offset is not None,
            resolved_limit=limit,
            resolved_offset=offset,
        )

    @property
    def need_transformation(self) -> bool:
        """Whether the result is reshaped by a ``select`` (``needTransformation``)."""
        return (self.has_group_by and self.has_select and self.has_order_by) or self.has_select
