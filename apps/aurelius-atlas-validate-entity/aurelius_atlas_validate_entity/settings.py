"""The app's settings, read once at start-up from the environment (VE-05, DD-197)."""

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, FilePath, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_VALIDATE_ENTITY_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_PORT = 21003
"""The app's port: the third auxiliary API, above lineage-model's 21002."""

DEFAULT_SERVER_URL = "https://localhost:21000"
"""The dev Atlas server: what ``nx serve`` of the server publishes, where the rules read runs in dev."""

DEFAULT_MINT_URL = "https://keycloak.localhost:8443/realms/master/protocol/openid-connect/token"
"""The dev issuer's token endpoint: the TLS :8443 listener every producer mints at (DD-113)."""

DEFAULT_SERVER_CLIENT_ID = "aurelius-atlas-validate-entity"
"""The Keycloak client the app signs in as (VEV-04, DD-499): its own service identity."""

DEFAULT_RULES_CACHE_SECONDS = 60.0
"""How long the read rule set is held (VEV-05): the editor's draft rides live; the rules do not."""

DEFAULT_BREAKER_FAIL_MAX = 5
"""Outages that open the catalogue circuit; the auth library's issuer-breaker default (AUX-02)."""

DEFAULT_BREAKER_RESET_TIMEOUT_SECONDS = 60.0
"""Seconds an open circuit stays open before its half-open trial call (LM-14's shape)."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels both uvicorn and the OTel console accept."""

TLS_PAIR_ERROR = (
    f"{ENV_PREFIX}TLS_CERT_FILE and {ENV_PREFIX}TLS_KEY_FILE must both be set, or both be unset, to configure TLS"
)


class ValidateEntitySettings(BaseSettings):
    """How the app runs, who issues its tokens, where its telemetry goes, and whom it asks for rules.

    Since 12.7 the app has one upstream — the catalogue server the governance
    rules are read from (VEV-03) — and one identity of its own to ask with
    (VEV-04, DD-499). The dev defaults point at what ``nx serve`` runs; every
    deployed environment sets its own values.
    """

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
    """The issuer root (Keycloak), which the app's tokens are verified against (VE-03)."""

    auth_realm: str = "master"
    """The realm the tokens are issued from."""

    auth_audience: str = "aurelius-atlas-validate-entity"
    """The accepted ``azp``/``aud`` value — this app's Keycloak client id (AUX-04, AUX-05);
    the dev deployment sets the webapp's ``aurelius``, whose tokens the browser sends."""

    auth_ca_file: FilePath | None = None
    """PEM CA verifying the issuer's TLS; unset uses the system trust store."""

    server_base_url: HttpUrl = DEFAULT_SERVER_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The catalogue server whose search answers the governance rules (VEV-03): the upstream
    this app grew at 12.7; a setting, never a hardcoded host (DV-69's sibling)."""

    token_url: HttpUrl = DEFAULT_MINT_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The issuer's token endpoint the app's own identity mints at (VEV-04, DD-499): the same
    :8443 listener every producer mints at (DD-113)."""

    server_client_id: str = DEFAULT_SERVER_CLIENT_ID
    """The Keycloak client the app signs in as (VEV-04, DD-499): its service account holds
    ``atlas-read``, and its token — never the caller's — rides every catalogue read."""

    server_client_secret: SecretStr | None = None
    """The secret of ``server_client_id``; never shown in logs. Unset keeps the leg closed:
    ``POST /`` answers 502, never a no-rules verdict (VEV-06)."""

    rules_cache_seconds: float = Field(default=DEFAULT_RULES_CACHE_SECONDS, ge=0)
    """How long the read rule set is cached in process (VEV-05): 0 reads on every call."""

    breaker_fail_max: int = Field(default=DEFAULT_BREAKER_FAIL_MAX, ge=1)
    """The catalogue outages that open the circuit (VEV-06): 5xx answers and transport failures
    count, 4xx answers are facts (the auth library's JWKS breaker shape, AUX-02)."""

    breaker_reset_timeout: float = Field(default=DEFAULT_BREAKER_RESET_TIMEOUT_SECONDS, gt=0)
    """Seconds an open circuit stays open before its half-open trial call (LM-14's shape)."""

    otel_token_url: HttpUrl | None = None
    """The issuer's token endpoint for the OTLP ingest credential (DD-196, DD-197): with
    ``otel_client_secret`` set, the app exports OTLP through its own pipeline; unset, it
    exports no OTLP (console only)."""

    otel_client_id: str = "otel-validate-entity"
    """The ingest realm client the app mints for (DD-197)."""

    otel_client_secret: SecretStr | None = None
    """The secret of ``otel_client_id``; never shown in logs."""

    otel_endpoint: str = "https://localhost:4319"
    """The collector's per-service-leg HTTP base for the OTLP export (DD-196)."""

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
