"""The CLI: settings, the Keycloak token, telemetry, one scan, the exit code (12.2, DQS-01, DQS-09, DQS-10).

The job runs one scan as one process and exits: 0 for a completed scan — rule-level ERROR findings
are data, not failures — and 1 for a run-level failure: a bad configuration, a refused write, an
unreachable catalogue (DQS-01). The catalogue door is ``aurelius-atlas-server-client``, and the job
signs in as its own service identity (DQS-10, DD-458).
"""

import argparse
import asyncio
import logging
import ssl
import sys
import time
from collections.abc import Callable, Sequence
from uuid import uuid4

import httpx2 as httpx
from aurelius_atlas_otel import ClientCredentialsTokenSource, build_otlp_pipeline, setup_telemetry
from aurelius_atlas_server_client import AtlasClient
from pydantic import ValidationError

from aurelius_atlas_quality_scanner.scan import run_scan, score_line
from aurelius_atlas_quality_scanner.settings import ScannerSettings
from aurelius_atlas_quality_scanner.sources import SourceRouter

SERVICE_NAME = "aurelius-atlas-quality-scanner"
"""The telemetry service name: the job's own identity in the traces (DQS-10)."""

TIMEOUT_SECONDS = 60.0
"""The catalogue request timeout: a scan's reads and its one write, bounded."""

EXIT_OK = 0
"""A completed scan (DQS-01): ERROR findings included, they are data."""

EXIT_FAILURE = 1
"""A run-level failure (DQS-01): bad settings, no token, an unreachable or refusing catalogue."""

MINT_REFUSAL = "the token endpoint refused the job's credentials: no scan runs without an identity"
"""The refused mint: the job's own identity is required, so the run fails (DQS-01, DQS-10)."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """The CLI's arguments: what to limit the scan to, and whether to write (DQS-09)."""
    parser = argparse.ArgumentParser(prog=SERVICE_NAME, description="Run one quality scan over the catalogue.")
    parser.add_argument("--dry-run", action="store_true", help="scan and print every candidate, write nothing")
    parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        metavar="QUALIFIED_NAME",
        help="limit the scan to this dataset's qualified name (repeatable)",
    )
    return parser.parse_args(argv)


def _tokens(source: ClientCredentialsTokenSource) -> Callable[[], str]:
    """The client's bearer source, failing loudly on a refused mint (DQS-01, DQS-10).

    The ingest source answers ``None`` when minting fails and nothing is cached — right for
    telemetry, whose 401 is visible at the collector. For the job, a refused identity is a
    run-level failure: the scan must not speak anonymously.
    """

    def token() -> str:
        value = source.bearer()
        if value is None:
            raise RuntimeError(MINT_REFUSAL)
        return value

    return token


def build_client(settings: ScannerSettings) -> tuple[AtlasClient, httpx.AsyncClient]:
    """The catalogue client and its connection pool, signing as the job's own identity (DQS-10).

    The token is minted once and refreshed ahead of expiry, so the scan's many reads and its one
    write share it. The caller closes the pool.
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
    """Install telemetry when the settings name an OTLP endpoint; keep it off otherwise."""
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


async def _scan(args: argparse.Namespace, settings: ScannerSettings) -> int:
    """Run one scan on a client and reader, printing what it did; answer the exit code (DQS-01, DQS-09)."""
    reader = SourceRouter(settings.sources, settings.max_rows)
    client, http = build_client(settings)
    run_id = str(uuid4())
    run_at_ms = int(time.time() * 1000)
    try:
        report = await run_scan(
            client,
            reader,
            settings,
            run_id=run_id,
            run_at_ms=run_at_ms,
            dataset_filter=set(args.datasets) if args.datasets else None,
            dry_run=args.dry_run,
        )
    finally:
        await http.aclose()
    for notice in report.notices:
        print(notice)  # noqa: T201 - command output
    if args.dry_run:
        for entity in report.entities:
            print(f"would store {score_line(entity)}")  # noqa: T201 - command output (DQS-09)
    verb = "would store" if args.dry_run else "stored"
    print(  # noqa: T201 - command output
        f"{verb} {len(report.entities)} entities from {report.datasets_read} datasets "
        f"({report.rules_total} rules, {report.rules_unbound} unbound, {report.datasets_skipped} skipped)"
    )
    return EXIT_OK


def run(argv: Sequence[str] | None = None) -> int:
    """Read settings, run one scan, answer the exit code (DQS-01).

    A settings error is a run-level failure: there is no scan to run without an identity or a map.
    A catalogue error raised out of :func:`~aurelius_atlas_quality_scanner.scan.run_scan` is the
    same — an unreachable or refusing store — and reaches here as an exception the caller sees.
    """
    args = parse_args(argv)
    try:
        settings = ScannerSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    except ValidationError as cause:
        print(f"configuration error: {cause}", file=sys.stderr)  # noqa: T201 - command output
        return EXIT_FAILURE
    logging.basicConfig(level=settings.log_level.upper())
    _setup_telemetry(settings)
    try:
        return asyncio.run(_scan(args, settings))
    except Exception:
        logging.getLogger(SERVICE_NAME).exception("the scan failed")
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(run())
