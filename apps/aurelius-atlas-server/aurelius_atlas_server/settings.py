"""The server's settings, read once at start-up from the environment (SRV-01, SRV-03)."""

from pathlib import Path
from typing import Literal, Self

from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_store_es import StoreSettings
from pydantic import DirectoryPath, Field, FilePath, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_SERVER_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_PORT = 21000
"""The port Apache Atlas listens on."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels both logfire and uvicorn know."""

TLS_PAIR_ERROR = (
    f"{ENV_PREFIX}TLS_CERT_FILE and {ENV_PREFIX}TLS_KEY_FILE must both be set, or both be unset, to configure TLS"
)


class ServerSettings(BaseSettings):
    """How the server runs and where its store is."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    host: str = "localhost"
    """The interface to listen on; the container image sets ``0.0.0.0``."""

    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    """The port to listen on (SRV-03)."""

    log_level: LogLevel = "info"
    """The lowest level of log record the server and uvicorn emit."""

    tls_cert_file: FilePath | None = None
    """PEM certificate to serve HTTPS with; requires ``tls_key_file`` (SRV-03)."""

    tls_key_file: FilePath | None = None
    """PEM private key of ``tls_cert_file``."""

    dashboard_dir: DirectoryPath | None = None
    """The built dashboards: ``dashboardv2`` at its root and ``dashboardv3`` in ``n/``; None serves the API only
    (DSH-04)."""

    models_dir: Path = BUILTIN_MODELS_DIR
    """The models loaded at start-up: by default ``addons/models`` of Apache Atlas 2.4.0; a missing directory loads
    none (MDL-01, MDL-16, DD-032)."""

    typedef_refresh_seconds: float = Field(default=5.0, ge=0)
    """How long the server answers from its type registry before it checks for another process's type change
    (TDS-13, DD-029)."""

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

    @model_validator(mode="after")
    def _tls_pair(self) -> Self:
        if (self.tls_cert_file is None) != (self.tls_key_file is None):
            raise ValueError(TLS_PAIR_ERROR)
        return self

    @property
    def tls(self) -> tuple[Path, Path] | None:
        """The certificate and key to serve HTTPS with, or None for plain HTTP."""
        if self.tls_cert_file is None or self.tls_key_file is None:
            return None
        return Path(self.tls_cert_file), Path(self.tls_key_file)

    def store_settings(self) -> StoreSettings:
        """The settings of the Elasticsearch store."""
        return StoreSettings(
            hosts=self.elasticsearch_hosts,
            username=self.elasticsearch_username,
            password=self.elasticsearch_password,
            ca_certs=self.elasticsearch_ca_certs,
        )
