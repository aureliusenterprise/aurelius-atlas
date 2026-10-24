"""E2E fixtures: the 8.2 chain — the app image, the real data2model, the fixture Atlas (DD-111).

The compose file starts three services: the app under test, the 8.1 data2model
image, and a canned-file fixture Atlas (a ``python -m http.server`` over
``e2e/fixtures``, DD-111). Tokens are minted from the dev Keycloak for the
public ``aurelius`` client — the audience the chain forwards (AUX-04) — and
both apps verify them against the issuer's TLS :8443 listener.
"""

import ssl
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import dotenv
import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_lineage_model_client import LineageModelClient
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the apps' and the issuer's certificates."""

SERVICE = "aurelius-atlas-lineage-model"

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the dev realm to serve tokens (a reused stack may be warming up)."""


class Settings(BaseSettings):
    """Test configuration: the dev realm identity the e2e token mint signs in as."""

    auth_client_id: str
    """The public realm client the tokens are minted for (the webapp's client, the chain's audience)."""

    username: str
    """The dev user the tokens are minted for."""

    password: SecretStr
    """The dev user's password; never shown in logs."""

    model_config = SettingsConfigDict(
        # Same prefix as the application's settings: the project .env Nx injects
        # into the e2e task carries prefixed names.
        env_prefix="AURELIUS_ATLAS_LINEAGE_MODEL_",
        env_file=dotenv.find_dotenv(),
        extra="ignore",
    )


@pytest.fixture(scope="session")
def settings() -> Settings:
    """The test configuration, read from the injected project environment."""
    return Settings()  # pyright: ignore[reportCallIssue] - values load from the environment


@pytest.fixture(scope="session", autouse=True)
def _environment() -> None:
    """Load the project's decrypted settings, which the compose file reads."""
    dotenv.load_dotenv(PROJECT / ".env")


@pytest.fixture(scope="session")
def keycloak() -> DockerCompose:
    """The dev Keycloak, started and healthy (the e2e target starts it; starting is idempotent).

    The issuer serves TLS on the published :8443 listener; both apps verify
    bearer tokens against it (LM-08, DTM-10), and the suite mints its tokens
    there. Like the other suites, this fixture starts the stack and does not
    stop it: a running dev stack is reused across sessions.
    """
    context = Path(__file__).parents[3].absolute() / "dev" / "keycloak"
    compose = DockerCompose(context=context)
    compose.start()
    return compose


@pytest.fixture(scope="session")
def token(keycloak: DockerCompose, settings: Settings) -> str:
    """A bearer token for the chain, minted from the dev realm as the dev writer.

    The public `aurelius` client's password grant (import/master.json): the
    token carries azp `aurelius`, the audience both apps accept — the audience
    of the webapp tokens the chain forwards (AUX-04, LM-08).
    """
    port = keycloak.get_service_port("keycloak", 8443)
    deadline = time.monotonic() + MINT_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.post(
                f"https://keycloak.localhost:{port}/realms/master/protocol/openid-connect/token",
                data={
                    "client_id": settings.auth_client_id,
                    "grant_type": "password",
                    "username": settings.username,
                    "password": settings.password.get_secret_value(),
                },
                verify=ssl.create_default_context(cafile=str(CA_FILE)),
                timeout=10,
            )
            response.raise_for_status()
            return str(response.json()["access_token"])
        except (httpx.HTTPError, KeyError) as error:  # The realm import may still be running.
            last_error = error
            time.sleep(2)
    timeout_error = TimeoutError(f"the dev realm served no token within {MINT_TIMEOUT_SECONDS}s")
    raise timeout_error from last_error


@pytest.fixture(scope="session")
def app_url(keycloak: DockerCompose) -> Iterator[str]:
    """The chain, started by the e2e target (app, data2model, fixture Atlas), once healthy; yields the app's base URL.

    ``docker compose up --wait`` returns when every service's healthcheck
    passes: the fixture Atlas answers its canned graph, the data2model and the
    app answer liveness over TLS. The Keycloak stack is a session dependency:
    both apps verify tokens against it, and the OTLP mints start there.
    """
    _ = keycloak
    context = Path(__file__).parent.absolute()
    with DockerCompose(context=context, env_file=str(PROJECT / ".env")) as compose:
        port = compose.get_service_port(SERVICE, 21002)
        yield f"https://localhost:{port}"


# The function loop (pytest-asyncio 1.x): the root config gives async fixtures
# a module loop, which here outlives the test loops its TLS connections were
# opened on — aclose then schedules on a closed loop ("Event loop is closed").
# On the function loop, client, requests, and aclose share one loop per test.
@pytest_asyncio.fixture(loop_scope="function")
async def client(app_url: str, token: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running app over HTTPS, verifying it against the dev CA, carrying the token."""
    async with httpx.AsyncClient(
        base_url=app_url,
        verify=ssl.create_default_context(cafile=str(CA_FILE)),
        headers={"authorization": f"Bearer {token}"},
    ) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def anonymous_client(app_url: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running app over HTTPS, without a token (the 401 path)."""
    async with httpx.AsyncClient(base_url=app_url, verify=ssl.create_default_context(cafile=str(CA_FILE))) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def api(app_url: str, token: str) -> AsyncIterator[LineageModelClient]:
    """The typed lineage-model client for the running app over HTTPS (CL-30).

    The fixture builds the httpx pool (the dev CA, no auth header — the client
    adds the bearer per call, CL-03) and closes it, the owner-closes rule of
    CL-02; the minted realm token is the client's token source.
    """
    async with httpx.AsyncClient(base_url=app_url, verify=ssl.create_default_context(cafile=str(CA_FILE))) as http:
        yield LineageModelClient(http, token)
