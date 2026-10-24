import ssl
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import dotenv
import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_server_client import AtlasClient
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the server's and the store's certificates."""

SERVICE = "aurelius-atlas-server"


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


@pytest_asyncio.fixture(loop_scope="function")
async def client(server: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running server over HTTPS, verifying it against the dev CA."""
    async with httpx.AsyncClient(base_url=server, verify=ssl.create_default_context(cafile=CA_FILE)) as client:
        yield client


# The function loop (pytest-asyncio 1.x): the root config gives async fixtures
# a module loop, which here outlives the test loops its TLS connections were
# opened on — aclose then schedules on a closed loop ("Event loop is closed").
# On the function loop, the client, its requests, and aclose share one loop.
@pytest_asyncio.fixture(loop_scope="function")
async def api(server: str) -> AsyncIterator[AtlasClient]:
    """The typed Atlas client for the running server over HTTPS (CL-11).

    The fixture builds the httpx pool and closes it (CL-02). The server's admin
    routes are open until 6.1, so the token source is empty — an empty source
    travels unauthenticated (CL-03), exactly as the dashboard calls arrive.
    """
    async with httpx.AsyncClient(base_url=server, verify=ssl.create_default_context(cafile=CA_FILE)) as http:
        yield AtlasClient(http, "")
