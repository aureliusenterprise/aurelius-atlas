from collections.abc import Generator
from pathlib import Path

import pytest
from testcontainers.compose import DockerCompose
from testcontainers.core.wait_strategies import HealthcheckWaitStrategy, HttpWaitStrategy

CA_FILE = Path(__file__).parents[1] / "certs" / "ca.pem"


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

    with DockerCompose(context=context) as compose:
        port = compose.get_service_port("aurelius-atlas-webapp", 8080)

        if not port:
            message = "aurelius-atlas-webapp service not found in Docker Compose"
            raise ValueError(message)

        yield compose.waiting_for(
            {
                "aurelius-atlas-webapp": HttpWaitStrategy(port=port, path="/en-US/").using_tls().for_status_code(200),
            },
        )


@pytest.fixture(scope="session")
def root_url(compose: DockerCompose) -> str:
    """Return the origin root URL for the application."""
    port = compose.get_service_port("aurelius-atlas-webapp", 8080)
    return f"https://localhost:{port}/"


@pytest.fixture(scope="session")
def base_url(root_url: str) -> str:
    """Return the en-US app URL for the application."""
    return f"{root_url}en-US/"


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
