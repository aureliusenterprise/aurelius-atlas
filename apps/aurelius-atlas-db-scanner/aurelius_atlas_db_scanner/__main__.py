"""The CLI: settings, the Keycloak token, telemetry, one scan, the exit code (13.3, DBS-02, DBS-10, DBS-11).

The job runs one scan as one process and exits: 0 for a completed scan — a table whose
reflection fails is data with a notice, not a failure — and 1 for a run-level failure: a bad
configuration, a refused token, a database that answers no connect in the timeout, a refused
write (DBS-02). The catalogue door is ``aurelius-atlas-server-client``, and the job signs in
as its own service identity (DBS-10, DD-458's pattern). The settings model is the CLI itself:
pydantic-settings parses the flags onto the fields (DD-472), so there is no second argument
parser. The database door closes before the exit, whatever happened.
"""

import asyncio
import logging
import ssl
import sys
from collections.abc import Callable, Sequence

import httpx2 as httpx
from aurelius_atlas_otel import ClientCredentialsTokenSource, build_otlp_pipeline, setup_telemetry
from aurelius_atlas_server_client import AtlasClient
from pydantic import ValidationError
from pydantic_settings import SettingsError

from aurelius_atlas_db_scanner.database import SqlDatabase
from aurelius_atlas_db_scanner.scan import dry_run_lines, run_scan, scan_line
from aurelius_atlas_db_scanner.settings import ScannerSettings

SERVICE_NAME = "aurelius-atlas-db-scanner"
"""The telemetry service name: the job's own identity in the traces (DBS-10)."""

TIMEOUT_SECONDS = 60.0
"""The catalogue request timeout: the scan's one write, bounded."""

EXIT_OK = 0
"""A completed scan (DBS-02): field-less tables included, they are data with a notice."""

EXIT_FAILURE = 1
"""A run-level failure (DBS-02): bad settings, no token, a silent database, a refused write."""

MINT_REFUSAL = "the token endpoint refused the job's credentials: no scan runs without an identity"
"""The refused mint: the job's own identity is required, so the run fails (DBS-02, DBS-10)."""


def _tokens(source: ClientCredentialsTokenSource) -> Callable[[], str]:
    """The client's bearer source, failing loudly on a refused mint (DBS-02, DBS-10).

    The ingest source answers ``None`` when minting fails and nothing is cached — right for
    telemetry, whose 401 is visible at the collector. For the job, a refused identity is a
    run-level failure: the scan does not speak anonymously (DBS-10).
    """

    def token() -> str:
        value = source.bearer()
        if value is None:
            raise RuntimeError(MINT_REFUSAL)
        return value

    return token


def build_client(settings: ScannerSettings) -> tuple[AtlasClient, httpx.AsyncClient]:
    """The catalogue client and its connection pool, signing as the job's own identity (DBS-10).

    The token is minted once and refreshed ahead of expiry, so the scan's one write shares it.
    The caller closes the pool.
    """
    token_source = ClientCredentialsTokenSource(
        str(settings.token_url),
        settings.client_id,
        settings.client_secret.get_secret_value(),
        ca_file=settings.ca_file,
    )
    verify = ssl.create_default_context(cafile=settings.ca_file) if settings.ca_file else ssl.create_default_context()
    http = httpx.AsyncClient(base_url=str(settings.server_url), verify=verify, timeout=TIMEOUT_SECONDS)
    return AtlasClient(http, _tokens(token_source)), http


def _setup_telemetry(settings: ScannerSettings) -> None:
    """Install telemetry when the settings name an OTLP endpoint; keep it off otherwise (DD-196)."""
    if not settings.otel_endpoint or not settings.otel_token_url or not settings.otel_client_id:
        setup_telemetry(SERVICE_NAME, "0.1.0")
        return
    ingest = ClientCredentialsTokenSource(
        str(settings.otel_token_url),
        settings.otel_client_id,
        (settings.otel_client_secret.get_secret_value() if settings.otel_client_secret else ""),
        ca_file=settings.ca_file,
    )
    pipeline = build_otlp_pipeline(settings.otel_endpoint, settings.ca_file, ingest)
    setup_telemetry(SERVICE_NAME, "0.1.0", pipeline=pipeline)


async def _scan(settings: ScannerSettings) -> int:
    """Run one scan on the two doors, printing what it did; answer the exit code (DBS-02, DBS-11)."""
    door = SqlDatabase(
        settings.dsn.get_secret_value(),
        connect_timeout_seconds=settings.connect_timeout_seconds,
    )
    door.open()  # A database that answers nothing raises here: the run fails naming host and database (DBS-02).
    client, http = build_client(settings)
    try:
        report = await run_scan(
            door,
            client.entity,
            settings,
            schema_filter=settings.schema,
            table_filter=settings.table,
            dry_run=settings.dry_run,
        )
    finally:
        door.close()
        await http.aclose()
    for notice in report.notices:
        print(notice)  # noqa: T201 - command output
    if settings.dry_run:
        for line in dry_run_lines(report):
            print(f"would store {line}")  # noqa: T201 - command output (DBS-11)
    print(scan_line(report, dry_run=settings.dry_run))  # noqa: T201 - command output
    return EXIT_OK


def run(argv: Sequence[str] | None = None) -> int:
    """Read settings, run one scan, answer the exit code (DBS-02).

    A settings error is a run-level failure: there is no scan to run without a DSN, an
    identity, or a named System. The settings model is the CLI: the flags it names
    (``--dry-run``, ``--table``, ``--schema``, DBS-11) parse onto its fields through the
    pydantic-settings CLI source, over the environment (DD-472); a malformed flag or a
    malformed setting is a configuration error and answers 1. A door error raised out of
    :func:`~aurelius-atlas-db-scanner.scan.run_scan` is the same — a silent database, a
    refused write — and reaches here as the logged failure answering 1.
    """
    try:
        settings = ScannerSettings(_cli_parse_args=list(sys.argv[1:] if argv is None else argv))  # pyright: ignore[reportCallIssue] - the settings read the environment
    except (ValidationError, SettingsError) as cause:
        print(f"configuration error: {cause}", file=sys.stderr)  # noqa: T201 - command output
        return EXIT_FAILURE
    logging.basicConfig(level=settings.log_level.upper())
    _setup_telemetry(settings)
    try:
        return asyncio.run(_scan(settings))
    except Exception:
        logging.getLogger(SERVICE_NAME).exception("the scan failed")
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(run())
