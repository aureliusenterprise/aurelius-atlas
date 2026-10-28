"""The server's settings, read once at start-up from the environment (SRV-01, SRV-03, SRV-06)."""

from pathlib import Path
from typing import Literal

from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_store_es import StoreSettings
from pydantic import DirectoryPath, Field, FilePath, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_SERVER_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_PORT = 21000
"""The port Apache Atlas listens on."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels both uvicorn and the OTel console accept."""


class ServerSettings(BaseSettings):
    """How the server runs and where its store is."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    host: str = "localhost"
    """The interface to listen on; the container image sets ``0.0.0.0``."""

    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    """The port to listen on (SRV-03)."""

    log_level: LogLevel = "info"
    """The lowest level of log record the server and uvicorn emit."""

    tls_cert_file: FilePath
    """PEM certificate to serve HTTPS with (SRV-06, DD-234): required — the server never serves plaintext,
    the way the store's password is required (SRV-01, SRV-02)."""

    tls_key_file: FilePath
    """PEM private key of ``tls_cert_file`` (SRV-06)."""

    hsts_enabled: bool = True
    """Whether responses carry ``Strict-Transport-Security`` (SRV-08, DD-236). The image ships True; the dev
    arrangement turns it off so a browser that visited the mkcert server is not pinned to HTTPS on the
    plaintext dev surfaces (ADR 039's named relaxations)."""

    dashboard_dir: DirectoryPath | None = None
    """The built dashboards: ``dashboardv2`` at its root and ``dashboardv3`` in ``n/``; None serves the API only
    (DSH-04)."""

    models_dir: Path = BUILTIN_MODELS_DIR
    """The models loaded at start-up: by default ``addons/models`` of Apache Atlas 2.4.0; a missing directory loads
    none (MDL-01, MDL-16, DD-032)."""

    typedef_refresh_seconds: float = Field(default=5.0, ge=0)
    """How long the server answers from its type registry before it checks for another process's type change
    (TDS-13, DD-029)."""

    delete_type: Literal["soft", "hard"] = "soft"
    """How entities are deleted unless a request chooses: ``atlas.DeleteHandlerV1.impl`` (EDL-04, DD-059)."""

    delete_type_override: bool = False
    """Whether a request's ``deleteType`` chooses: ``atlas.rest.enable.delete.type.override`` (EDL-04, DD-059)."""

    tasks_enabled: bool = True
    """Whether propagation is deferred to tasks a worker runs after the request: ``atlas.tasks.enabled`` (TSK-02,
    DD-081)."""

    task_poll_seconds: float = Field(default=10.0, gt=0)
    """How often the worker looks for tasks other processes recorded or left behind (DD-080)."""

    revision: str = "UNKNOWN"
    """The source revision the server was built from, reported by ``admin/version`` (ADM-01)."""

    elasticsearch_hosts: list[HttpUrl] = Field(min_length=1)
    """Base URLs of the Elasticsearch nodes, as a JSON list: ``["https://localhost:9200"]``."""

    elasticsearch_username: str = "elastic"
    """User for the store."""

    elasticsearch_password: SecretStr
    """Password for the store; never shown in logs."""

    elasticsearch_ca_certs: FilePath
    """PEM file with the certificate authority of the Elasticsearch server certificate."""

    otel_token_url: HttpUrl | None = None
    """The issuer's token endpoint for the OTLP ingest credential (7.18,
    DD-196): with ``otel_client_secret`` set, the server exports OTLP through
    the app-owned pipeline (the collector's per-service leg accepts only
    client-credentials JWTs); unset, the server exports no OTLP (console
    only). The OTel env vars (``OTEL_EXPORTER_OTLP_*``) are deliberately not
    read: the 60s dev token cannot ride a static header (DD-196)."""

    otel_client_id: str = "otel-atlas-server"
    """The ingest realm client the server mints for (7.18, DD-196)."""

    otel_client_secret: SecretStr | None = None
    """The secret of ``otel_client_id``; never shown in logs."""

    otel_endpoint: str = "https://localhost:4319"
    """The collector's per-service-leg HTTP base for the OTLP export
    (7.18, DD-196); the dev compose overrides with the service DNS name."""

    otel_ca_file: FilePath | None = None
    """PEM CA verifying the collector's TLS for the OTLP export; unset uses
    the system trust store (the dev stack's mkcert CA is not system-wide)."""

    @property
    def tls(self) -> tuple[Path, Path]:
        """The certificate and key to serve HTTPS with (SRV-03, SRV-06, DD-234)."""
        return Path(self.tls_cert_file), Path(self.tls_key_file)

    def store_settings(self) -> StoreSettings:
        """The settings of the Elasticsearch store."""
        return StoreSettings(
            hosts=self.elasticsearch_hosts,
            username=self.elasticsearch_username,
            password=self.elasticsearch_password,
            ca_certs=self.elasticsearch_ca_certs,
        )
