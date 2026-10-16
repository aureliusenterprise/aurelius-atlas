from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

import pytest
from aurelius_aws_lambda_example import handler
from aurelius_aws_lambda_example.models import Settings
from pydantic import HttpUrl, SecretStr, TypeAdapter

OIDC_ENDPOINT = "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token"
FAKE_CLIENT_SECRET = "not-a-real-secret"  # noqa: S105  # test fixture value, never used against a real IdP


def _make_settings(**overrides: Any) -> Mock:  # noqa: ANN401
    """Return a spec'd Settings mock for a scenario, defaulted to a plaintext broker.

    Mocks never read the environment, so tests are deterministic whatever the
    developer's or CI's ambient configuration says (Nx injects the project `.env`
    into every task's environment). `spec=Settings` keeps the mock honest: an
    attribute the model does not have raises AttributeError, as does one the
    scenario left unset — so a field the app starts to depend on surfaces as a
    loud failure here rather than a silently truthy child mock.
    """
    scenario: dict[str, Any] = {
        "aws_region": "eu-central-1",
        "environment": "production",
        "is_development": False,
        "kafka_bootstrap_servers": "localhost:9092",
        "kafka_ca_file": "",
        "kafka_oauth_client_id": "",
        # A real SecretStr, as the model holds: the handler unwraps it with
        # get_secret_value(), which a bare str would not survive.
        "kafka_oauth_client_secret": SecretStr(""),
        "kafka_oauth_token_endpoint_url": "",
        "kafka_topic_name": "entities",
        "log_level": "INFO",
        # A real HttpUrl, as production would hold: the handler str()-converts it.
        "schema_registry_url": TypeAdapter(HttpUrl).validate_python("http://localhost:8081"),
    }
    scenario.update(overrides)
    return Mock(spec=Settings, **scenario)


@pytest.fixture(autouse=True)
def _clear_initialize_cache() -> None:
    """initialize() is cached; clear it so each test sees fresh settings."""
    handler.initialize.cache_clear()


@pytest.fixture
def settings_scenario() -> Callable[..., Mock]:
    """Return the scenario factory for settings combinations without a named fixture."""
    return _make_settings


@pytest.fixture
def settings_plaintext() -> Mock:
    """A broker reached without TLS or SASL."""
    return _make_settings()


@pytest.fixture
def settings_tls() -> Mock:
    """A broker reached over TLS, verified against a CA bundle."""
    return _make_settings(kafka_ca_file="/certs/ca.pem")


@pytest.fixture
def settings_oauth() -> Mock:
    """A broker reached over SASL_SSL with OAUTHBEARER client credentials."""
    return _make_settings(
        kafka_ca_file="/certs/ca.pem",
        kafka_oauth_client_id="kafka-lambda",
        kafka_oauth_client_secret=SecretStr(FAKE_CLIENT_SECRET),
        kafka_oauth_token_endpoint_url=OIDC_ENDPOINT,
    )
