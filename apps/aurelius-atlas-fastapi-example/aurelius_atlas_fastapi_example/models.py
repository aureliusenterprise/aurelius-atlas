from collections.abc import Hashable, Sequence
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from aurelius_atlas_sdk.postgresql import sanitize_tsquery
from pydantic import BaseModel, Field, HttpUrl, NonNegativeInt, PositiveInt, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

DEVELOPMENT = "development"

type LogLevel = Literal["trace", "debug", "info", "notice", "warn", "warning", "error", "fatal"]
"""The lowest level of log record the app emits (the set the logfire shell accepted, DD-121)."""

# libpq sslmode values that do not verify the server certificate; unusable outside development.
_UNVERIFIED_SSLMODES = ("disable", "allow", "prefer")

# Namespace for this application's environment variables. Every Settings field is read
# from ``AURELIUS_ATLAS_FASTAPI_<FIELD>`` so configuration from other projects in the
# workspace (or a developer's shell) can never populate this application's fields.
ENV_PREFIX = "AURELIUS_ATLAS_FASTAPI_"


class Envelope[T: BaseModel | None](BaseModel):
    """A generic envelope model that wraps a value with a unique identifier."""

    guid: UUID = Field(
        description="The unique identifier for the value contained in the envelope.",
    )

    op: Literal["INSERT", "UPDATE", "DELETE"] = Field(
        description="The operation type for the envelope.",
    )

    timestamp: datetime = Field(
        description="The timestamp when the envelope was created with timezone information.",
        default_factory=lambda: datetime.now(tz=UTC),
    )

    value: T | None = Field(
        description="The value contained in the envelope.",
    )


class PaginatedResponse[T: BaseModel](BaseModel):
    """A generic paginated response model that wraps paginated data with total count."""

    data: Sequence[T] = Field(
        description="The paginated results.",
    )

    total: int = Field(
        description="The total number of items matching the query filter, ignoring pagination.",
    )


class PaginationQueryParams(BaseModel):
    """Query parameters for pagination."""

    skip: NonNegativeInt = Field(
        default=0,
        description="Number of items to skip for pagination.",
    )

    limit: PositiveInt = Field(
        default=100,
        description="Maximum number of items to return per page.",
        le=1000,
    )


class FindAllQueryParams(PaginationQueryParams):
    """Query parameters for the find all endpoint."""

    search: str | None = Field(
        default=None,
        description="Optional search query to filter entities.",
    )

    @field_validator("search", mode="before")
    @classmethod
    def sanitize_search(cls, value: str | None) -> str | None:
        """
        Sanitize search query for PostgreSQL full-text search.

        Args:
            value: The raw search query string.

        Returns:
            Sanitized search query or None if input is empty/whitespace only.
        """
        return sanitize_tsquery(value)


class Settings(BaseSettings, Hashable):
    """Application configuration settings."""

    environment: str = Field(
        default="production",
        description="The environment in which the application is running. Set to 'development' for local testing.",
    )

    auth_fail_max: int = Field(
        default=5,
        description="The maximum number of failed authentication attempts before triggering the circuit breaker.",
    )

    auth_realm_name: str = Field(
        description="The name of the authentication realm.",
    )

    auth_reset_timeout: int = Field(
        default=60,
        description="The timeout in seconds to wait before resetting the authentication circuit breaker.",
    )

    db_fail_max: int = Field(
        default=5,
        description="The maximum number of failed database operations before triggering the circuit breaker.",
    )

    auth_client_id: str | None = Field(
        default=None,
        description="The client id this application authenticates as; seeds the default auth_audience.",
    )

    auth_server_url: HttpUrl = Field(
        description="The base URL of the authentication server.",
    )

    auth_audience: str = Field(
        default_factory=lambda settings: settings.get("auth_client_id") or "",
        description=(
            "The audience this API accepts: a token is authorized when this value appears in its 'azp' claim "
            "or 'aud' claim list. Defaults to AURELIUS_ATLAS_FASTAPI_AUTH_CLIENT_ID; required outside development mode."
        ),
    )

    auth_write_role: str = Field(
        default="",
        description=(
            "The role mutating endpoints (PUT/DELETE) require: accepted when it appears in the token's "
            "'realm_access.roles' or in the 'resource_access.<auth_audience>.roles' list (client roles are "
            "namespaced per client; roles of other clients never satisfy the gate). Empty disables the "
            "authorization check; required outside development mode so a deployment cannot ship "
            "authentication without authorization by forgetting the variable."
        ),
    )

    auto_create_schema: bool = Field(
        default_factory=lambda settings: settings.get("environment") == DEVELOPMENT,
        description="Automatically create the database schema. Enabled by default in development mode.",
    )

    cdc_disconnect_poll_timeout: float = Field(
        default=5.0,
        description=(
            "The timeout in seconds to wait for SSE notifications before "
            "re-checking whether the client has disconnected."
        ),
    )

    cdc_shutdown_join_timeout: float = Field(
        default=2.0,
        description="The timeout in seconds to wait for the CDC polling thread to stop during shutdown.",
    )

    cdc_subscriber_queue_maxsize: int = Field(
        default=1000,
        description="The maximum number of buffered CDC notifications per SSE subscriber queue.",
    )

    db_reset_timeout: int = Field(
        default=60,
        description="The timeout in seconds to wait before resetting the database circuit breaker.",
    )

    database_driver: str = Field(
        default="postgresql+psycopg",
        description="The driver for the database.",
    )

    database_host: str = Field(
        default="localhost",
        description="The host for the database.",
    )

    database_name: str = Field(
        default="postgres",
        description="The name of the database.",
    )

    database_password: SecretStr = Field(
        description="The password for the database.",
    )

    database_port: int = Field(
        default=5432,
        description="The port for the database.",
    )

    database_username: str = Field(
        default="postgres",
        description="The username for the database.",
    )

    host: str = Field(
        default="127.0.0.1",
        description="The host to bind the server to.",
    )

    log_level: LogLevel = Field(
        default="info",
        description="The logging level for the application.",
    )

    port: int = Field(
        default=8000,
        description="The port to bind the server to.",
    )

    auth_ca_file: str = Field(
        default="",
        description=(
            "PEM CA bundle used to verify the authentication server's TLS certificate. "
            "Empty uses the operating system default trust store."
        ),
    )

    database_sslmode: str = Field(
        default="prefer",
        description=(
            "PostgreSQL TLS mode (disable, prefer, require, verify-ca, verify-full). "
            "The development defaults set verify-full to match the TLS-only database."
        ),
    )

    database_sslrootcert: str = Field(
        default="",
        description=(
            "PEM CA bundle used to verify the database server's TLS certificate. "
            "Required for verify-ca and verify-full; ignored by libpq otherwise."
        ),
    )

    tls_cert_file: str = Field(
        default="",
        description="PEM certificate served by the application. Empty disables TLS on the server.",
    )

    tls_key_file: str = Field(
        default="",
        description="PEM private key matching tls_cert_file. Required when TLS is enabled.",
    )

    @property
    def is_development(self) -> bool:
        """Check if the application is running in development mode."""
        return self.environment == DEVELOPMENT

    @model_validator(mode="after")
    def enforce_transport_security(self) -> Settings:
        """Fail fast when a non-development deployment runs with unverified transport.

        The defaults (``database_sslmode="prefer"``, empty ``tls_cert_file``) are
        convenient for local development, where the TLS material lives in the
        project ``.env``. Outside development they must be set explicitly:
        otherwise a deployment that forgets the variables silently downgrades to
        opportunistic/unverified TLS — credentials and tokens over a channel a
        network-path attacker can read or impersonate.
        """
        if self.is_development:
            return self

        if self.database_sslmode in _UNVERIFIED_SSLMODES:
            msg = (
                f"{ENV_PREFIX}DATABASE_SSLMODE={self.database_sslmode!r} does not verify the database server "
                "certificate. Set it to 'verify-ca' or 'verify-full' "
                f"(with {ENV_PREFIX}DATABASE_SSLROOTCERT) outside development mode."
            )
            raise ValueError(msg)
        if self.database_sslmode in ("verify-ca", "verify-full") and not self.database_sslrootcert:
            msg = (
                f"{ENV_PREFIX}DATABASE_SSLMODE={self.database_sslmode!r} requires {ENV_PREFIX}DATABASE_SSLROOTCERT "
                "with the CA bundle that issued the database certificate."
            )
            raise ValueError(msg)
        if not self.tls_cert_file or not self.tls_key_file:
            msg = (
                f"{ENV_PREFIX}TLS_CERT_FILE and {ENV_PREFIX}TLS_KEY_FILE are required outside development mode: "
                "the API serves bearer tokens and must not run on plain HTTP. "
                f"Set {ENV_PREFIX}ENVIRONMENT=development only for local stacks."
            )
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def enforce_auth_security(self) -> Settings:
        """Fail fast when a non-development deployment misconfigures authentication or authorization.

        Two silent-downgrade paths are closed here:

        * A plaintext ``auth_server_url`` lets a network-path attacker serve a forged
          OpenID configuration / JWKS, which mints tokens this API would accept — the
          whole bearer-token scheme collapses. OAuth token endpoints elsewhere in the
          workspace are https-only for the same reason.
        * An empty ``auth_audience`` (no ``AUTH_CLIENT_ID``, no explicit audience) would
          accept any token from the issuer, and an empty ``auth_write_role`` would
          authenticate every caller for mutating operations. Both must be explicit.
        """
        if self.is_development:
            return self

        if self.auth_server_url.scheme.lower() != "https":
            msg = (
                f"{ENV_PREFIX}AUTH_SERVER_URL must use https outside development mode "
                f"(got {self.auth_server_url.scheme!r}): JWKS/OIDC discovery over plaintext HTTP lets a "
                "network-path attacker forge tokens by serving its own keys."
            )
            raise ValueError(msg)
        if not self.auth_audience:
            msg = (
                f"{ENV_PREFIX}AUTH_AUDIENCE (or {ENV_PREFIX}AUTH_CLIENT_ID) is required outside development "
                "mode: without an audience this API accepts any token issued by the auth server."
            )
            raise ValueError(msg)
        if not self.auth_write_role:
            msg = (
                f"{ENV_PREFIX}AUTH_WRITE_ROLE is required outside development mode: without a required "
                "role, every authenticated principal may write and delete entities."
            )
            raise ValueError(msg)

        return self

    @property
    def database_url(self) -> URL:
        """Construct the database URL."""
        query: dict[str, str] = {"sslmode": self.database_sslmode}
        if self.database_sslrootcert:
            query["sslrootcert"] = self.database_sslrootcert
        return URL.create(
            drivername=self.database_driver,
            username=self.database_username,
            password=self.database_password.get_secret_value(),
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
            query=query,
        )

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        frozen=True,
    )
