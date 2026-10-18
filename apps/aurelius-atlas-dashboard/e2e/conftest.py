import ssl
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import dotenv
import httpx
import pytest
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the dashboard's certificate."""

SERVER_PROJECT = PROJECT.parent / "aurelius-atlas-server"
SERVER_CA_FILE = SERVER_PROJECT / "certs" / "ca.pem"
"""The server project's copy of the same dev CA (one mkcert root, `nx certgen` per project)."""

DASHBOARD_SERVICE = "aurelius-atlas-dashboard"
SERVER_SERVICE = "aurelius-atlas-server"


@pytest.fixture(scope="session", autouse=True)
def _environment() -> None:
    """Load the project's decrypted settings, which the compose file reads."""
    dotenv.load_dotenv(PROJECT / ".env")


@pytest.fixture(scope="session")
def stack() -> Iterator[DockerCompose]:
    """The stack of the project's `docker-compose.yaml`, once healthy: the dashboard origin and the API server.

    ``docker compose up --wait`` returns when the server image's healthcheck passes, and the dashboard
    container starts only after it (``depends_on: service_healthy``).
    """
    with DockerCompose(context=PROJECT, env_file=str(PROJECT / ".env")) as compose:
        yield compose


@pytest.fixture(scope="session")
def dashboard(stack: DockerCompose) -> str:
    """The public origin: the dashboard image, with the API proxied from the server (DD-034)."""
    port = stack.get_service_port(DASHBOARD_SERVICE, 8080)
    return f"https://localhost:{port}"


@pytest.fixture(scope="session")
def server(stack: DockerCompose) -> str:
    """The server's own origin, reached directly beside the proxy."""
    port = stack.get_service_port(SERVER_SERVICE, 21000)
    return f"https://localhost:{port}"


@pytest.fixture
async def dashboard_client(dashboard: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the dashboard origin over HTTPS, verifying it against the dev CA.

    nginx serves the dashboards and proxies the API here; its certificate is the dashboard project's
    own leaf, issued by the same mkcert root the CA file holds.
    """
    context = ssl.create_default_context(cafile=CA_FILE)
    async with httpx.AsyncClient(base_url=dashboard, verify=context) as client:
        yield client


@pytest.fixture
async def server_client(server: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the server's own origin over HTTPS, verifying it against the dev CA."""
    context = ssl.create_default_context(cafile=SERVER_CA_FILE)
    async with httpx.AsyncClient(base_url=server, verify=context) as client:
        yield client
