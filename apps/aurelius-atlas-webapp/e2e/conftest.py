import json
import os
import re
import ssl
import time
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import dotenv
import pytest
from docker import from_env as docker_from_env
from docker.models.containers import Container
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt, wait_fixed
from testcontainers.compose import DockerCompose
from testcontainers.core.wait_strategies import HttpWaitStrategy

CA_FILE = Path(__file__).parents[1] / "certs" / "ca.pem"

# The compose file publishes these fixed host ports; the readiness probes and
# the URLs below are built from them (the strategy resolves containers as
# 127.0.0.1 + the given port, so a fixed mapping is what makes a pre-start
# strategy possible at all).
WEBAPP_HOST_PORT = 18444
ATLAS_SERVER_HOST_PORT = 18445

# The dev collector (dev/observability, started by the observability fixture).
# Its publishes are loopback-pinned (CIA-03), so the direct-ingest tests below
# reach it on 127.0.0.1; the certificate carries the "otel-collector" SAN, so
# that is the TLS server hostname. The shared ingest token (DD-103) is Nx's
# injected dev default from the project .env.
OBSERVABILITY_PROJECT = "aurelius-atlas-dev-observability"
COLLECTOR_HOST = "127.0.0.1"
COLLECTOR_PORT = 4318
SERVICE_PORT = 4319
LEGACY_PORT = 4321
COLLECTOR_TLS_NAME = "otel-collector"

# Tempo's query API on the same stack (compose publishes :3200): the
# attribution probe reads back through it — TraceQL resource predicates
# prove the collector stamped the user onto the telemetry (CIA-05, DD-105).
TEMPO_HOST = "127.0.0.1"
TEMPO_PORT = 3200
DEFAULT_INGEST_TOKEN = "otel-dev-ingest-token"  # noqa: S105  # the public dev default, not a secret (DD-103)
DEFAULT_INGEST_CLIENT_SECRET = "kbTROtW6-P6ibQ7iAovsceJceRz39HpQ"  # noqa: S105  # the public dev default, not a secret (DD-107)

# The OIDC leg's issuer (DD-103): the e2e Keycloak serves HTTPS on :8443 and
# mints iss=.../realms/master on that listener, so the collector must validate
# against exactly that issuer. The oidc extension (collector ≥ 0.142 schema:
# providers/issuer_url) fetches its JWKS through OIDC discovery on that URL —
# over TLS pinned to the shared dev CA (mounted at /dev-ca in the collector).
# The compose file's dev default (plaintext :8080) is overridden here for the
# e2e run.
KEYCLOAK_ISSUER = "https://keycloak.localhost:8443/realms/master"
COLLECTOR_OIDC_CA_IN_CONTAINER = "/dev-ca/ca.pem"


class Settings(BaseSettings):
    """Test configuration."""

    auth_realm_name: str = "master"
    password: SecretStr
    username: str

    model_config = SettingsConfigDict(
        # Namespace this project's e2e config: the Nx-injected .env uses
        # AURELIUS_ATLAS_WEBAPP_-prefixed names (the sign-in user, APC-10).
        env_prefix="AURELIUS_ATLAS_WEBAPP_",
        env_file=dotenv.find_dotenv(),
        extra="ignore",
    )


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Return the test configuration."""
    return Settings()  # type: ignore[values are loaded from the environment]


@pytest.fixture(scope="session", autouse=True)
def _environment() -> None:
    """Load the environment variables."""
    dotenv.load_dotenv(dotenv.find_dotenv())


@pytest.fixture(scope="session")
def observability() -> DockerCompose:
    """
    Return a Docker Compose instance for the observability services.

    The collector's browser leg (OIDC) is pointed at the e2e Keycloak issuer
    and JWKS (CA-pinned) via the ambient env the compose file interpolates
    (DD-103): the suite's Keycloak mints :8443 tokens, which the compose dev
    default (plaintext :8080 issuer) would not match.

    The per-service leg (DD-107) flips the same way: the slice metrics-pullers
    mint their client-credentials JWTs from the issuer, so they inherit the
    suite's TLS :8443 issuer + CA pin (the compose dev default is the
    plaintext :8080 listener) — env the keycloak/postgres/elasticsearch
    compose files interpolate into the puller containers, each of which
    mounts its slice's certs/ (the same mkcert CA material).

    Note: This fixture starts the observability services if they're not already running, but does not stop them after
    the tests. This allows the services to be reused across multiple test sessions, but may require manual cleanup if
    the services are no longer needed.
    """
    os.environ["OTEL_COLLECTOR_OIDC_ISSUER"] = KEYCLOAK_ISSUER
    os.environ["OTEL_COLLECTOR_OIDC_CA_FILE"] = COLLECTOR_OIDC_CA_IN_CONTAINER
    os.environ["OTEL_INGEST_TOKEN_URL"] = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token"
    os.environ["OTEL_INGEST_CA_FILE"] = "/certs/ca.pem"
    context = Path(__file__).parents[3].absolute() / "dev" / "observability"
    compose = DockerCompose(context=context)

    compose.start()

    return compose


@pytest.fixture(scope="session")
def keycloak(observability: DockerCompose) -> DockerCompose:
    """
    Return a Docker Compose instance for the Keycloak service.

    The 7.1 shell has no sign-in (auth is 7.3), but the e2e nginx config proxies
    /api/ to Keycloak as the dev stack's standing backend, so the proxy-path
    scenario (SHL-11) needs it running.

    Note: This fixture starts the Keycloak service if it's not already running, but does not stop it after
    the tests. This allows the services to be reused across multiple test sessions, but may require manual cleanup if
    the services are no longer needed.
    """
    _ = observability  # Ensure that the observability services are started before starting Keycloak

    context = Path(__file__).parents[3].absolute() / "dev" / "keycloak"
    compose = DockerCompose(context=context)

    # Readiness is compose's own: start() runs ``up --wait`` and the keycloak
    # service carries a healthcheck, so the command returns when Keycloak is
    # ready (DD-106: this is the gate that lets the collector's
    # ``restart: on-failure`` cover its OIDC-discovery boot race). No
    # testcontainers HealthcheckWaitStrategy here: the strategy reads
    # docker-py ``attrs`` the ComposeContainer wrapper does not have, and a
    # strategy must be registered before start() to run at all.
    compose.start()

    return compose


@pytest.fixture(scope="session")
def elasticsearch(observability: DockerCompose) -> DockerCompose:
    """Return a Docker Compose instance for the dev Elasticsearch stack.

    The e2e target's ``up`` dependency starts this stack before pytest runs,
    with the compose dev defaults — and the slice's metrics-puller mints its
    ingest JWT at boot (DD-107). This fixture re-runs ``up --wait`` with the
    flipped mint env (the ``observability`` fixture sets it) so the puller
    is recreated against this suite's TLS issuer; without it the ES puller's
    :8080-issued tokens are 401 on the flipped per-service leg (CIA-07).

    Note: like the observability/keycloak fixtures, this starts the stack
    and leaves it running for reuse across sessions.
    """
    _ = observability  # The stack external-attaches the observability network (metrics-puller): it must exist.

    context = Path(__file__).parents[3].absolute() / "dev" / "elasticsearch"
    compose = DockerCompose(context=context)

    compose.start()

    return compose


@pytest.fixture(scope="session")
def compose(
    keycloak: DockerCompose, elasticsearch: DockerCompose, observability: DockerCompose
) -> Generator[DockerCompose]:
    """Return a Docker Compose instance."""
    _ = keycloak, elasticsearch, observability  # Ensure that the proxy upstreams are up before starting the app

    context = Path(__file__).parent.absolute()

    compose = DockerCompose(context=context, env_file=dotenv.find_dotenv())
    # Both host ports are fixed in the compose file, so the readiness probes
    # are fully known before the stack starts: nginx serving the shell, and
    # the Atlas server answering its version endpoint directly (DD-053 — the
    # /api/ proxy test needs the server itself up, probing through nginx would
    # race its own boot). Registered pre-start so start() runs them.
    compose.waiting_for(
        {
            "aurelius-atlas-webapp": HttpWaitStrategy(port=WEBAPP_HOST_PORT, path="/en-US/")
            .using_tls()
            .for_status_code(200),
            "atlas-server": HttpWaitStrategy(port=ATLAS_SERVER_HOST_PORT, path="/api/atlas/admin/version")
            .using_tls()
            .for_status_code(200),
        },
    )

    with compose:
        yield compose


@pytest.fixture(scope="session")
def root_url(compose: DockerCompose) -> str:
    """Return the origin root URL for the application."""
    _ = compose  # Ensure the stack is up (and ready) before any URL is used.
    return f"https://localhost:{WEBAPP_HOST_PORT}/"


@pytest.fixture(scope="session")
def base_url(root_url: str) -> str:
    """Return the en-US app URL for the application."""
    return f"{root_url}en-US/"


def _clear_cookies(retry_state: RetryCallState) -> None:
    """Start the next login attempt from a clean cookie jar."""
    page: Page = retry_state.kwargs.get("page") or retry_state.args[0]
    page.context.clear_cookies()


@pytest.fixture
@retry(
    retry=retry_if_exception_type(PlaywrightError),
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    reraise=True,
    before_sleep=_clear_cookies,
)
def authenticated(page: Page, base_url: str, settings: Settings) -> Page:
    """
    Sign in through Keycloak and return the page (APC-05 / APC-10).

    Every webapp route sits behind the auth guard (DD-052), so the page tests
    start from here. A navigation can be aborted mid-login when the e2e stack
    starts its compose networks while tests run (net::ERR_NETWORK_CHANGED), so
    each retry starts from a clean cookie jar: Keycloak may already have
    issued the session on the failed pass.
    """
    page.goto(base_url)

    page.wait_for_url(re.compile(f"/realms/{settings.auth_realm_name}/protocol/openid-connect/auth"))

    page.locator("#username").fill(settings.username)
    page.locator("#password").fill(settings.password.get_secret_value())
    page.get_by_role("button", name="Sign in").click()

    page.wait_for_url(re.compile(base_url))

    return page


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:  # noqa: ARG001
    """Trust the ephemeral local development CA in Playwright browsers.

    Playwright's bundled browsers ship their own trust stores and cannot enroll
    the mkcert root, so page navigation skips browser certificate verification.
    This is the one named relaxation of the browser-facing path (ADR 039): the
    certificate chain and hostname are verified against the CA by the explicit
    ``test__browser_facing_tls_verifies_against_ca`` check instead, nginx still
    verifies the proxies with ``proxy_ssl_verify`` (``config/nginx.conf``), and
    non-browser E2E paths always verify.
    """
    return {"ignore_https_errors": True}


@pytest.fixture(scope="session")
def ingest_token() -> str:
    """The shared collector ingest token the task environment carries (DD-103).

    Nx injects the project ``.env`` into the e2e task (the ``decrypt``
    dependency); the dev default is the fallback so a bare pytest run outside
    the Nx target still speaks the dev stack's language.
    """
    return os.environ.get("OTEL_COLLECTOR_INGEST_TOKEN", DEFAULT_INGEST_TOKEN)


@pytest.fixture
def user_token(keycloak: DockerCompose, settings: Settings) -> str:
    """A real user access token minted by the e2e Keycloak (DD-103, CIA-01/02).

    The password grant for the dev sign-in user (the same ``aurelius`` client
    the SPA rides, ``directAccessGrantsEnabled``): the token carries the
    ``otel-collector`` audience the realm's otel-ingest scope mints, which is
    what the collector's OIDC receiver requires. ``keycloak`` guarantees the
    issuer is up; the shared dev CA verifies the :8443 listener.

    Function-scoped on purpose: the dev realm mints 60s tokens, and the
    suite runs each test once per browser (~7 minutes total) — a session-
    scoped token is stale for the last browser.
    """
    _ = keycloak
    body = urlencode(
        {
            "grant_type": "password",
            "client_id": "aurelius",
            "username": settings.username,
            "password": settings.password.get_secret_value(),
        }
    ).encode()
    request = Request(f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token", data=body, method="POST")  # noqa: S310  # https constant issuer
    context = ssl.create_default_context(cafile=str(CA_FILE))

    with urlopen(request, context=context) as response:  # noqa: S310  # https constant issuer, CA-verified
        return json.load(response)["access_token"]


@pytest.fixture
def service_token(keycloak: DockerCompose) -> str:
    """A client-credentials token for the otel-atlas-server ingest client (DD-107, CIA-06/07).

    The same grant the graduated producers present on the per-service leg:
    the realm's confidential ``otel-atlas-server`` client (import/master.json,
    service accounts only) with the shared dev client secret — the Nx-
    injected ``OTEL_INGEST_CLIENT_SECRET`` (the dev default is the fallback,
    like ``ingest_token``). ``keycloak`` guarantees the issuer is up; the
    realm import must be live (see the dev-keycloak AGENTS note: import
    applies on recreate, so a pre-existing stack needs a restart).

    Function-scoped: the dev realm mints 60s tokens (the ``user_token``
    fixture's rule, same for the browser loop).
    """
    _ = keycloak
    body = urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": "otel-atlas-server",
            "client_secret": os.environ.get("OTEL_INGEST_CLIENT_SECRET", DEFAULT_INGEST_CLIENT_SECRET),
        }
    ).encode()
    request = Request(f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token", data=body, method="POST")  # noqa: S310  # https constant issuer
    context = ssl.create_default_context(cafile=str(CA_FILE))

    with urlopen(request, context=context) as response:  # noqa: S310  # https constant issuer, CA-verified
        return json.load(response)["access_token"]


@pytest.fixture(scope="session")
def collector_container(observability: DockerCompose) -> Container:  # noqa: ARG001
    """The running collector container of the dev observability stack (CIA-03).

    Found by compose labels rather than name, mirroring how the fixture above
    starts it. ``observability`` guarantees the stack is up. The collector
    crash-loops until Keycloak answers its OIDC discovery (DD-103/DD-106) and
    the restart policy brings it back, so the fixture polls for the settled
    state — running with its port bindings in place — rather than reading the
    container mid-restart (a restarting container reports no bindings).
    """
    client = docker_from_env()
    deadline = time.monotonic() + 120
    while True:
        containers = client.containers.list(
            filters={
                "label": [
                    f"com.docker.compose.project={OBSERVABILITY_PROJECT}",
                    "com.docker.compose.service=otel-collector",
                ]
            }
        )
        if containers:
            container = containers[0]
            container.reload()
            ports = container.attrs["NetworkSettings"]["Ports"]
            if container.status == "running" and any(ports.values()):
                return container
        if time.monotonic() >= deadline:
            message = "the dev/observability collector did not settle into a running state"
            raise ValueError(message)
        time.sleep(2)
