import logging
from types import TracebackType
from typing import Self

from elasticsearch import ApiError, AsyncElasticsearch, TransportError

from .errors import StoreUnavailableError, UnsupportedVersionError
from .health import HealthReport, HealthStatus, check_health
from .settings import StoreSettings

LOGGER = logging.getLogger(__name__)

SUPPORTED_MAJOR_VERSION = 9
"""The Elasticsearch major version this store supports (STO-04)."""

STORE_NOT_OPEN_ERROR = "Elasticsearch store is not open"


class ElasticsearchStore:
    """The single entry point to Elasticsearch: owns one client from ``open`` to ``close`` (STO-03).

    Use it as an async context manager:

    ```python
    async with ElasticsearchStore(settings) as store:
        report = await store.health()
    ```
    """

    def __init__(self, settings: StoreSettings) -> None:
        self._settings = settings
        self._client: AsyncElasticsearch | None = None

    @property
    def is_open(self) -> bool:
        """Whether the store holds an open client."""
        return self._client is not None

    @property
    def client(self) -> AsyncElasticsearch:
        """The open client.

        Raises:
            RuntimeError: When the store is not open.
        """
        if self._client is None:
            raise RuntimeError(STORE_NOT_OPEN_ERROR)
        return self._client

    async def open(self) -> None:
        """Connect and check that the server runs a supported version (STO-04).

        Opening an open store does nothing.

        Raises:
            StoreUnavailableError: When the server cannot be reached or rejects the request.
            UnsupportedVersionError: When the server's major version is not supported.
        """
        if self._client is not None:
            return

        client = AsyncElasticsearch(
            hosts=self._settings.host_urls,
            basic_auth=(self._settings.username, self._settings.password.get_secret_value()),
            ca_certs=str(self._settings.ca_certs_path),
            verify_certs=True,
            request_timeout=self._settings.request_timeout,
        )

        try:
            version = await _server_version(client)
        except BaseException:
            await client.close()
            raise

        if _major(version) != SUPPORTED_MAJOR_VERSION:
            await client.close()
            raise UnsupportedVersionError(version, SUPPORTED_MAJOR_VERSION)

        self._client = client
        LOGGER.info("Connected to Elasticsearch %s at %s", version, ", ".join(self._settings.host_urls))

    async def close(self) -> None:
        """Close the client; closing a closed store does nothing (STO-03)."""
        client, self._client = self._client, None
        if client is not None:
            await client.close()
            LOGGER.info("Closed the Elasticsearch client")

    async def health(self) -> HealthReport:
        """Report whether the store can serve requests; never raises (STO-05, STO-06)."""
        if self._client is None:
            return HealthReport(status=HealthStatus.DOWN, reason="store is not open")
        return await check_health(self._client)

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()


async def _server_version(client: AsyncElasticsearch) -> str:
    try:
        info = await client.info()
    except ApiError as error:
        message = f"Elasticsearch rejected the connection with status {error.meta.status}"
        raise StoreUnavailableError(message) from error
    except TransportError as error:
        message = f"Elasticsearch is unreachable ({type(error).__name__})"
        raise StoreUnavailableError(message) from error
    return str(info["version"]["number"])


def _major(version: str) -> int | None:
    head = version.split(".", 1)[0]
    return int(head) if head.isdigit() else None
