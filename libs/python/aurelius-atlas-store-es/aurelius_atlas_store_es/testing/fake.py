"""A stand-in for ``AsyncElasticsearch`` for unit tests that need no server."""

import json
from decimal import Decimal
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
    ) -> dict[str, Any]:
        """Answer like ``_search`` with the documents matching a ``match_all`` or ``term`` query.

        With ``sort``, hits are ordered by their id and carry it as their sort value, after ``search_after``.
        """
        hits = []
        for document_id, (source, seq_no) in (
            sorted(self._index_of(index).items()) if sort else self._index_of(index).items()
        ):
            if not _matches(source, query) or (search_after is not None and document_id <= search_after[0]):
                continue
            hit: dict[str, Any] = {"_id": document_id, "_source": source}
            if seq_no_primary_term:
                hit |= {"_seq_no": seq_no, "_primary_term": self.primary_term}
            if sort:
                hit["sort"] = [document_id]
            hits.append(hit)
        return {"hits": {"total": {"value": len(hits)}, "hits": hits[:size]}}

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


def _matches(source: dict[str, Any], query: dict[str, Any] | None) -> bool:
    """Whether ``source`` matches a ``match_all``, or a single-field ``term`` or ``terms`` query."""
    if query is None or "match_all" in query:
        return True
    if "terms" in query:
        ((field, values),) = query["terms"].items()
        found = source.get(field)
        held = found if isinstance(found, list) else [found]
        return any(value in held for value in values)
    ((field, value),) = query["term"].items()
    found = source.get(field)
    return value in found if isinstance(found, list) else found == value
