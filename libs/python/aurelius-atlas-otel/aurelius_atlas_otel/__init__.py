"""The OTLP ingest credential shared by Aurelius Atlas services (7.18, DD-196, DD-197)."""

from aurelius_atlas_otel.ingest import (
    REFRESH_AHEAD_SECONDS,
    ClientCredentialsTokenSource,
    IngestPipeline,
    build_otlp_pipeline,
)
from aurelius_atlas_otel.telemetry import (
    OTEL_EXPORTER_OTLP_ENDPOINT,
    Providers,
    bridge_logging,
    build_providers,
    setup_telemetry,
)

__all__ = [
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "REFRESH_AHEAD_SECONDS",
    "ClientCredentialsTokenSource",
    "IngestPipeline",
    "Providers",
    "bridge_logging",
    "build_otlp_pipeline",
    "build_providers",
    "setup_telemetry",
]
