"""The FastAPI application: settings, auth, telemetry, the ``/`` validation route (VE-01, VE-03, DD-108)."""

import logging
from importlib.metadata import version

import logfire
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_otel import ClientCredentialsTokenSource, IngestPipeline, build_otlp_pipeline
from fastapi import FastAPI

from aurelius_atlas_validate_entity.mock import MOCK_VALIDATION
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings

NAME = "aurelius-atlas-validate-entity"
LOGGER = logging.getLogger(NAME)


def create_app(
    settings: ValidateEntitySettings,
    auth: KeycloakAuth | None = None,
) -> FastAPI:
    """Build the application.

    Args:
        settings: The app's settings.
        auth: The token verifier; by default one built from the settings. Injectable for
            tests, which point it at a fake issuer.

    The app is the legacy mock (DV-14, DD-112): the entity body is never read and the
    answer is the fixed document (VE-01) — no store, no upstream, no cache (the
    legacy's dev ``@cached`` is not ported), no start-up work beyond the telemetry.
    """
    verifier = auth if auth is not None else _auth(settings)

    app = FastAPI(title=NAME, version=version(NAME), docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.auth = verifier

    @app.get("/liveness", status_code=204)
    def liveness() -> None:
        """The container healthcheck: 204 while the process serves (no auth)."""

    @app.post("/", dependencies=[verifier.require_auth])
    def validate_entity() -> dict:
        """Answer the fixed governance-quality mock for any body (VE-01, VE-02).

        The token is verified for this app's audience (VE-03, DV-24) and nothing is
        forwarded — the legacy's ``requires_auth(transparent=True)`` read the token
        and ignored it; the port keeps that: authentication yes, authorisation by
        the fixed answer. The body is the entity the editor is saving; the mock
        never inspects it, malformed bodies included.
        """
        return MOCK_VALIDATION

    # Telemetry (DD-107, DD-108): the app owns its OTLP export through the shared
    # pipeline — a client-credentials JWT as otel-validate-entity, refreshed per
    # export; unset settings mean console-only (AUX-03).
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


def _auth(settings: ValidateEntitySettings) -> KeycloakAuth:
    """The app's token verifier, mapped from the settings (VE-03)."""
    return KeycloakAuth(
        AuthConfig(
            server_url=str(settings.auth_server_url),
            realm=settings.auth_realm,
            audience=settings.auth_audience,
            ca_file=str(settings.auth_ca_file) if settings.auth_ca_file else None,
        )
    )


def _ingest_pipeline(settings: ValidateEntitySettings) -> IngestPipeline | None:
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
