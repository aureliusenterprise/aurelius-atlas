"""The CLI: settings, the Keycloak tokens, telemetry, one scan, the exit code (13.1, KSC-01, KSC-08..10).

The job runs one scan as one process and exits: 0 for a completed scan — a topic whose fields
cannot be read is data with a notice, not a failure — and 1 for a run-level failure: a bad
configuration, a refused token, a broker that answers no metadata, a refused write (KSC-01). The
catalogue door is ``aurelius-atlas-server-client``, and the job signs in as its own service
identity (KSC-09, DD-458's pattern). The settings model is the CLI itself: pydantic-settings
parses the flags onto the fields (DD-470), so there is no second argument parser. The broker
door closes before the exit, whatever happened.
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

from aurelius_atlas_kafka_scanner.cluster import KafkaCluster
from aurelius_atlas_kafka_scanner.registry import SchemaRegistry
from aurelius_atlas_kafka_scanner.scan import dry_run_lines, run_scan, scan_line
from aurelius_atlas_kafka_scanner.settings import ScannerSettings

SERVICE_NAME = "aurelius-atlas-kafka-scanner"
"""The telemetry service name: the job's own identity in the traces (KSC-09)."""

TIMEOUT_SECONDS = 60.0
"""The catalogue request timeout: the scan's one read of the tree and its one write, bounded."""

EXIT_OK = 0
"""A completed scan (KSC-01): field-less topics included, they are data with a notice."""

EXIT_FAILURE = 1
"""A run-level failure (KSC-01): bad settings, no token, a silent broker, a refused write."""

MINT_REFUSAL = "the token endpoint refused the job's credentials: no scan runs without an identity"
"""The refused mint: the job's own identity is required, so the run fails (KSC-01, KSC-09)."""


def _broker_oauth_source(settings: ScannerSettings) -> ClientCredentialsTokenSource | None:
    """The mint the broker's OAUTHBEARER listener accepts, or ``None`` when the door needs none (KSC-10).

    The same client-credentials source the catalogue and the OTLP legs ride: the trio is the
    settings validator's job to demand (KSC-10); this only wires it.
    """
    if settings.sasl_mechanism != "OAUTHBEARER" or settings.sasl_oauth_token_url is None:
        return None
    return ClientCredentialsTokenSource(
        str(settings.sasl_oauth_token_url),
        settings.sasl_oauth_client_id or "",
        settings.sasl_oauth_client_secret.get_secret_value() if settings.sasl_oauth_client_secret else "",
        ca_file=settings.ca_file,
    )


def _tokens(source: ClientCredentialsTokenSource) -> Callable[[], str]:
    """The client's bearer source, failing loudly on a refused mint (KSC-01, KSC-09).

    The ingest source answers ``None`` when minting fails and nothing is cached — right for
    telemetry, whose 401 is visible at the collector. For the job, a refused identity is a
    run-level failure: the scan does not speak anonymously (KSC-09).
    """

    def token() -> str:
        value = source.bearer()
        if value is None:
            raise RuntimeError(MINT_REFUSAL)
        return value

    return token


def build_client(settings: ScannerSettings) -> tuple[AtlasClient, httpx.AsyncClient]:
    """The catalogue client and its connection pool, signing as the job's own identity (KSC-09).

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
    """Install telemetry when the settings name an OTLP endpoint; keep it off otherwise (KSC-10)."""
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
    """Run one scan on the three doors, printing what it did; answer the exit code (KSC-01, KSC-08)."""
    cluster = KafkaCluster(
        settings.bootstrap_servers,
        ca_file=settings.ca_file,
        admin_request_timeout_ms=settings.admin_request_timeout_ms,
        poll_timeout_seconds=settings.poll_timeout_seconds,
        sniff_messages=settings.sniff_messages,
        security_protocol=settings.security_protocol,
        sasl_mechanism=settings.sasl_mechanism,
        sasl_username=settings.sasl_username,
        sasl_password=settings.sasl_password.get_secret_value() if settings.sasl_password else None,
        oauth_source=_broker_oauth_source(settings),
    )
    registry = SchemaRegistry(
        str(settings.schema_registry_url) if settings.schema_registry_url else None,
        ca_file=settings.ca_file,
        timeout_seconds=settings.registry_timeout_seconds,
    )
    client, http = build_client(settings)
    try:
        report = await run_scan(
            cluster,
            registry,
            client.entity,
            settings,
            topic_filter=settings.topic,
            dry_run=settings.dry_run,
        )
    finally:
        await registry.close()
        cluster.close()
        await http.aclose()
    for notice in report.notices:
        print(notice)  # noqa: T201 - command output
    if settings.dry_run:
        for line in dry_run_lines(report):
            print(f"would store {line}")  # noqa: T201 - command output (KSC-08)
    print(scan_line(report, dry_run=settings.dry_run))  # noqa: T201 - command output
    return EXIT_OK


def run(argv: Sequence[str] | None = None) -> int:
    """Read settings, run one scan, answer the exit code (KSC-01).

    A settings error is a run-level failure: there is no scan to run without an identity or a
    broker to ask. The settings model is the CLI: the flags it names (``--dry-run``, ``--topic``,
    KSC-08) parse onto its fields through the pydantic-settings CLI source, over the environment
    (DD-470); a malformed flag or a malformed setting is a configuration error and answers 1.
    A door error raised out of :func:`~aurelius_atlas_kafka_scanner.scan.run_scan` is the same — a
    silent broker, a refused write — and reaches here as an exception the caller sees in the log.
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
