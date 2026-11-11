"""E2E fixtures: the app image on TLS, the dev Keycloak mint, and the 12.7 catalogue chain.

Since 12.7 the stack stands a real Atlas server beside the app (the scanner's
pattern, DD-200's sibling): the app reads its governance rules from that server
with its own service identity (VEV-04), and the suite seeds the rules through
the catalogue as the dev writer. Seeding rides the writer's password-grant
token; the caller token the suite sends to ``POST /`` is the browser's, minted
for the public ``aurelius`` client (DV-75) — the two identities never mix (the
caller's token verifies at the gate and is never forwarded, VEV-04).
"""

import base64
import json
import ssl
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from pathlib import Path
from typing import Any

import dotenv
import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity
from aurelius_atlas_server_client import AtlasClient, DeleteType
from aurelius_atlas_validate_entity_client import ValidateEntityClient
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the app's, the server's and the issuer's certificates."""

SERVICE = "aurelius-atlas-validate-entity"

SERVER_URL = "https://localhost:21007"
"""The chain's Atlas server, published loopback-pinned by the e2e compose (CIA-03)."""

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the dev realm to serve tokens (a reused stack may be warming up)."""

LEG_CLIENT_ID = "aurelius-atlas-validate-entity"
"""The app's own service client (VEV-04, DD-499): the identity its catalogue leg mints as."""

GOV_RULE_TYPE = "m4i_gov_data_quality"
"""The type the rules ride (VEV-03): the governance rule type of the m4i model."""

LEG_MINT_HINT = (
    "The dev realm did not answer the app's client credentials with a usable token (VEV-04). "
    "A refusal means the running Keycloak was imported before the "
    "`aurelius-atlas-validate-entity` client entered import/master.json: a running realm is "
    "not overwritten by a re-import. A token without `atlas-read` means the service account's "
    "role grant did not import. Both are fixed the same way: `docker compose -f "
    "dev/keycloak/docker-compose.yaml down -v && docker compose -f dev/keycloak/"
    "docker-compose.yaml up -d` (the dev stack's data is disposable), or delete the master "
    "realm in the admin console and start the stack again."
)
"""What the suite raises when the realm answers the leg's mint with a refusal or a
role-less token: the running realm predates the client or its grant."""


class Settings(BaseSettings):
    """Test configuration: the identities the suite mints with, read from the project environment."""

    auth_client_id: str
    """The public realm client the caller tokens are minted for (the webapp's client, the app's audience)."""

    username: str
    """The dev user the caller/seeding tokens are minted for."""

    password: SecretStr
    """The dev user's password; never shown in logs."""

    server_client_secret: SecretStr
    """The secret of the app's own service client — the realm import's value, mirrored here."""

    model_config = SettingsConfigDict(
        # Same prefix as the application's settings: the project .env Nx injects
        # into the e2e task carries prefixed names.
        env_prefix="AURELIUS_ATLAS_VALIDATE_ENTITY_",
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
    """The dev telemetry stack, started and left running (both OTLP legs ride it)."""
    context = Path(__file__).parents[3].absolute() / "dev" / "observability"
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
    context = Path(__file__).parents[3].absolute() / "dev" / "keycloak"
    compose = DockerCompose(context=context)
    compose.start()
    return compose


@pytest.fixture(scope="session")
def elasticsearch(observability: DockerCompose) -> DockerCompose:
    """The dev Elasticsearch stack, started and left running; the server's store."""
    _ = observability  # The stack external-attaches the observability network.
    context = Path(__file__).parents[3].absolute() / "dev" / "elasticsearch"
    compose = DockerCompose(context=context)
    compose.start()
    return compose


def _token_url(keycloak: DockerCompose) -> str:
    """The dev realm's token endpoint on its TLS :8443 listener (DD-202)."""
    port = keycloak.get_service_port("keycloak", 8443)
    return f"https://keycloak.localhost:{port}/realms/master/protocol/openid-connect/token"


def _mint(url: str, body: dict[str, str], *, stale_hint_on_refusal: bool = False) -> dict[str, Any]:
    """One CA-verified mint with a warm-up retry; the token answer.

    Transport errors and 5xx retry to the deadline (a reused stack may still be booting). A
    refused client-credentials mint is never a warm-up problem once the realm answered:
    with the hint asked for, it raises the stale-realm remedy (a realm imported before the
    client entered the import file knows the client not — the scanner's precedent).
    """
    deadline = time.monotonic() + MINT_TIMEOUT_SECONDS
    last: Exception | None = None
    while True:
        refused = False
        try:
            response = httpx.post(url, data=body, verify=str(CA_FILE), timeout=10)
            refused = response.status_code in (400, 401)
            response.raise_for_status()
            return dict(response.json())
        except (httpx.HTTPError, OSError) as error:
            if refused and stale_hint_on_refusal:
                msg = LEG_MINT_HINT
                raise RuntimeError(msg) from error
            last = error
            if time.monotonic() >= deadline:
                timeout_error = TimeoutError(f"the dev realm served no token within {MINT_TIMEOUT_SECONDS}s")
                raise timeout_error from last
            time.sleep(2)


def _claims(token: str) -> dict[str, Any]:
    """The claims of a minted JWT, unverified: the suite fetched it from the issuer itself."""
    payload = token.split(".")[1]
    return dict(json.loads(base64.urlsafe_b64decode(payload + "==")))


def _leg_probe(settings: Settings, keycloak: DockerCompose) -> None:
    """Probe the app's own mint once, before the stack starts (VEV-04).

    A client the running realm does not know, or a service account whose role grant did
    not import, is the suite's own setup error: the remedy must name it (``LEG_MINT_HINT``)
    instead of surfacing as every verdict call answering 502 (VEV-06).
    """
    answer = _mint(
        _token_url(keycloak),
        {
            "grant_type": "client_credentials",
            "client_id": LEG_CLIENT_ID,
            "client_secret": settings.server_client_secret.get_secret_value(),
        },
        stale_hint_on_refusal=True,
    )
    claims = _claims(str(answer["access_token"]))
    if "atlas-read" not in str(claims.get("resource_access")):
        msg = LEG_MINT_HINT
        raise RuntimeError(msg)


@pytest.fixture(scope="session")
def stack(keycloak: DockerCompose, elasticsearch: DockerCompose, settings: Settings) -> Iterator[str]:
    """The app image and the chain's server (the e2e compose), once healthy; the app's base URL.

    ``docker compose up --wait`` returns when both images' healthchecks pass. The Keycloak,
    store and collector stacks are session dependencies, started first and left running
    (DD-223); only this stack's two containers stop at the end. The leg's mint is probed
    before the stack starts: the realm join is the setup the hint exists for.
    """
    _ = keycloak, elasticsearch
    _leg_probe(settings, keycloak)
    context = Path(__file__).parent.absolute()
    with DockerCompose(context=context, env_file=str(PROJECT / ".env")) as compose:
        port = compose.get_service_port(SERVICE, 21003)
        yield f"https://localhost:{port}"


@pytest.fixture
def token(keycloak: DockerCompose, settings: Settings) -> str:
    """A caller bearer token for the app, minted as the dev writer (the browser's identity).

    The public `aurelius` client's password grant (import/master.json): the token carries
    azp `aurelius`, the audience the app accepts — the audience of the webapp tokens the
    browser's editor sends (AUX-04, DV-75). It verifies at the gate and is never forwarded
    to the catalogue (VEV-04).

    Minted per test, not per session: the realm issues 60-second access tokens
    (`accessTokenLifespan` in import/master.json) and the suite runs longer than that, so
    one shared token expires mid-run.
    """
    return str(
        _mint(
            _token_url(keycloak),
            {
                "client_id": settings.auth_client_id,
                "grant_type": "password",
                "username": settings.username,
                "password": settings.password.get_secret_value(),
            },
        )["access_token"],
    )


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
                    "client_id": "aurelius",
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
    """The typed Atlas client as the dev writer: it seeds the governance rules and deletes them.

    The writer is the seeding identity, not the identity under test; the caller token the
    verdict calls carry is minted separately (VEV-04). The fixture builds the httpx pool
    and closes it (CL-02). It speaks to the chain's server directly on its published port
    — that is the catalogue the app reads too, in-network under its certificate name.
    """
    async with httpx.AsyncClient(base_url=SERVER_URL, verify=str(CA_FILE), timeout=30.0) as http:
        yield AtlasClient(http, UserToken(keycloak, settings))


@pytest_asyncio.fixture(loop_scope="function")
async def client(stack: str, token: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running app over HTTPS, verifying it against the dev CA, carrying the token."""
    async with httpx.AsyncClient(
        base_url=stack,
        verify=ssl.create_default_context(cafile=str(CA_FILE)),
        headers={"authorization": f"Bearer {token}"},
    ) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def anonymous_client(stack: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running app over HTTPS, without a token (the 401 path)."""
    async with httpx.AsyncClient(base_url=stack, verify=ssl.create_default_context(cafile=str(CA_FILE))) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def api(stack: str, token: str) -> AsyncIterator[ValidateEntityClient]:
    """The typed validate-entity client for the running app over HTTPS (CL-40).

    The fixture builds the httpx pool (the dev CA, no auth header — the client
    adds the bearer per call, CL-03) and closes it, the owner-closes rule of
    CL-02; the minted realm token is the client's token source.
    """
    async with httpx.AsyncClient(base_url=stack, verify=ssl.create_default_context(cafile=str(CA_FILE))) as http:
        yield ValidateEntityClient(http, token)


@pytest_asyncio.fixture(loop_scope="function")
async def seed_rules(writer: AtlasClient) -> AsyncIterator[Callable[[list[dict[str, Any]]], Awaitable[dict[str, str]]]]:
    """The governance-rule seeder, self-cleaning (DD-223: namespaced writes, deleted after).

    Answers ``{temp index: real guid}`` for the seeded records, so a test names its own
    rules in a store other suites seed in parallel (the shared dev store); every seeded
    record is hard-deleted when the test ends, leaving the webapp suite's banner pins a
    clean rule set.
    """
    seeded: list[str] = []

    async def seed_(rules: list[dict[str, Any]]) -> dict[str, str]:
        entities = [
            AtlasEntity(
                type_name=GOV_RULE_TYPE,
                guid=f"-{index}",
                attributes={"qualifiedName": rule["name"], **rule},
            )
            for index, rule in enumerate(rules)
        ]
        response = await writer.entity.create_or_update_bulk(AtlasEntitiesWithExtInfo(entities=entities))
        assigned = response.guid_assignments or {}
        seeded.extend(str(guid) for guid in assigned.values())
        return {str(index): str(assigned[f"-{index}"]) for index in range(len(rules))}

    try:
        yield seed_
    finally:
        if seeded:
            # Hard, not soft: the app's walk excludes deleted entities, but a hard delete
            # keeps the shared dev store clean for the other suites (DD-223).
            await writer.entity.delete_by_guids(seeded, delete_type=DeleteType.HARD)
