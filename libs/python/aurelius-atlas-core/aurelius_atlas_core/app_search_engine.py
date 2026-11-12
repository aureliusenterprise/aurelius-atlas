"""The App Search engines ``atlas-dev`` and ``atlas-dev-quality`` answered from the entity index (ASE-03 to
ASE-11, ASQ-02 to ASQ-06, DD-523 to DD-525, DD-530, DD-531).

The original webapp sends App Search's Search API requests: a query, filters, facets, a sort, a page and the
fields to answer. An engine is the entity documents it holds and its fields; each field is a row of its table:
its kind, and the index field it is read from or the constant it holds. A request is checked against the table,
as App Search checks it, and becomes one search of the entity index; the answer is read back through the table
in App Search's shape.
"""  # noqa: D205 - one sentence

import html
import math
import re
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from aurelius_atlas_core.app_search_document import (
    APP_SEARCH_FIELD,
    DIMENSIONS,
    KEYWORD_FIELDS,
    NAME_FIELDS,
    QUALITY_KEYWORD_FIELDS,
    QUALITY_NUMBER_FIELDS,
    QUALITY_RESULT_FIELD,
    QUALITY_TEXT_FIELDS,
    QUALITY_TOTALS_FIELD,
    SOURCE_HASH_FIELD,
)
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.search_query import ACTIVE
from aurelius_atlas_core.stored_entity import StoredAppSearch, StoredQualityResult

ENGINE = "atlas-dev"
"""The engine of the entity documents (LAS-01)."""

QUALITY_ENGINE = "atlas-dev-quality"
"""The engine of the quality results (LAS-11, ASQ-02)."""

MAX_PAGE = 100
MAX_PAGE_SIZE = 1000
MAX_FACET_SIZE = 250
RESULT_WINDOW = 10_000
"""The results a search reaches at most, Elasticsearch's ``max_result_window``: none beyond the 10,000th."""

MIN_SNIPPET = 20
MAX_SNIPPET = 1000
DEFAULT_SNIPPET = 100

_DIRECTIONS = ("asc", "desc")
_WORD = re.compile(r"\w+")


class Kind(StrEnum):
    """An App Search field's schema type."""

    TEXT = "text"
    NUMBER = "number"


@dataclass(frozen=True)
class EngineField:
    """A field of the engine: its kind, and either the index field it is read from or its constant (DD-523).

    ``text`` is the analysed sub-field a query's words are matched in; ``read`` gives the value from a hit's
    source; ``missing`` is the number a document without the index field holds for filters, facets and sorts
    (DD-530).
    """

    kind: Kind
    path: str | None = None
    constant: Any = None
    text: str | None = None
    read: Callable[[Mapping[str, Any]], Any] | None = None
    missing: float | None = None

    def value(self, source: Mapping[str, Any]) -> Any:  # noqa: ANN401 - a field's JSON value
        """The field's value in a hit's source."""
        return self.constant if self.read is None else self.read(source)


def _stored(name: str) -> Callable[[Mapping[str, Any]], Any]:
    """The reader of a stored App Search field, its default when the stored document lacks it."""
    default = StoredAppSearch.model_fields[name].get_default(call_default_factory=True)

    def read(source: Mapping[str, Any]) -> Any:  # noqa: ANN401 - a field's JSON value
        return (source.get(APP_SEARCH_FIELD) or {}).get(name, default)

    return read


def _nested(path: str, default: Any) -> Callable[[Mapping[str, Any]], Any]:  # noqa: ANN401 - a JSON value
    """The reader of a dotted index field, ``default`` where the source lacks it."""
    keys = path.split(".")

    def read(source: Mapping[str, Any]) -> Any:  # noqa: ANN401 - a field's JSON value
        value: Any = source
        for key in keys:
            value = value.get(key) if isinstance(value, dict) else None
        return default if value is None else value

    return read


_TOTALS = {"dqscore": "score", "dqscorecnt": "count", "dqscoresum": "total"}
"""The score fields of ``atlas-dev`` and the totals they are read from (ASQ-04, ASQ-05)."""


def _fields() -> dict[str, EngineField]:
    """The engine's fields (14.1's ``atlas-dev`` documents): the entity's, the stored ones, the constants."""
    guid = EngineField(Kind.TEXT, path="guid", read=lambda source: source.get("guid"))
    fields = {
        "id": guid,
        "guid": guid,
        "typename": EngineField(Kind.TEXT, path="typeName", read=lambda source: source.get("typeName")),
        "supertypenames": EngineField(Kind.TEXT, path="typeName", read=lambda source: [source.get("typeName")]),
    }
    for name in NAME_FIELDS:
        path = f"{APP_SEARCH_FIELD}.{name}"
        fields[name] = EngineField(Kind.TEXT, path=path, text=f"{path}.text", read=_stored(name))
    for name in KEYWORD_FIELDS:
        fields[name] = EngineField(Kind.TEXT, path=f"{APP_SEARCH_FIELD}.{name}", read=_stored(name))
    fields["businessruleid"] = EngineField(Kind.NUMBER, constant=0.0)
    for name in ("deriveddataownerguid", "deriveddatastewardguid", "deriveddomainleadguid", "entityname"):
        fields[name] = EngineField(Kind.TEXT, constant=None)
    for name in (
        "classificationstext",
        "deriveddatasetguids",
        "deriveddatasetnames",
        "derivedentityguids",
        "derivedentitynames",
    ):
        fields[name] = EngineField(Kind.TEXT, constant=[])
    for dimension in (*DIMENSIONS, "overall"):
        for prefix, total in _TOTALS.items():
            path = f"{QUALITY_TOTALS_FIELD}.{dimension}.{total}"
            fields[f"{prefix}_{dimension}"] = EngineField(Kind.NUMBER, path=path, read=_nested(path, 0.0), missing=0.0)
    for dimension in DIMENSIONS:
        path = f"{QUALITY_TOTALS_FIELD}.{dimension}.rules"
        fields[f"qualityguid_{dimension}"] = EngineField(Kind.TEXT, path=path, read=_nested(path, []))
    return fields


FIELDS = _fields()
"""``atlas-dev``'s fields by name: LAS-02 to LAS-07, and the scores read from the totals (ASQ-04 to ASQ-06)."""


def _quality_fields() -> dict[str, EngineField]:
    """``atlas-dev-quality``'s fields (14.1's documents): the score entity's GUID and its result's (ASQ-02)."""
    fields = {"id": EngineField(Kind.TEXT, path="guid", read=lambda source: source.get("guid"))}
    defaults = {
        name: info.get_default(call_default_factory=True) for name, info in StoredQualityResult.model_fields.items()
    }
    for name in ("guid", *QUALITY_KEYWORD_FIELDS):
        stored = "qualityguid" if name == "guid" else name
        path = f"{QUALITY_RESULT_FIELD}.{stored}"
        fields[name] = EngineField(Kind.TEXT, path=path, read=_nested(path, defaults[stored]))
    for name in QUALITY_TEXT_FIELDS:
        path = f"{QUALITY_RESULT_FIELD}.{name}"
        fields[name] = EngineField(Kind.TEXT, path=path, text=f"{path}.text", read=_nested(path, defaults[name]))
    for name in QUALITY_NUMBER_FIELDS:
        path = f"{QUALITY_RESULT_FIELD}.{name}"
        fields[name] = EngineField(Kind.NUMBER, path=path, read=_nested(path, defaults[name]))
    return fields


QUALITY_FIELDS = _quality_fields()
"""``atlas-dev-quality``'s fields by name (LAS-11, ASQ-02)."""


@dataclass(frozen=True)
class Engine:
    """An engine: its name, the filter of the entity documents it holds, and its fields (DD-531)."""

    name: str
    holds: tuple[dict[str, Any], ...]
    fields: Mapping[str, EngineField]


ATLAS_DEV = Engine(ENGINE, ({"term": {"state": ACTIVE}}, {"exists": {"field": SOURCE_HASH_FIELD}}), FIELDS)
"""The active entities with an App Search document, stale or not (ASE-03, DD-524)."""

ATLAS_DEV_QUALITY = Engine(
    QUALITY_ENGINE,
    ({"term": {"state": ACTIVE}}, {"exists": {"field": f"{QUALITY_RESULT_FIELD}.qualityguid"}}),
    QUALITY_FIELDS,
)
"""The active score entities with a quality result (ASQ-02)."""

ENGINES = {engine.name: engine for engine in (ATLAS_DEV, ATLAS_DEV_QUALITY)}
"""The engines by name (ASE-01, ASQ-01)."""


class AppSearchError(Exception):
    """A request App Search refuses: its status and one message per problem (ASE-04, DD-527)."""

    def __init__(self, status: int, *messages: str) -> None:
        """A refusal with ``status`` for ``messages``."""
        super().__init__("; ".join(messages))
        self.status = status
        self.messages = list(messages)

    def to_json(self) -> dict[str, list[str]]:
        """App Search's error body."""
        return {"errors": self.messages}


@dataclass
class _Facet:
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
    facets: dict[str, list[_Facet]] = field(default_factory=dict)
    sort: list[tuple[str, str]] = field(default_factory=list)
    current: int = 1
    size: int = 10
    result_fields: dict[str, _ResultField] | None = None
    search_fields: dict[str, float] | None = None


class _Errors:
    """The problems found in a request, raised together."""

    def __init__(self, fields: Mapping[str, EngineField]) -> None:
        self.fields = fields
        self.messages: list[str] = []

    def add(self, message: str) -> None:
        self.messages.append(message)

    def raise_any(self) -> None:
        if self.messages:
            raise AppSearchError(400, *self.messages)


def parse(body: object, engine: Engine = ATLAS_DEV) -> Search:
    """The request checked as App Search checks it against ``engine``'s fields; other keys ignored (ASE-04,
    DD-527).

    Raises:
        AppSearchError: 400 with each problem found.
    """  # noqa: D205 - one sentence
    if not isinstance(body, dict):
        raise AppSearchError(400, "The request body must be a JSON object")
    errors = _Errors(engine.fields)
    search = Search(engine)
    query = body.get("query", "")
    if isinstance(query, str):
        search.query = query
    elif query is not None:
        errors.add("Query must be a string")
    if (filters := body.get("filters")) is not None:
        search.filters = [_filter(filters, errors, "Filters")]
    if (facets := body.get("facets")) is not None:
        search.facets = _facets(facets, errors)
    if (sort := body.get("sort")) is not None:
        search.sort = _sort(sort, errors)
    if (page := body.get("page")) is not None:
        search.current, search.size = _page(page, errors)
    if (result_fields := body.get("result_fields")) is not None:
        search.result_fields = _result_fields(result_fields, errors)
    if (search_fields := body.get("search_fields")) is not None:
        search.search_fields = _search_fields(search_fields, errors)
    errors.raise_any()
    return search


def _known(name: object, errors: _Errors, what: str) -> EngineField | None:
    """The engine's field of that name, or a problem named after ``what``."""
    found = errors.fields.get(name) if isinstance(name, str) else None
    if found is None:
        errors.add(f"{what} contains an unknown field: {name}")
    return found


_ALL = {"match_all": {}}
_NONE = {"match_none": {}}


def _filter(node: object, errors: _Errors, what: str) -> dict[str, Any]:
    """A filter object: its fields and its ``all``, ``any`` and ``none`` lists, joined as ``all`` (ASE-06)."""
    if not isinstance(node, dict):
        errors.add(f"{what} must be an object")
        return _ALL
    clauses: list[dict[str, Any]] = []
    for key, value in node.items():
        if key in ("all", "any", "none"):
            if not isinstance(value, list):
                errors.add(f"{what} {key} must be a list of filters")
                continue
            nested = [_filter(item, errors, what) for item in value]
            if key == "all":
                clauses.append({"bool": {"filter": nested}})
            elif key == "any":
                clauses.append({"bool": {"should": nested, "minimum_should_match": 1}} if nested else _NONE)
            else:
                clauses.append({"bool": {"must_not": nested}})
        elif (engine_field := _known(key, errors, what)) is not None:
            clauses.append(_field_filter(key, engine_field, value, errors))
    return {"bool": {"filter": clauses}}


def _field_filter(name: str, engine_field: EngineField, value: object, errors: _Errors) -> dict[str, Any]:
    """A field's value filter, any of a list, or a number field's range from included to not (ASE-06)."""
    if isinstance(value, dict):
        return _range_filter(name, engine_field, value, errors)
    values = value if isinstance(value, list) else [value]
    wanted = [_filter_value(name, engine_field, item, errors) for item in values]
    if engine_field.path is None:
        held = engine_field.constant if isinstance(engine_field.constant, list) else [engine_field.constant]
        return _ALL if any(item in held for item in wanted if item is not None) else _NONE
    terms = {"terms": {engine_field.path: [item for item in wanted if item is not None]}}
    missing = engine_field.missing
    return _or_missing(engine_field, terms) if missing is not None and missing in wanted else terms


def _or_missing(engine_field: EngineField, clause: dict[str, Any]) -> dict[str, Any]:
    """The clause, or the field missing: a document without it holds the field's ``missing`` value (DD-530)."""
    absent = {"bool": {"must_not": [{"exists": {"field": engine_field.path}}]}}
    return {"bool": {"should": [clause, absent], "minimum_should_match": 1}}


def _filter_value(name: str, engine_field: EngineField, value: object, errors: _Errors) -> object:
    """A filter value of the field's kind: a string for text, a number for a number field."""
    if engine_field.kind is Kind.TEXT and isinstance(value, str):
        return value
    if engine_field.kind is Kind.NUMBER and _is_number(value):
        return value
    errors.add(f"Filter value for {name} must be a {'string' if engine_field.kind is Kind.TEXT else 'number'}")
    return None


def _range_filter(name: str, engine_field: EngineField, bounds: dict[str, Any], errors: _Errors) -> dict[str, Any]:
    """``{from, to}`` of a number field: from included, to not."""
    if engine_field.kind is not Kind.NUMBER:
        errors.add(f"Filter for {name} must be a value or a list of values: it is a text field")
        return _ALL
    lower, upper = bounds.get("from"), bounds.get("to")
    if (lower is None and upper is None) or not all(item is None or _is_number(item) for item in (lower, upper)):
        errors.add(f"Range filter for {name} must have a number from or to")
        return _ALL
    if engine_field.path is None:
        constant = engine_field.constant
        inside = (lower is None or constant >= lower) and (upper is None or constant < upper)
        return _ALL if inside else _NONE
    limits = ({"gte": lower} if lower is not None else {}) | ({"lt": upper} if upper is not None else {})
    clause = {"range": {engine_field.path: limits}}
    missing = engine_field.missing
    inside = missing is not None and (lower is None or missing >= lower) and (upper is None or missing < upper)
    return _or_missing(engine_field, clause) if inside else clause


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _facets(facets: object, errors: _Errors) -> dict[str, list[_Facet]]:
    """Each field's value facets: ``size`` 1 to 250, sorted by count or value (ASE-07)."""
    if not isinstance(facets, dict):
        errors.add("Facets must be an object")
        return {}
    parsed: dict[str, list[_Facet]] = {}
    for name, value in facets.items():
        if _known(name, errors, "Facets") is None:
            continue
        parsed[name] = [_facet(name, item, errors) for item in (value if isinstance(value, list) else [value])]
    return parsed


def _facet(name: str, facet: object, errors: _Errors) -> _Facet:
    """One facet: its type must be ``value``; a range facet is refused (DV-158)."""
    if not isinstance(facet, dict):
        errors.add(f"Facet for {name} must be an object")
        return _Facet(0, {})
    if facet.get("type") == "range":
        errors.add(f"Range facets are not supported: {name}")
    elif facet.get("type") != "value":
        errors.add(f"Facet type for {name} must be value")
    size = facet.get("size", 10)
    if not isinstance(size, int) or isinstance(size, bool) or not 1 <= size <= MAX_FACET_SIZE:
        errors.add(f"Facet size for {name} must be between 1 and {MAX_FACET_SIZE}")
        size = 10
    order = {"_count": "desc"}
    if (sort := facet.get("sort")) is not None:
        if isinstance(sort, dict) and len(sort) == 1 and next(iter(sort)) in ("count", "value"):
            ((key, direction),) = sort.items()
            if direction in _DIRECTIONS:
                order = {"_count" if key == "count" else "_key": direction}
            else:
                errors.add(f"Facet sort for {name} must be asc or desc")
        else:
            errors.add(f"Facet sort for {name} must be by count or by value")
    return _Facet(size, order)


def _sort(sort: object, errors: _Errors) -> list[tuple[str, str]]:
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
        elif name == "_score" or _known(name, errors, "Sort") is not None:
            parsed.append((name, direction))
    return parsed


def _page(page: object, errors: _Errors) -> tuple[int, int]:
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


def _result_fields(result_fields: object, errors: _Errors) -> dict[str, _ResultField]:
    """Each field's raw value and snippet, with their sizes (ASE-10)."""
    if not isinstance(result_fields, dict):
        errors.add("Result fields must be an object")
        return {}
    parsed = {}
    for name, options in result_fields.items():
        engine_field = _known(name, errors, "Result fields")
        if engine_field is None:
            continue
        if not isinstance(options, dict):
            errors.add(f"Result field {name} must be an object")
            continue
        raw, snippet = options.get("raw"), options.get("snippet")
        result = _ResultField(raw=raw is not None or snippet is None)
        if isinstance(raw, dict) and "size" in raw:
            result.raw_size = _size(raw["size"], f"Raw size for {name}", MIN_SNIPPET, None, errors)
        if snippet is not None:
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
        parsed[name] = result
    return parsed


def _size(value: object, what: str, least: int, most: int | None, errors: _Errors) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < least or (most is not None and value > most):
        errors.add(f"{what} must be at least {least}" + (f" and at most {most}" if most is not None else ""))
        return least
    return value


def _search_fields(search_fields: object, errors: _Errors) -> dict[str, float]:
    """The text fields a query's words are matched in, each with its weight (ASE-05)."""
    if not isinstance(search_fields, dict):
        errors.add("Search fields must be an object")
        return {}
    parsed = {}
    for name, options in search_fields.items():
        engine_field = _known(name, errors, "Search fields")
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
    """The index fields a query's words are matched in, with their weights (DD-525): the stored text fields."""
    weights = search.search_fields or dict.fromkeys(search.engine.fields, 1.0)
    fields = []
    for name, weight in weights.items():
        engine_field = search.engine.fields[name]
        target = engine_field.text or engine_field.path
        if (
            engine_field.kind is Kind.TEXT
            and target is not None
            and target not in (spec.split("^")[0] for spec in fields)
        ):
            fields.append(target if weight == 1 else f"{target}^{weight:g}")
    return fields


def query_body(search: Search) -> dict[str, Any]:
    """The search of the entity index: the engine's documents, the query, filters, facets, sort, page."""
    must: list[dict[str, Any]] = []
    if search.query.strip():
        must.append(
            {
                "simple_query_string": {
                    "query": search.query,
                    "fields": _matched_fields(search),
                    "default_operator": "or",
                    "lenient": True,
                }
            }
        )
    start = (search.current - 1) * search.size
    fields = search.engine.fields
    aggs = {
        f"{name}#{index}": {"terms": _facet_terms(fields[name], facet)}
        for name, facets in search.facets.items()
        if fields[name].path is not None
        for index, facet in enumerate(facets)
    }
    return {
        "query": {"bool": {"filter": [*search.engine.holds, *search.filters], "must": must}},
        "sort": _sort_clauses(search.sort, fields),
        "aggs": aggs,
        "from_": min(start, RESULT_WINDOW),
        "size": max(0, min(search.size, RESULT_WINDOW - start)),
    }


def _facet_terms(engine_field: EngineField, facet: _Facet) -> dict[str, Any]:
    """A facet's ``terms``: one more value than asked, to drop an empty one; missing values counted (DD-530)."""
    terms = {"field": engine_field.path, "size": facet.size + 1, "order": _facet_order(facet)}
    return terms if engine_field.missing is None else terms | {"missing": engine_field.missing}


def _facet_order(facet: _Facet) -> list[dict[str, str]]:
    """A facet's order; ties of counts by value (ASE-07)."""
    return [facet.order, {"_key": "asc"}] if "_count" in facet.order else [facet.order]


def _sort_clauses(sort: list[tuple[str, str]], fields: Mapping[str, EngineField]) -> list[dict[str, Any]]:
    """The sort, constants dropped, a missing number as its ``missing`` value, ties by ``id`` (ASE-08, DD-530)."""
    clauses: list[dict[str, Any]] = []
    for name, direction in sort or [("_score", "desc")]:
        if name == "_score":
            clauses.append({"_score": {"order": direction}})
        elif (path := fields[name].path) is not None:
            missing = fields[name].missing
            clauses.append({path: {"order": direction} | ({} if missing is None else {"missing": missing})})
    return [*clauses, {"guid": {"order": "asc"}}]


class AppSearchEngine:
    """An engine over ``documents``' entity index, ``atlas-dev`` by default (ASE-03 to ASE-11, ASQ-03)."""

    def __init__(self, documents: ElasticsearchEntityDocuments, engine: Engine = ATLAS_DEV) -> None:
        """``engine`` answering from ``documents``."""
        self._documents = documents
        self._engine = engine

    async def search(self, body: object) -> dict[str, Any]:
        """App Search's answer to the request ``body``.

        Raises:
            AppSearchError: 400 for a request App Search refuses (ASE-04).
        """
        search = parse(body, self._engine)
        response = await self._documents.search_app_search(**query_body(search))
        total = int(response["hits"]["total"]["value"])
        return {
            "meta": {
                "alerts": [],
                "warnings": [],
                "precision": 2,
                "page": {
                    "current": search.current,
                    "total_pages": math.ceil(total / search.size),
                    "total_results": total,
                    "size": search.size,
                },
                "engine": {"name": self._engine.name, "type": "default"},
                "request_id": uuid.uuid4().hex,
            },
            "results": [_result(hit, search) for hit in response["hits"]["hits"]],
            "facets": _answered_facets(search, response.get("aggregations") or {}, total),
        }


def _result(hit: Mapping[str, Any], search: Search) -> dict[str, Any]:
    """One result: the fields asked for, ``id`` always, and ``_meta`` (ASE-10)."""
    source = hit["_source"]
    fields = search.engine.fields
    asked = search.result_fields if search.result_fields is not None else dict.fromkeys(fields, _ResultField(raw=True))
    result: dict[str, Any] = {"id": {"raw": source.get("guid")}}
    words = [word.lower() for word in _WORD.findall(search.query)]
    for name, options in asked.items():
        value = _plain(fields[name].value(source))
        answered: dict[str, Any] = {}
        if options.raw:
            answered["raw"] = _cut(value, options.raw_size)
        if options.snippet:
            answered["snippet"] = _snippet(value, words, options)
        result[name] = answered
    result["_meta"] = {"id": source.get("guid"), "engine": search.engine.name, "score": float(hit.get("_score") or 0.0)}
    return result


def _plain(value: Any) -> Any:  # noqa: ANN401 - a field's JSON value
    """The value as JSON answers it: a number the store reads as a ``Decimal`` a float, in a list too."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _cut(value: Any, size: int | None) -> Any:  # noqa: ANN401 - a field's JSON value
    """A text, or each text of a list, cut to ``size`` characters."""
    if size is None:
        return value
    if isinstance(value, str):
        return value[:size]
    if isinstance(value, list):
        return [item[:size] if isinstance(item, str) else item for item in value]
    return value


def _snippet(value: Any, words: list[str], options: _ResultField) -> str | None:  # noqa: ANN401 - a JSON value
    """The first text holding one of the query's words, cut, escaped, the words in ``<em>``; the first text when
    none does and ``fallback`` asks for it (DV-158).
    """  # noqa: D205 - one sentence
    texts = [item for item in (value if isinstance(value, list) else [value]) if isinstance(item, str)]
    wanted = set(words)
    for text in texts:
        cut = text[: options.snippet_size]
        if any(word.lower() in wanted for word in _WORD.findall(cut)):
            return _highlighted(cut, wanted)
    if options.fallback and texts:
        return html.escape(texts[0][: options.snippet_size])
    return None


def _highlighted(text: str, words: set[str]) -> str:
    parts, last = [], 0
    for match in _WORD.finditer(text):
        if match.group().lower() in words:
            parts += [html.escape(text[last : match.start()]), f"<em>{html.escape(match.group())}</em>"]
            last = match.end()
    return "".join([*parts, html.escape(text[last:])])


def _answered_facets(search: Search, aggregations: Mapping[str, Any], total: int) -> dict[str, Any]:
    """Each facet field's facets in the request's order: the values and counts, empty values left out (ASE-07)."""
    answered: dict[str, Any] = {}
    for name, facets in search.facets.items():
        engine_field = search.engine.fields[name]
        answered[name] = []
        for index, facet in enumerate(facets):
            if engine_field.path is None:
                constant = engine_field.constant
                data = [{"value": constant, "count": total}] if total and _is_number(constant) else []
            else:
                buckets = aggregations[f"{name}#{index}"]["buckets"]
                data = [
                    {"value": _plain(bucket["key"]), "count": bucket["doc_count"]}
                    for bucket in buckets
                    if bucket["key"] not in ("", None)
                ][: facet.size]
            answered[name].append({"type": "value", "data": data})
    return answered
