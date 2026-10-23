"""The OTLP ingest credential shared by Aurelius Atlas services (7.18, DD-107, DD-108)."""

from aurelius_atlas_otel.ingest import (
    REFRESH_AHEAD_SECONDS,
    ClientCredentialsTokenSource,
    IngestPipeline,
    build_otlp_pipeline,
)

__all__ = [
    "REFRESH_AHEAD_SECONDS",
    "ClientCredentialsTokenSource",
    "IngestPipeline",
    "build_otlp_pipeline",
]
