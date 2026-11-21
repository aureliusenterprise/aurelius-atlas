"""``es_clauses``: every clause core emits comes from one module (QRY-01, DD-767).

These tests pin the JSON shape each builder returns, because that dictionary is the wire contract the store and
its fake both read. The bodies moved here unchanged, so the assertions are the ones the builders always had to hold.
"""

from typing import Any

import pytest
from aurelius_atlas_core import es_clauses
from aurelius_atlas_core.entity_embedding import VECTOR_FIELD
from aurelius_atlas_core.free_text import TextQuery
from aurelius_atlas_core.search_query import Condition, Criterion, Group, Test, VectorQuery

E = "aurelius_atlas_core.es_clauses"


@pytest.mark.covers(f"{E}.match_all", f"{E}.match_none", f"{E}.search_path", rules=["QRY-01"])
def test__the_empty_clauses_and_a_field_path() -> None:
    """The always/never clauses and the ``search.`` prefix of a field path."""
    assert es_clauses.match_all() == {"match_all": {}}
    assert es_clauses.match_none() == {"match_none": {}}
    assert es_clauses.search_path("name") == "search.name"


@pytest.mark.covers(
    f"{E}.term",
    f"{E}.terms",
    f"{E}.range_",
    f"{E}.prefix",
    f"{E}.wildcard",
    f"{E}.regexp",
    f"{E}.exists",
    rules=["QRY-01"],
)
def test__single_field_clauses() -> None:
    """Each single-field clause wraps its path and value in the shape Elasticsearch reads."""
    assert es_clauses.term("search.name", "x") == {"term": {"search.name": "x"}}
    assert es_clauses.terms("search.name", ["x", "y"]) == {"terms": {"search.name": ["x", "y"]}}
    assert es_clauses.range_("search.age", {"gte": 1, "lt": 9}) == {"range": {"search.age": {"gte": 1, "lt": 9}}}
    assert es_clauses.prefix("search.name", "ab") == {"prefix": {"search.name": "ab"}}
    assert es_clauses.wildcard("search.name", {"value": "a*b"}) == {"wildcard": {"search.name": {"value": "a*b"}}}
    assert es_clauses.regexp("search.name", {"value": "a.b"}) == {"regexp": {"search.name": {"value": "a.b"}}}
    assert es_clauses.exists("search.name") == {"exists": {"field": "search.name"}}


@pytest.mark.covers(
    f"{E}.bool_", f"{E}.should", f"{E}.must_not", f"{E}.filter_", f"{E}.escape_wildcard", rules=["QRY-01"]
)
def test__bool_combinators_hold_only_the_kinds_given() -> None:
    """A ``bool`` carries exactly the clause kinds passed, and an explicit ``minimum_should_match`` (DD-767)."""
    one, two = es_clauses.term("a", 1), es_clauses.term("b", 2)
    assert es_clauses.bool_(filter=[one]) == {"bool": {"filter": [one]}}
    assert es_clauses.bool_(must=[one], must_not=[two], minimum_should_match=2) == {
        "bool": {"must": [one], "must_not": [two], "minimum_should_match": 2}
    }
    # An empty list still puts the kind in; None leaves it out, as a missing kind (DD-767).
    assert es_clauses.bool_(should=[]) == {"bool": {"should": []}}
    assert es_clauses.bool_() == {"bool": {}}
    assert es_clauses.should([one, two]) == {"bool": {"should": [one, two], "minimum_should_match": 1}}
    assert es_clauses.should([one], minimum=2) == {"bool": {"should": [one], "minimum_should_match": 2}}
    assert es_clauses.must_not([one]) == {"bool": {"must_not": [one]}}
    assert es_clauses.filter_([one]) == {"bool": {"filter": [one]}}
    assert es_clauses.escape_wildcard("a*b?c\\d") == "a\\*b\\?c\\\\d"


@pytest.mark.covers(f"{E}.filter_clause", rules=["QRY-01"])
def test__a_filter_tree_becomes_the_clauses_of_each_predicate() -> None:
    """Each predicate in the Test enum becomes the clause its port defined."""

    def clause(
        field: str, test: Test, value: object = None, *, value2: object = None, array: bool = False
    ) -> dict[str, Any]:
        """The clause of one criterion."""
        return es_clauses.filter_clause(Criterion(field=field, test=test, value=value, value2=value2, array=array))

    assert clause("name", Test.NOTHING) == {"match_none": {}}
    assert clause("name", Test.ANYTHING) == {"match_all": {}}
    assert clause("name", Test.ANY_OF, ["b", "a"]) == {"terms": {"search.name": ["a", "b"]}}
    # The pattern's ``*`` stays the glob separator; the text around it is escaped.
    assert clause("name", Test.MATCHES, "a*b") == {
        "wildcard": {"search.name": {"value": "a*b", "case_insensitive": True}}
    }
    assert clause("name", Test.REGEX, "a.b") == {"regexp": {"search.name": {"value": "a.b", "flags": "NONE"}}}
    assert clause("name", Test.WORD_REGEX, "a.b") == {
        "regexp": {"search.name.text": {"value": "a.b", "flags": "NONE", "case_insensitive": True}}
    }
    assert clause("name", Test.EQ, "x") == {"term": {"search.name": "x"}}
    assert clause("name", Test.NEQ, "x") == {"bool": {"must_not": [{"term": {"search.name": "x"}}]}}
    assert clause("age", Test.LT, 5) == {"range": {"search.age": {"lt": 5}}}
    assert clause("age", Test.RANGE, 1, value2=9) == {"range": {"search.age": {"gte": 1, "lte": 9}}}
    assert clause("name", Test.STARTS_WITH, "ab") == {"prefix": {"search.name": "ab"}}
    assert clause("name", Test.ENDS_WITH, "ab") == {"wildcard": {"search.name": {"value": "*ab"}}}
    assert clause("name", Test.CONTAINS, "ab") == {"wildcard": {"search.name": {"value": "*ab*"}}}
    assert clause("tag", Test.CONTAINS, "ab", array=True) == {"term": {"search.tag": "ab"}}
    assert clause("name", Test.IS_NULL) == {"bool": {"must_not": [{"exists": {"field": "search.name"}}]}}
    assert clause("name", Test.NOT_NULL) == {"exists": {"field": "search.name"}}
    # NOT_EMPTY on a keyword also excludes the empty string; on text it only needs the field present.
    assert clause("keyword.name", Test.NOT_EMPTY) == {
        "bool": {
            "filter": [{"exists": {"field": "search.keyword.name"}}],
            "must_not": [{"term": {"search.keyword.name": ""}}],
        }
    }
    assert clause("text.name", Test.NOT_EMPTY) == {
        "bool": {"filter": [{"exists": {"field": "search.text.name"}}], "must_not": []}
    }


@pytest.mark.covers(f"{E}.filter_clause", rules=["QRY-01"])
def test__a_group_and_ors_the_children_clauses() -> None:
    """An ``AND`` group filters with all children, an ``OR`` group lets any one hold."""
    a = Criterion(field="name", test=Test.EQ, value="x")
    b = Criterion(field="age", test=Test.GTE, value=3)
    assert es_clauses.filter_clause(Group(condition=Condition.AND, criteria=(a, b))) == {
        "bool": {"filter": [{"term": {"search.name": "x"}}, {"range": {"search.age": {"gte": 3}}}]}
    }
    assert es_clauses.filter_clause(Group(condition=Condition.OR, criteria=(a, b))) == {
        "bool": {
            "should": [{"term": {"search.name": "x"}}, {"range": {"search.age": {"gte": 3}}}],
            "minimum_should_match": 1,
        }
    }


@pytest.mark.covers(f"{E}.text_clause", f"{E}.engine_text", rules=["QRY-01"])
def test__free_text_carries_weights_for_basic_search_only() -> None:
    """The weighted basic query, and the engine's own reading without weights or ``analyze_wildcard`` (DD-525)."""
    basic = es_clauses.text_clause(TextQuery("cat dog", {"name": 5, "desc": 1}))
    assert basic == {
        "simple_query_string": {
            "query": "cat dog",
            "fields": ["search.name.text^5", "search.desc.text^1"],
            "default_operator": "or",
            "analyze_wildcard": True,
            "lenient": True,
        }
    }
    # The engine's reading resolves the fields itself and omits analyze_wildcard (DD-525).
    engine = es_clauses.engine_text("cat", ["search.name.text", "search.desc.text^2"])
    assert engine == {
        "simple_query_string": {
            "query": "cat",
            "fields": ["search.name.text", "search.desc.text^2"],
            "default_operator": "or",
            "lenient": True,
        }
    }


@pytest.mark.covers(f"{E}.terms_agg", rules=["QRY-01"])
def test__a_terms_aggregation_orders_by_count_then_value() -> None:
    """A facet's ``terms`` aggregation defaults to count then value, and carries ``include``/``missing`` (DD-530)."""
    assert es_clauses.terms_agg("search.tag", 10) == {
        "terms": {"field": "search.tag", "size": 10, "order": [{"_count": "desc"}, {"_key": "asc"}]}
    }
    assert es_clauses.terms_agg("search.tag", 4, order=[{"_key": "asc"}], include="a.*", missing="-") == {
        "terms": {"field": "search.tag", "size": 4, "order": [{"_key": "asc"}], "include": "a.*", "missing": "-"}
    }


@pytest.mark.covers(f"{E}.knn", rules=["QRY-01"])
def test__a_vector_query_nearest_among_a_filter() -> None:
    """A ``knn`` over the embedding field, bounded by the filter and scaled by its weight (DD-441)."""
    allowed = es_clauses.filter_([es_clauses.term("typeName", "Dataset")])
    assert es_clauses.knn(VectorQuery(vector=(0.5, 0.25), k=7, weight=2.0), allowed) == {
        "field": VECTOR_FIELD,
        "query_vector": [0.5, 0.25],
        "k": 7,
        "num_candidates": 100,
        "filter": allowed,
        "boost": 2.0,
    }
