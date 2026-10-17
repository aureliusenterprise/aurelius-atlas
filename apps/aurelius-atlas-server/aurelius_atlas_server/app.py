"""The FastAPI application: settings, the store's lifetime, error handling and routers (DD-015, DD-016)."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version

import logfire
from aurelius_atlas_store_es import ElasticsearchStore
from fastapi import FastAPI

from aurelius_atlas_server.errors import AtlasError, AtlasJSONResponse, atlas_error_handler
from aurelius_atlas_server.routes import ADMIN
from aurelius_atlas_server.settings import ServerSettings

NAME = "aurelius-atlas-server"
LOGGER = logging.getLogger(NAME)


def create_app(settings: ServerSettings, store: ElasticsearchStore | None = None) -> FastAPI:
    """Build the application.

    Args:
        settings: The server's settings.
        store: The store to use; by default one built from the settings. It is opened when the application
            starts, which fails when the store cannot be opened (SRV-02), and closed when it stops.
    """
    store = store if store is not None else ElasticsearchStore(settings.store_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        LOGGER.info("Starting %s %s", app.title, app.version)
        await store.open()
        try:
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
    app.add_exception_handler(AtlasError, atlas_error_handler)
    app.include_router(ADMIN)

    logfire.configure(
        send_to_logfire=False,
        service_name=NAME,
        service_version=app.version,
        min_level=settings.log_level,
        console=logfire.ConsoleOptions(min_log_level=settings.log_level),
    )
    logfire.instrument_fastapi(app)
    LOGGER.setLevel(settings.log_level.upper())
    return app
