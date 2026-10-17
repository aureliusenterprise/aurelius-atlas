from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, FilePath, HttpUrl, SecretStr, field_validator

HTTPS_ONLY_ERROR = "Elasticsearch hosts must use https; plain http is not supported"


class StoreSettings(BaseModel):
    """Connection settings for the Elasticsearch store.

    The application builds this object from its own configuration; the library never reads
    environment variables (STO-01). There is deliberately no setting that disables certificate
    verification (STO-02).
    """

    model_config = ConfigDict(frozen=True)

    hosts: list[HttpUrl] = Field(min_length=1)
    """Base URLs of the cluster nodes, e.g. ``https://localhost:9200``."""

    username: str = "elastic"
    """User for HTTP basic authentication."""

    password: SecretStr
    """Password for HTTP basic authentication; never shown in ``repr`` or logs (STO-08)."""

    ca_certs: FilePath
    """PEM file with the certificate authority that signed the server certificate."""

    request_timeout: float = Field(default=10.0, gt=0)
    """Seconds to wait for a single request before it counts as failed."""

    @field_validator("hosts")
    @classmethod
    def _require_https(cls, hosts: list[HttpUrl]) -> list[HttpUrl]:
        if any(host.scheme != "https" for host in hosts):
            raise ValueError(HTTPS_ONLY_ERROR)
        return hosts

    @property
    def host_urls(self) -> list[str]:
        """The hosts as plain strings, in the form the Elasticsearch client expects."""
        return [str(host).rstrip("/") for host in self.hosts]

    @property
    def ca_certs_path(self) -> Path:
        """The CA file as a path."""
        return Path(self.ca_certs)
