# HTTP client timeout configuration (in seconds)
import ssl
from collections.abc import Generator

import httpx2 as httpx
from fastapi import HTTPException

from aurelius_atlas_fastapi_example.globals import LOGGER

from .settings import Settings

HTTP_TIMEOUT = 5.0


def http_client(settings: Settings) -> Generator[httpx.Client]:
    """Return an HTTP client for making requests to external services."""
    # httpx2 rides the OS trust store and ignores SSL_CERT_FILE, so pass the CA
    # explicitly as a context when the environment ships a private CA (DD-122).
    context = (
        ssl.create_default_context(cafile=str(settings.auth_ca_file))
        if settings.auth_ca_file
        else ssl.create_default_context()
    )
    with httpx.Client(timeout=HTTP_TIMEOUT, verify=context) as client:
        try:
            yield client
        except httpx.HTTPError as e:
            LOGGER.error("HTTP error occurred: %s", e)
            raise HTTPException(status_code=503) from e
