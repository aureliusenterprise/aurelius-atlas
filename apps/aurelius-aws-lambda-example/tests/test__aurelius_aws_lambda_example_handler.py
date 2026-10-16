from typing import Any
from unittest.mock import Mock, patch

import pytest
from aurelius_aws_lambda_example import handler
from aurelius_aws_lambda_example.models import Settings
from pydantic import HttpUrl, SecretStr, TypeAdapter

# The realm's real token endpoint; the validator test builds a real Settings
# around it, and only the (missing) credentials matter.
OIDC_ENDPOINT = "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token"
# Same fixture secret as conftest's OAuth scenario; never used against a real IdP.
FAKE_CLIENT_SECRET = "not-a-real-secret"  # noqa: S105  # test fixture value, never used against a real IdP


def test__initialize_without_ca_file_uses_plaintext_config(settings_plaintext: Mock) -> None:
    """Without a CA bundle neither the registry nor the producer gets TLS options."""
    with (
        patch.object(handler, "Settings", return_value=settings_plaintext),
        patch.object(handler, "SchemaRegistryClient"),
        patch.object(handler, "Producer") as producer_class,
    ):
        _, _, _, producer = handler.initialize()

    (producer_config,), _ = producer_class.call_args
    assert producer_config == {"bootstrap.servers": settings_plaintext.kafka_bootstrap_servers}
    assert "security.protocol" not in producer_config
    assert producer is producer_class.return_value


def test__initialize_with_ca_file_configures_registry_and_producer_tls(settings_tls: Mock) -> None:
    """A configured CA bundle is passed to the registry and merged into the producer."""
    settings = settings_tls

    with (
        patch.object(handler, "Settings", return_value=settings),
        patch.object(handler, "SchemaRegistryClient") as registry_client,
        patch.object(handler, "Producer") as producer_class,
    ):
        handler.initialize()

    (registry_config,), _ = registry_client.call_args
    assert registry_config["url"] == str(settings.schema_registry_url)
    assert registry_config["ssl.ca.location"] == "/certs/ca.pem"

    (producer_config,), _ = producer_class.call_args
    assert producer_config["bootstrap.servers"] == settings.kafka_bootstrap_servers
    assert producer_config["security.protocol"] == "SSL"
    assert producer_config["ssl.ca.location"] == "/certs/ca.pem"
    assert producer_config["ssl.endpoint.identification.algorithm"] == "https"


def test__initialize_warns_in_development_mode(settings_scenario: Mock) -> None:
    """Development mode is flagged in the log after successful initialization."""
    settings = settings_scenario(environment="development", is_development=True)

    with (
        patch.object(handler, "Settings", return_value=settings),
        patch.object(handler, "SchemaRegistryClient"),
        patch.object(handler, "Producer"),
        patch.object(handler, "LOGGER") as logger,
    ):
        _, _, _, producer = handler.initialize()

    assert producer is not None
    logger.warning.assert_called_once()


def test__initialize_with_oauth_configures_sasl_ssl_producer(settings_oauth: Mock) -> None:
    """A configured token endpoint upgrades the producer to SASL_SSL/OAUTHBEARER."""
    settings = settings_oauth

    with (
        patch.object(handler, "Settings", return_value=settings),
        patch.object(handler, "SchemaRegistryClient"),
        patch.object(handler, "Producer") as producer_class,
    ):
        handler.initialize()

    (producer_config,), _ = producer_class.call_args
    assert producer_config["security.protocol"] == "SASL_SSL"
    assert producer_config["sasl.mechanism"] == "OAUTHBEARER"
    assert producer_config["sasl.oauthbearer.method"] == "oidc"
    assert producer_config["sasl.oauthbearer.token.endpoint.url"] == settings.kafka_oauth_token_endpoint_url
    assert producer_config["sasl.oauthbearer.client.credentials.client.id"] == "kafka-lambda"
    # The producer receives the unwrapped secret; the settings object keeps it masked.
    assert producer_config["sasl.oauthbearer.client.credentials.client.secret"] == FAKE_CLIENT_SECRET
    # The token endpoint (HTTPS) is verified against the same CA as the broker.
    assert producer_config["https.ca.location"] == "/certs/ca.pem"
    assert producer_config["ssl.ca.location"] == "/certs/ca.pem"


@pytest.mark.parametrize(
    "overrides",
    [
        # Endpoint without credentials.
        {"kafka_oauth_token_endpoint_url": OIDC_ENDPOINT},
        # Endpoint and id, no secret.
        {"kafka_oauth_token_endpoint_url": OIDC_ENDPOINT, "kafka_oauth_client_id": "kafka-lambda"},
        # Credentials without endpoint: initialize() would silently build a
        # non-OAuth producer config instead of failing.
        {"kafka_oauth_client_id": "kafka-lambda", "kafka_oauth_client_secret": SecretStr(FAKE_CLIENT_SECRET)},
        # Client id alone.
        {"kafka_oauth_client_id": "kafka-lambda"},
    ],
    ids=["endpoint-only", "endpoint-and-id", "credentials-without-endpoint", "id-only"],
)
def test__settings_reject_partial_oauth_configuration(overrides: dict[str, Any]) -> None:
    """Every partial combination of the OAuth trio is rejected (all-or-none)."""
    # Every OAuth field starts from an explicit empty: Nx injects the project
    # .env into the task environment, which carries real values for them -- a
    # field left implicit would be filled from there and complete the trio.
    # The scenario then overrides exactly the partial subset under test.
    kwargs: dict[str, Any] = {
        "aws_region": "eu-central-1",
        "kafka_bootstrap_servers": "localhost:9092",
        "kafka_topic_name": "entities",
        "schema_registry_url": TypeAdapter(HttpUrl).validate_python("http://localhost:8081"),
        "kafka_oauth_token_endpoint_url": "",
        "kafka_oauth_client_id": "",
        "kafka_oauth_client_secret": SecretStr(""),
    }
    kwargs.update(overrides)

    with pytest.raises(ValueError, match="must all be set together"):
        Settings(**kwargs)


def test__settings_reject_insecure_token_endpoint() -> None:
    """A configured token endpoint must use https: the grant posts the client secret to it."""
    with pytest.raises(
        ValueError,
        match="must use https://",
    ):
        Settings(
            aws_region="eu-central-1",
            kafka_bootstrap_servers="localhost:9092",
            kafka_topic_name="entities",
            schema_registry_url=TypeAdapter(HttpUrl).validate_python("http://localhost:8081"),
            kafka_oauth_token_endpoint_url="http://keycloak.localhost:8080/realms/kafka/protocol/openid-connect/token",  # noqa: S106  # inert URL fixture, rejected by the code under test
            kafka_oauth_client_id="kafka-lambda",
            kafka_oauth_client_secret=SecretStr(FAKE_CLIENT_SECRET),
        )


def test__settings_secret_never_appears_in_str_or_repr() -> None:
    """initialize() logs Settings at DEBUG; the OAuth secret must stay masked there."""
    settings = Settings(
        aws_region="eu-central-1",
        kafka_bootstrap_servers="localhost:9092",
        kafka_oauth_client_id="kafka-lambda",
        kafka_oauth_client_secret=SecretStr(FAKE_CLIENT_SECRET),
        kafka_oauth_token_endpoint_url=OIDC_ENDPOINT,
        kafka_topic_name="entities",
        schema_registry_url=TypeAdapter(HttpUrl).validate_python("http://localhost:8081"),
    )

    assert FAKE_CLIENT_SECRET not in str(settings)
    assert FAKE_CLIENT_SECRET not in repr(settings)
