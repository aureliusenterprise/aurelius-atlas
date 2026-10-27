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
from playwright.sync_api import Browser, Page
from playwright.sync_api import Error as PlaywrightError
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
# that is the TLS server hostname. The shared ingest token (DD-193) is Nx's
# injected dev default from the project .env.
OBSERVABILITY_PROJECT = "aurelius-atlas-dev-observability"
COLLECTOR_HOST = "127.0.0.1"
COLLECTOR_PORT = 4318
SERVICE_PORT = 4319
LEGACY_PORT = 4321
COLLECTOR_TLS_NAME = "otel-collector"

# Tempo's query API on the same stack (compose publishes :3200): the
# attribution probe reads back through it — TraceQL resource predicates
# prove the collector stamped the user onto the telemetry (CIA-05, DD-194).
TEMPO_HOST = "127.0.0.1"
TEMPO_PORT = 3200
DEFAULT_INGEST_TOKEN = "otel-dev-ingest-token"  # noqa: S105  # the public dev default, not a secret (DD-193)
DEFAULT_INGEST_CLIENT_SECRET = "kbTROtW6-P6ibQ7iAovsceJceRz39HpQ"  # noqa: S105  # the public dev default, not a secret (DD-196)

# The issuer this suite mints from (DD-193, DD-202): the e2e Keycloak serves
# HTTPS on :8443 and stamps iss=.../realms/master from that listener — the
# mint fixtures below and every per-service producer use it, and the
# collector's oidc extension validates it (CA-pinned discovery, from the
# collector's own certs/). Standardizing the mint on :8443 is what keeps
# every suite in one issuer world (DD-202); the plaintext :8080 listener
# stays validated in the collector, for the human dev browser only (ADR 039).
KEYCLOAK_ISSUER = "https://keycloak.localhost:8443/realms/master"

# The dev plaintext listener (ADR 039, the collector's second provider): the
# mint the human dev browser does, and the mint the CIA-11 fixture below
# reproduces, to prove the collector accepts that iss too (DD-202).
KEYCLOAK_DEV_ISSUER = "http://keycloak.localhost:8080/realms/master"


class Settings(BaseSettings):
    """Test configuration: the dev identity the browser signs in as (APC-10)."""

    auth_realm_name: str = "master"
    """The realm the tokens are minted from."""

    password: SecretStr
    """The dev user's password; never shown in logs."""

    username: str
    """The dev user the browser signs in as."""

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

    No issuer env is set here (DD-202): the collector validates both dev
    Keycloak listeners from its own config, and every producer — this
    suite's minted tokens included — presents the TLS :8443 iss, so the
    stack boots in exactly one world no matter who started it first.

    Note: This fixture starts the observability services if they're not already running, but does not stop them after
    the tests. This allows the services to be reused across multiple test sessions, but may require manual cleanup if
    the services are no longer needed.
    """
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
    # ready (DD-195: this is the gate that lets the collector's
    # ``restart: on-failure`` cover its OIDC-discovery boot race). No
    # testcontainers HealthcheckWaitStrategy here: the strategy reads
    # docker-py ``attrs`` the ComposeContainer wrapper does not have, and a
    # strategy must be registered before start() to run at all.
    compose.start()

    return compose


@pytest.fixture(scope="session")
def elasticsearch(observability: DockerCompose) -> DockerCompose:
    """Return a Docker Compose instance for the dev Elasticsearch stack.

    The e2e target's ``up`` dependency starts this stack before pytest runs;
    this fixture guarantees it (and the observability network it attaches).
    The slice's metrics-puller mints its ingest JWT at boot on the suite's
    TLS :8443 issuer — the compose's literal, same issuer this suite mints
    and the collector validates (DD-202), so no re-start with flipped env
    is needed anymore.

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
    # the Atlas server answering its version endpoint directly (DD-142 — the
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


def _sign_in(page: Page, base_url: str, settings: Settings) -> None:
    """Run the Keycloak form login, and wait for the authenticated app.

    The page sits on the login form (the auth guard's redirect landed there);
    fill it, sign in, and settle: the navbar renders once the SPA's check-sso
    handshake has traded the SSO session for tokens, so a caller can trust
    the page — and the context's cookies — as signed in (APC-05, APC-10).
    """
    page.wait_for_url(re.compile(f"/realms/{settings.auth_realm_name}/protocol/openid-connect/auth"))

    page.locator("#username").fill(settings.username)
    page.locator("#password").fill(settings.password.get_secret_value())
    page.get_by_role("button", name="Sign in").click()

    page.wait_for_url(re.compile(base_url))

    page.locator("nav.navbar").wait_for(state="visible", timeout=30_000)


def _wait_signed_in(page: Page) -> bool:
    """Watch the boot: True when the app renders, False when Keycloak's form answers.

    The auth guard's redirect and the SPA boot race by design; the navbar is
    the app's own chrome (the Keycloak form has none), so the first of the two
    to appear decides. The poll interval bounds the common path's cost: a
    replayed session shows the navbar in ~1s, a form lands within the first
    polls (DD-224).
    """
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if "/realms/" in page.url:
            return False
        if page.locator("nav.navbar").count() > 0:
            return True
        page.wait_for_timeout(250)
    return False


@pytest.fixture(scope="session")
def _storage_state(
    tmp_path_factory: pytest.TempPathFactory,
    browser: Browser,
    base_url: str,
    settings: Settings,
) -> str:
    """Sign in once per browser and save the session as a Playwright storage state (DD-224).

    The suite's ~37 authenticated tests per browser each used to run the full
    Keycloak form login. What a login leaves behind is the realm's SSO session
    (``KEYCLOAK_IDENTITY``, a 30-minute idle window refreshed by every visit),
    and the SPA boots with ``check-sso`` and a silent-iframe redirect (APC-05):
    a test context that starts from this state mints its own 60s access tokens
    from the stored SSO session, with no login form. The user's password never
    enters the state — it carries cookies, not credentials.

    A navigation can be aborted mid-login when the e2e stack starts its
    compose networks while tests run (net::ERR_NETWORK_CHANGED), so each
    retry starts from a clean cookie jar: Keycloak may already have issued
    the session on the failed pass.
    """
    state_path = str(tmp_path_factory.mktemp("auth") / "state.json")

    @retry(
        retry=retry_if_exception_type(PlaywrightError),
        stop=stop_after_attempt(2),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=_clear_cookies,
    )
    def sign_in(page: Page) -> None:
        page.goto(base_url)

        _sign_in(page, base_url, settings)

    context = browser.new_context(ignore_https_errors=True)
    try:
        sign_in(page=context.new_page())

        context.storage_state(path=state_path)
    finally:
        context.close()

    return state_path


@pytest.fixture
def authenticated(
    browser: Browser,
    browser_context_args: dict,
    _storage_state: str,
    base_url: str,
    settings: Settings,
) -> Generator[Page]:
    """
    Return a page signed in through Keycloak (APC-05 / APC-10, DD-224).

    Every webapp route sits behind the auth guard (DD-141), so the page tests
    start from here. The Keycloak SSO session captured once per browser
    (``_storage_state``) rides the new context: the SPA's check-sso boot
    mints the test's own 60s access tokens from it, and no login form runs.
    The context is the test's own — cookies, storage and cache stay isolated
    the way the per-test form login left them.

    Self-healing: when the page lands on the login form anyway — the shared
    session died (the resilience suite's logout test ends the realm session,
    DD-153/RSL-02) — the fixture runs the form login and refreshes the shared
    state, so the next test replays from a live session again.
    """
    context = browser.new_context(storage_state=_storage_state, **browser_context_args)
    try:
        page = context.new_page()
        page.goto(base_url)

        if not _wait_signed_in(page):
            _sign_in(page, base_url, settings)
            context.storage_state(path=_storage_state)

        yield page
    finally:
        context.close()


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
    """The shared collector ingest token the task environment carries (DD-193).

    Nx injects the project ``.env`` into the e2e task (the ``decrypt``
    dependency); the dev default is the fallback so a bare pytest run outside
    the Nx target still speaks the dev stack's language.
    """
    return os.environ.get("OTEL_COLLECTOR_INGEST_TOKEN", DEFAULT_INGEST_TOKEN)


@pytest.fixture
def user_token(keycloak: DockerCompose, settings: Settings) -> str:
    """A real user access token minted by the e2e Keycloak (DD-193, CIA-01/02).

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
    """A client-credentials token for the otel-atlas-server ingest client (DD-196, CIA-06/07).

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


@pytest.fixture
def plaintext_service_token(keycloak: DockerCompose) -> str:
    """A client-credentials token minted from the plaintext :8080 listener (CIA-11, DD-202).

    Keycloak stamps ``iss`` from the listener that served the mint, so this
    token carries ``iss=http://keycloak.localhost:8080/realms/master`` — the
    issuer the human dev browser presents (ADR 039's listener), which the
    collector's second OIDC provider must accept. The mint needs no CA pin:
    the listener is plaintext HTTP.

    Function-scoped: the dev realm mints 60s tokens (the ``service_token``
    fixture's rule).
    """
    _ = keycloak
    body = urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": "otel-atlas-server",
            "client_secret": os.environ.get("OTEL_INGEST_CLIENT_SECRET", DEFAULT_INGEST_CLIENT_SECRET),
        }
    ).encode()
    request = Request(f"{KEYCLOAK_DEV_ISSUER}/protocol/openid-connect/token", data=body, method="POST")  # noqa: S310  # the dev stack's plaintext listener, by design (ADR 039)

    with urlopen(request) as response:  # noqa: S310  # plaintext dev issuer, mint-side by design
        return json.load(response)["access_token"]


@pytest.fixture(scope="session")
def collector_container(observability: DockerCompose) -> Container:  # noqa: ARG001
    """The running collector container of the dev observability stack (CIA-03).

    Found by compose labels rather than name, mirroring how the fixture above
    starts it. ``observability`` guarantees the stack is up. The collector
    crash-loops until Keycloak answers its OIDC discovery (DD-193/DD-195) and
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
