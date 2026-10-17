class StoreError(Exception):
    """Base class for errors raised by the Elasticsearch store."""


class StoreUnavailableError(StoreError):
    """The store could not be opened: the server is unreachable, timed out or rejected the request."""


class UnsupportedVersionError(StoreError):
    """The server runs an Elasticsearch major version this store does not support."""

    def __init__(self, version: str, supported_major: int) -> None:
        super().__init__(f"Elasticsearch {version} is not supported; major version {supported_major} is required")
        self.version = version
        self.supported_major = supported_major
