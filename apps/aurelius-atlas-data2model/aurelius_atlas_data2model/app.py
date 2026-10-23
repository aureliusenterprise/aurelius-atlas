"""The FastAPI application: settings, auth, telemetry, the ``/extract`` route (DTM-01, DTM-10, DD-108)."""

import logging
from importlib.metadata import version
from typing import Any

import logfire
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_otel import ClientCredentialsTokenSource, IngestPipeline, build_otlp_pipeline
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aurelius_atlas_data2model.extract import extract
from aurelius_atlas_data2model.rules import ExtractionRequest
from aurelius_atlas_data2model.settings import Data2ModelSettings

NAME = "aurelius-atlas-data2model"
LOGGER = logging.getLogger(NAME)

BAD_REQUEST = 400
"""The status of a malformed request body (DTM-11)."""


def create_app(settings: Data2ModelSettings, auth: KeycloakAuth | None = None) -> FastAPI:
    """Build the application.

    Args:
        settings: The app's settings.
        auth: The token verifier; by default one built from the settings. Injectable for
            tests, which point it at a fake issuer.

    The app is stateless: no store, no start-up work beyond the telemetry (DD-108).
    """
    auth = auth if auth is not None else _auth(settings)

    app = FastAPI(title=NAME, version=version(NAME), docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.auth = auth

    @app.get("/liveness", status_code=204)
    def liveness() -> None:
        """The container healthcheck: 204 while the process serves (no auth)."""

    @app.post("/extract", dependencies=[auth.require_auth])
    def extract_model(body: ExtractionRequest) -> dict[str, Any]:
        """Rows and rules in, the ar3 model string and metadata out (DTM-01)."""
        return extract(body)

    @app.exception_handler(RequestValidationError)
    def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        """A body that fails the request model is a 400 with an Atlas-shaped error body (DTM-11).

        The legacy answered a malformed extraction with a Flask ``ValueError`` — a 500;
        the port states 400 (the 8.1 spec's deviation).
        """
        first = error.errors()[0] if error.errors() else {}
        message = f"invalid extraction request: {first.get('msg', 'malformed body')}"
        LOGGER.info("Rejected extraction request: %s", message)
        return JSONResponse(status_code=BAD_REQUEST, content={"errorCode": "ATLAS-400-00-029", "errorMessage": message})

    # Telemetry (DD-107, DD-108): the app owns its OTLP export through the shared
    # pipeline — a client-credentials JWT as otel-data2model, refreshed per export;
    # unset settings mean console-only (AUX-03).
    ingest = _ingest_pipeline(settings)
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
    return app


def _auth(settings: Data2ModelSettings) -> KeycloakAuth:
    """The app's token verifier, mapped from the settings (DTM-10)."""
    return KeycloakAuth(
        AuthConfig(
            server_url=str(settings.auth_server_url),
            realm=settings.auth_realm,
            audience=settings.auth_audience,
            ca_file=str(settings.auth_ca_file) if settings.auth_ca_file else None,
        )
    )


def _ingest_pipeline(settings: Data2ModelSettings) -> IngestPipeline | None:
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
