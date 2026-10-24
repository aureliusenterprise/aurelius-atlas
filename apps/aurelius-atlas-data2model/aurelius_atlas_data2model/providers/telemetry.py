"""The telemetry factories: the native OTel providers and the OTLP ingest leg (DD-107, DD-108, DD-120, DD-121).

The app owns its export through the shared ``aurelius-atlas-otel`` pipeline —
a client-credentials JWT as ``otel-data2model``, refreshed per export; unset
settings mean no OTLP export at all (AUX-03).
"""

from aurelius_atlas_otel import (
    ClientCredentialsTokenSource,
    IngestPipeline,
    build_otlp_pipeline,
    setup_telemetry,
)
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPX2ClientInstrumentor

from aurelius_atlas_data2model.globals import LOGGER, NAME
from aurelius_atlas_data2model.settings import Data2ModelSettings


def ingest_pipeline(settings: Data2ModelSettings) -> IngestPipeline | None:
    """The app-owned OTLP export for the per-service ingest leg (DD-107, DD-108).

    None when the ingest credential is not configured (console-only telemetry).
    """
    if settings.otel_token_url is None or settings.otel_client_secret is None:
        return None
    source = ClientCredentialsTokenSource(
        token_url=str(settings.otel_token_url),
        client_id=settings.otel_client_id,
        client_secret=settings.otel_client_secret.get_secret_value(),
        ca_file=str(settings.otel_ca_file) if settings.otel_ca_file else None,
    )
    ca_file = str(settings.otel_ca_file) if settings.otel_ca_file else None
    return build_otlp_pipeline(settings.otel_endpoint, ca_file, source)


def configure_telemetry(app: FastAPI, settings: Data2ModelSettings) -> None:
    """Wire the app's telemetry: the native providers, the instrumentors, the log level.

    The ingest leg rides only when it is configured (AUX-03); ``setup_telemetry``
    is process-global, as the other 8.x apps call it (DD-108, DD-121). Debug
    runs also print spans to stdout (the dev console, DD-121). The httpx
    instrumentor covers the issuer calls the auth library makes (verification,
    JWKS) so every HTTP call of the process is visible (DD-121).
    """
    ingest = ingest_pipeline(settings)
    setup_telemetry(
        NAME,
        app.version,
        pipeline=ingest,
        console=settings.log_level in {"trace", "debug"},
    )
    FastAPIInstrumentor.instrument_app(app)
    HTTPX2ClientInstrumentor().instrument()
    LOGGER.setLevel(settings.log_level.upper())
