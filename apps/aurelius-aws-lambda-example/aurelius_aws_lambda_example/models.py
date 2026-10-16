from typing import Literal, Self

from pydantic import AliasChoices, Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

type Environment = Literal["development", "production"]


class Settings(BaseSettings):
    """Settings for the application."""

    # Namespace for this application's environment variables (see the FastAPI app's
    # Settings for the rationale). aws_region is the one exception: it keeps the
    # standard AWS_REGION name because the boto3/AWS SDK credential chain and the
    # MSK IAM signer (aurelius_kafka.msk) read the same variable — a prefixed
    # duplicate would create two sources of truth for one value.
    model_config = SettingsConfigDict(env_prefix="AURELIUS_LAMBDA_")

    aws_region: str = Field(
        # AliasChoices keeps this lookup alias-only: a bare validation_alias plus
        # populate_by_name would ALSO read the prefixed name, which would let two
        # variables configure one value. The second choice binds ``aws_region=``
        # init kwargs (e.g. in tests); env lookup matches both case-insensitively
        # to the standard AWS_REGION variable only.
        validation_alias=AliasChoices("AWS_REGION", "aws_region"),
        description="AWS region for the application.",
    )

    environment: Environment = Field(
        default="production",
        description="The environment the application is running in.",
    )

    kafka_bootstrap_servers: str = Field(
        description="Comma-separated list of Kafka brokers to connect to.",
    )

    kafka_ca_file: str = Field(
        default="",
        description=(
            "PEM CA bundle used to verify the Kafka broker and Schema Registry over TLS. "
            "Empty uses the operating system default trust store."
        ),
    )

    kafka_topic_name: str = Field(
        description="Name of the Kafka topic to produce messages to.",
    )

    kafka_oauth_token_endpoint_url: str = Field(
        default="",
        description=(
            "OIDC token endpoint used to fetch OAUTHBEARER tokens for the Kafka broker. "
            "Empty means the broker is reached without SASL (e.g. mTLS or plaintext)."
        ),
    )

    kafka_oauth_client_id: str = Field(
        default="",
        description="Keycloak client id for the OAuth client-credentials grant.",
    )

    kafka_oauth_client_secret: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "Keycloak client secret for the OAuth client-credentials grant. "
            "A SecretStr so repr/str (and therefore logging) never leak it; "
            "callers unwrap with get_secret_value()."
        ),
    )

    log_level: str = Field(
        default="INFO",
        description="Minimum log level to display at runtime.",
    )

    schema_registry_url: HttpUrl = Field(
        description="URL of the schema registry.",
    )

    @model_validator(mode="after")
    def _require_oauth_credentials(self) -> Self:
        """Reject any partial OAuth configuration (all-or-none).

        Validating only "endpoint set, credentials missing" would let
        credentials without an endpoint through, after which initialize()
        silently builds a non-OAuth producer config.
        """
        # .get_secret_value(): a SecretStr instance is truthy even when empty.
        present = [
            bool(self.kafka_oauth_token_endpoint_url),
            bool(self.kafka_oauth_client_id),
            bool(self.kafka_oauth_client_secret.get_secret_value()),
        ]
        if 0 < sum(present) < len(present):
            message = (
                "kafka_oauth_token_endpoint_url, kafka_oauth_client_id and "
                "kafka_oauth_client_secret must all be set together"
            )
            raise ValueError(message)
        return self

    @field_validator("kafka_oauth_token_endpoint_url")
    @classmethod
    def _require_https_token_endpoint(cls, value: str) -> str:
        """Require https for a configured token endpoint (empty = no OAuth).

        The client-credentials grant posts the client secret to this endpoint;
        over plain http the secret travels in cleartext. HttpUrl is not used
        as the field type because the empty string is the "OAuth disabled"
        sentinel, but scheme enforcement matches what HttpUrl would give.
        """
        if value and not value.startswith("https://"):
            message = "kafka_oauth_token_endpoint_url must use https:// (client credentials are posted to it)"
            raise ValueError(message)
        return value

    @property
    def is_development(self) -> bool:
        """Check if the application is running in a development environment."""
        return self.environment == "development"
