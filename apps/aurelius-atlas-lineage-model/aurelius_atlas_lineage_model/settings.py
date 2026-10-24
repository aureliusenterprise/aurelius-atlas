"""The app's settings, read once at start-up from the environment (LM-10, DD-108)."""

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, FilePath, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_LINEAGE_MODEL_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_PORT = 21002
"""The app's port: the second auxiliary API, above data2model's 21001."""

DEFAULT_BREAKER_FAIL_MAX = 5
"""Outages that open an upstream circuit; the auth library's issuer-breaker default (AUX-02)."""

DEFAULT_BREAKER_RESET_TIMEOUT_SECONDS = 60.0
"""Seconds an open circuit stays open before its half-open trial; the auth library's default."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels both uvicorn and the OTel console accept."""

TLS_PAIR_ERROR = (
    f"{ENV_PREFIX}TLS_CERT_FILE and {ENV_PREFIX}TLS_KEY_FILE must both be set, or both be unset, to configure TLS"
)


class LineageModelSettings(BaseSettings):
    """How the app runs, who issues its tokens, where its telemetry goes, and what it proxies."""

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
    """The issuer root (Keycloak), which the app's tokens are verified against (LM-08)."""

    auth_realm: str = "master"
    """The realm the tokens are issued from."""

    auth_audience: str = "aurelius-atlas-lineage-model"
    """The accepted ``azp``/``aud`` value — this app's Keycloak client id (AUX-04, AUX-05);
    the dev deployment sets the webapp's ``aurelius``, whose tokens the chain forwards."""

    auth_ca_file: FilePath | None = None
    """PEM CA verifying the issuer's TLS; unset uses the system trust store."""

    atlas_base_url: HttpUrl
    """The Atlas metadata API whose ``v2/lineage`` feed is flattened (DV-16: a setting,
    not a hardcoded host; the server's feed is increment 5.1)."""

    data2model_url: HttpUrl
    """The data2model API (8.1) the flattened rows and fixed rules are POSTed to (LM-04)."""

    breaker_fail_max: int = Field(default=DEFAULT_BREAKER_FAIL_MAX, ge=1)
    """The upstream outages that open a circuit (LM-15, LM-13): 5xx answers and transport
    failures count, 4xx answers are facts (the auth library's JWKS breaker shape, AUX-02)."""

    breaker_reset_timeout: float = Field(default=DEFAULT_BREAKER_RESET_TIMEOUT_SECONDS, gt=0)
    """Seconds an open circuit stays open before its half-open trial call (LM-14, LM-15)."""

    otel_token_url: HttpUrl | None = None
    """The issuer's token endpoint for the OTLP ingest credential (DD-107, DD-108): with
    ``otel_client_secret`` set, the app exports OTLP through its own pipeline; unset, it
    exports no OTLP (console only)."""

    otel_client_id: str = "otel-lineage-model"
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
