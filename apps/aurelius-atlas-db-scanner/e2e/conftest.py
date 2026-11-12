"""E2E fixtures: the real server, the suite's own Postgres, and the scanner's own identity (DBS-02, DBS-10).

The suite drives the scanner in-process — the job is a batch CLI, not a service — against a
stack whose services are the Atlas server and one disposable Postgres (DD-507): the suite
seeds the database over its published port and discards it with the stack, so no shared store
is ever written to or restarted (DD-223). Seeding and cleanup of the catalogue ride the
webapp suite's writer (the public client's password grant); every scan speaks as the
scanner's own service identity, minted by client credentials (DD-458's pattern). Every schema
the suite seeds carries the run's ``zz<run>`` prefix and is dropped at the end.
"""

import base64
import json
import secrets
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import dotenv
import httpx2 as httpx
import psycopg
import pytest
import pytest_asyncio
from aurelius_atlas_db_scanner.__main__ import build_client
from aurelius_atlas_db_scanner.settings import ENV_PREFIX, ScannerSettings
from aurelius_atlas_server_client import AtlasClient, DeleteType
from psycopg import sql
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from testcontainers.compose import DockerCompose

if TYPE_CHECKING:
    from typing import LiteralString

    from pydantic import HttpUrl

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the server's and the issuer's certificates."""

SERVER_HOST_PORT = 21007
"""The host port the e2e compose publishes the server on, loopback-pinned (CIA-03)."""

POSTGRES_HOST_PORT = 25432
"""The host port the e2e compose publishes the suite's Postgres on, loopback-pinned."""

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the dev realm to serve tokens (a reused stack may be warming up)."""

SCANNER_CLIENT_ID = "aurelius-atlas-db-scanner"
"""The service client the job signs in as (DD-458's pattern, DBS-10)."""

SCANNER_MINT_HINT = (
    "The dev realm did not answer the scanner's client credentials with a usable token. "
    "A refusal means the running Keycloak was imported before the "
    "`aurelius-atlas-db-scanner` client entered import/master.json: a running realm is "
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

    postgres_password: SecretStr
    """The password of the suite's Postgres (DD-507): the compose service's and the DSN's, one value."""

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
    context = WORKSPACE_ROOT / "dev" / "observability"
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
    context = WORKSPACE_ROOT / "dev" / "keycloak"
    compose = DockerCompose(context=context)
    compose.start()
    return compose


@pytest.fixture(scope="session")
def elasticsearch(observability: DockerCompose) -> DockerCompose:
    """The dev Elasticsearch stack, started and left running; the server's store."""
    _ = observability  # The stack external-attaches the observability network.
    context = WORKSPACE_ROOT / "dev" / "elasticsearch"
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
    a confidential client (DD-458's pattern). Every scenario's audit name is the ``sub``
    answered here: a service account carries no ``preferred_username`` beyond the realm's own naming.
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

    ``docker compose up --wait`` returns when both services' healthchecks pass: the server's
    image healthcheck (liveness over TLS) and the suite's Postgres. The stack rides the dev
    store and issuer, started first by the fixtures and left running (DD-223); only this
    stack's server and its disposable database stop at the end.
    """
    _ = keycloak, elasticsearch
    context = Path(__file__).parent.absolute()
    with DockerCompose(context=context, env_file=str(PROJECT / ".env")):
        yield f"https://localhost:{SERVER_HOST_PORT}"


def _dsn(settings: Settings) -> str:
    """The scan DSN for the suite's Postgres: the host-published port, the real driver path."""
    return f"postgresql+psycopg://atlas:{settings.postgres_password.get_secret_value()}@127.0.0.1:{POSTGRES_HOST_PORT}/scan"


def _seed_dsn(settings: Settings) -> str:
    """The seeding DSN: the same database over psycopg's plain driver, no SQLAlchemy dialect."""
    return f"postgresql://atlas:{settings.postgres_password.get_secret_value()}@127.0.0.1:{POSTGRES_HOST_PORT}/scan"


@pytest.fixture(scope="session")
def scanner_settings(server: str, settings: Settings, keycloak: DockerCompose) -> ScannerSettings:
    """The scan's settings: this stack's server and database, and the scanner's identity.

    The realm is probed once, before any scan: a client the running realm does not know is
    the suite's own setup error, and the remedy must name it (``SCANNER_MINT_HINT``) instead
    of surfacing as a scan-time refusal. The system name, DSN and schema pattern ride per test
    — each scenario namespaces them to its run — through ``model_copy``.
    """
    _scanner_claims(settings, keycloak)
    return ScannerSettings(
        server_url=cast("HttpUrl", server),
        dsn=SecretStr(_dsn(settings)),
        system_name="E2E Database",
        client_secret=settings.client_secret,
        ca_file=str(CA_FILE),
    )


@pytest.fixture
def seeded_database(server: str, settings: Settings, run_token: str) -> Iterator[dict[str, str]]:
    """The run's schemas and tables on the suite's Postgres; dropped when the test ends.

    Two run-namespaced schemas, seeded with psycopg straight over the published port:
    ``<run>a`` holds ``orders`` (a commented table, a commented column) and ``line``
    (a simple foreign key into ``orders`` and a composite one into ``shops``), plus
    ``empty`` (no columns at all); ``<run>b`` holds ``shops`` (a composite primary key) and
    ``employee`` (a self-referencing key). Every name carries the run token, and the schemas
    drop with their contents (CASCADE) when the test ends — the disposable database keeps
    nothing between tests (DD-507).
    """
    _ = server  # The stack must answer before any seed statement runs.
    schema_a, schema_b = f"zz{run_token}a", f"zz{run_token}b"
    statements = [
        f"CREATE SCHEMA {schema_a}",
        f"CREATE SCHEMA {schema_b}",
        f"CREATE TABLE {schema_a}.orders (id integer PRIMARY KEY, shop_name text)",
        f"COMMENT ON TABLE {schema_a}.orders IS 'One row per customer order'",
        f"COMMENT ON COLUMN {schema_a}.orders.shop_name IS 'Where the order was placed'",
        f"CREATE TABLE {schema_b}.shops (code text, region text, PRIMARY KEY (code, region))",
        (
            f"CREATE TABLE {schema_a}.line ("
            f"  id integer PRIMARY KEY,"
            f"  order_id integer REFERENCES {schema_a}.orders (id),"
            f"  shop_code text,"
            f"  shop_region text,"
            f"  FOREIGN KEY (shop_code, shop_region) REFERENCES {schema_b}.shops (code, region))"
        ),
        f"CREATE TABLE {schema_a}.empty ()",
        (
            f"CREATE TABLE {schema_b}.employee ("
            f"  id integer PRIMARY KEY,"
            f"  manager_id integer REFERENCES {schema_b}.employee (id))"
        ),
    ]
    # The names are the run's own tokens, not input: the cast tells psycopg's typed query
    # parameter (LiteralString) what the f-strings cannot — the DDL is ours, end to end.
    with psycopg.connect(_seed_dsn(settings), autocommit=True) as connection:
        for statement in statements:
            connection.execute(sql.SQL(cast("LiteralString", statement)))
    yield {"schema_a": schema_a, "schema_b": schema_b}
    with psycopg.connect(_seed_dsn(settings), autocommit=True) as connection:
        connection.execute(sql.SQL(cast("LiteralString", f"DROP SCHEMA {schema_a} CASCADE")))
        connection.execute(sql.SQL(cast("LiteralString", f"DROP SCHEMA {schema_b} CASCADE")))


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
    """The typed Atlas client as the dev writer: it reads the tree back and deletes it (DBS-09).

    The writer is the cleanup identity, not the identity under test; the scans speak through
    ``scanner`` instead. The fixture builds the httpx pool and closes it (CL-02).
    """
    async with httpx.AsyncClient(base_url=server, verify=str(CA_FILE), timeout=30.0) as http:
        yield AtlasClient(http, user_token)


@pytest_asyncio.fixture(loop_scope="function")
async def scanner(scanner_settings: ScannerSettings) -> AsyncIterator[AtlasClient]:
    """The catalogue client the scan speaks as: the scanner's own service identity (DBS-10).

    Built by the app's own ``build_client`` — the same door the CLI opens, so the suite proves
    the job's identity end to end: client credentials, accepted audiences, and the token
    refreshed ahead of expiry across the scan's calls.
    """
    client, http = build_client(scanner_settings)
    try:
        yield client
    finally:
        await http.aclose()


@pytest.fixture
def run_token() -> str:
    """One run token: the single ``zz<run>`` word every schema and System name carries."""
    return secrets.token_hex(4)


@pytest.fixture
def scanner_claims(settings: Settings, keycloak: DockerCompose) -> dict[str, Any]:
    """Fresh claims of a scanner token, minted inside the test's session (DBS-10).

    The audit principal of a client-credentials token is its ``sub`` (AUT-03's fallback: a
    service account has no human ``preferred_username``); scenarios name the writes' user by
    the ``sub`` answered here.
    """
    return _scanner_claims(settings, keycloak)


class Seeded:
    """What one scan wrote on the shared store; hard-deleted at its end (never left).

    ``record`` takes the entities of one bulk write with the guids the store assigned them;
    ``purge`` deletes them newest-listed first — the build order is system, collection,
    datasets, fields, processes, so reversing it tears the processes and fields down first.
    """

    def __init__(self, client: AtlasClient) -> None:
        self._client = client
        self._guids: list[str] = []

    def record(self, entities: list[Any], assigned: dict[str, str]) -> None:
        """Remember one written batch: every entity's real guid, build order kept."""
        for entity in entities:
            guid = str(assigned.get(str(entity.guid), entity.guid))
            if guid not in self._guids:
                self._guids.append(guid)

    async def purge(self) -> None:
        """Hard-delete every remembered entity, reversed (leaves first)."""
        if self._guids:
            await self._client.entity.delete_by_guids(list(reversed(self._guids)), delete_type=DeleteType.HARD)


@pytest_asyncio.fixture(loop_scope="function")
async def cleanup(writer: AtlasClient) -> AsyncIterator[Seeded]:
    """What a test scanned onto the store; hard-deleted at its end (never left, never restarted).

    The names are zz-token-namespaced and self-cleaned, so the shared dev store keeps nothing
    between tests (DD-223).
    """
    seeded = Seeded(writer)
    yield seeded
    await seeded.purge()
