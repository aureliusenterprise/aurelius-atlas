"""The app's settings, read once at start from the environment and the command line (13.3, DBS-02, DBS-03, DBS-10..12).

One model carries every setting and the run's flags (DBS-11): environment variables under
:data:`ENV_PREFIX` first, command-line arguments over them, both through pydantic-settings' CLI
source — there is no second argument parser to keep in step with the fields (DD-472). Secrets
are environment settings like the rest, and the CLI does not advertise a flag for them
(:data:`~pydantic_settings.CliSuppress`): the DSN of a production database carries its
credentials in one string, so ``--help`` never names it (DD-506).
"""

import warnings
from typing import Literal, Self

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    CliSuppress,
    CliToggleFlag,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, NoSuchModuleError

ENV_PREFIX = "AURELIUS_ATLAS_DB_SCANNER_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_CLIENT_ID = "aurelius-atlas-db-scanner"
"""The Keycloak client the job signs in as (DBS-10, DD-458's pattern): its own service identity."""

DEFAULT_SERVER_URL = "https://localhost:21000"
"""The dev Atlas server: what ``nx serve`` of the server publishes, where the scan runs in dev."""

DEFAULT_MINT_URL = "https://keycloak.localhost:8443/realms/master/protocol/openid-connect/token"
"""The dev issuer's token endpoint: the TLS :8443 listener every producer mints at (DD-113)."""

DEFAULT_SCHEMA_NAME = "default"
"""The Collection's name for a dialect's nameless default schema, when the operator names none (DBS-04)."""

DEFAULT_PATTERN = "*"
"""The schema/table filter that admits every name (DBS-04, DBS-05, the Kafka scanner's KSC-02)."""

DEFAULT_CONNECT_TIMEOUT_SECONDS = 10.0
"""How long the door waits for the database to answer a connect (DBS-02): a silent database
fails the run, and this bounds the wait instead of hanging it."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels the app's logging accepts."""


# The --schema filter's field (DBS-11) is named ``schema``, which shadows the deprecated
# pydantic v1 ``schema()`` method BaseSettings still carries — one this app never calls.
# The filter narrows pydantic's shadow-warning to this exact field of this exact class.
warnings.filterwarnings("ignore", message='Field name "schema" in "ScannerSettings"')


class ScannerSettings(BaseSettings):
    """Where the database and the catalogue are, how the job authenticates, what it scans, and what bounds it."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        frozen=True,
        extra="ignore",
        cli_prog_name="aurelius-atlas-db-scanner",
        cli_kebab_case=True,
        cli_hide_none_type=True,
        cli_avoid_json=True,
        cli_exit_on_error=False,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Command line over environment over dotenv (DD-472): an explicit flag beats ambient config.

        The CLI source parses only what the caller hands it (``_cli_parse_args``): built without
        that, the settings read environment alone, so a test process never parses its own
        pytest arguments as scanner flags.
        """
        return (
            CliSettingsSource(settings_cls),
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    log_level: LogLevel = "info"
    """The lowest level of log record the job emits."""

    dsn: CliSuppress[SecretStr]
    """The database URL (DBS-10, DD-506): required, and suppressed from ``--help`` like every
    other secret — the flag would put a password in the shell history and the process list.
    One DSN per run (DD-503): a deployment with n databases runs the job n times."""

    system_name: str
    """The System entity's name (DBS-03): the catalogue's label for the platform the database
    belongs to. There is no default — a scan without a named system would invent one."""

    schema_name: str = DEFAULT_SCHEMA_NAME
    """The Collection's name for the default schema of a dialect that has none (DBS-03, DBS-04):
    the SQLite case, where the scanned schema carries no name of its own."""

    server_url: HttpUrl = DEFAULT_SERVER_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The Atlas metadata API the job writes the tree to (DBS-10)."""

    token_url: HttpUrl = DEFAULT_MINT_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The issuer's token endpoint the job's client credentials are sent to (DBS-10)."""

    client_id: str = DEFAULT_CLIENT_ID
    """The confidential client the job signs in as (DBS-10, DD-458's pattern)."""

    client_secret: CliSuppress[SecretStr]
    """The secret of ``client_id``; there is no default — a scan without an identity does not run.
    Suppressed from ``--help`` (DD-472): the documented interface stays the knobs, not the secrets."""

    dry_run: CliToggleFlag[bool] = Field(default=False, description="read everything and print the tree, write nothing")
    """``--dry-run`` / ``--no-dry-run`` (DBS-11): the whole read, no write."""

    schema: list[str] | None = Field(  # pyright: ignore[reportIncompatibleMethodOverride] - the name is the flag and the env key (DBS-11)
        default=None, description="limit the scan to schemas matching this pattern (repeatable)"
    )
    """``--schema`` repeated (DBS-11): the patterns that limit this run's schemas, matched like
    :attr:`schemas`. Unset scans what :attr:`schemas` admits."""

    table: list[str] | None = Field(
        default=None, description="limit the scan to tables matching this pattern (repeatable)"
    )
    """``--table`` repeated (DBS-11): the patterns that limit this run's tables, matched like
    :attr:`tables`. A database that lacks a named one is a notice, not a failure."""

    ca_file: str | None = None
    """PEM CA verifying the server's and the issuer's TLS; unset uses the system trust store."""

    schemas: str = DEFAULT_PATTERN
    """A comma-separated list of schema-name patterns; ``*`` matches any run of characters and a
    name matching any pattern is scanned, case-insensitive (DBS-04)."""

    tables: str = DEFAULT_PATTERN
    """A comma-separated list of table-name patterns, matched the same way (DBS-05, KSC-02)."""

    connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS
    """How long the door waits for the database to answer a connect (DBS-02)."""

    otel_token_url: HttpUrl | None = None
    """The issuer for the OTLP ingest token; unset with ``otel_endpoint`` keeps telemetry off."""

    otel_client_id: str | None = None
    """The OTLP ingest client id, with ``otel_token_url``."""

    otel_client_secret: CliSuppress[SecretStr | None] = None
    """The secret of ``otel_client_id`` — suppressed from ``--help``."""

    otel_endpoint: str | None = None
    """The OTLP endpoint telemetry is exported to; unset keeps telemetry off (DD-196)."""

    @field_validator("dsn", mode="before")
    @classmethod
    def _check_dsn(cls, value: object) -> object:
        """The DSN must be a database URL whose driver the job has (DBS-01, DBS-12).

        A URL the URL parser cannot read is a configuration error naming the key; a dialect
        whose DBAPI is not installed is one naming the driver to add to the image. The check
        loads no connection — it is the start's job, and the door's silence rule (DBS-02)
        belongs to the connect, not to this parse.
        """
        if not isinstance(value, str):
            return value
        try:
            url = make_url(value)
        except ArgumentError as cause:
            msg = f"{ENV_PREFIX}DSN is not a database URL: {cause}"
            raise ValueError(msg) from cause
        scheme = value.split("://", 1)[0]
        try:
            dialect = url.get_dialect()
        except NoSuchModuleError as cause:
            msg = f"{ENV_PREFIX}DSN names no SQLAlchemy dialect this job knows ({scheme}): {cause}"
            raise ValueError(msg) from cause
        try:
            dialect.import_dbapi()
        except ModuleNotFoundError as cause:
            msg = (
                f"{ENV_PREFIX}DSN names the {dialect.name} dialect with the {dialect.driver} driver,"
                f" which is not installed: add the {dialect.driver} package to the job"
            )
            raise ValueError(msg) from cause
        return value

    @field_validator("system_name")
    @classmethod
    def _check_system_name(cls, value: str) -> str:
        """An empty SYSTEM_NAME would name the System nothing: refused, not defaulted (DBS-03, DBS-12)."""
        if not value.strip():
            msg = f"{ENV_PREFIX}SYSTEM_NAME names no system: name the platform the database belongs to"
            raise ValueError(msg)
        return value

    @field_validator("schemas", "tables")
    @classmethod
    def _check_patterns(cls, value: str, info: object) -> str:
        """The schema/table patterns must not be empty: an empty list would silently admit nothing (DBS-04, DBS-05)."""
        if not any(pattern.strip() for pattern in value.split(",")):
            name = getattr(info, "field_name", "patterns").upper()
            msg = f"{ENV_PREFIX}{name} names no pattern: use '*' to admit every name"
            raise ValueError(msg)
        return value

    @field_validator("connect_timeout_seconds")
    @classmethod
    def _check_timeout(cls, value: float) -> float:
        """A timeout that is not positive would bound the connect with a lie (DBS-12)."""
        if value <= 0:
            msg = f"{ENV_PREFIX}CONNECT_TIMEOUT_SECONDS must be positive"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _check_telemetry_trio(self) -> Self:
        """The OTLP trio stands or falls together, as in the quality scanner (DD-196)."""
        trio = (self.otel_token_url, self.otel_client_id, self.otel_endpoint)
        if any(trio) and not all(trio):
            msg = f"{ENV_PREFIX}OTEL_ENDPOINT, _TOKEN_URL and _CLIENT_ID stand together"
            raise ValueError(msg)
        return self
