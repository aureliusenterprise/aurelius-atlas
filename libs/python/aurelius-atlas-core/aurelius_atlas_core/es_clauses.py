"""Elasticsearch clauses core emits, in one place: filters, ranges, text, kNN, and facet aggregations (QRY-01).

The ``bool``, ``should``, ``must`` and ``knn`` dictionaries the entity documents and the App Search engines emit
are built here, so one predicate or clause kind is written once. A clause is a plain dictionary; the store and its
fake read the same JSON, so the shape these builders return is the wire contract (DD-767).
"""

from typing import Any

from aurelius_atlas_model.discovery import Condition

from aurelius_atlas_core.entity_embedding import VECTOR_FIELD
from aurelius_atlas_core.free_text import TextQuery
from aurelius_atlas_core.search_fields import KEYWORD, TEXT
from aurelius_atlas_core.search_query import Filter, Group, Test, VectorQuery

_MATCH_ALL = {"match_all": {}}
_MATCH_NONE = {"match_none": {}}


def match_all() -> dict[str, Any]:
    """A ``match_all`` clause, matching every document."""
    return dict(_MATCH_ALL)


def match_none() -> dict[str, Any]:
    """A ``match_none`` clause, matching no document."""
    return dict(_MATCH_NONE)


def search_path(name: str) -> str:
    """The index path of a search field, under the entity document's ``search`` object (DD-088)."""
    return f"search.{name}"


def term(path: str, value: Any) -> dict[str, Any]:  # noqa: ANN401 - a field's value
    """A ``term`` for one value of a field."""
    return {"term": {path: value}}


def terms(path: str, values: list[Any]) -> dict[str, Any]:
    """A ``terms`` for any value of a field among ``values``."""
    return {"terms": {path: values}}


def range_(path: str, bounds: dict[str, Any]) -> dict[str, Any]:
    """A ``range`` over a field with the given ``gte``/``lte``/``gt``/``lt`` bounds."""
    return {"range": {path: bounds}}


def prefix(path: str, value: str) -> dict[str, Any]:
    """A ``prefix`` for a field starting with ``value``."""
    return {"prefix": {path: value}}


def wildcard(path: str, spec: Any) -> dict[str, Any]:  # noqa: ANN401 - a pattern or its options
    """A ``wildcard`` for a field matching a pattern, with its options."""
    return {"wildcard": {path: spec}}


def regexp(path: str, spec: Any) -> dict[str, Any]:  # noqa: ANN401 - a pattern or its options
    """A ``regexp`` for a field matching a regular expression, with its options."""
    return {"regexp": {path: spec}}


def exists(path: str) -> dict[str, Any]:
    """An ``exists`` for a field holding a value."""
    return {"exists": {"field": path}}


def bool_(
    *,
    must: list[dict[str, Any]] | None = None,
    filter: list[dict[str, Any]] | None = None,  # noqa: A002 - Elasticsearch's clause name
    must_not: list[dict[str, Any]] | None = None,
    should: list[dict[str, Any]] | None = None,
    minimum_should_match: int | None = None,
) -> dict[str, Any]:
    """A ``bool`` with only the clause kinds given (DD-767).

    A list, empty or not, puts the key in; ``None`` leaves the kind out, as Elasticsearch treats a missing kind.
    """
    clauses = {
        key: value
        for key, value in {
            "must": must,
            "filter": filter,
            "must_not": must_not,
            "should": should,
            "minimum_should_match": minimum_should_match,
        }.items()
        if value is not None
    }
    return {"bool": clauses}


def should(clauses: list[dict[str, Any]], *, minimum: int = 1) -> dict[str, Any]:
    """A ``bool`` whose ``should`` needs ``minimum`` (one, by default) of ``clauses``."""
    return bool_(should=clauses, minimum_should_match=minimum)


def must_not(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    """A ``bool`` excluding every one of ``clauses``."""
    return bool_(must_not=clauses)


def filter_(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    """A ``bool`` requiring every one of ``clauses``, unconstrained on ``should``."""
    return bool_(filter=clauses)


def escape_wildcard(value: str) -> str:
    r"""A value safe as the literal text of a Lucene ``wildcard`` pattern, ``*`` and ``?`` and ``\`` escaped."""
    return "".join(f"\\{character}" if character in "*?\\" else character for character in value)


def _contains(path: str, value: Any, *, array: bool) -> dict[str, Any]:  # noqa: ANN401 - a field's value
    """A ``CONTAINS``: a term an array element equals, or a substring a string holds."""
    if array:
        return term(path, value)
    return wildcard(path, {"value": f"*{escape_wildcard(str(value))}*"})


def filter_clause(node: Filter) -> dict[str, Any]:  # noqa: C901, PLR0911, PLR0912 - one clause per test
    """A filter of the search query as an Elasticsearch query (SRC-05, DD-089)."""
    if isinstance(node, Group):
        clauses = [filter_clause(child) for child in node.criteria]
        if node.condition is Condition.AND:
            return filter_(clauses)
        return should(clauses)
    path, value = search_path(node.field), node.value
    match node.test:
        case Test.NOTHING:
            return match_none()
        case Test.ANYTHING:
            return match_all()
        case Test.ANY_OF:
            return terms(path, sorted(value))
        case Test.MATCHES:
            pattern = "*".join(escape_wildcard(part) for part in str(value).split("*"))
            return wildcard(path, {"value": pattern, "case_insensitive": True})
        case Test.REGEX:
            return regexp(path, {"value": value, "flags": "NONE"})
        case Test.WORD_REGEX:
            return regexp(f"{path}.{TEXT}", {"value": value, "flags": "NONE", "case_insensitive": True})
        case Test.EQ:
            return term(path, value)
        case Test.NEQ:
            return must_not([term(path, value)])
        case Test.LT | Test.LTE | Test.GT | Test.GTE:
            return range_(path, {node.test.value.lower(): value})
        case Test.RANGE:
            return range_(path, {"gte": value, "lte": node.value2})
        case Test.STARTS_WITH:
            return prefix(path, value)
        case Test.ENDS_WITH:
            return wildcard(path, {"value": f"*{escape_wildcard(value)}"})
        case Test.CONTAINS:
            return _contains(path, value, array=node.array)
        case Test.NOT_CONTAINS:
            return must_not([_contains(path, value, array=node.array)])
        case Test.IS_NULL:
            return must_not([exists(path)])
        case Test.NOT_NULL:
            return exists(path)
        case _:  # Test.NOT_EMPTY
            empty = [term(path, "")] if node.field.startswith(f"{KEYWORD}.") else []
            return bool_(filter=[exists(path)], must_not=empty)


def text_clause(text: TextQuery) -> dict[str, Any]:
    """Free text: ``simple_query_string`` over the text sub-fields, each boosted by its weight (DD-092)."""
    fields = [f"{search_path(name)}.{TEXT}^{weight}" for name, weight in text.fields.items()]
    return {
        "simple_query_string": {
            "query": text.text,
            "fields": fields,
            "default_operator": "or",
            "analyze_wildcard": True,
            "lenient": True,
        }
    }


def terms_agg(
    field: str,
    size: int,
    *,
    order: list[dict[str, str]] | None = None,
    include: str | None = None,
    missing: Any = None,  # noqa: ANN401 - a facet's missing value
) -> dict[str, Any]:
    """A ``terms`` aggregation of a field, most documents first then by value; ``order``, ``include`` and
    ``missing`` as an App Search facet asks (DD-530).
    """  # noqa: D205 - one sentence
    terms: dict[str, Any] = {"field": field, "size": size}
    terms["order"] = [{"_count": "desc"}, {"_key": "asc"}] if order is None else order
    if include is not None:
        terms["include"] = include
    if missing is not None:
        terms["missing"] = missing
    return {"terms": terms}


def engine_text(query: str, fields: list[str]) -> dict[str, Any]:
    """A free-text ``simple_query_string`` over index fields, as the App Search engine and the view door query (DD-525).

    The engine's own reading, apart from the weighted ``text_clause`` a basic search emits: no
    ``analyze_wildcard``, and the fields given as the engine resolved them.
    """
    return {
        "simple_query_string": {
            "query": query,
            "fields": fields,
            "default_operator": "or",
            "lenient": True,
        }
    }


def knn(vector: VectorQuery, filter: dict[str, Any]) -> dict[str, Any]:  # noqa: A002 - Elasticsearch's clause name
    """A ``knn`` for the nearest to ``vector`` among those ``filter`` allows, weighted (SBM-02, DD-441, DD-596)."""
    return {
        "field": VECTOR_FIELD,
        "query_vector": list(vector.vector),
        "k": vector.k,
        "num_candidates": vector.num_candidates,
        "filter": filter,
        "boost": vector.weight,
    }
