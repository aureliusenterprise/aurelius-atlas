"""The FastAPI application: settings, the store's lifetime, error handling and routers (DD-015, DD-016)."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import logfire
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_audit_repository import ElasticsearchEntityAuditRepository
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.model_loader import ModelLoader
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_typesystem.registry import TypeRegistry
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from aurelius_atlas_server.errors import AtlasError, AtlasJSONResponse, atlas_error_handler
from aurelius_atlas_server.routes import ADMIN, ENTITY, RELATIONSHIP, TYPES
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.task_worker import TaskWorker

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
    models are loaded and patched (MDL-16); the entity store's indices are created and interrupted writes recovered
    (ENS-01, ENS-07), and the audit index (DD-082). With tasks enabled, a worker runs the tasks requests record
    (TSK-04, DD-080).
    """
    store = store if store is not None else ElasticsearchStore(settings.store_settings())
    registry = TypeRegistry()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        LOGGER.info("Starting %s %s", app.title, app.version)
        worker: TaskWorker | None = None
        await store.open()
        try:
            entity_store = EntityStore(registry, ElasticsearchEntityDocuments(store.client))
            await entity_store.prepare()
            entity_audits = ElasticsearchEntityAuditRepository(store.client)
            await entity_audits.prepare()
            app.state.entity_audits = entity_audits
            typedef_store = TypedefStore(
                registry,
                ElasticsearchTypedefDocument(store.client),
                usage=entity_store.type_in_use,
                refresh_seconds=settings.typedef_refresh_seconds,
            )
            await typedef_store.load()
            await ModelLoader(typedef_store).load(settings.models_dir)
            await entity_store.recover()
            app.state.typedef_store = typedef_store
            app.state.entity_store = entity_store
            audit = EntityChangeNotifier(entity_store, [EntityAuditListener(entity_audits, entity_store.now)])
            app.state.task_management = TaskManagement(entity_store, notifier=audit)
            if settings.tasks_enabled:
                worker = TaskWorker(app.state.task_management, poll_seconds=settings.task_poll_seconds)
                entity_store.task_listeners.append(worker.wake)
                worker.start()
                app.state.task_worker = worker
            yield
        finally:
            if worker is not None:
                await worker.stop()
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
    app.include_router(ENTITY)
    app.include_router(RELATIONSHIP)
    if settings.dashboard_dir is not None:
        mount_dashboards(app, settings.dashboard_dir)

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
