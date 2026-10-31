"""E2E fixtures: the app on TLS, the Keycloak mint, and clients — per lane (10.5b, DD-282).

Compose (the default, CI's lane): the app image on the dev stack, the dev
realm's mint. Cluster (``ATLAS_E2E_TARGET=cluster``): the app dialled at its
Service's real name through a port-forward (SAN-honest TLS, CHT-104), the
token minted through ``keycloak.atlas.test`` — the same issuer origin the
deployed pods verify against (DD-265) — with the writer password read from the
release's ``atlas-keycloak-users`` Secret. The lane machinery is
aurelius-atlas-cluster-lane's; this conftest names only what is the suite's:
the app Service, the mint identity, the clients.

The suite's tests are data-independent (extract-from-body), so the cluster
lane needs no seeding.
"""

import ssl
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import dotenv
import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_cluster_lane import (
    SecretReader,
    ServiceForward,
    install_cluster_fixtures,
    lane_target,
    mint_token,
)
from aurelius_atlas_data2model_client import Data2ModelClient
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]

SERVICE = "aurelius-atlas-data2model"

# The cluster shapes (the umbrella install of tools/cluster/install.sh).
SERVICE_CLUSTER = "atlas-data2model"
"""The aux chart's Service (the umbrella's release name + chart name)."""
SERVICE_PORT = 21001
"""The Service's real port — what the shim rewrites alongside the name (CHT-104)."""
ISSUER_HOST = "keycloak.atlas.test"
"""The edge-routed issuer: CoreDNS rewrites it in-cluster (DD-265), the lane's
resolver maps it here — the pods' own issuer origin, so the mint stays honest."""
KEYCLOAK_USERS_SECRET = "atlas-keycloak-users"
"""The release Secret carrying the smoke users' passwords (CHT-78)."""
CLUSTER_NAMESPACE = "atlas"

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the realm to serve tokens (a warming stack may be starting up)."""

# The session `cluster` gate, the autouse resolver shim, and `ca_file` come
# from the lane library (CHT-103); compose mode never touches kubectl.
install_cluster_fixtures(sys.modules[__name__], PROJECT / "certs")


class Settings(BaseSettings):
    """Test configuration: the dev realm identity the compose-lane mint signs in as."""

    auth_client_id: str
    """The public realm client the tokens are minted for (the webapp's client, the app's audience)."""

    username: str
    """The dev user the tokens are minted for."""

    password: SecretStr
    """The dev user's password; never shown in logs."""

    model_config = SettingsConfigDict(
        # Same prefix as the application's settings: the project .env Nx injects
        # into the e2e task carries prefixed names.
        env_prefix="AURELIUS_ATLAS_DATA2MODEL_",
        env_file=dotenv.find_dotenv(),
        extra="ignore",
    )


@pytest.fixture(scope="session")
def settings() -> Settings:
    """The test configuration, read from the injected project environment (compose lane)."""
    return Settings()  # pyright: ignore[reportCallIssue] - values load from the environment


@pytest.fixture(scope="session", autouse=True)
def _environment() -> None:
    """Load the project's decrypted settings, which the compose file reads (no-op when absent)."""
    dotenv.load_dotenv(PROJECT / ".env")


@pytest.fixture(scope="session")
def keycloak() -> DockerCompose | None:
    """The dev Keycloak, started and healthy (compose lane; the e2e target starts it, idempotent).

    The issuer serves TLS on the published :8443 listener; the app verifies
    bearer tokens against it (DTM-10), and the suite mints its tokens there.
    Like the other suites, this fixture starts the stack and does not stop it:
    a running dev stack is reused across sessions. The cluster lane has no
    stack to start — the release's own Keycloak answers at ISSUER_HOST.
    """
    if lane_target() == "cluster":
        return None
    context = Path(__file__).parents[3].absolute() / "dev" / "keycloak"
    compose = DockerCompose(context=context)
    compose.start()
    return compose


@pytest.fixture(scope="session")
def token(request: pytest.FixtureRequest, ca_file: str) -> str:
    """A bearer token for the app, minted from the realm as the writer (the `aurelius` client).

    One mint, two origins (CHT-104): the compose lane mints at the dev realm's
    published :8443 with the .env password; the cluster lane mints at
    ``https://keycloak.atlas.test`` — the same origin the deployed pods
    verify against — with the password read from the release's
    ``atlas-keycloak-users`` Secret. Both tokens carry azp `aurelius`, the
    audience the app accepts (AUX-04); the minikube overlay's audience
    override (CHT-105) is what answers it on the cluster.
    """
    if lane_target() == "cluster":
        password = SecretReader(CLUSTER_NAMESPACE).read(KEYCLOAK_USERS_SECRET, "writer-password")
        return mint_token(
            f"https://{ISSUER_HOST}",
            password,
            ca_file=ca_file,
            timeout=MINT_TIMEOUT_SECONDS,
        )
    keycloak = request.getfixturevalue("keycloak")
    settings = request.getfixturevalue("settings")
    assert keycloak is not None  # the compose lane: the dev stack is up (the e2e target guarantees it)
    port = keycloak.get_service_port("keycloak", 8443)
    return mint_token(
        f"https://keycloak.localhost:{port}",
        settings.password.get_secret_value(),
        client_id=settings.auth_client_id,
        username=settings.username,
        ca_file=ca_file,
        timeout=MINT_TIMEOUT_SECONDS,
    )


@pytest.fixture(scope="session")
def app_url(request: pytest.FixtureRequest, _cluster_dns: None, ca_file: str) -> Iterator[str]:
    """The app's base URL on the lane ATLAS_E2E_TARGET picked, once healthy.

    Compose (default): the app image on the dev issuer (started by the e2e
    target); ``docker compose up --wait`` returns when the image's healthcheck
    passes, and the Keycloak stack is a session dependency — the app's
    /extract verifies tokens against it. Cluster: the Service's own name at
    its real port through a port-forward, so the URL, SNI, and verified SAN
    stay honest (CHT-104).
    """
    if lane_target() == "cluster":
        with ServiceForward(
            SERVICE_CLUSTER,
            SERVICE_PORT,
            f"{SERVICE_CLUSTER}.atlas.svc.cluster.local",
            namespace=CLUSTER_NAMESPACE,
            probe_path="/liveness",
            ca_file=ca_file,
        ) as forward:
            yield forward.url
        return
    keycloak = request.getfixturevalue("keycloak")
    _ = keycloak
    context = Path(__file__).parent.absolute()
    with DockerCompose(context=context, env_file=str(PROJECT / ".env")) as compose:
        port = compose.get_service_port(SERVICE, SERVICE_PORT)
        yield f"https://localhost:{port}"


# The function loop (pytest-asyncio 1.x): the root config gives async fixtures
# a module loop, which here outlives the test loops its TLS connections were
# opened on — aclose then schedules on a closed loop ("Event loop is closed").
# On the function loop, client, requests, and aclose share one loop per test.
@pytest_asyncio.fixture(loop_scope="function")
async def client(app_url: str, token: str, ca_file: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running app over HTTPS, verifying it against the lane's CA, carrying the token."""
    async with httpx.AsyncClient(
        base_url=app_url,
        verify=ssl.create_default_context(cafile=ca_file),
        headers={"authorization": f"Bearer {token}"},
    ) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def anonymous_client(app_url: str, ca_file: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running app over HTTPS, without a token (the 401 path)."""
    async with httpx.AsyncClient(base_url=app_url, verify=ssl.create_default_context(cafile=ca_file)) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def api(app_url: str, token: str, ca_file: str) -> AsyncIterator[Data2ModelClient]:
    """The typed data2model client for the running app over HTTPS (CL-21).

    The fixture builds the httpx pool (the lane's CA, no auth header — the
    client adds the bearer per call, CL-03) and closes it, the owner-closes
    rule of CL-02; the minted realm token is the client's token source.
    """
    async with httpx.AsyncClient(base_url=app_url, verify=ssl.create_default_context(cafile=ca_file)) as http:
        yield Data2ModelClient(http, token)
