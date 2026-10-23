"""E2E fixtures: the app image on TLS, the dev Keycloak mint, and clients."""

import ssl
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import dotenv
import httpx
import pytest
import pytest_asyncio
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the app's and the issuer's certificates."""

SERVICE = "aurelius-atlas-data2model"

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the dev realm to serve tokens (a reused stack may be warming up)."""


class Settings(BaseSettings):
    """Test configuration: the dev realm identity the e2e token mint signs in as."""

    auth_client_id: str
    """The public realm client the tokens are minted for (the webapp's client, the app's audience)."""

    username: str
    password: SecretStr

    model_config = SettingsConfigDict(
        # Same prefix as the application's settings: the project .env Nx injects
        # into the e2e task carries prefixed names.
        env_prefix="AURELIUS_ATLAS_DATA2MODEL_",
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

    The issuer serves TLS on the published :8443 listener; the app verifies
    bearer tokens against it (DTM-10), and the suite mints its tokens there.
    Like the other suites, this fixture starts the stack and does not stop it:
    a running dev stack is reused across sessions.
    """
    context = Path(__file__).parents[3].absolute() / "dev" / "keycloak"
    compose = DockerCompose(context=context)
    compose.start()
    return compose


@pytest.fixture(scope="session")
def token(keycloak: DockerCompose, settings: Settings) -> str:
    """A bearer token for the app, minted from the dev realm as the dev writer.

    The public `aurelius` client's password grant (import/master.json): the
    token carries azp `aurelius`, the audience the app accepts — the audience
    of the webapp tokens the lineage chain forwards (AUX-04).
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
    """The app image on the dev issuer (started by the e2e target), once healthy; yields its base URL.

    ``docker compose up --wait`` returns when the image's healthcheck passes.
    The Keycloak stack is a session dependency: the app's /extract verifies
    tokens against it, and the OTLP mint starts at the same issuer.
    """
    _ = keycloak
    context = Path(__file__).parent.absolute()
    with DockerCompose(context=context, env_file=str(PROJECT / ".env")) as compose:
        port = compose.get_service_port(SERVICE, 21001)
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
