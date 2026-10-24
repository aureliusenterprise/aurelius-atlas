import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from aurelius_atlas_otel import bridge_logging, setup_telemetry
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPX2ClientInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from sqlmodel import SQLModel

from aurelius_atlas_fastapi_example.globals import LOGGER, METADATA, NAME
from aurelius_atlas_fastapi_example.models import Settings
from aurelius_atlas_fastapi_example.providers import database, get_broadcaster
from aurelius_atlas_fastapi_example.providers.metrics import register_sse_metric
from aurelius_atlas_fastapi_example.routes import ENTITIES, HEALTH


def setup_logging(level: str) -> None:
    """Configure application and uvicorn loggers for OTEL log export."""
    log_level = level.upper()

    names = (NAME, "uvicorn.error", "uvicorn.access")
    bridge_logging(*names)
    for logger_name in names:
        logging.getLogger(logger_name).setLevel(log_level)


def make_lifespan(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Return a lifespan context manager configured with the given settings."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        """
        Manages the startup and shutdown of the FastAPI application.

        Starts the shared PostgreSQL listener on startup and shuts it down on exit.

        Args:
            app: The FastAPI application instance.

        Yields:
            None: When the application is running.
        """
        LOGGER.info("Starting %s (%s) 🚀", app.title, app.version)
        LOGGER.debug("Application settings: %s", settings)

        if app.debug:
            LOGGER.warning("🚨 Running in development mode. Not for production use! 🚨")

        if settings.auto_create_schema:
            LOGGER.info("Auto-creating database schema...")
            db_engine = database(settings=settings)
            SQLModel.metadata.create_all(db_engine)
            LOGGER.info("Database schema created successfully")

        with get_broadcaster(settings=settings):
            yield

        LOGGER.info("Stopping %s. Goodbye 👋", app.title)

    return lifespan


def setup_routes(app: FastAPI) -> None:
    """Include API routes in the FastAPI application."""
    app.include_router(
        ENTITIES,
        prefix="/entities",
        tags=["Entities"],
    )

    app.include_router(
        HEALTH,
        prefix="/health",
        tags=["Health"],
        include_in_schema=False,
    )


def create_app(settings: Settings) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        lifespan=make_lifespan(settings),
        debug=settings.is_development,
        description=METADATA.get("Summary", ""),
        title=NAME,
        version=f"v{METADATA.get('Version', '')}",
    )

    setup_routes(app)

    # Telemetry (DD-121): native OTel providers. This producer rides the
    # legacy shared-token leg (CIA-10): the env-driven OTLP export —
    # endpoint, CA, static bearer — is standard SDK env configuration, read
    # by setup_telemetry's env leg (DD-107: its per-service graduation is
    # deferred). The W3C traceparent headers the Angular frontend injects
    # (aurelius-atlas-observability interceptor) are joined by the native
    # propagators by default. Debug runs also print to stdout (DD-121).
    setup_telemetry(
        app.title,
        app.version,
        logs=True,
        console=settings.log_level in {"trace", "debug"},
    )

    FastAPIInstrumentor.instrument_app(app)
    HTTPX2ClientInstrumentor().instrument()
    PsycopgInstrumentor().instrument()

    register_sse_metric()

    setup_logging(settings.log_level)

    return app


def main(settings: Settings) -> FastAPI:
    """
    Main entry point for the FastAPI application.

    Returns:
        FastAPI: The FastAPI application instance.
    """
    return create_app(settings)
