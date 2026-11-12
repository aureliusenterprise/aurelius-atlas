"""E2E fixtures: the real server, the suite's own broker, and the scanner's identity (KSC-09, KSC-10).

The suite drives the scanner in-process — the job is a batch CLI, not a service — against a
stack whose services are the Atlas server and one disposable broker and Schema Registry
(DD-533, the pattern of db-scanner's Postgres, DD-507): the stack starts with the suite and
discards its cluster data with it. The store and the issuer stay the dev ones. Seeding and
cleanup ride the webapp suite's writer (the public client's password grant); every scan speaks
as the scanner's own service identity, minted by client credentials (DD-469's pattern). Every
topic the suite creates carries the run's ``zz<run>`` prefix and is deleted at the end, and no
fixture here restarts a shared dev stack (DD-223).
"""

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
from aurelius_atlas_kafka_scanner.__main__ import build_client
from aurelius_atlas_kafka_scanner.settings import ENV_PREFIX, ScannerSettings
from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_server_client import AtlasClient, DeleteType
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from testcontainers.compose import DockerCompose

if TYPE_CHECKING:
    from pydantic import HttpUrl

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the server's and the issuer's certificates."""

SERVER_HOST_PORT = 21006
"""The host port the e2e compose publishes the server on, loopback-pinned (CIA-03)."""

BROKER_HOST_PORT = 29092
"""The host port of the broker's plain listener, loopback-pinned (CIA-03). The compose file
publishes the same number and the broker advertises it: the host door dials what the broker
answers, the contract of the old dev stack's ports (DD-469) kept as this stack's literal."""

SASL_HOST_PORT = 29095
"""The host port of the broker's SASL listener, loopback-pinned (CIA-03)."""

REGISTRY_HOST_PORT = 28081
"""The host port of the Schema Registry, loopback-pinned (CIA-03)."""

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the dev realm to serve tokens (a reused stack may be warming up)."""

SCANNER_CLIENT_ID = "aurelius-atlas-kafka-scanner"
"""The service client the job signs in as (DD-469's pattern, KSC-09)."""

SCANNER_MINT_HINT = (
    "The dev realm did not answer the scanner's client credentials with a usable token. "
    "A refusal means the running Keycloak was imported before the "
    "`aurelius-atlas-kafka-scanner` client entered import/master.json: a running realm is "
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

    sasl_username: str
    """The SCRAM principal of the suite broker's SASL listener (KSC-10): injected by Nx from
    the project .env, and the same value the compose's ``sasl-init`` reads for its guard."""

    sasl_password: SecretStr
    """The secret of ``sasl_username`` — one value two places: Settings and the compose guard."""

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
    a confidential client (DD-469's pattern). Every scenario's audit name is the ``sub``
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
    """The e2e stack — the Atlas server beside its own broker and Registry — once healthy; its base URL.

    ``docker compose up --wait`` returns when every service's healthcheck passes: the server's
    liveness over TLS, the broker's metadata answer, the Registry's subject list, and the
    one-shot ``sasl-init`` exit. The stack rides the dev store and issuer, started first by the
    fixtures and left running (DD-223); this whole stack comes down at the end, and the
    broker's data with it (DD-533).
    """
    _ = keycloak, elasticsearch
    context = Path(__file__).parent.absolute()
    with DockerCompose(context=context, env_file=str(PROJECT / ".env")):
        yield f"https://localhost:{SERVER_HOST_PORT}"


@pytest.fixture(scope="session")
def scanner_settings(server: str, settings: Settings, keycloak: DockerCompose) -> ScannerSettings:
    """The scan's settings: this stack's server, broker, and Registry, and the scanner's identity.

    The realm is probed once, before any scan: a client the running realm does not know is
    the suite's own setup error, and the remedy must name it (``SCANNER_MINT_HINT``) instead
    of surfacing as a scan-time refusal. The system name and topic patterns ride per test —
    each scenario namespaces them to its run — through ``model_copy``.
    """
    _scanner_claims(settings, keycloak)
    return ScannerSettings(
        server_url=cast("HttpUrl", server),  # pydantic validates the URL text at init
        client_secret=settings.client_secret,
        ca_file=str(CA_FILE),
        bootstrap_servers=f"localhost:{BROKER_HOST_PORT}",
        schema_registry_url=cast("HttpUrl", f"http://localhost:{REGISTRY_HOST_PORT}"),
    )


@pytest.fixture(scope="session")
def sasl_settings(scanner_settings: ScannerSettings, settings: Settings) -> ScannerSettings:
    """The scan's settings on the broker's SASL listener: the same scan over SCRAM (KSC-10).

    The suite broker's second host listener answers SASL_PLAINTEXT with SCRAM-SHA-512
    (DD-471's stand-in for auth'd customer clusters, now the stack's own); the credentials
    are the values the project environment carries and ``sasl-init`` wrote into the cluster.
    """
    return scanner_settings.model_copy(
        update={
            "bootstrap_servers": f"localhost:{SASL_HOST_PORT}",
            "security_protocol": "SASL_PLAINTEXT",
            "sasl_mechanism": "SCRAM-SHA-512",
            "sasl_username": settings.sasl_username,
            "sasl_password": settings.sasl_password,
        },
    )


@pytest.fixture
def scanner_claims(settings: Settings, keycloak: DockerCompose) -> dict[str, Any]:
    """Fresh claims of a scanner token, minted inside the test's session (KSC-09).

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
    """The typed Atlas client as the dev writer: it reads the tree back and deletes it (KSC-07).

    The writer is the cleanup identity, not the identity under test; the scans speak through
    ``scanner`` instead. The fixture builds the httpx pool and closes it (CL-02).
    """
    async with httpx.AsyncClient(base_url=server, verify=str(CA_FILE), timeout=30.0) as http:
        yield AtlasClient(http, user_token)


@pytest_asyncio.fixture(loop_scope="function")
async def scanner(scanner_settings: ScannerSettings) -> AsyncIterator[AtlasClient]:
    """The catalogue client the scan speaks as: the scanner's own service identity (KSC-09).

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
    """One run token: the single ``zz<run>`` word every topic and System name carries."""
    return secrets.token_hex(4)


@pytest.fixture
def bootstrap(scanner_settings: ScannerSettings) -> str:
    """The suite broker's bootstrap string, as the scan's settings name it."""
    return scanner_settings.bootstrap_servers


@pytest.fixture
def registry_url(scanner_settings: ScannerSettings) -> str:
    """The dev Schema Registry's URL, as the scan's settings name it."""
    return str(scanner_settings.schema_registry_url)


@pytest.fixture
def topics(bootstrap: str, run_token: str) -> Iterator[Callable[..., str]]:
    """A topic factory on the suite broker: create one ``zz<run>``-named topic and remember it.

    The returned callable answers the new topic's name (``zz<run><suffix>``); every created
    topic is deleted when the test ends, whatever else cleanup did. The broker is discarded
    with the stack, but the run never leaves its own topics lying around for the next one.
    """
    admin = KafkaAdminClient(bootstrap_servers=bootstrap)
    created: list[str] = []

    def create(suffix: str) -> str:
        name = f"zz{run_token}{suffix}"
        admin.create_topics([NewTopic(name=name, num_partitions=1, replication_factor=1)])
        created.append(name)
        return name

    yield create
    admin.delete_topics(created, timeout_ms=30_000)
    admin.close()


@pytest.fixture
def produce(bootstrap: str) -> Iterator[Callable[[str, bytes], None]]:
    """Produce one record to a topic and wait until the broker holds it."""
    producer = KafkaProducer(bootstrap_servers=bootstrap)

    def send(topic: str, value: bytes) -> None:
        producer.send(topic, value).get(timeout=30)
        producer.flush(timeout=30)

    yield send
    producer.close()


@pytest_asyncio.fixture(loop_scope="function")
async def register(registry_url: str) -> AsyncIterator[Callable[[str, str, str], Awaitable[int]]]:
    """Register an Avro or JSON schema under a ``zz<run>``-named subject; answer its id.

    The returned callable takes ``(subject, schema_type, schema_text)``, posts it as the
    subject's latest version, and answers the Registry's schema id (the wire sniff needs it).
    Subjects the suite made are deleted at the test's end — the shared Registry keeps nothing.
    """
    subjects: list[str] = []

    async def put(subject: str, schema_type: str, schema_text: str) -> int:
        async with httpx.AsyncClient(base_url=registry_url, timeout=30) as http:
            response = await http.post(
                f"/subjects/{subject}/versions",
                json={"schemaType": schema_type, "schema": schema_text},
            )
            response.raise_for_status()
            subjects.append(subject)
            return int(response.json()["id"])

    yield put
    async with httpx.AsyncClient(base_url=registry_url, timeout=30) as http:
        for subject in subjects:
            # Confluent's permanent delete wants the versions gone first (40405
            # otherwise); the subject then goes with them.
            await http.delete(f"/subjects/{subject}/versions/latest")
            await http.delete(f"/subjects/{subject}?permanent=true")


class Seeded:
    """What one scan wrote on the shared store; hard-deleted at its end (never left).

    ``record`` takes the entities of one bulk write with the guids the store assigned them;
    ``purge`` deletes them newest-listed first — the build order is system, collection,
    datasets, fields, so reversing it tears fields down before the datasets that hold them.
    """

    def __init__(self, client: AtlasClient) -> None:
        self._client = client
        self._guids: list[str] = []

    def record(self, entities: list[AtlasEntity], assigned: dict[str, str]) -> None:
        """Remember one written batch: every entity's real guid, build order kept."""
        for entity in entities:
            guid = str(assigned.get(str(entity.guid), entity.guid))
            if guid not in self._guids:
                self._guids.append(guid)

    async def purge(self) -> None:
        """Hard-delete every remembered entity, reversed (fields first)."""
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
