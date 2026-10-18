"""A stand-in for ``AsyncElasticsearch`` for unit tests that need no server."""

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
        self.seq_no = -1

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
        document: dict[str, Any],
        op_type: str | None = None,
        if_seq_no: int | None = None,
        if_primary_term: int | None = None,
        **_options: object,
    ) -> dict[str, Any]:
        """Store ``document``, raising ``ConflictError`` like Elasticsearch for ``op_type=create`` or ``if_seq_no``."""
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

    async def info(self) -> dict[str, Any]:
        """Answer like ``GET /``, or raise the configured error."""
        if self.info_error is not None:
            raise self.info_error
        return {"cluster_name": self.cluster_name, "version": {"number": self.version}}

    async def close(self) -> None:
        """Count the call."""
        self.close_calls += 1
