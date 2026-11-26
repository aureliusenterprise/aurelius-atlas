"""E2E fixtures: the MCP front door on TLS, the dev Keycloak mint, and the 21.3 catalogue chain.

The chain stands a real Atlas server and the real verdicts API beside the app under test
(the aux chain pattern, DD-200's sibling): every tool forwards the caller's own bearer
token to those upstreams (MCP-03), so the suite needs the whole chain live — no fake
upstream can prove the relay. Seeding rides the writer's password-grant token through
the catalogue directly; the tokens the suite presents at ``/mcp`` are the browser's own,
minted for the public ``aurelius`` client (AUX-04, DV-75) — exactly what an agent mints.

The writer's catalogue write role rides the catalogue client's ``resource_access`` entry,
never the audience entry (MCP-28, DD-898): the pre-stack probe below decodes a real
token and fails loudly, with the stale-realm remedy, when the running realm hands out
the claim shape an older import made — the one bug no unit fake could catch.
"""

import base64
import json
import ssl
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from typing import Any

import dotenv
import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity
from aurelius_atlas_server_client import AtlasClient, DeleteType
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the app's, the server's and the issuer's certificates."""

SERVICE = "aurelius-atlas-mcp"

SERVER_URL = "https://localhost:21009"
"""The chain's Atlas server, published loopback-pinned by the e2e compose (CIA-03)."""

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the dev realm to serve tokens (a reused stack may be warming up)."""

WRITE_ROLE_CLIENT = "aurelius-atlas-server"
"""The client whose ``resource_access`` entry carries the catalogue write role (MCP-28, DD-898)."""

GOV_RULE_TYPE = "m4i_gov_data_quality"
"""The type the validate_entity rule rides (MCP-12): the governance rule type of the m4i model."""

BROWSER_TOKEN_HINT = (
    "The dev realm did not give the dev writer a token with the catalogue write role under "
    f"the {WRITE_ROLE_CLIENT!r} client (MCP-27). A running Keycloak was imported before "
    "the realm file carried the writer's grants, and a running realm is not overwritten by "
    "a re-import. The remedy: `docker compose -f infra/keycloak/docker-compose.yaml "
    "down -v && docker compose -f infra/keycloak/docker-compose.yaml up -d` (the dev "
    "stack's data is disposable), or delete the master realm in the admin console and "
    "start the stack again."
)
"""What the probe raises when the realm hands out a token without the writer's grant."""


class Settings(BaseSettings):
    """Test configuration: the identities the suite mints with, read from the project environment."""

    auth_client_id: str = "aurelius"
    """The public realm client the caller tokens are minted for (the webapp's client, the app's audience)."""

    username: str = "aurelius-writer"
    """The dev user the writer tokens are minted for."""

    password: SecretStr
    """The dev user's password; never shown in logs."""

    reader_username: str = "aurelius-reader"
    """The dev user holding atlas-read only: the caller that must not write (MCP-30)."""

    reader_password: SecretStr = SecretStr("bzMCZRmdyOBOA3xHvaOu7Q")  # the public dev default, not a secret
    """The reader's password, the realm import's public dev default."""

    model_config = SettingsConfigDict(
        # Same prefix as the application's settings: the project .env Nx injects
        # into the e2e task carries prefixed names.
        env_prefix="AURELIUS_ATLAS_MCP_",
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
def observability() -> DockerCompose:
    """The dev telemetry stack, started and left running (the chain's two exporters ride it)."""
    context = Path(__file__).parents[3].absolute() / "infra" / "observability"
    compose = DockerCompose(context=context)
    compose.start()
    return compose


@pytest.fixture(scope="session")
def keycloak(observability: DockerCompose) -> DockerCompose:
    """The dev Keycloak, started and left running; the issuer both identities mint at.

    Readiness is compose's own: start() runs ``up --wait`` and the service carries a
    healthcheck, and the realm import is done before the listener serves. Like the other
    suites, this fixture leaves the stack running for reuse (DD-223).
    """
    _ = observability  # The stack external-attaches the observability network.
    context = Path(__file__).parents[3].absolute() / "infra" / "keycloak"
    compose = DockerCompose(context=context)
    compose.start()
    return compose


@pytest.fixture(scope="session")
def elasticsearch(observability: DockerCompose) -> DockerCompose:
    """The dev Elasticsearch stack, started and left running; the server's store."""
    _ = observability  # The stack external-attaches the observability network.
    context = Path(__file__).parents[3].absolute() / "infra" / "elasticsearch"
    compose = DockerCompose(context=context)
    compose.start()
    return compose


def _token_url(keycloak: DockerCompose) -> str:
    """The dev realm's token endpoint on its TLS :8443 listener (DD-202)."""
    port = keycloak.get_service_port("keycloak", 8443)
    return f"https://keycloak.localhost:{port}/realms/master/protocol/openid-connect/token"


def _mint(url: str, body: dict[str, str]) -> dict[str, Any]:
    """One CA-verified mint with a warm-up retry; the token answer.

    Transport errors and 5xx retry to the deadline (a reused stack may still be booting).
    A password-grant refusal is retried too: unlike the aux suites' client-credentials
    probe, a wrong here is a realm whose users did not import, and the probe below names
    that remedy once the realm answers at all (MCP-27).
    """
    deadline = time.monotonic() + MINT_TIMEOUT_SECONDS
    last: Exception | None = None
    while True:
        try:
            response = httpx.post(url, data=body, verify=str(CA_FILE), timeout=10)
            response.raise_for_status()
            return dict(response.json())
        except (httpx.HTTPError, OSError) as error:
            last = error
            if time.monotonic() >= deadline:
                timeout_error = TimeoutError(f"the dev realm served no token within {MINT_TIMEOUT_SECONDS}s")
                raise timeout_error from last
            time.sleep(2)


def _claims(token: str) -> dict[str, Any]:
    """The claims of a minted JWT, unverified: the suite fetched it from the issuer itself."""
    payload = token.split(".")[1]
    return dict(json.loads(base64.urlsafe_b64decode(payload + "==")))


def _password_grant(settings: Settings, keycloak: DockerCompose, username: str, password: str) -> str:
    """One browser-style access token: the public client's password grant (AUX-04)."""
    answer = _mint(
        _token_url(keycloak),
        {
            "client_id": settings.auth_client_id,
            "grant_type": "password",
            "username": username,
            "password": password,
        },
    )
    return str(answer["access_token"])


def _writer_grant(settings: Settings, keycloak: DockerCompose) -> str:
    """A fresh access token as the dev writer, presented at /mcp."""
    return _password_grant(settings, keycloak, settings.username, settings.password.get_secret_value())


def _reader_grant(settings: Settings, keycloak: DockerCompose) -> str:
    """A fresh access token as the reader that must be refused by the write gate (MCP-30)."""
    return _password_grant(settings, keycloak, settings.reader_username, settings.reader_password.get_secret_value())


@pytest.fixture(scope="session")
def _token_probe(keycloak: DockerCompose, settings: Settings) -> None:
    """Probe the realm's claim shape once, before the stack starts (MCP-27, DD-898).

    The whole increment's bug is a claim the unit fakes baked wrong: the catalogue write
    role rides the catalogue client's ``resource_access`` entry, not the audience's
    (MCP-28). If the running realm hands the writer a token without it, every write tool
    would refuse for a setup reason — the probe fails here, with the remedy, instead.
    """
    claims = _claims(_writer_grant(settings, keycloak))
    entry = claims.get("resource_access", {}).get(WRITE_ROLE_CLIENT, {})
    if "atlas-write" not in entry.get("roles", []):
        msg = BROWSER_TOKEN_HINT
        raise RuntimeError(msg)


@pytest.fixture(scope="session")
def stack(
    keycloak: DockerCompose, elasticsearch: DockerCompose, _token_probe: None, settings: Settings
) -> Iterator[str]:
    """The app image and its chain (the e2e compose), once healthy; the app's base URL.

    ``docker compose up --wait`` returns when the images' healthchecks pass: the server
    and the verdicts API before the app (their gates in the stack file). The Keycloak,
    store and collector stacks are session dependencies, started first and left running
    (DD-223); only this stack's containers stop at the end.
    """
    _ = keycloak, elasticsearch, settings
    context = Path(__file__).parent.absolute()
    with DockerCompose(context=context, env_file=str(PROJECT / ".env")) as compose:
        port = compose.get_service_port(SERVICE, 21005)
        yield f"https://localhost:{port}"


class UserToken:
    """The dev writer's access tokens, minted by the public client's password grant.

    Callable as the server client's token source (CL-03). Minted fresh ahead of expiry:
    the dev realm's tokens live 60 seconds and the session's seeding outlives one.
    """

    def __init__(self, keycloak: DockerCompose, settings: Settings) -> None:
        self._url = _token_url(keycloak)
        self._settings = settings
        self._token = ""
        self._expires = 0.0

    def __call__(self) -> str:
        """A token with margin before its expiry."""
        if time.monotonic() > self._expires - 15:
            answer = _mint(
                self._url,
                {
                    "grant_type": "password",
                    "client_id": self._settings.auth_client_id,
                    "username": self._settings.username,
                    "password": self._settings.password.get_secret_value(),
                },
            )
            self._token = str(answer["access_token"])
            self._expires = time.monotonic() + float(answer["expires_in"])
        return self._token


# The function loop (pytest-asyncio 1.x): the root config gives async fixtures a module
# loop, which here outlives the test loops their TLS connections were opened on — aclose
# then schedules on a closed loop ("Event loop is closed"). On the function loop, client,
# requests, and aclose share one loop per test.
@pytest_asyncio.fixture(loop_scope="function")
async def writer(keycloak: DockerCompose, settings: Settings) -> AsyncIterator[AtlasClient]:
    """The typed Atlas client as the dev writer: it seeds the catalogue and cleans up.

    The writer is the seeding identity, not the identity under test; the tokens the tools
    forward are minted per test (MCP-03). The fixture builds the httpx pool and closes it
    (CL-02). It speaks to the chain's server directly on its published port — that is the
    catalogue the tools relay to too, in-network under its certificate name.
    """
    async with httpx.AsyncClient(base_url=SERVER_URL, verify=str(CA_FILE), timeout=30.0) as http:
        yield AtlasClient(http, UserToken(keycloak, settings))


@pytest.fixture
def token(keycloak: DockerCompose, settings: Settings) -> str:
    """A writer bearer for /mcp, minted as the browser mints (the public client, MCP-02).

    Minted per test, not per session: the realm issues 60-second access tokens
    (`accessTokenLifespan` in import/master.json) and the suite runs longer than that, so
    one shared token expires mid-run.
    """
    return _writer_grant(settings, keycloak)


@pytest.fixture
def reader_token(keycloak: DockerCompose, settings: Settings) -> str:
    """A reader bearer for /mcp: atlas-read only, so the write gate must refuse it (MCP-30)."""
    return _reader_grant(settings, keycloak)


# The function loop, as for `writer`: the MCP session's streams and the test share one loop.
@pytest_asyncio.fixture(loop_scope="function")
async def mcp_session(stack: str) -> Callable[[str], AbstractAsyncContextManager[ClientSession]]:
    """Build one MCP client session against the running app, presenting the bearer given to it.

    A factory, not a fixture, because a test's identity is the token it presents: one
    app, many callers (MCP-02, MCP-29/30). The httpx pool verifies the app against the
    dev CA and carries the bearer into the streamable-HTTP transport's every request.
    """

    @asynccontextmanager
    async def _open(bearer: str) -> AsyncIterator[ClientSession]:
        headers = {"authorization": f"Bearer {bearer}"}
        http_client = httpx.AsyncClient(base_url=stack, verify=str(CA_FILE), headers=headers, timeout=30.0)
        async with (
            http_client,
            streamable_http_client(f"{stack}/mcp", http_client=http_client) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            yield session

    return _open


@pytest_asyncio.fixture(loop_scope="function")
async def seed_entities(
    writer: AtlasClient,
) -> AsyncIterator[Callable[[list[AtlasEntity]], Awaitable[dict[str, str]]]]:
    """The entity seeder, self-cleaning (DD-223: namespaced writes, hard-deleted after).

    Answers ``{temp index: real guid}`` for the seeded records, so a test names its own
    entities in a store other suites seed in parallel (the shared dev store); every
    seeded record is hard-deleted when the test ends.
    """
    seeded: list[str] = []

    async def seed_(entities: list[AtlasEntity]) -> dict[str, str]:
        response = await writer.entity.create_or_update_bulk(AtlasEntitiesWithExtInfo(entities=entities))
        assigned = response.guid_assignments or {}
        seeded.extend(str(guid) for guid in assigned.values())
        return {str(index): str(assigned[f"-{index}"]) for index in range(len(entities))}

    try:
        yield seed_
    finally:
        if seeded:
            # Hard, not soft: the tools' reads exclude deleted entities, but a hard
            # delete keeps the shared dev store clean for the other suites (DD-223).
            await writer.entity.delete_by_guids(seeded, delete_type=DeleteType.HARD)


@pytest_asyncio.fixture(loop_scope="function")
async def anonymous_client(stack: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running app over HTTPS, without a token (the 401 path, MCP-32)."""
    async with httpx.AsyncClient(base_url=stack, verify=ssl.create_default_context(cafile=str(CA_FILE))) as client:
        yield client
