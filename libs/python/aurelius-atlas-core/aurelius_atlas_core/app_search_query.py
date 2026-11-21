"""A Search API request checked against an engine's fields and turned into one search of its index (ASE-04 to
ASE-09, ASQ-03, ASG-05, DD-527, DD-790).

The request — query, filters, facets, sort, page, result fields — is checked against the schema's table, and
becomes the body of one Elasticsearch search; the clause dictionaries come from ``es_clauses`` (19.1).
"""  # noqa: D205 - one sentence

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from aurelius_atlas_core import es_clauses
from aurelius_atlas_core.app_search_schema import (
    _DIRECTIONS,
    ATLAS_DEV,
    DEFAULT_SNIPPET,
    MAX_FACET_SIZE,
    MAX_PAGE,
    MAX_PAGE_SIZE,
    MAX_SNIPPET,
    MIN_SNIPPET,
    AppSearchError,
    Engine,
    EngineField,
    Errors,
    Kind,
    _is_number,
    filter_clauses,
    known,
)
from aurelius_atlas_core.search_query import MAX_RESULT_WINDOW, VectorQuery


@dataclass
class Facet:
    """One facet of a field: the most frequent values first, or by value."""

    size: int
    order: dict[str, str]


@dataclass
class _ResultField:
    """What a result holds of a field: its raw value, cut to ``raw_size``, and its snippet."""

    raw: bool
    raw_size: int | None = None
    snippet: bool = False
    snippet_size: int = DEFAULT_SNIPPET
    fallback: bool = False


@dataclass
class Search:
    """A request checked against the engine's fields, ready to run (ASE-04)."""

    engine: Engine = ATLAS_DEV
    query: str = ""
    filters: list[dict[str, Any]] = field(default_factory=list)
    facets: dict[str, list[Facet]] = field(default_factory=dict)
    sort: list[tuple[str, str]] = field(default_factory=list)
    current: int = 1
    size: int = 10
    start: int | None = None
    """The first hit's index, in place of ``current`` times ``size``: the view door pages by ``offset`` (AVR-07)."""
    result_fields: dict[str, _ResultField] | None = None
    search_fields: dict[str, float] | None = None
    vector: VectorQuery | None = None
    """The entities nearest to a vector, among those the engine holds and the filters allow (ASV-03, DD-596):
    a ``knn`` search with the same filters inside it, its score added to the query's matches (DD-441, DD-442)."""


def parse(body: object, engine: Engine = ATLAS_DEV) -> Search:
    """The request checked as App Search checks it against ``engine``'s fields; other keys ignored (ASE-04,
    DD-527).

    Raises:
        AppSearchError: 400 with each problem found.
    """  # noqa: D205 - one sentence
    if not isinstance(body, dict):
        raise AppSearchError(400, "The request body must be a JSON object")
    errors = Errors(engine.fields)
    search = Search(engine)
    query = body.get("query", "")
    if isinstance(query, str):
        search.query = query
    elif query is not None:
        errors.add("Query must be a string")
    if (filters := body.get("filters")) is not None:
        search.filters = [filter_clauses(filters, errors, "Filters")]
    if (facets := body.get("facets")) is not None:
        search.facets = _facets(facets, errors)
    if (sort := body.get("sort")) is not None:
        search.sort = parse_sort(sort, errors)
    if (page := body.get("page")) is not None:
        search.current, search.size = _page(page, errors)
    if (result_fields := body.get("result_fields")) is not None:
        search.result_fields = _result_fields(result_fields, errors)
    if (search_fields := body.get("search_fields")) is not None:
        search.search_fields = _search_fields(search_fields, errors)
    errors.raise_any()
    return search


def _facets(facets: object, errors: Errors) -> dict[str, list[Facet]]:
    """Each field's value facets: ``size`` 1 to 250, sorted by count or value (ASE-07)."""
    if not isinstance(facets, dict):
        errors.add("Facets must be an object")
        return {}
    parsed: dict[str, list[Facet]] = {}
    for name, value in facets.items():
        if known(name, errors, "Facets") is None:
            continue
        parsed[name] = [_facet(name, item, errors) for item in (value if isinstance(value, list) else [value])]
    return parsed


def _facet(name: str, facet: object, errors: Errors) -> Facet:
    """One facet: its type must be ``value``; a range facet is refused (DV-158)."""
    if not isinstance(facet, dict):
        errors.add(f"Facet for {name} must be an object")
        return Facet(0, {})
    if facet.get("type") == "range":
        errors.add(f"Range facets are not supported: {name}")
    elif facet.get("type") != "value":
        errors.add(f"Facet type for {name} must be value")
    size = facet.get("size", 10)
    if not isinstance(size, int) or isinstance(size, bool) or not 1 <= size <= MAX_FACET_SIZE:
        errors.add(f"Facet size for {name} must be between 1 and {MAX_FACET_SIZE}")
        size = 10
    return Facet(size, _facet_order(name, facet.get("sort"), errors))


def _facet_order(name: str, sort: object, errors: Errors) -> dict[str, str]:
    """A facet's Elasticsearch order from its ``sort``: by count or by value, asc or desc (ASE-07)."""
    if sort is None:
        return {"_count": "desc"}
    if not (isinstance(sort, dict) and len(sort) == 1 and next(iter(sort)) in ("count", "value")):
        errors.add(f"Facet sort for {name} must be by count or by value")
        return {"_count": "desc"}
    ((key, direction),) = sort.items()
    if direction not in _DIRECTIONS:
        errors.add(f"Facet sort for {name} must be asc or desc")
        return {"_count": "desc"}
    return {"_count" if key == "count" else "_key": direction}


def parse_sort(sort: object, errors: Errors) -> list[tuple[str, str]]:
    """A field or ``_score`` with its direction, or a list of them (ASE-08)."""
    clauses = sort if isinstance(sort, list) else [sort]
    parsed = []
    for clause in clauses:
        if not isinstance(clause, dict) or len(clause) != 1:
            errors.add("Sort must be an object of one field and its direction, or a list of them")
            continue
        ((name, direction),) = clause.items()
        if direction not in _DIRECTIONS:
            errors.add(f"Sort direction for {name} must be asc or desc")
        elif name == "_score" or known(name, errors, "Sort") is not None:
            parsed.append((name, direction))
    return parsed


def _page(page: object, errors: Errors) -> tuple[int, int]:
    """``current`` 1 to 100 and ``size`` 1 to 1,000 (ASE-09)."""
    if not isinstance(page, dict):
        errors.add("Page must be an object")
        return 1, 10
    current, size = page.get("current", 1), page.get("size", 10)
    if not isinstance(current, int) or isinstance(current, bool) or not 1 <= current <= MAX_PAGE:
        errors.add(f"Page current must be between 1 and {MAX_PAGE}")
        current = 1
    if not isinstance(size, int) or isinstance(size, bool) or not 1 <= size <= MAX_PAGE_SIZE:
        errors.add(f"Page size must be between 1 and {MAX_PAGE_SIZE}")
        size = 10
    return current, size


def _result_fields(result_fields: object, errors: Errors) -> dict[str, _ResultField]:
    """Each field's raw value and snippet, with their sizes (ASE-10)."""
    if not isinstance(result_fields, dict):
        errors.add("Result fields must be an object")
        return {}
    parsed = {}
    for name, options in result_fields.items():
        engine_field = known(name, errors, "Result fields")
        if engine_field is None:
            continue
        if not isinstance(options, dict):
            errors.add(f"Result field {name} must be an object")
            continue
        parsed[name] = _result_field(name, options, engine_field, errors)
    return parsed


def _result_field(name: str, options: dict[str, Any], engine_field: EngineField, errors: Errors) -> _ResultField:
    """One result field's raw value and snippet, with their sizes (ASE-10)."""
    raw, snippet = options.get("raw"), options.get("snippet")
    result = _ResultField(raw=raw is not None or snippet is None)
    if isinstance(raw, dict) and "size" in raw:
        result.raw_size = _size(raw["size"], f"Raw size for {name}", MIN_SNIPPET, None, errors)
    if snippet is not None:
        _apply_snippet(result, name, engine_field, snippet, errors)
    return result


def _apply_snippet(result: _ResultField, name: str, engine_field: EngineField, snippet: object, errors: Errors) -> None:
    """Fill in one result field's snippet: text fields only, with its size and fallback (ASE-10)."""
    if engine_field.kind is not Kind.TEXT:
        errors.add(f"Snippets are only for text fields: {name}")
    snippet_options = snippet if isinstance(snippet, dict) else {}
    result.snippet = True
    result.snippet_size = _size(
        snippet_options.get("size", DEFAULT_SNIPPET),
        f"Snippet size for {name}",
        MIN_SNIPPET,
        MAX_SNIPPET,
        errors,
    )
    result.fallback = snippet_options.get("fallback") is True


def _size(value: object, what: str, least: int, most: int | None, errors: Errors) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < least or (most is not None and value > most):
        errors.add(f"{what} must be at least {least}" + (f" and at most {most}" if most is not None else ""))
        return least
    return value


def _search_fields(search_fields: object, errors: Errors) -> dict[str, float]:
    """The text fields a query's words are matched in, each with its weight (ASE-05)."""
    if not isinstance(search_fields, dict):
        errors.add("Search fields must be an object")
        return {}
    parsed = {}
    for name, options in search_fields.items():
        engine_field = known(name, errors, "Search fields")
        if engine_field is None:
            continue
        if engine_field.kind is not Kind.TEXT:
            errors.add(f"Search fields must be text fields: {name}")
            continue
        weight = options.get("weight", 1) if isinstance(options, dict) else None
        if not _is_number(weight):
            errors.add(f"Search field weight for {name} must be a number")
            continue
        parsed[name] = float(weight)  # type: ignore[arg-type] - checked a number
    return parsed


def _matched_fields(search: Search) -> list[str]:
    """The index fields a query's words are matched in, with their weights (DD-525): the stored text fields.

    ``search_fields`` names the engine's fields, or—as the view door passes them—index paths used as they
    are: the door's query fields are typed per entity type and never rows of one table (DD-586).
    """
    weights = search.search_fields or dict.fromkeys(search.engine.fields, 1.0)
    fields = []
    for name, weight in weights.items():
        engine_field = search.engine.fields.get(name)
        if engine_field is not None and engine_field.kind is not Kind.TEXT:
            continue
        target = (engine_field.text or engine_field.path) if engine_field is not None else name
        if target is not None and target not in (spec.split("^")[0] for spec in fields):
            fields.append(target if weight == 1 else f"{target}^{weight:g}")
    return fields


def query_body(search: Search) -> dict[str, Any]:
    """The search of the entity index: the engine's documents, the query, filters, facets, sort, page."""
    must: list[dict[str, Any]] = []
    if search.query.strip():
        must.append(es_clauses.engine_text(search.query, _matched_fields(search)))
    start = search.start if search.start is not None else (search.current - 1) * search.size
    fields = search.engine.fields
    aggs = {
        f"{name}#{index}": facet_terms(fields[name], facet)
        for name, facets in search.facets.items()
        if fields[name].path is not None
        for index, facet in enumerate(facets)
    }
    holds = [*search.engine.holds, *search.filters]
    knn = None
    if search.vector is not None:
        knn = es_clauses.knn(search.vector, es_clauses.filter_(holds))
    return {
        "query": None if knn is not None and not must else es_clauses.bool_(filter=holds, must=must),
        "knn": knn,
        "sort": sort_clauses(search.sort, fields, search.engine.id_field),
        "aggs": aggs,
        "from_": min(start, MAX_RESULT_WINDOW),
        "size": max(0, min(search.size, MAX_RESULT_WINDOW - start)),
        "index": search.engine.index,
    }


def facet_terms(engine_field: EngineField, facet: Facet) -> dict[str, Any]:
    """A facet's ``terms`` aggregation: one more value than asked, to drop an empty one; missing counted (DD-530)."""
    return es_clauses.terms_agg(
        cast("str", engine_field.path), facet.size + 1, order=facet_order(facet), missing=engine_field.missing
    )


def facet_order(facet: Facet) -> list[dict[str, str]]:
    """A facet's order; ties of counts by value (ASE-07)."""
    return [facet.order, {"_key": "asc"}] if "_count" in facet.order else [facet.order]


def sort_clauses(sort: list[tuple[str, str]], fields: Mapping[str, EngineField], id_field: str) -> list[dict[str, Any]]:
    """The sort, constants dropped, a missing number as its ``missing`` value, ties by ``id`` (ASE-08, DD-530)."""
    clauses: list[dict[str, Any]] = []
    for name, direction in sort or [("_score", "desc")]:
        if name == "_score":
            clauses.append({"_score": {"order": direction}})
        elif (path := fields[name].path) is not None:
            missing = fields[name].missing
            clauses.append({path: {"order": direction} | ({} if missing is None else {"missing": missing})})
    return [*clauses, {id_field: {"order": "asc"}}]
