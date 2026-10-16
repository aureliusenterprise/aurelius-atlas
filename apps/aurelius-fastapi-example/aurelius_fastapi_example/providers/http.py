# HTTP client timeout configuration (in seconds)
from collections.abc import Generator

import httpx
from fastapi import HTTPException

from aurelius_fastapi_example.globals import LOGGER

from .settings import Settings

HTTP_TIMEOUT = 5.0


def http_client(settings: Settings) -> Generator[httpx.Client]:
    """Return an HTTP client for making requests to external services."""
    # httpx verifies TLS with certifi and ignores SSL_CERT_FILE, so pass the
    # CA explicitly when the environment ships a private certificate authority.
    verify: str | bool = settings.auth_ca_file or True
    with httpx.Client(timeout=HTTP_TIMEOUT, verify=verify) as client:
        try:
            yield client
        except httpx.HTTPError as e:
            LOGGER.error("HTTP error occurred: %s", e)
            raise HTTPException(status_code=503) from e
