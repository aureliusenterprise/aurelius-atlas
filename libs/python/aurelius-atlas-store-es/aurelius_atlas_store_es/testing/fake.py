"""A stand-in for ``AsyncElasticsearch`` for unit tests that need no server."""

from typing import Any

from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig

NODE = NodeConfig("https", "localhost", 9200)


def response_meta(status: int) -> ApiResponseMeta:
    """Response metadata as the transport attaches it to an ``ApiError``."""
    return ApiResponseMeta(status=status, http_version="1.1", headers=HttpHeaders(), duration=0.0, node=NODE)


class FakeCluster:
    """The ``cluster`` namespace of the fake client."""

    def __init__(self, client: FakeClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        """Answer like ``GET _cluster/health``, or raise the configured error."""
        if self._client.health_error is not None:
            raise self._client.health_error
        return {"cluster_name": self._client.cluster_name, "status": self._client.cluster_status}


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

    async def info(self) -> dict[str, Any]:
        """Answer like ``GET /``, or raise the configured error."""
        if self.info_error is not None:
            raise self.info_error
        return {"cluster_name": self.cluster_name, "version": {"number": self.version}}

    async def close(self) -> None:
        """Count the call."""
        self.close_calls += 1
