"""The app's settings, read once at start-up from the environment (DTM-10, DD-108)."""

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, FilePath, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_DATA2MODEL_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_PORT = 21001
"""The app's port: the first auxiliary API, above the server's 21000."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels both logfire and uvicorn know."""

TLS_PAIR_ERROR = (
    f"{ENV_PREFIX}TLS_CERT_FILE and {ENV_PREFIX}TLS_KEY_FILE must both be set, or both be unset, to configure TLS"
)


class Data2ModelSettings(BaseSettings):
    """How the app runs, who issues its tokens, and where its telemetry goes."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    host: str = "localhost"
    """The interface to listen on; the container image sets ``0.0.0.0``."""

    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    """The port to listen on."""

    log_level: LogLevel = "info"
    """The lowest level of log record the app and uvicorn emit."""

    tls_cert_file: FilePath | None = None
    """PEM certificate to serve HTTPS with; requires ``tls_key_file``."""

    tls_key_file: FilePath | None = None
    """PEM private key of ``tls_cert_file``."""

    auth_server_url: HttpUrl
    """The issuer root (Keycloak), which the app's tokens are verified against (DTM-10)."""

    auth_realm: str = "master"
    """The realm the tokens are issued from."""

    auth_audience: str = "aurelius-atlas-data2model"
    """The accepted ``azp``/``aud`` value — this app's Keycloak client id (AUX-04, AUX-05)."""

    auth_ca_file: FilePath | None = None
    """PEM CA verifying the issuer's TLS; unset uses the system trust store."""

    otel_token_url: HttpUrl | None = None
    """The issuer's token endpoint for the OTLP ingest credential (DD-107, DD-108): with
    ``otel_client_secret`` set, the app exports OTLP through its own pipeline; unset, it
    exports no OTLP (console only)."""

    otel_client_id: str = "otel-data2model"
    """The ingest realm client the app mints for (DD-108)."""

    otel_client_secret: SecretStr | None = None
    """The secret of ``otel_client_id``; never shown in logs."""

    otel_endpoint: str = "https://localhost:4319"
    """The collector's per-service-leg HTTP base for the OTLP export (DD-107)."""

    otel_ca_file: FilePath | None = None
    """PEM CA verifying the collector's TLS for the OTLP export; unset uses the system trust store."""

    @model_validator(mode="after")
    def _tls_pair(self) -> Self:
        """TLS is configured by a pair, never by one half of it."""
        if (self.tls_cert_file is None) != (self.tls_key_file is None):
            raise ValueError(TLS_PAIR_ERROR)
        return self

    @property
    def tls(self) -> tuple[Path, Path] | None:
        """The certificate and key to serve HTTPS with, or None for plain HTTP."""
        if self.tls_cert_file is None or self.tls_key_file is None:
            return None
        return Path(self.tls_cert_file), Path(self.tls_key_file)
