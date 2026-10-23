"""A stand-in for ``AsyncElasticsearch`` for unit tests that need no server."""

import json
import re
from decimal import Decimal
from functools import cmp_to_key
from typing import Any

from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig
from elasticsearch import ConflictError, NotFoundError

NODE = NodeConfig("https", "localhost", 9200)


def response_meta(status: int) -> ApiResponseMeta:
    """Response metadata as the transport attaches it to an ``ApiError``."""
    return ApiResponseMeta(status=status, http_version="1.1", headers=HttpHeaders(), duration=0.0, node=NODE)


def _not_found() -> NotFoundError:
    return NotFoundError("document_missing", response_meta(404), {"found": False})


def _conflict() -> ConflictError:
    return ConflictError("version_conflict_engine_exception", response_meta(409), {"status": 409})


class FakeCluster:
    """The ``cluster`` namespace of the fake client."""

    def __init__(self, client: FakeClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        """Answer like ``GET _cluster/health``, or raise the configured error."""
        if self._client.health_error is not None:
            raise self._client.health_error
        return {"cluster_name": self._client.cluster_name, "status": self._client.cluster_status}


class FakeIndices:
    """The ``indices`` namespace of the fake client: aliases and index creation."""

    def __init__(self, client: FakeClient) -> None:
        self._client = client

    async def exists_alias(self, *, name: str) -> bool:
        """Whether ``name`` is an alias of a created index."""
        return name in self._client.aliases

    async def create(self, *, index: str, aliases: dict[str, Any] | None = None, **_settings: object) -> dict[str, Any]:
        """Create ``index`` with ``aliases``; settings and mappings are accepted and ignored."""
        self._client.documents.setdefault(index, {})
        for alias in aliases or {}:
            self._client.aliases[alias] = index
        return {"acknowledged": True, "index": index}

    async def put_mapping(self, *, index: str, **_mapping: object) -> dict[str, Any]:
        """Count the call; the fake keeps no mappings."""
        self._client.mapping_updates.append(index)
        return {"acknowledged": True}

    async def put_settings(self, *, index: str, **_settings: object) -> dict[str, Any]:
        """Count the call; the fake keeps no settings."""
        self._client.settings_updates.append(index)
        return {"acknowledged": True}

    async def refresh(self, *, index: str) -> dict[str, Any]:
        """Count the call; the fake's documents are always visible."""
        self._client.refreshes.append(index)
        return {"_shards": {"failed": 0}}


class FakeClient:
    """Records how it was built and closed; ``info`` and ``cluster.health`` return or raise as configured.

    Cast it to ``AsyncElasticsearch`` where a client is expected; it implements only what the store uses.
    """

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.version = "9.5.5"
        self.cluster_name = "aurelius-atlas"
        self.cluster_status = "green"
        self.info_error: BaseException | None = None
        self.health_error: BaseException | None = None
        self.close_calls = 0
        self.cluster = FakeCluster(self)
        self.indices = FakeIndices(self)
        self.aliases: dict[str, str] = {}
        self.documents: dict[str, dict[str, tuple[dict[str, Any], int]]] = {}
        self.primary_term = 1
        self.mapping_updates: list[str] = []
        self.settings_updates: list[str] = []
        self.seq_no = -1
        self.refreshes: list[str] = []

    def _index_of(self, name: str) -> dict[str, tuple[dict[str, Any], int]]:
        return self.documents.setdefault(self.aliases.get(name, name), {})

    async def get(self, *, index: str, id: str, source: bool = True) -> dict[str, Any]:  # noqa: A002 - Elasticsearch's name
        """Answer like ``GET index/_doc/id``, raising ``NotFoundError`` for a missing document."""
        stored = self._index_of(index).get(id)
        if stored is None:
            raise _not_found()
        document, seq_no = stored
        response: dict[str, Any] = {"_id": id, "_seq_no": seq_no, "_primary_term": self.primary_term, "found": True}
        if source:
            response["_source"] = document
        return response

    async def index(  # noqa: PLR0913 - Elasticsearch's keyword arguments
        self,
        *,
        index: str,
        id: str,  # noqa: A002 - Elasticsearch's name
        document: dict[str, Any] | bytes,
        op_type: str | None = None,
        if_seq_no: int | None = None,
        if_primary_term: int | None = None,
        **_options: object,
    ) -> dict[str, Any]:
        """Store ``document``, raising ``ConflictError`` like Elasticsearch for ``op_type=create`` or ``if_seq_no``.

        A body given as bytes is read as Elasticsearch reads it, its floats kept as decimals.
        """
        if isinstance(document, bytes):
            document = _read(document)
        documents = self._index_of(index)
        current = documents.get(id)
        if op_type == "create" and current is not None:
            raise _conflict()
        if if_seq_no is not None and (
            current is None or current[1] != if_seq_no or if_primary_term != self.primary_term
        ):
            raise _conflict()
        self.seq_no += 1
        seq_no = self.seq_no
        documents[id] = (document, seq_no)
        return {"_id": id, "_seq_no": seq_no, "_primary_term": self.primary_term, "result": "created"}

    async def mget(self, *, index: str, ids: list[str]) -> dict[str, Any]:
        """Answer like ``_mget``: one entry per id, ``found`` or not."""
        docs = []
        for document_id in ids:
            try:
                docs.append(await self.get(index=index, id=document_id))
            except NotFoundError:
                docs.append({"_id": document_id, "found": False})
        return {"docs": docs}

    async def bulk(self, *, operations: bytes, **_options: object) -> dict[str, Any]:
        """Apply ``create``, ``index`` and ``delete`` actions of an NDJSON body, each with its own outcome."""
        lines = iter([line for line in operations.split(b"\n") if line.strip()])
        items = []
        for action_line in lines:
            ((kind, action),) = _read(action_line).items()
            versions = {"if_seq_no": action.get("if_seq_no"), "if_primary_term": action.get("if_primary_term")}
            try:
                if kind == "delete":
                    result = await self.delete(index=action["_index"], id=action["_id"], **versions)
                else:
                    result = await self.index(
                        index=action["_index"],
                        id=action["_id"],
                        document=_read(next(lines)),
                        op_type="create" if kind == "create" else None,
                        **versions,
                    )
                items.append({kind: {"_id": action["_id"], "status": 200 if kind == "delete" else 201, **result}})
            except ConflictError:
                items.append({kind: {"_id": action["_id"], "status": 409}})
            except NotFoundError:
                items.append({kind: {"_id": action["_id"], "status": 404}})
        return {"errors": any(next(iter(item.values()))["status"] >= 300 for item in items), "items": items}  # noqa: PLR2004

    async def delete(
        self,
        *,
        index: str,
        id: str,  # noqa: A002 - Elasticsearch's name
        if_seq_no: int | None = None,
        if_primary_term: int | None = None,
    ) -> dict[str, Any]:
        """Delete a document, raising ``NotFoundError`` when missing and ``ConflictError`` on a stale version."""
        documents = self._index_of(index)
        current = documents.get(id)
        if current is None:
            raise _not_found()
        if if_seq_no is not None and (current[1] != if_seq_no or if_primary_term != self.primary_term):
            raise _conflict()
        del documents[id]
        return {"_id": id, "result": "deleted"}

    async def search(  # noqa: PLR0913 - Elasticsearch's keyword arguments
        self,
        *,
        index: str,
        size: int = 10,
        query: dict[str, Any] | None = None,
        sort: list[Any] | None = None,
        search_after: list[Any] | None = None,
        seq_no_primary_term: bool = False,
        from_: int = 0,
        track_total_hits: bool | None = None,
    ) -> dict[str, Any]:
        """Answer like ``_search`` with the documents matching the query, ``size`` of them from ``from_``.

        With ``sort``, hits are ordered by the sort fields and carry their sort values; a plain direction stands a
        document without the field in with its id, an options object puts it last. Only hits after
        ``search_after`` are answered. The total counts every match.
        """
        _ = track_total_hits
        order = [_sort_clause(clause) for clause in sort or []]
        hits = []
        for document_id, (source, seq_no) in self._index_of(index).items():
            values = [_sort_value(source, field, document_id, options) for field, options in order]
            if not _matches(source, query) or (search_after is not None and _compare(values, search_after, order) <= 0):
                continue
            hit: dict[str, Any] = {"_id": document_id, "_source": source}
            if seq_no_primary_term:
                hit |= {"_seq_no": seq_no, "_primary_term": self.primary_term}
            if sort:
                hit["sort"] = values
            hits.append(hit)
        if sort:
            hits.sort(key=cmp_to_key(lambda a, b: _compare(a["sort"], b["sort"], order)))
        return {"hits": {"total": {"value": len(hits)}, "hits": hits[from_ : from_ + size]}}

    async def count(self, *, index: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Answer like ``_count`` for a ``match_all`` or ``term`` query."""
        return {"count": sum(1 for source, _ in self._index_of(index).values() if _matches(source, query))}

    async def info(self) -> dict[str, Any]:
        """Answer like ``GET /``, or raise the configured error."""
        if self.info_error is not None:
            raise self.info_error
        return {"cluster_name": self.cluster_name, "version": {"number": self.version}}

    async def close(self) -> None:
        """Count the call."""
        self.close_calls += 1


def _read(body: bytes) -> dict[str, Any]:
    """A JSON body as Elasticsearch reads it, its floats as decimals."""
    return json.loads(body, parse_float=Decimal)


def _matches(source: dict[str, Any], query: dict[str, Any] | None) -> bool:  # noqa: PLR0911 - one per kind
    """Whether ``source`` matches a query: ``match_all``, ``match_none``, ``bool`` (``filter``, ``must_not``,
    ``should``), and single-field ``term``, ``terms``, ``range``, ``prefix``, ``wildcard`` and ``exists``.
    """  # noqa: D205 - one sentence
    if query is None or "match_all" in query:
        return True
    if "match_none" in query:
        return False
    if "bool" in query:
        clauses = query["bool"]
        should = clauses.get("should", [])
        return (
            all(_matches(source, clause) for clause in clauses.get("filter", []))
            and not any(_matches(source, clause) for clause in clauses.get("must_not", []))
            and (not should or any(_matches(source, clause) for clause in should))
        )
    if "exists" in query:
        return _held(source, query["exists"]["field"]) != []
    ((kind, condition),) = query.items()
    ((field, operand),) = condition.items()
    held = _held(source, field)
    if kind == "range":
        return any(_in_range(value, operand) for value in held)
    if kind == "terms":
        return any(value in held for value in operand)
    if kind == "prefix":
        return any(isinstance(value, str) and value.startswith(operand) for value in held)
    if kind == "wildcard":
        pattern = _wildcard(operand["value"] if isinstance(operand, dict) else operand)
        return any(isinstance(value, str) and pattern.fullmatch(value) is not None for value in held)
    return operand in held


def _value(source: dict[str, Any], field: str) -> Any:  # noqa: ANN401 - any field value
    """A field's value: by its full name, or through objects, as a dotted path."""
    if field in source:
        return source[field]
    head, separator, rest = field.partition(".")
    while separator:
        inner = source.get(head)
        if isinstance(inner, dict):
            found = _value(inner, rest)
            if found is not None:
                return found
        step, separator, rest = rest.partition(".")
        head = f"{head}.{step}"
    return None


def _held(source: dict[str, Any], field: str) -> list[Any]:
    """The values a field holds: none, one, or an array's."""
    value = _value(source, field)
    return [] if value is None else value if isinstance(value, list) else [value]


def _wildcard(pattern: str) -> re.Pattern[str]:
    """An Elasticsearch wildcard pattern as a regular expression: ``*``, ``?``, and backslash escaping."""
    parts, escaped = [], False
    for character in pattern:
        if escaped:
            parts.append(re.escape(character))
            escaped = False
        elif character == "\\":
            escaped = True
        else:
            parts.append(".*" if character == "*" else "." if character == "?" else re.escape(character))
    return re.compile("".join(parts), re.DOTALL)


def _sort_clause(clause: Any) -> tuple[str, dict[str, Any]]:  # noqa: ANN401 - a sort clause
    ((field, options),) = clause.items()
    return field, options if isinstance(options, dict) else {"order": options, "missing": "_id"}


def _sort_value(source: dict[str, Any], field: str, document_id: str, options: dict[str, Any]) -> Any:  # noqa: ANN401
    """A hit's value of a sort field: an array's least, or largest descending; the id or None when missing."""
    held = _held(source, field)
    if not held:
        return document_id if options.get("missing") == "_id" else None
    return max(held) if options.get("order") == "desc" else min(held)


_BOUNDS = {
    "gt": lambda value, bound: value > bound,
    "gte": lambda value, bound: value >= bound,
    "lt": lambda value, bound: value < bound,
    "lte": lambda value, bound: value <= bound,
}


def _in_range(value: Any, bounds: dict[str, Any]) -> bool:  # noqa: ANN401 - any field value
    """Whether a present value meets every bound of a ``range`` query."""
    return value is not None and all(_BOUNDS[name](value, bound) for name, bound in bounds.items())


def _compare(left: list[Any], right: list[Any], order: list[tuple[str, dict[str, Any]]]) -> int:
    """Compare two hits' sort values field by field, each ascending or descending, missing ones last."""
    for a, b, (_, options) in zip(left, right, order, strict=False):
        if a == b:
            continue
        if a is None or b is None:
            return 1 if a is None else -1
        smaller = -1 if a < b else 1
        return -smaller if options.get("order") == "desc" else smaller
    return 0
