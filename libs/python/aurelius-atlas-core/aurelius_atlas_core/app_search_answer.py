"""App Search's answer: the engine over documents, its rendered hits and the highlighted snippet (ASE-10 to
ASE-11, ASQ-03, ASG-05, DD-525, DD-790).

The query module checks and builds the request, the search runs on the engine's index, and each hit is read
back through the schema's table in App Search's shape. The highlighter splits on ``free_text``'s word (19.1's
DD-772), so it cannot disagree with the index.
"""  # noqa: D205 - one sentence

import html
import math
import uuid
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from aurelius_atlas_store_es.text_analysis import WORD, words

from aurelius_atlas_core.app_search_query import Search, _ResultField, parse, query_body
from aurelius_atlas_core.app_search_schema import ATLAS_DEV, Engine, _is_number
from aurelius_atlas_core.entity_documents import SearchDocuments


class AppSearchEngine:
    """An engine over ``documents``' indices, ``atlas-dev`` by default (ASE-03 to ASE-11, ASQ-03, ASG-05)."""

    def __init__(self, documents: SearchDocuments, engine: Engine = ATLAS_DEV) -> None:
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
    document_id = source.get(search.engine.id_field)
    asked = search.result_fields if search.result_fields is not None else dict.fromkeys(fields, _ResultField(raw=True))
    result: dict[str, Any] = {"id": {"raw": document_id}}
    query_words = words(search.query)
    for name, options in asked.items():
        value = plain(fields[name].value(source))
        answered: dict[str, Any] = {}
        if options.raw:
            answered["raw"] = _cut(value, options.raw_size)
        if options.snippet:
            answered["snippet"] = _snippet(value, query_words, options)
        result[name] = answered
    result["_meta"] = {"id": document_id, "engine": search.engine.name, "score": float(hit.get("_score") or 0.0)}
    return result


def plain(value: Any) -> Any:  # noqa: ANN401 - a field's JSON value
    """The value as JSON answers it: a number the store reads as a ``Decimal`` a float, in a list too."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [plain(item) for item in value]
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


def _snippet(value: Any, query_words: list[str], options: _ResultField) -> str | None:  # noqa: ANN401 - a JSON value
    """The first text holding one of the query's words, cut, escaped, the words in ``<em>``; the first text when
    none does and ``fallback`` asks for it (DV-158).
    """  # noqa: D205 - one sentence
    texts = [item for item in (value if isinstance(value, list) else [value]) if isinstance(item, str)]
    wanted = set(query_words)
    for text in texts:
        cut = text[: options.snippet_size]
        if any(word in wanted for word in words(cut)):
            return _highlighted(cut, wanted)
    if options.fallback and texts:
        return html.escape(texts[0][: options.snippet_size])
    return None


def _highlighted(text: str, words: set[str]) -> str:
    parts, last = [], 0
    for match in WORD.finditer(text):
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
                    {"value": plain(bucket["key"]), "count": bucket["doc_count"]}
                    for bucket in buckets
                    if bucket["key"] not in ("", None)
                ][: facet.size]
            answered[name].append({"type": "value", "data": data})
    return answered
