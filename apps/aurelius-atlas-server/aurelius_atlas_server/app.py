"""The FastAPI application: settings, the store's lifetime, error handling and routers (DD-015, DD-016)."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import logfire
from aurelius_atlas_core.model_loader import ModelLoader
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_typesystem.registry import TypeRegistry
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from aurelius_atlas_server.errors import AtlasError, AtlasJSONResponse, atlas_error_handler
from aurelius_atlas_server.otel_ingest import ClientCredentialsTokenSource, IngestPipeline, build_otlp_pipeline
from aurelius_atlas_server.routes import ADMIN, TYPES
from aurelius_atlas_server.settings import ServerSettings

NAME = "aurelius-atlas-server"
LOGGER = logging.getLogger(NAME)


DASHBOARD_V3_DIR = "n"
"""Where ``dashboardv3`` sits in the dashboard directory, and below which path it is served."""


def mount_dashboards(app: FastAPI, directory: Path) -> None:
    """Serve ``dashboardv3`` at ``/n/`` and ``dashboardv2`` at ``/`` (DSH-01, DSH-02; DD-018).

    Mounted after the API routes, so the API takes precedence (DSH-03).
    """
    app.mount(
        f"/{DASHBOARD_V3_DIR}", StaticFiles(directory=directory / DASHBOARD_V3_DIR, html=True), name="dashboardv3"
    )
    app.mount("/", StaticFiles(directory=directory, html=True), name="dashboardv2")


def create_app(settings: ServerSettings, store: ElasticsearchStore | None = None) -> FastAPI:
    """Build the application.

    Args:
        settings: The server's settings.
        store: The store to use; by default one built from the settings. It is opened when the application
            starts, which fails when the store cannot be opened (SRV-02), and closed when it stops.

    The type registry is loaded from the stored type definitions when the application starts (TDS-12), then the
    models are loaded and patched (MDL-16).
    """
    store = store if store is not None else ElasticsearchStore(settings.store_settings())
    registry = TypeRegistry()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        LOGGER.info("Starting %s %s", app.title, app.version)
        await store.open()
        try:
            typedef_store = TypedefStore(
                registry,
                ElasticsearchTypedefDocument(store.client),
                refresh_seconds=settings.typedef_refresh_seconds,
            )
            await typedef_store.load()
            await ModelLoader(typedef_store).load(settings.models_dir)
            app.state.typedef_store = typedef_store
            yield
        finally:
            await store.close()
            LOGGER.info("Stopped %s", app.title)

    app = FastAPI(
        title=NAME,
        version=version(NAME),
        lifespan=lifespan,
        default_response_class=AtlasJSONResponse,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.store = store
    app.state.type_registry = registry
    app.add_exception_handler(AtlasError, atlas_error_handler)
    app.include_router(ADMIN)
    app.include_router(TYPES)
    if settings.dashboard_dir is not None:
        mount_dashboards(app, settings.dashboard_dir)

    # Telemetry (SHL-14, DD-107): the console is logfire's; the OTLP export
    # is the app's own pipeline when the ingest credential is configured —
    # exporters whose session injects a fresh client-credentials JWT per
    # export (the collector's per-service leg, CIA-07). Unset settings mean
    # console-only: logfire's env-driven OTLP export is not used, so a
    # server without an ingest identity exports nothing (DD-107).
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
                "metrics": logfire.MetricsOptions(
                    additional_readers=[ingest[1]],
                ),
            }
            if ingest is not None
            else {}
        ),
    )
    logfire.instrument_fastapi(app)
    LOGGER.setLevel(settings.log_level.upper())
    return app


def _ingest_pipeline(settings: ServerSettings) -> IngestPipeline | None:
    """The app-owned OTLP export for the per-service ingest leg (7.18, DD-107).

    None when the ingest credential is not configured (console-only telemetry).

    :param settings: the server settings
    :returns: (span processor, metric reader) or None
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
