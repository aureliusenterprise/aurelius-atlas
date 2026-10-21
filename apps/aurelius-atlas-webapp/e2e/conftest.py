import re
from collections.abc import Generator
from pathlib import Path

import dotenv
import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt, wait_fixed
from testcontainers.compose import DockerCompose
from testcontainers.core.wait_strategies import HealthcheckWaitStrategy, HttpWaitStrategy

CA_FILE = Path(__file__).parents[1] / "certs" / "ca.pem"

# The compose file publishes these fixed host ports; the readiness probes and
# the URLs below are built from them (the strategy resolves containers as
# 127.0.0.1 + the given port, so a fixed mapping is what makes a pre-start
# strategy possible at all).
WEBAPP_HOST_PORT = 18444
ATLAS_SERVER_HOST_PORT = 18445


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

    compose.start()

    return compose.waiting_for(
        {
            "keycloak": HealthcheckWaitStrategy(),
        },
    )


@pytest.fixture(scope="session")
def compose(keycloak: DockerCompose, observability: DockerCompose) -> Generator[DockerCompose]:
    """Return a Docker Compose instance."""
    _ = keycloak, observability  # Ensure that the proxy upstreams are up before starting the app

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
