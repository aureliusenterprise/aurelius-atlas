"""The settings: prefix, defaults, the DSN check, and the validators (DBS-01, DBS-02, DBS-11, DBS-12)."""

from collections.abc import Callable

import pytest
from aurelius_atlas_db_scanner.settings import (
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_PATTERN,
    DEFAULT_SCHEMA_NAME,
    ENV_PREFIX,
    ScannerSettings,
)
from pydantic import ValidationError
from pydantic_settings import SettingsError

MINT = "https://keycloak.localhost:8443/realms/master/protocol/openid-connect/token"

Settings = Callable[..., ScannerSettings]
"""The settings fixture's type: the builder the conftest hands every test."""


@pytest.mark.covers(rules=["DBS-03", "DBS-10", "DBS-11"])
def test_defaults_are_the_dev_stack(settings: Settings) -> None:
    """The unset job aims at the dev server and issuer, admits every name, and waits ten seconds."""
    job = settings()
    assert str(job.server_url).startswith("https://localhost:21000")
    assert str(job.token_url) == MINT
    assert job.client_id == "aurelius-atlas-db-scanner"
    assert job.schema_name == DEFAULT_SCHEMA_NAME
    assert job.schemas == DEFAULT_PATTERN
    assert job.tables == DEFAULT_PATTERN
    assert job.connect_timeout_seconds == DEFAULT_CONNECT_TIMEOUT_SECONDS
    assert job.system_name == "Test Database"


@pytest.mark.covers(rules=["DBS-03", "DBS-04", "DBS-05", "DBS-11"])
def test_environment_sets_the_prefixed_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """The settings read the project's own prefix — other projects' variables never set them."""
    monkeypatch.setenv(f"{ENV_PREFIX}SYSTEM_NAME", "Warehouse")
    monkeypatch.setenv(f"{ENV_PREFIX}SCHEMA_NAME", "public")
    monkeypatch.setenv(f"{ENV_PREFIX}SCHEMAS", "sales*, ops")
    monkeypatch.setenv(f"{ENV_PREFIX}TABLES", "orders, *_hist")
    monkeypatch.setenv(f"{ENV_PREFIX}DSN", "sqlite://")
    monkeypatch.setenv(f"{ENV_PREFIX}CLIENT_SECRET", "s3cret")
    job = ScannerSettings()  # pyright: ignore[reportCallIssue] - the environment carries the required keys
    assert job.system_name == "Warehouse"
    assert job.schema_name == "public"
    assert job.schemas == "sales*, ops"
    assert job.tables == "orders, *_hist"


@pytest.mark.covers(rules=["DBS-10", "DBS-12"])
def test_a_secretless_job_does_not_configure() -> None:
    """There is no default secret: a scan without an identity has no settings (DBS-10)."""
    with pytest.raises(ValidationError, match="client_secret"):
        ScannerSettings(dsn="sqlite:///:memory:", system_name="x")  # pyright: ignore[reportCallIssue] - the point is the missing field


@pytest.mark.covers(rules=["DBS-12"])
def test_a_job_without_a_dsn_does_not_configure() -> None:
    """The DSN is required: there is no default database to scan (DBS-12)."""
    with pytest.raises(ValidationError, match="dsn"):
        ScannerSettings(system_name="x", client_secret="s")  # pyright: ignore[reportCallIssue] - the point is the missing field  # noqa: S106 - a test secret


@pytest.mark.covers(rules=["DBS-01", "DBS-12"])
def test_a_dsn_that_is_not_a_database_url_is_refused_naming_the_key(settings: Settings) -> None:
    """'not a dsn' is a configuration error that names DSN, not a door error (DBS-01, DBS-12)."""
    with pytest.raises(ValidationError, match="DSN is not a database URL"):
        settings(dsn="not a dsn")


@pytest.mark.covers(rules=["DBS-01", "DBS-12"])
def test_a_dsn_whose_driver_is_missing_names_the_driver_to_install(settings: Settings) -> None:
    """The image ships psycopg and sqlite3; another dialect is a configuration error naming it (DBS-01)."""
    with pytest.raises(ValidationError, match=r"oracledb.*not installed"):
        settings(dsn="oracle+oracledb://user@host:1521/warehouse")


@pytest.mark.covers(rules=["DBS-01", "DBS-12"])
def test_a_dsn_of_an_unknown_dialect_is_refused(settings: Settings) -> None:
    """A product SQLAlchemy itself does not know fails at the start the same way (DBS-01)."""
    with pytest.raises(ValidationError, match="DSN"):
        settings(dsn="wathever://user@host/db")


@pytest.mark.covers(rules=["DBS-01", "DBS-12"])
def test_the_delivered_dialects_configure(settings: Settings) -> None:
    """Postgres through psycopg and SQLite from the standard library are the delivered pair (DBS-01)."""
    assert settings(dsn="sqlite:///:memory:").dsn.get_secret_value() == "sqlite:///:memory:"
    job = settings(dsn="postgresql+psycopg://user:s3cret@db.example:5432/warehouse")
    assert "psycopg" in job.dsn.get_secret_value()


@pytest.mark.covers(rules=["DBS-03", "DBS-12"])
def test_an_empty_system_name_is_refused_naming_the_key(settings: Settings) -> None:
    """There is no default System: whitespace names nothing and is refused (DBS-03, DBS-12)."""
    with pytest.raises(ValidationError, match="SYSTEM_NAME names no system"):
        settings(system_name="   ")


@pytest.mark.covers(rules=["DBS-04", "DBS-05", "DBS-12"])
def test_empty_pattern_lists_are_refused(settings: Settings) -> None:
    """A SCHEMAS/TABLES of nothing but commas would silently admit nothing — refused, not defaulted."""
    with pytest.raises(ValidationError, match="SCHEMAS names no pattern"):
        settings(schemas=",  ,")
    with pytest.raises(ValidationError, match="TABLES names no pattern"):
        settings(tables=",")


@pytest.mark.covers(rules=["DBS-02", "DBS-12"])
def test_a_timeout_that_is_not_positive_is_refused(settings: Settings) -> None:
    """The connect timeout bounds the wait; zero or less is a configuration error (DBS-12)."""
    with pytest.raises(ValidationError, match="CONNECT_TIMEOUT_SECONDS must be positive"):
        settings(connect_timeout_seconds=0)
    assert settings(connect_timeout_seconds=1.5).connect_timeout_seconds == 1.5


@pytest.mark.covers(rules=["DBS-11"])
def test_the_telemetry_trio_stands_together(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    """Half an OTLP trio is a configuration error, the quality scanner's rule (DD-196)."""
    with pytest.raises(ValidationError, match="stand together"):
        settings(otel_endpoint="https://otel:4318")
    monkeypatch.setenv(f"{ENV_PREFIX}OTEL_TOKEN_URL", MINT)
    monkeypatch.setenv(f"{ENV_PREFIX}OTEL_CLIENT_ID", "otel-ingest-client")
    job = settings(otel_endpoint="https://otel:4318")
    assert job.otel_client_id == "otel-ingest-client"
    assert str(job.otel_token_url) == MINT


@pytest.mark.covers(rules=["DBS-11"])
def test_the_command_line_sets_the_flags_it_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """The settings model is the CLI (DD-472): the flags it names, over the environment.

    --dry-run, repeatable --table, repeatable --schema, and a flag for any key — a flag beats
    the environment's value, and the secrets stay the environment's because they have no flag.
    """
    monkeypatch.setenv(f"{ENV_PREFIX}DSN", "sqlite:///from-env.db")
    monkeypatch.setenv(f"{ENV_PREFIX}SYSTEM_NAME", "From Env")
    monkeypatch.setenv(f"{ENV_PREFIX}CLIENT_SECRET", "from-the-environment")
    job = ScannerSettings(
        _cli_parse_args=[  # pyright: ignore[reportCallIssue] - the CLI source reads the argv it is handed
            "--dry-run",
            "--table",
            "orders",
            "--table",
            "*_hist",
            "--schema",
            "sales*",
            "--system-name",
            "From Flags",
            "--schema-name",
            "public",
            "--connect-timeout-seconds",
            "2.5",
        ]
    )
    assert job.dry_run is True
    assert job.table == ["orders", "*_hist"]
    assert job.schema == ["sales*"]
    assert job.system_name == "From Flags"  # the flag beats the environment
    assert job.schema_name == "public"
    assert job.connect_timeout_seconds == 2.5
    assert job.dsn.get_secret_value() == "sqlite:///from-env.db"  # the secret stays the environment's
    assert job.client_secret.get_secret_value() == "from-the-environment"


@pytest.mark.covers(rules=["DBS-11"])
def test_a_flag_free_build_reads_the_environment_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Built without argv (as a test process is), the settings never parse the process's own arguments."""
    monkeypatch.setenv(f"{ENV_PREFIX}SYSTEM_NAME", "Quietly")
    job = ScannerSettings(dsn="sqlite:///:memory:", client_secret="s")  # pyright: ignore[reportCallIssue] - system_name rides the environment  # noqa: S106 - a test secret
    assert job.system_name == "Quietly"
    assert job.dry_run is False
    assert job.table is None
    assert job.schema is None


@pytest.mark.covers(rules=["DBS-10", "DBS-11"])
def test_the_help_names_the_operators_knobs_and_never_a_secret(capsys: pytest.CaptureFixture[str]) -> None:
    """--help advertises the flags an operator turns; the secret fields are suppressed from it (DD-472).

    The DSN in particular: its flag would put a database password in shell history and the
    process list (DD-506), so the documented interface is the knobs, not the credentials.
    """
    with pytest.raises(SystemExit):
        ScannerSettings(_cli_parse_args=["--help"])  # pyright: ignore[reportCallIssue] - argparse exits after printing
    help_text = capsys.readouterr().out
    assert "--dry-run" in help_text
    assert "--table" in help_text
    assert "--schema" in help_text
    assert "--system-name" in help_text
    assert "--dsn" not in help_text
    assert "--client-secret" not in help_text
    assert "--otel-client-secret" not in help_text


@pytest.mark.covers(rules=["DBS-12"])
def test_there_is_no_output_file_option() -> None:
    """The catalogue is the only output: an --out flag is refused, not silently ignored (DBS-12)."""
    with pytest.raises(SettingsError, match="unrecognized arguments: --out"):
        ScannerSettings(_cli_parse_args=["--out", "catalog.json"])  # pyright: ignore[reportCallIssue] - the point is the unknown flag
