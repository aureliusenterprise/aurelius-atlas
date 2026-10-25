import json
import re
import ssl
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import dotenv
import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, Engine
from sqlmodel import Session, SQLModel, create_engine
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt, wait_fixed
from testcontainers.compose import DockerCompose
from testcontainers.core.wait_strategies import HttpWaitStrategy

CA_FILE = Path(__file__).parents[1] / "certs" / "ca.pem"

# The issuer this suite mints from (DD-193, DD-202): the e2e Keycloak serves
# HTTPS on :8443 and stamps iss=.../realms/master from that listener — the
# mint fixtures below and every per-service producer use it, and the
# collector's oidc extension validates it (CA-pinned discovery, from the
# collector's own certs/). Standardizing the mint on :8443 is what keeps
# every suite in one issuer world (DD-202); the plaintext :8080 listener
# stays validated in the collector, for the human dev browser only (ADR 039).
KEYCLOAK_ISSUER = "https://keycloak.localhost:8443/realms/master"


class Settings(BaseSettings):
    """Test configuration: the dev identity the browser signs in as and the database behind it."""

    auth_realm_name: str
    """The realm the tokens are minted from."""

    database_name: str
    """The database the backend serves."""

    database_password: SecretStr
    """The database password; never shown in logs."""

    database_port: int
    """The published port of the database."""

    database_username: str
    """The database user."""

    password: SecretStr
    """The dev user's password; never shown in logs."""

    username: str
    """The dev user the browser signs in as."""

    model_config = SettingsConfigDict(
        # Namespace this project's e2e config: the compose files and the
        # Nx-injected .env use AURELIUS_ATLAS_FRONTEND_-prefixed names.
        env_prefix="AURELIUS_ATLAS_FRONTEND_",
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
    suite's minted tokens included, and the keycloak stack's metrics-puller
    it starts — presents the TLS :8443 iss, so the stack boots in exactly
    one world no matter who started it first.

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

    Note: This fixture starts the Keycloak service if it's not already running, but does not stop it after the tests.
    This allows the service to be reused across multiple test sessions, but may require manual cleanup if the service is
    no longer needed.
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
def compose(keycloak: DockerCompose, observability: DockerCompose) -> Generator[DockerCompose]:
    """Return a Docker Compose instance."""
    _ = keycloak, observability  # Ensure that the auth and observability services are started before starting the app

    context = Path(__file__).parent.absolute()

    with DockerCompose(context=context, env_file=dotenv.find_dotenv()) as compose:
        port = compose.get_service_port("aurelius-atlas-frontend-example", 8080)

        if not port:
            message = "aurelius-atlas-frontend-example service not found in Docker Compose"
            raise ValueError(message)

        yield compose.waiting_for(
            {
                "aurelius-atlas-frontend-example": HttpWaitStrategy(port=port, path="/en-US/")
                .using_tls()
                .for_status_code(200),
            },
        )


@pytest.fixture(scope="session")
def base_url(compose: DockerCompose) -> str:
    """Return the base URL for the application."""
    port = compose.get_service_port("aurelius-atlas-frontend-example", 8080)
    return f"https://localhost:{port}/en-US/"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:  # noqa: ARG001
    """Trust the ephemeral local development CA in Playwright browsers.

    Playwright's bundled browsers ship their own trust stores and cannot enroll
    the mkcert root, so page navigation skips browser certificate verification.
    This is the one named relaxation of the browser-facing path (ADR 039): the
    certificate chain and hostname are verified against the CA by the explicit
    ``test__browser_facing_tls_verifies_against_ca`` check instead, nginx still
    verifies the backend with ``proxy_ssl_verify`` (``config/nginx.conf``), and
    non-browser E2E paths (API, Keycloak, Postgres) always verify.
    """
    return {"ignore_https_errors": True}


def _clear_cookies(retry_state: RetryCallState) -> None:
    """Start the next login attempt from a clean cookie jar."""
    page: Page = retry_state.kwargs.get("page") or retry_state.args[0]
    page.context.clear_cookies()


@pytest.fixture()
@retry(
    retry=retry_if_exception_type(PlaywrightError),
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    reraise=True,
    before_sleep=_clear_cookies,
)
def authenticated(page: Page, base_url: str, settings: Settings) -> Page:
    """
    Authenticate the user and return the page.

    The e2e stack starts its own compose networks while the tests run, and
    Chromium aborts in-flight navigations when the host interface list changes
    (net::ERR_NETWORK_CHANGED, occasionally surfacing as a wait timeout). The
    abort can land mid-login, so each retry starts from a clean cookie jar:
    Keycloak may already have issued the session on the failed pass.
    """
    page.goto(base_url)

    page.wait_for_url(re.compile(f"/realms/{settings.auth_realm_name}/protocol/openid-connect/auth"))

    page.locator("#username").fill(settings.username)
    page.locator("#password").fill(settings.password.get_secret_value())
    page.get_by_role("button", name="Sign in").click()

    page.wait_for_url(re.compile(base_url))

    return page


@pytest.fixture(scope="session", autouse=True)
def database(compose: DockerCompose, settings: Settings) -> Engine:
    """Setup and teardown the database."""
    hostname, port = compose.get_service_host_and_port("postgres-app", settings.database_port)

    if not (hostname and port):
        message = "PostgreSQL service not found in Docker Compose"
        raise ValueError(message)

    url = URL.create(
        drivername="postgresql+psycopg",
        username=settings.database_username,
        password=settings.database_password.get_secret_value(),
        host="localhost" if hostname in ("0.0.0.0", "::") else hostname,  # noqa: S104
        port=port,
        database=settings.database_name,
        query={"sslmode": "verify-full", "sslrootcert": str(CA_FILE)},
    )

    engine = create_engine(url)

    # Create the database schema
    SQLModel.metadata.create_all(engine)

    return engine


@pytest.fixture
def session(database: Engine) -> Generator[Session]:
    """Return a SQLModel session."""
    with Session(database, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def user_token(keycloak: DockerCompose, settings: Settings) -> str:
    """A real user access token minted by the e2e Keycloak (DD-193, CIA-01/02).

    The password grant for the dev sign-in user (the same ``aurelius`` client
    the SPA rides, ``directAccessGrantsEnabled``): the token carries the
    ``otel-collector`` audience the realm's otel-ingest scope mints, which is
    what the collector's browser-leg OIDC receiver requires. ``keycloak``
    guarantees the issuer is up; the shared dev CA verifies the :8443 listener.

    Function-scoped on purpose: the dev realm mints 60s tokens, and the test
    using it runs once per browser (~7 minutes total) — a session-scoped
    token is stale for the last browser.
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

    with urlopen(request, context=context) as response:  # noqa: S310  # CA-verified constant issuer
        return json.load(response)["access_token"]
