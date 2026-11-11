"""The app's settings, read once at start from the environment (12.2, DD-458, DD-459)."""

import json
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_QUALITY_SCANNER_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_MAX_ROWS = 1_000_000
"""The most rows one dataset's read returns (DQS-05): a memory bound, not a sampling choice."""

DEFAULT_SEARCH_LIMIT = 100
"""The page size of the rule search (DQS-02): the basic search's page, paged by marker to the end."""

DEFAULT_CLIENT_ID = "aurelius-atlas-quality-scanner"
"""The Keycloak client the job signs in as (DQS-10, DD-458): its own service identity."""

DEFAULT_SERVER_URL = "https://localhost:21000"
"""The dev Atlas server: what ``nx serve`` of the server publishes, where the scan runs in dev."""

DEFAULT_MINT_URL = "https://keycloak.localhost:8443/realms/master/protocol/openid-connect/token"
"""The dev issuer's token endpoint: the TLS :8443 listener every producer mints at (DD-113)."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels the app's logging accepts."""

SOURCE_MAP_ERROR = (
    f"{ENV_PREFIX}SOURCES must be a JSON array of source objects, each naming its dataset "
    '(by "qualifiedName" or "guid"), its "kind", and its "config": '
    '[{"dataset": {"qualifiedName": "/d3"}, "kind": "file", "config": {"path": "/data/d3.parquet"}}]'
)

DATASET_IDENTITY_ERROR = 'a "dataset" names exactly one of "qualifiedName" or "guid"'
"""The dataset identity rule: exactly one of the two, always (DQS-20)."""

DUPLICATE_SOURCE_ERROR = f"{ENV_PREFIX}SOURCES names one dataset twice"
"""Two sources for one dataset: the router would hold two answers for it (DQS-17)."""


class DatasetIdentity(BaseModel):
    """The catalogue dataset a source's rows belong to: named by qualified name, or by guid (DQS-20)."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    qualified_name: str | None = Field(default=None, alias="qualifiedName")
    """The dataset's qualified name — a label its owner can rename."""

    guid: str | None = None
    """The dataset's guid — the identity the catalogue never reissues, so a source keyed here survives a rename."""

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        """A dataset names exactly one of the two identities — never both, never neither (DQS-20)."""
        if (self.qualified_name is None) == (self.guid is None):
            raise ValueError(DATASET_IDENTITY_ERROR)
        return self

    def key(self) -> str:
        """The identity this source matches on: its guid when it has one, else its name (DQS-20)."""
        return self.guid if self.guid is not None else str(self.qualified_name)


class FileConfig(BaseModel):
    """The ``file`` kind's config: the extract path the operator named (DQS-17)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    """The extract's path. The map, never the dataset's name, is where a path comes from (DD-459)."""


KIND_CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {"file": FileConfig}
"""The settings' kind table: each kind's config schema (DD-462). A kind not here is accepted; the
router skips its datasets at scan time (DQS-18), so a newer map still runs on an older job."""


class SourceEntry(BaseModel):
    """One source: the dataset it belongs to, the reader kind, and that kind's config (DQS-17, 12.4a)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset: DatasetIdentity
    """The catalogue dataset these rows belong to, by name or guid (DQS-20)."""

    kind: str
    """The reader's name: ``file`` in this cut (DQS-18)."""

    config: dict[str, object]
    """The kind's own configuration, checked against its schema in :data:`KIND_CONFIG_SCHEMAS`."""

    @model_validator(mode="after")
    def _check_config(self) -> Self:
        """A known kind's config must satisfy that kind's schema; an unknown kind's config waits (DQS-18)."""
        schema = KIND_CONFIG_SCHEMAS.get(self.kind)
        if schema is not None:
            schema.model_validate(self.config)
        return self

    @property
    def keyed_by_guid(self) -> bool:
        """Whether this source names its dataset by guid (DQS-20)."""
        return self.dataset.guid is not None


class ScannerSettings(BaseSettings):
    """Where the catalogue is, who the job signs in as, which extracts it reads, and what bounds a scan."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    log_level: LogLevel = "info"
    """The lowest level of log record the job emits."""

    server_url: HttpUrl = DEFAULT_SERVER_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The Atlas metadata API the job reads rules from and writes scores to (DQS-10)."""

    token_url: HttpUrl = DEFAULT_MINT_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The issuer's token endpoint the job's client credentials are sent to (DQS-10)."""

    client_id: str = DEFAULT_CLIENT_ID
    """The confidential client the job signs in as (DD-458)."""

    client_secret: SecretStr
    """The secret of ``client_id``; there is no default — a scan without an identity does not run."""

    ca_file: str | None = None
    """PEM CA verifying the server's and the issuer's TLS; unset uses the system trust store."""

    sources: list[SourceEntry] = Field(default_factory=list)
    """The sources the scan reads (DQS-04, DQS-17, DQS-20, DD-459): each names its dataset,
    by qualified name or guid. A dataset no source names is skipped, never guessed at."""

    max_rows: int = Field(default=DEFAULT_MAX_ROWS, ge=1)
    """The most rows one dataset's read returns (DQS-05)."""

    search_limit: int = Field(default=DEFAULT_SEARCH_LIMIT, ge=1)
    """The page size of the rule search (DQS-02)."""

    otel_token_url: HttpUrl | None = None
    """The issuer for the OTLP ingest token; unset with ``otel_endpoint`` keeps telemetry off."""

    otel_client_id: str | None = None
    """The OTLP ingest client id, with ``otel_token_url``."""

    otel_client_secret: SecretStr | None = None
    """The secret of ``otel_client_id``."""

    otel_endpoint: str | None = None
    """The OTLP endpoint telemetry is exported to; unset keeps telemetry off."""

    @field_validator("sources", mode="before")
    @classmethod
    def _parse_sources(cls, value: object) -> object:
        """Read ``SOURCES`` as a JSON array of source objects (DQS-17, DD-462, DD-464).

        An empty configuration (``{}``, ``[]``, or unset) is no sources. Any other shape -- a bare
        path, a non-empty map -- is a settings error that names the array shape. Each source's own
        keys are checked by :class:`SourceEntry` and :class:`DatasetIdentity`.
        """
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as cause:
                raise ValueError(SOURCE_MAP_ERROR) from cause
        if isinstance(value, dict) and not value:
            return []
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return value
        raise ValueError(SOURCE_MAP_ERROR)

    @field_validator("sources")
    @classmethod
    def _check_sources_unique(cls, sources: list[SourceEntry]) -> list[SourceEntry]:
        """No dataset is named by two sources: the router would then hold two answers for one dataset (DQS-17)."""
        keys = [entry.dataset.key() for entry in sources]
        if len(keys) != len(set(keys)):
            raise ValueError(DUPLICATE_SOURCE_ERROR)
        return sources
