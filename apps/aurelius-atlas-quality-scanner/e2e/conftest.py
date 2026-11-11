"""E2E fixtures: the real server on the dev store, and the scanner's own identity (DQS-10).

The suite drives the scanner in-process — the job is a batch CLI, not a service — against a
stack whose only service is the Atlas server, on the dev store and the dev issuer. Seeding
rides the webapp suite's writer (the public client's password grant); every scan speaks as
the scanner's own service identity, minted by client credentials (DD-458).
"""

import asyncio
import base64
import json
import secrets
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import dotenv
import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity
from aurelius_atlas_quality_scanner.__main__ import build_client
from aurelius_atlas_quality_scanner.settings import ENV_PREFIX, ScannerSettings
from aurelius_atlas_server_client import AtlasClient, DeleteType
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from testcontainers.compose import DockerCompose

if TYPE_CHECKING:
    from pydantic import HttpUrl

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the server's and the issuer's certificates."""

SERVER_HOST_PORT = 21005
"""The host port the e2e compose publishes the server on, loopback-pinned (CIA-03)."""

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the dev realm to serve tokens (a reused stack may be warming up)."""

SCANNER_CLIENT_ID = "aurelius-atlas-quality-scanner"
"""The service client the job signs in as (DD-458)."""

SCORE_TYPE = "m4i_dq_score"
"""The type the scores are stored as (DD-455): what the scenarios read back."""

SCANNER_MINT_HINT = (
    "The dev realm did not answer the scanner's client credentials with a usable token "
    "(DD-458). A refusal means the running Keycloak was imported before the "
    "`aurelius-atlas-quality-scanner` client entered import/master.json: a running realm is "
    "not overwritten by a re-import. A token without `atlas-write` means the service "
    "account's role grant did not import. Both are fixed the same way: `docker compose -f "
    "dev/keycloak/docker-compose.yaml down -v && docker compose -f dev/keycloak/"
    "docker-compose.yaml up -d` (the dev stack's data is disposable), or delete the master "
    "realm in the admin console and start the stack again."
)
"""What the suite raises when the realm answers the scanner's mint with a refusal or a
role-less token: the running realm predates the client or its grant."""


class Settings(BaseSettings):
    """Test configuration: the identities the suite mints with, read from the project environment."""

    password: SecretStr
    """The dev writer's password; the seeding grant's credential."""

    username: str = "aurelius-writer"
    """The dev realm user the seeding tokens are minted for."""

    client_secret: SecretStr
    """The secret of the scanner's own service client — the realm import's value."""

    model_config = SettingsConfigDict(
        # Same prefix as the application's settings: the project .env Nx injects into the
        # e2e task carries prefixed names.
        env_prefix=ENV_PREFIX,
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
    """The dev telemetry stack, started and left running (the server's OTLP leg rides it)."""
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
    client entered the import file knows the client not).
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
                msg = SCANNER_MINT_HINT
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


def _scanner_claims(settings: Settings, keycloak: DockerCompose) -> dict[str, Any]:
    """Mint as the scanner's own service client (client credentials) and answer its claims.

    The client authenticates by its HTTP Basic credential — the client-credentials grant of
    a confidential client (DD-458). Every scenario's audit name is the ``sub`` answered here:
    a service account carries no ``preferred_username`` beyond the realm's own naming.
    """
    answer = _mint(
        _token_url(keycloak),
        {
            "grant_type": "client_credentials",
            "client_id": SCANNER_CLIENT_ID,
            "client_secret": settings.client_secret.get_secret_value(),
        },
        stale_hint_on_refusal=True,
    )
    claims = _claims(str(answer["access_token"]))
    if "atlas-write" not in str(claims.get("resource_access")):
        msg = SCANNER_MINT_HINT
        raise RuntimeError(msg)
    return claims


@pytest.fixture(scope="session")
def server(keycloak: DockerCompose, elasticsearch: DockerCompose) -> Iterator[str]:
    """The e2e Atlas server on the dev store, once healthy; its base URL.

    ``docker compose up --wait`` returns when the image's own healthcheck passes (liveness
    over TLS). The stack rides the dev store and issuer, started first by the fixtures and
    left running (DD-223); only this stack's server stops at the end.
    """
    _ = keycloak, elasticsearch
    context = Path(__file__).parent.absolute()
    with DockerCompose(context=context, env_file=str(PROJECT / ".env")):
        yield f"https://localhost:{SERVER_HOST_PORT}"


@pytest.fixture(scope="session")
def scanner_settings(server: str, settings: Settings, keycloak: DockerCompose) -> ScannerSettings:
    """The scan's settings: this stack's server, the scanner's own identity, a small page.

    The realm is probed once, before any scan: a client the running realm does not know is
    the suite's own setup error, and the remedy must name it (``SCANNER_MINT_HINT``) instead
    of surfacing as a scan-time refusal. The source list rides per test — extracts are
    written to a temp dir — through ``model_copy``.
    """
    _scanner_claims(settings, keycloak)
    return ScannerSettings(
        server_url=cast("HttpUrl", server),  # pydantic validates the URL text at init
        client_secret=settings.client_secret,
        ca_file=str(CA_FILE),
        search_limit=2,
    )


@pytest.fixture
def scanner_claims(settings: Settings, keycloak: DockerCompose) -> dict[str, Any]:
    """Fresh claims of a scanner token, minted inside the test's session (DQS-10).

    The audit principal of a client-credentials token is its ``sub`` (AUT-03's fallback: a
    service account has no human ``preferred_username``); scenarios name the writes' user by
    the ``sub`` answered here.
    """
    return _scanner_claims(settings, keycloak)


class UserToken:
    """The dev writer's access tokens, minted by the public client's password grant.

    Callable as the server client's token source (CL-03). Minted fresh ahead of expiry: the
    dev realm's tokens live 60 seconds and the session's seeding outlives one.
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


@pytest.fixture(scope="session")
def user_token(keycloak: DockerCompose, settings: Settings) -> UserToken:
    """The writer's token source, shared by the suite."""
    return UserToken(keycloak, settings)


# The function loop (pytest-asyncio 1.x): the root config gives async fixtures a module
# loop, which outlives the test loops their TLS connections were opened on. On the function
# loop, the clients, their requests, and their aclose share one loop per test — the same
# reasoning as the aux apps' e2e conftests.
@pytest_asyncio.fixture(loop_scope="function")
async def writer(server: str, user_token: UserToken) -> AsyncIterator[AtlasClient]:
    """The typed Atlas client as the dev writer: it seeds the graphs and deletes them (DQS-03).

    The writer is the seeding identity, not the identity under test; the scans speak through
    ``scanner`` instead. The fixture builds the httpx pool and closes it (CL-02).
    """
    async with httpx.AsyncClient(base_url=server, verify=str(CA_FILE), timeout=30.0) as http:
        yield AtlasClient(http, user_token)


@pytest_asyncio.fixture(loop_scope="function")
async def scanner(scanner_settings: ScannerSettings) -> AsyncIterator[AtlasClient]:
    """The catalogue client the scan speaks as: the scanner's own service identity (DQS-10).

    Built by the app's own ``build_client`` — the same door the CLI opens, so the suite
    proves the job's identity end to end: client credentials, accepted audiences, and the
    token refreshed ahead of expiry across the scan's calls.
    """
    client, http = build_client(scanner_settings)
    try:
        yield client
    finally:
        await http.aclose()


@pytest.fixture
def run_token() -> str:
    """One run token: the single ``zz<run>`` word every seeded name carries."""
    return secrets.token_hex(4)


@pytest.fixture
def seed(writer: AtlasClient) -> Callable[[str, dict[str, Any]], Awaitable[dict[str, str]]]:
    """The m4i mini-graph seeder: one bulk create of dataset, field, and rule (REL-11).

    The ends ride ``relationshipAttributes`` naming the request's own temp guids, which the
    server resolves through the request's guid assignments — the webapp suite's idiom. The
    rule's mandatory ``id`` is the run's hex. Answers ``{dataset, field, rule}: guid``.
    """

    async def seed_(run: str, rule_attributes: dict[str, Any]) -> dict[str, str]:
        names = {"dataset": f"zz{run}warehouse", "field": f"zz{run}field", "rule": f"zz{run}rule"}
        dataset = AtlasEntity(
            type_name="m4i_dataset",
            guid="-0",
            attributes={"qualifiedName": names["dataset"], "name": names["dataset"]},
            relationship_attributes={"fields": [{"guid": "-1", "typeName": "m4i_field"}]},
        )
        field = AtlasEntity(
            type_name="m4i_field",
            guid="-1",
            attributes={"qualifiedName": names["field"], "name": names["field"]},
        )
        rule = AtlasEntity(
            type_name="m4i_data_quality",
            guid="-2",
            attributes={
                "qualifiedName": names["rule"],
                "name": names["rule"],
                "id": int(run[:6], 16),
                # The type's boolean default is false; the scan skips a rule stored inactive (DQS-02).
                "active": True,
                **rule_attributes,
            },
            relationship_attributes={"fields": [{"guid": "-1", "typeName": "m4i_field"}]},
        )
        response = await writer.entity.create_or_update_bulk(AtlasEntitiesWithExtInfo(entities=[dataset, field, rule]))
        assigned = response.guid_assignments or {}
        temps = {"dataset": "-0", "field": "-1", "rule": "-2"}
        return {key: str(assigned[temp]) for key, temp in temps.items()}

    return seed_


@pytest.fixture
def wait_for_rule(writer: AtlasClient) -> Callable[[str, str], Awaitable[None]]:
    """Wait until the field's ``dataQuality`` end names the rule (the edge-search race).

    A relationship lands as a near-real-time record the reads search, so a scan started the
    instant the create answered can bind nothing; the scenarios wait the edge first (the
    webapp suite's seed idiom).
    """

    async def wait_(field_guid: str, rule_guid: str) -> None:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            found = await writer.entity.by_guids([field_guid], min_ext_info=True)
            entity = (found.entities or [None])[0]
            ends = (entity.relationship_attributes or {}).get("dataQuality") if entity else None
            if any(str(end.get("guid")) == rule_guid for end in ends or []):
                return
            await asyncio.sleep(1)
        msg = f"the field {field_guid} never gained the rule edge {rule_guid}"
        raise TimeoutError(msg)

    return wait_


@pytest_asyncio.fixture(loop_scope="function")
async def cleanup(writer: AtlasClient) -> AsyncIterator[Seeded]:
    """What a test seeded on the store; hard-deleted at its end (never left, never restarted).

    ``graphs`` carries entity GUIDs, ``scores`` the score keys (unique attributes of
    ``m4i_dq_score``). The names are zz-token-namespaced and self-cleaned, so the shared dev
    store keeps nothing between tests (DD-223).
    """
    seeded = Seeded()
    yield seeded
    if seeded.graphs:
        await writer.entity.delete_by_guids(list(seeded.graphs), delete_type=DeleteType.HARD)
    for key in seeded.score_keys:
        await writer.entity.delete_by_unique_attributes(SCORE_TYPE, {"scoreKey": key}, delete_type=DeleteType.HARD)


class Seeded:
    """What one test seeded: entity GUIDs and score keys, for the cleanup fixture's teardown."""

    def __init__(self) -> None:
        self.graphs: list[str] = []
        """The GUIDs of the seeded m4i entities."""

        self.score_keys: list[str] = []
        """The ``scoreKey`` values of the score entities the scan stored."""

    def graph(self, *guids: str) -> None:
        """Record seeded entity GUIDs."""
        self.graphs.extend(guids)

    def scores(self, *keys: str) -> None:
        """Record stored score keys."""
        self.score_keys.extend(keys)
