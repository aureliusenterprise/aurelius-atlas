import pytest
from aurelius_kafka import oauth_client_config

OIDC_ENDPOINT = "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token"
FAKE_SECRET = "not-a-real-secret"  # noqa: S105  # test fixture value, never used against a real IdP


def test__oauth_client_config_rejects_insecure_token_endpoint() -> None:
    """A non-https token endpoint is rejected: the grant would post the secret in cleartext."""
    with pytest.raises(ValueError, match="must use https://"):
        oauth_client_config(
            token_endpoint_url="http://keycloak.localhost:8080/realms/kafka/protocol/openid-connect/token",  # noqa: S106  # inert URL fixture, rejected by the code under test
            client_id="kafka-producer",
            client_secret=FAKE_SECRET,
        )


def test__oauth_client_config() -> None:
    """Verify the OAUTHBEARER/OIDC client options are built as expected."""
    config = oauth_client_config(
        token_endpoint_url=OIDC_ENDPOINT,
        client_id="kafka-producer",
        client_secret=FAKE_SECRET,
        ca_location="/certs/ca.pem",
    )

    assert config == {
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "OAUTHBEARER",
        "sasl.oauthbearer.method": "oidc",
        "sasl.oauthbearer.token.endpoint.url": OIDC_ENDPOINT,
        "sasl.oauthbearer.client.credentials.client.id": "kafka-producer",
        "sasl.oauthbearer.client.credentials.client.secret": FAKE_SECRET,
        "ssl.ca.location": "/certs/ca.pem",
        "https.ca.location": "/certs/ca.pem",
        "ssl.endpoint.identification.algorithm": "https",
    }


def test__oauth_client_config_with_scope() -> None:
    """Verify an explicitly requested scope is added to the options."""
    config = oauth_client_config(
        token_endpoint_url=OIDC_ENDPOINT,
        client_id="kafka-e2e",
        client_secret=FAKE_SECRET,
        ca_location="/certs/ca.pem",
        scope="kafka-audience",
    )

    assert config["sasl.oauthbearer.scope"] == "kafka-audience"


def test__oauth_client_config_without_ca_uses_system_trust() -> None:
    """Without a CA bundle no CA options are emitted (system trust stores apply)."""
    config = oauth_client_config(
        token_endpoint_url=OIDC_ENDPOINT,
        client_id="kafka-producer",
        client_secret=FAKE_SECRET,
    )

    assert config["security.protocol"] == "SASL_SSL"
    assert "ssl.ca.location" not in config
    assert "https.ca.location" not in config


def test__oauth_client_config_merges_extra() -> None:
    """Verify extra options are merged into the OAuth client options."""
    config = oauth_client_config(
        token_endpoint_url=OIDC_ENDPOINT,
        client_id="kafka-producer",
        client_secret=FAKE_SECRET,
        ca_location="/certs/ca.pem",
        extra={"client.id": "test"},
    )

    assert config["client.id"] == "test"
    assert config["security.protocol"] == "SASL_SSL"
