import html
import os
import re
import ssl
import time
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

KEYCLOAK_PROJECT = PROJECT.parents[1] / "dev" / "keycloak"
"""The identity provider this stack authenticates against (6.1); its `.env` holds the dev secrets."""

ISSUER = "https://keycloak.localhost:8443/realms/master"
CLIENT_ID = "aurelius-atlas"
WRITER = "aurelius-writer"


@pytest.fixture(scope="session", autouse=True)
def _environment() -> None:
    """Load the settings the compose file reads and the e2e login needs.

    The project's own ``.env`` (Nx decrypts it) plus the identity provider's dev secrets — the
    relying-party client secret and the dev users' passwords. The Keycloak file is loaded here, not
    the project's: Nx injects only the project's ``.env`` into the task environment.
    """
    dotenv.load_dotenv(PROJECT / ".env")
    dotenv.load_dotenv(KEYCLOAK_PROJECT / ".env")


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


def mint_bearer(username: str) -> str:
    """An access token for a dev realm user, minted at the issuer (the guard's bearer path, AUTH-03).

    The password grant is enabled on the relying-party client in ``dev/keycloak/import/master.json``
    for exactly this purpose; the token is signed and issued by the same Keycloak the stack
    authenticates against.
    """
    response = httpx.post(
        f"{ISSUER}/protocol/openid-connect/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": os.environ["AURELIUS_ATLAS_DASHBOARD_ATLAS_RP_CLIENT_SECRET"],
            "grant_type": "password",
            "username": username,
            "password": os.environ["DEV_USER_WRITER_PASSWORD"],
        },
        verify=ssl.create_default_context(cafile=CA_FILE),  # one mkcert root signs every leaf here
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def writer_bearer() -> str:
    """A fresh bearer token for the dev user who holds the ADMIN realm role (DSH-04)."""
    deadline = time.monotonic() + 60
    while True:
        try:
            return mint_bearer(WRITER)
        except httpx.HTTPStatusError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)  # the import may still be settling after a stack recreate


@pytest.fixture(scope="session")
def writer_password() -> str:
    """The dev user's password, for the browser's login form (DSH-07)."""
    return os.environ["DEV_USER_WRITER_PASSWORD"]


def _form_action(page: str) -> str:
    match = re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', page)
    if match is None:
        msg = "Keycloak's login form is not on the page"
        raise AssertionError(msg)
    return html.unescape(match.group(1))


async def _sign_in(client: httpx.AsyncClient) -> None:
    """Drive the whole login dance over the dashboard origin, leaving the session cookie on the jar.

    What a gated browser walk does (DSH-07), one request at a time: the server's login start (through
    nginx's ``/api/`` proxy) answers the issuer's authorization URL; the issuer answers its login
    form; the POST answers this origin's callback with the code; the callback exchanges it and answers
    with the session cookie. The stack's redirect URI is this origin (port 8444), so the dance ends
    where the tests run.
    """
    start = await client.get("/api/atlas/auth/login?next=/")
    authorize = await client.get(start.headers["location"], follow_redirects=True)  # the login form
    action = _form_action(authorize.text)
    granted = await client.post(action, data={"username": WRITER, "password": os.environ["DEV_USER_WRITER_PASSWORD"]})
    callback = await client.get(granted.headers["location"])
    if callback.status_code != httpx.codes.FOUND or client.cookies.get("ATLASSESSIONID") is None:
        msg = "the login dance over the dashboard origin ended without a session"
        raise AssertionError(msg)


@pytest.fixture
async def logged_in_client(dashboard: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the dashboard origin, signed in as the dev writer through the gate (6.1).

    The gated pages (DSH-01/02) answer only with a session; this client holds one, minted against
    this very stack.
    """
    context = ssl.create_default_context(cafile=CA_FILE)
    async with httpx.AsyncClient(base_url=dashboard, verify=context, timeout=30) as client:
        await _sign_in(client)
        yield client


@pytest.fixture
async def session_cookie(logged_in_client: httpx.AsyncClient) -> str:
    """The value of a live session cookie, to seed a browser context (DSH-05/06)."""
    value = logged_in_client.cookies.get("ATLASSESSIONID")
    if value is None:
        msg = "the signed-in client holds no session cookie"
        raise AssertionError(msg)
    return value
