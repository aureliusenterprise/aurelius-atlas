import json
import os
import ssl
import time
from collections.abc import AsyncIterator, Generator, Iterator
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import dotenv
import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_server_client import AtlasClient
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the server's and the store's certificates."""

KEYCLOAK_ISSUER = "https://keycloak.localhost:8443/realms/master"
"""The dev realm on its TLS listener, the issuer the server verifies (6.1a, DD-250)."""

USERNAME = "aurelius-writer"
"""The dev realm's writer, whose tokens the suite sends and as whom the browser signs in."""

TOKEN_MARGIN_SECONDS = 15
"""A token this close to its expiry is minted anew: the dev realm's tokens live 60 seconds."""

SERVICE = "aurelius-atlas-server"
TIMEOUT = httpx.Timeout(30.0)
"""Per request: httpx's 5-second default was hit on shared CI runners by entity writes that refresh the store's
indices (``ReadTimeout`` in ``entity-owned-drop`` and ``entity-classification-propagation``)."""


@pytest.fixture(scope="session")
def server() -> Iterator[str]:
    """The server image on the dev store (started by the e2e target), once healthy; yields its base URL.

    ``docker compose up --wait`` returns when the image's healthcheck passes.
    """
    with DockerCompose(context=Path(__file__).parent, env_file=str(PROJECT / ".env")) as compose:
        port = compose.get_service_port(SERVICE, 21000)
        yield f"https://localhost:{port}"


@pytest.fixture(scope="session", autouse=True)
def _environment() -> None:
    """Load the project's decrypted settings, which the compose file reads."""
    dotenv.load_dotenv(PROJECT / ".env")


class UserToken:
    """The writer's access token from the dev realm, by the password grant of the webapp's client; minted anew
    when it is about to expire (6.1a, AUT-02).
    """  # noqa: D205 - one sentence

    def __init__(self) -> None:
        self._token = ""
        self._expires = 0.0

    def __call__(self) -> str:
        """A token valid for at least ``TOKEN_MARGIN_SECONDS``."""
        if time.monotonic() > self._expires - TOKEN_MARGIN_SECONDS:
            body = urlencode(
                {
                    "grant_type": "password",
                    "client_id": "aurelius",
                    "username": USERNAME,
                    "password": os.environ["DEV_USER_WRITER_PASSWORD"],
                }
            ).encode()
            request = Request(f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token", data=body, method="POST")  # noqa: S310 - the https issuer
            with urlopen(request, context=ssl.create_default_context(cafile=CA_FILE)) as response:  # noqa: S310 - CA-verified
                answer = json.load(response)
            self._token, self._expires = answer["access_token"], time.monotonic() + float(answer["expires_in"])
        return self._token


class Bearer(httpx.Auth):
    """Each request with the token source's current token."""

    def __init__(self, token: UserToken) -> None:
        self._token = token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        """Add the ``Authorization`` header."""
        request.headers["Authorization"] = f"Bearer {self._token()}"
        yield request


@pytest.fixture(scope="session")
def user_token() -> UserToken:
    """The writer's tokens, shared by the suite."""
    return UserToken()


@pytest_asyncio.fixture(loop_scope="function")
async def client(server: str, user_token: UserToken) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running server over HTTPS as the dev writer, verifying it against the dev CA."""
    async with httpx.AsyncClient(
        base_url=server, verify=ssl.create_default_context(cafile=CA_FILE), timeout=TIMEOUT, auth=Bearer(user_token)
    ) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def anonymous(server: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running server over HTTPS without credentials (AUT-04)."""
    async with httpx.AsyncClient(
        base_url=server, verify=ssl.create_default_context(cafile=CA_FILE), timeout=TIMEOUT
    ) as client:
        yield client


# The function loop (pytest-asyncio 1.x): the root config gives async fixtures
# a module loop, which here outlives the test loops its TLS connections were
# opened on — aclose then schedules on a closed loop ("Event loop is closed").
# On the function loop, the client, its requests, and aclose share one loop.
@pytest_asyncio.fixture(loop_scope="function")
async def api(server: str, user_token: UserToken) -> AsyncIterator[AtlasClient]:
    """The typed Atlas client for the running server over HTTPS (CL-11), as the dev writer (CL-03, AUT-02).

    The fixture builds the httpx pool and closes it (CL-02).
    """
    async with httpx.AsyncClient(
        base_url=server, verify=ssl.create_default_context(cafile=CA_FILE), timeout=TIMEOUT
    ) as http:
        yield AtlasClient(http, user_token)
