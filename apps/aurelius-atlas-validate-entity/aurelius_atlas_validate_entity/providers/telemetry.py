"""The telemetry factories: logfire, the OTLP ingest leg (DD-107, DD-108, DD-120).

The app owns its export through the shared ``aurelius-atlas-otel`` pipeline —
a client-credentials JWT as ``otel-validate-entity``, refreshed per export;
unset settings mean console-only telemetry (AUX-03).
"""

import logfire
from aurelius_atlas_otel import ClientCredentialsTokenSource, IngestPipeline, build_otlp_pipeline
from fastapi import FastAPI

from aurelius_atlas_validate_entity.globals import LOGGER, NAME
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings


def ingest_pipeline(settings: ValidateEntitySettings) -> IngestPipeline | None:
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


def configure_telemetry(app: FastAPI, settings: ValidateEntitySettings) -> None:
    """Wire the app's telemetry: logfire's export, the FastAPI instrumentor, the log level.

    The ingest leg rides only when it is configured (AUX-03); ``logfire.configure``
    is process-global, as the other 8.x apps call it (DD-108).
    """
    ingest = ingest_pipeline(settings)
    logfire.configure(
        send_to_logfire=False,
        service_name=NAME,
        service_version=app.version,
        min_level=settings.log_level,
        console=logfire.ConsoleOptions(min_log_level=settings.log_level),
        **(
            {
                "additional_span_processors": [ingest[0]],
                "metrics": logfire.MetricsOptions(additional_readers=[ingest[1]]),
            }
            if ingest is not None
            else {}
        ),
    )
    logfire.instrument_fastapi(app)
    LOGGER.setLevel(settings.log_level.upper())
