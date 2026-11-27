"""The app's settings, read once at start-up from the environment (MCP-16, DD-197, DD-887)."""

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, FilePath, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_MCP_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_PORT = 21005
"""The app's port: above the embedder's 21004, in the auxiliary band (DD-887)."""

DEFAULT_SERVER_URL = "https://localhost:21000"
"""The dev Atlas server: what ``nx serve`` of the server publishes, where every tool's read runs."""

DEFAULT_VALIDATE_ENTITY_URL = "https://localhost:21003"
"""The dev validate-entity API: where the verdicts tool's call runs (MCP-12)."""

DEFAULT_WRITE_ROLE = "atlas-write"
"""The role a write tool requires (MCP-11): the webapp's own write role, kept as one name (ADR 017)."""

DEFAULT_WRITE_ROLE_CLIENT = "aurelius-atlas-server"
"""The client whose ``resource_access`` entry carries the write role (MCP-28, DD-898):
the catalogue's client, because Keycloak namespaces client roles per client and
``atlas-write`` is the catalogue client's role — the same client the webapp's editor
gate reads and the server enforces (AUZ-01, DD-300)."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels both uvicorn and the console accept."""

TLS_PAIR_ERROR = (
    f"{ENV_PREFIX}TLS_CERT_FILE and {ENV_PREFIX}TLS_KEY_FILE must both be set, or both be unset, to configure TLS"
)


class McpSettings(BaseSettings):
    """How the app runs, who issues its tokens, and where its two upstreams are.

    The app is a protocol adapter (DD-887): it holds no catalogue of its own, so its
    settings are only the listen surface, the issuer the caller's token verifies
    against, and the two catalogue services the tools forward to. There is no
    service identity here — the caller's token is the only credential that ever
    travels upstream (MCP-03, DD-890).
    """

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    host: str = "localhost"
    """The interface to listen on; the container image sets ``0.0.0.0``."""

    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    """The port to listen on."""

    log_level: LogLevel = "info"
    """The lowest level of log record the app emits."""

    tls_cert_file: FilePath | None = None
    """PEM certificate to serve HTTPS with; requires ``tls_key_file``."""

    tls_key_file: FilePath | None = None
    """PEM private key of ``tls_cert_file``."""

    auth_server_url: HttpUrl
    """The issuer root (Keycloak), which the caller's token verifies against (MCP-02)."""

    auth_realm: str = "master"
    """The realm the tokens are issued from."""

    auth_audience: str = "aurelius"
    """The accepted ``azp``/``aud`` value (AUX-04): in dev the webapp's client, whose tokens the
    agent's minted token carries; a deployed cluster names this app's own client."""

    auth_ca_file: FilePath | None = None
    """PEM CA verifying the issuer's TLS; unset uses the system trust store."""

    write_role: str = DEFAULT_WRITE_ROLE
    """The role a write tool requires (MCP-11); empty disables the gate, the development-only posture
    the shared auth library keeps (its ``write_role`` rule, ADR 017)."""

    write_role_client: str = DEFAULT_WRITE_ROLE_CLIENT
    """The client entry of ``resource_access`` the write role is read from (MCP-28, DD-898). It is
    the catalogue's client, not this app's audience: a browser token of the public ``aurelius``
    client carries ``atlas-write`` under ``aurelius-atlas-server``, the same claim the server's
    own gate enforces on the forwarded token."""

    server_base_url: HttpUrl = DEFAULT_SERVER_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The catalogue server every discovery, read, write and typedef tool forwards to (MCP-03)."""

    validate_entity_base_url: HttpUrl = (  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
        DEFAULT_VALIDATE_ENTITY_URL
    )
    """The validate-entity API the verdicts tool forwards to (MCP-12)."""

    upstream_timeout_seconds: float = Field(default=10.0, gt=0)
    """How long a catalogue call may take before the relay gives up on it."""

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
