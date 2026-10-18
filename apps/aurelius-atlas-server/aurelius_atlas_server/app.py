"""The FastAPI application: settings, the store's lifetime, error handling and routers (DD-015, DD-016)."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version

import logfire
from aurelius_atlas_core.model_loader import ModelLoader
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_typesystem.registry import TypeRegistry
from fastapi import FastAPI

from aurelius_atlas_server.auth.guard import install_auth
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
            if settings.auth_enabled:
                await app.state.oidc.aclose()
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
    install_auth(app)

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
