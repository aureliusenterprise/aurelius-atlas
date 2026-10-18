import html
import os
import re
import ssl
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Protocol

import dotenv
import httpx
import pytest
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the server's and the store's certificates."""

KEYCLOAK_PROJECT = PROJECT.parents[1] / "dev" / "keycloak"
"""The identity provider this stack authenticates against (6.1); its `.env` holds the dev secrets."""

SERVICE = "aurelius-atlas-server"

ISSUER = "https://keycloak.localhost:8443/realms/master"
CLIENT_ID = "aurelius-atlas"
WRITER = "aurelius-writer"
READER = "aurelius-reader"


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
    """Load the settings the compose file interpolates and the e2e login needs.

    The project's own ``.env`` (Nx decrypts it) plus the identity provider's dev secrets: the RP
    client secret (the compose passes it to the server as ``AUTH_CLIENT_SECRET``, and the bearer
    mint below needs it) and the dev users' passwords. They are deliberately absent from the
    project's ``.env`` — Nx injects that file into *every* task environment, and ``AUTH_*`` keys in
    it would switch the guard on inside the unit tests, which run the unconfigured installation
    (AUTH-01).
    """
    dotenv.load_dotenv(PROJECT / ".env")
    dotenv.load_dotenv(KEYCLOAK_PROJECT / ".env")


@pytest.fixture
async def client(server: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running server over HTTPS, verifying it against the dev CA."""
    async with httpx.AsyncClient(base_url=server, verify=ssl.create_default_context(cafile=CA_FILE)) as client:
        yield client


@pytest.fixture
async def auth_client(server: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client that does not follow redirects: the login flow is asserted step by step (AUTH-06 to AUTH-10)."""
    async with httpx.AsyncClient(
        base_url=server,
        verify=ssl.create_default_context(cafile=CA_FILE),
        follow_redirects=False,
        timeout=30,
    ) as client:
        yield client


def mint_bearer(username: str, password: str) -> str:
    """An access token for a dev realm user, minted at the issuer (AUTH-03's bearer path).

    The password grant is enabled on the relying-party client in ``dev/keycloak/import/master.json``
    for exactly this purpose; the token is signed and issued by the same Keycloak the server verifies
    against, so the guard treats it like a browser session's token.
    """
    response = httpx.post(
        f"{ISSUER}/protocol/openid-connect/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": os.environ["ATLAS_RP_CLIENT_SECRET"],
            "grant_type": "password",
            "username": username,
            "password": password,
        },
        verify=ssl.create_default_context(cafile=KEYCLOAK_PROJECT / "certs" / "ca.pem"),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


@pytest.fixture
def writer_bearer() -> str:
    """A fresh bearer token for the dev user who holds the ADMIN realm role.

    Minted per test: the realm issues hour-long tokens, but the suite must not depend on how long
    one lives — a fixture that outlives its token would fail the scenario it seeded.
    """
    deadline = time.monotonic() + 60
    while True:
        try:
            return mint_bearer(WRITER, os.environ["DEV_USER_WRITER_PASSWORD"])
        except httpx.HTTPStatusError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)  # the import may still be settling after a stack recreate


@pytest.fixture
def reader_bearer() -> str:
    """A fresh bearer token for the dev user who holds no roles."""
    return mint_bearer(READER, os.environ["DEV_USER_READER_PASSWORD"])


class SignIn(Protocol):
    """Runs the login dance for a dev user and answers with the callback's response."""

    async def __call__(self, next_url: str = "/", *, username: str = WRITER) -> httpx.Response:
        """Sign the user in at the given URL and answer with the callback's response."""
        ...


@pytest.fixture
def sign_in(auth_client: httpx.AsyncClient) -> SignIn:
    """A callable that runs the whole login dance against the server origin (the callback's response).

    The same chain a browser walks (DSH-07 minus nginx): the server's login start answers the
    issuer's authorization URL; the issuer answers its login form, which takes the dev user's
    credentials; the POST answers this server's redirect URI with the code; the server's callback
    exchanges it and answers the kept URL with the session cookie. The client keeps the cookie
    afterwards, as the browser's jar does.

    A fixture rather than a module function the tests import: pytest modules do not import their
    ``conftest``, and the e2e directory lives under the pyright project, where such an import
    would not resolve.
    """

    async def sign_in(next_url: str = "/", *, username: str = WRITER) -> httpx.Response:
        start = await auth_client.get(f"/api/atlas/auth/login?next={next_url}")
        # Walk the issuer's redirects as a browser would, one step at a time: it answers either
        # its login form or — when its own session is still alive, as after a logout that never
        # followed the end-session redirect — the callback straight away.
        authorize = await auth_client.get(start.headers["location"], follow_redirects=False)
        for _ in range(5):  # a redirect chain that never settles is a bug, not a loop to trust
            if authorize.status_code in (
                301,
                302,
                303,
                307,
                308,
            ) and "/api/atlas/auth/callback" in authorize.headers.get("location", ""):
                return await auth_client.get(authorize.headers["location"])  # the SSO path skips the form
            if "kc-form-login" in authorize.text:
                break
            authorize = await auth_client.get(authorize.headers["location"], follow_redirects=False)
        action = _form_action(authorize.text)
        granted = await auth_client.post(action, data={"username": username, "password": _password(username)})
        return await auth_client.get(granted.headers["location"])

    return sign_in


def _password(username: str) -> str:
    return os.environ["DEV_USER_READER_PASSWORD" if username == READER else "DEV_USER_WRITER_PASSWORD"]


def _form_action(page: str) -> str:
    match = re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', page)
    if match is None:
        msg = "Keycloak's login form is not on the page"
        raise AssertionError(msg)
    return html.unescape(match.group(1))
