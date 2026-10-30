"""Parsing a DSL query and reading its metadata (DSL-01 to DSL-04, DSL-06, DSL-07).

Read from ``AtlasDSL`` and the grammar ``AtlasDSLLexer.g4``/``AtlasDSLParser.g4`` of Apache Atlas 2.4.0, and its
tests ``DSLParsingTest`` (``testInvalidDSL``), ``GremlinQueryComposerTest`` and ``DSLQueriesTest``, whose queries
``fixtures/atlas_queries.json`` holds with their source lines.
"""

import json
from pathlib import Path

import pytest
from aurelius_atlas_dsl.atlas_dsl import QueryMetadata, parse
from aurelius_atlas_dsl.dsl_tree import (
    ArithE,
    ComparisonClause,
    Expr,
    FromExpression,
    HasTermClause,
    Identifier,
    Literal,
    LiteralKind,
    Operator,
    WhereClause,
)
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

A = "aurelius_atlas_dsl.atlas_dsl"

_FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "atlas_queries.json").read_text(encoding="utf-8"))
_QUERIES = [pytest.param(row["query"], row["parses"], id=row["source"]) for row in _FIXTURE["queries"]]


def _source(query: str) -> FromExpression:
    source = parse(query).sources[0]
    assert isinstance(source, FromExpression)
    return source


def _condition(query: str) -> ComparisonClause:
    where = _source(query).where
    assert where is not None
    comp_e = where.expr.comp_e
    assert isinstance(comp_e, ComparisonClause)
    return comp_e


def _atom(arith_e: ArithE) -> object:
    return arith_e.multi_e.atom_e


@pytest.mark.covers(f"{A}.parse", rules=["DSL-03", "DSL-04"])
@pytest.mark.parametrize(("query", "parses"), _QUERIES)
def test__parse_reads_atlas_test_queries_as_atlas_does(query: str, parses: bool) -> None:  # noqa: FBT001
    """Atlas's own test queries parse, and ``DSLParsingTest``'s invalid ones fail with ``INVALID_DSL_QUERY``."""
    if parses:
        assert parse(query).text.endswith("<EOF>")
    else:
        with pytest.raises(AtlasError) as raised:
            parse(query)
        assert raised.value.code is AtlasErrorCode.INVALID_DSL_QUERY


@pytest.mark.covers(f"{A}.parse", rules=["DSL-04"])
def test__parse_reports_antlrs_message_of_the_last_syntax_error() -> None:
    """The reason is ANTLR's message, inside Atlas's ``INVALID_DSL_QUERY`` text."""
    query = "db orderby(name) orderby(owner)"
    with pytest.raises(AtlasError) as raised:
        parse(query)
    assert raised.value.code is AtlasErrorCode.INVALID_DSL_QUERY
    assert str(raised.value) == (
        "Invalid DSL query: db orderby(name) orderby(owner) | Reason: mismatched input 'orderby' expecting "
        "{<EOF>, K_LIMIT}. Please refer to Atlas DSL grammar for more information"
    )


@pytest.mark.covers(f"{A}.parse", rules=["DSL-03", "DSL-04"])
@pytest.mark.parametrize("query", ["", "where", "hive_table where", "hive_table limit", "hive_table select"])
def test__parse_rejects_an_incomplete_query(query: str) -> None:
    """The tokens must make up a whole ``query``, up to the end of the input."""
    with pytest.raises(AtlasError) as raised:
        parse(query)
    assert raised.value.code is AtlasErrorCode.INVALID_DSL_QUERY


@pytest.mark.covers(f"{A}.parse", rules=["DSL-01"])
def test__parse_reads_keywords_in_any_case() -> None:
    """``WHERE``, ``Where`` and ``where`` are one keyword; ``LT`` is ``<``."""
    lower = _condition("t where a < 1")
    upper = _condition("t WHERE a LT 1")
    assert (lower.operator, upper.operator) == (Operator.LT, Operator.LT)
    assert (lower.operator_text, upper.operator_text) == ("<", "LT")


@pytest.mark.covers(f"{A}.parse", rules=["DSL-01"])
@pytest.mark.parametrize(
    ("query", "lhs"),
    [
        ("t where db.name = 1", "db.name"),
        ("t where fromDate = 1", "fromDate"),
        ("t where likes = 1", "likes"),
        ("t where `a b` = 1", "`a b`"),
    ],
)
def test__parse_reads_names_joined_to_keywords_as_one_identifier(query: str, lhs: str) -> None:
    """The longest match wins: a dotted name or a keyword run into letters is one ``ID``, as is a quoted string."""
    assert _atom(_condition(query).lhs) == Identifier(lhs)


@pytest.mark.covers(f"{A}.parse", rules=["DSL-01"])
def test__parse_splits_a_second_dot_into_a_new_identifier() -> None:
    """``a.b.c`` lexes as ``a.b`` and ``.c``: ``ID`` allows one run of keywords between letters."""
    query = parse("a.b.c")
    assert [source.text for source in query.sources] == ["a.b", ".c"]


@pytest.mark.covers(f"{A}.parse", rules=["DSL-01"])
def test__parse_reads_a_signed_number_as_one_token() -> None:
    """``-5`` after a space is a ``NUMBER``, so ``a -5`` is two sources, the second a literal, not a subtraction."""
    query = parse("a -5")
    assert [source.text for source in query.sources] == ["a", "-5"]
    assert query.sources[1] == FromExpression(Literal(LiteralKind.NUMBER, "-5"), None, None, "-5")


@pytest.mark.covers(f"{A}.parse", rules=["DSL-01"])
def test__parse_skips_whitespace_and_comments() -> None:
    """Spaces, line breaks, ``--`` and ``/* */`` comments are on the hidden channel."""
    plain = parse("t where a = 1")
    spaced = parse("t\n\twhere /* why */ a   =\r\n1 -- trailing")
    assert spaced == plain


@pytest.mark.covers(f"{A}.parse", rules=["DSL-02"])
def test__parse_drops_a_character_no_token_begins_with() -> None:
    """``@`` begins no token: it is dropped, and the term is read as two names (``DSLQueriesTest`` errorQueries)."""
    query = parse("hive_table hasTerm modernTrade@salesGlossary")
    term = query.sources[0]
    assert isinstance(term, Expr)
    assert isinstance(term.comp_e, HasTermClause)
    assert term.comp_e.target == Identifier("modernTrade")
    assert query.sources[1].text == "salesGlossary"


@pytest.mark.covers(f"{A}.parse", rules=["DSL-02"])
def test__parse_keeps_a_quoted_at_sign() -> None:
    """Inside quotes ``@`` is part of the string (``GremlinQueryComposerTest.glossaryTermQueries``)."""
    term = parse('Table hasTerm "sales@glossary"').sources[0]
    assert isinstance(term, Expr)
    assert isinstance(term.comp_e, HasTermClause)
    assert term.comp_e.target == Identifier('"sales@glossary"')


@pytest.mark.covers(f"{A}.parse", rules=["DSL-01"])
def test__parse_reads_a_value_array() -> None:
    """``[ ... ]`` is a ``valueArray`` literal of the ``ID`` tokens in it."""
    rhs = _atom(_condition("Asset where name=['t1', 't2', 't3']").rhs)
    assert rhs == Literal(LiteralKind.VALUE_ARRAY, "['t1','t2','t3']", ("'t1'", "'t2'", "'t3'"))


@pytest.mark.covers(f"{A}.parse", f"{A}.QueryMetadata.of", rules=["DSL-07"])
@pytest.mark.parametrize("query", ["t limit 1e3", "t limit 3000000000", "t limit 10 offset 2147483648"])
def test__parse_rejects_a_limit_java_cannot_read_as_int(query: str) -> None:
    """A ``NUMBER`` ``Integer.parseInt`` rejects fails the query, naming the number (DV-88)."""
    with pytest.raises(AtlasError) as raised:
        parse(query)
    assert raised.value.code is AtlasErrorCode.INVALID_DSL_QUERY
    assert 'For input string: "' in str(raised.value)


@pytest.mark.covers(f"{A}.QueryMetadata.of", rules=["DSL-06"])
@pytest.mark.parametrize(
    ("query", "limit", "offset"),
    [
        ("t", 0, 0),
        ("t limit 5", 5, 0),
        ("t limit 5 offset 36", 5, 36),
        ("t limit +7 offset -1", 7, -1),
        ("t limit 2147483647", 2147483647, 0),
    ],
)
def test__query_metadata_resolves_limit_and_offset(query: str, limit: int, offset: int) -> None:
    """The ``limit`` and ``offset`` numbers as ``Integer.parseInt`` reads them; 0 where absent."""
    metadata = QueryMetadata.of(parse(query))
    assert (metadata.has_limit_offset, metadata.resolved_limit, metadata.resolved_offset) == (
        query != "t",
        limit,
        offset,
    )


@pytest.mark.covers(f"{A}.QueryMetadata.of", f"{A}.QueryMetadata.need_transformation", rules=["DSL-06"])
@pytest.mark.parametrize(
    ("query", "clauses", "transform"),
    [
        ("from DB", (False, False, False), False),
        ("from DB select DB.name", (True, False, False), True),
        ("from DB groupby (owner) select count()", (True, True, False), True),
        ("from DB orderby name", (False, False, True), False),
        ("from DB groupby (owner) select owner orderby owner", (True, True, True), True),
    ],
)
def test__query_metadata_tells_the_clauses(query: str, clauses: tuple[bool, bool, bool], transform: bool) -> None:  # noqa: FBT001
    """``select``, ``groupby`` and ``orderby`` are told apart; a ``select`` needs the result reshaped."""
    metadata = QueryMetadata.of(parse(query))
    assert (metadata.has_select, metadata.has_group_by, metadata.has_order_by) == clauses
    assert metadata.need_transformation is transform


@pytest.mark.covers(f"{A}.parse", rules=["DSL-03"])
def test__parse_takes_antlrs_reading_of_an_ambiguous_source() -> None:
    """``t where a = 1`` is a ``fromExpression`` with its where, not the source ``t`` and a ``whereClause``."""
    query = parse("t where a = 1")
    assert len(query.sources) == 1
    source = query.sources[0]
    assert isinstance(source, FromExpression)
    assert isinstance(source.where, WhereClause)
