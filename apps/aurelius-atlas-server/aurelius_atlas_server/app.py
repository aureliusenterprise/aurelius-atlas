"""The FastAPI application: settings, the store's lifetime, error handling and routers (DD-015, DD-016)."""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import httpx2 as httpx
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_core.atlas_audit_service import AtlasAuditService
from aurelius_atlas_core.audit_reduction_service import AtlasAuditReductionService
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_audit_repository import ElasticsearchEntityAuditRepository
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.metrics_service import MetricsService
from aurelius_atlas_core.metrics_util import AtlasMetricsUtil
from aurelius_atlas_core.model_loader import ModelLoader
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.typedef_audit_listener import BufferedTypeDefAuditListener
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.atlas_audit import AuditOperation
from aurelius_atlas_otel import (
    ClientCredentialsTokenSource,
    bridge_logging,
    build_otlp_log_processor,
    build_otlp_pipeline,
    setup_telemetry,
)
from aurelius_atlas_store_es import ElasticsearchStore, HealthStatus
from aurelius_atlas_typesystem.registry import TypeRegistry
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from aurelius_atlas_server.audit_aging_scheduler import AuditAgingScheduler
from aurelius_atlas_server.authentication import AuthenticationMiddleware, SessionStore
from aurelius_atlas_server.errors import AtlasError, AtlasJSONResponse, atlas_error_handler
from aurelius_atlas_server.metrics_scheduler import MetricsScheduler
from aurelius_atlas_server.oidc_client import OidcClient
from aurelius_atlas_server.request_context import RequestContextMiddleware
from aurelius_atlas_server.routes import ADMIN, DISCOVERY, ENTITY, GLOSSARY, LINEAGE, LOGIN, RELATIONSHIP, TYPES
from aurelius_atlas_server.security_headers import SecurityHeadersMiddleware
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.task_worker import TaskWorker

NAME = "aurelius-atlas-server"
LOGGER = logging.getLogger(NAME)
BRIDGED_LOGGERS = (NAME, "aurelius_atlas_core", "aurelius_atlas_store_es", "uvicorn.error")
"""The loggers whose records the collector receives (OBS-01): the server's, its libraries' and uvicorn's errors."""


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


def build_auth(settings: ServerSettings, http: httpx.Client | None = None) -> KeycloakAuth:
    """The token verifier: the provider's tokens for the server's client and the further audiences (AUT-02)."""
    return KeycloakAuth(
        AuthConfig(
            server_url=str(settings.auth_server_url),
            realm=settings.auth_realm,
            audience=settings.auth_client_id,
            extra_audiences=tuple(settings.auth_audiences),
            ca_file=None if settings.auth_ca_file is None else str(settings.auth_ca_file),
        ),
        http=http,
    )


def build_oidc(settings: ServerSettings, auth: KeycloakAuth, http: httpx.AsyncClient | None = None) -> OidcClient:
    """The server's client at the provider, which browsers sign in with (AUT-05)."""
    return OidcClient(
        auth,
        client_id=settings.auth_client_id,
        client_secret=settings.auth_client_secret.get_secret_value(),
        principal_claim=settings.auth_principal_claim,
        groups_claim=settings.auth_groups_claim,
        ca_file=None if settings.auth_ca_file is None else str(settings.auth_ca_file),
        http=http,
    )


def create_app(
    settings: ServerSettings,
    store: ElasticsearchStore | None = None,
    *,
    auth: KeycloakAuth | None = None,
    oidc_http: httpx.AsyncClient | None = None,
) -> FastAPI:
    """Build the application.

    Args:
        settings: The server's settings.
        store: The store to use; by default one built from the settings. It is opened when the application
            starts, which fails when the store cannot be opened (SRV-02), and closed when it stops.
        auth: The token verifier; by default one for the settings' provider (AUT-02).
        oidc_http: The HTTP client the sign-in calls the provider with; by default one of its own (AUT-05).

    The type registry is loaded from the stored type definitions when the application starts (TDS-12), then the
    models are loaded and patched (MDL-16); the entity store's indices are created and interrupted writes recovered
    (ENS-01, ENS-07), and the audit index (DD-082). With tasks enabled, a worker runs the tasks requests record
    (TSK-04, DD-080).
    """
    store = store if store is not None else ElasticsearchStore(settings.store_settings())
    registry = TypeRegistry()
    auth, oidc, sessions = _authentication(settings, auth, oidc_http)
    metrics_util = AtlasMetricsUtil()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        LOGGER.info("Starting %s %s", app.title, app.version)
        started = int(time.time() * 1000)
        _start(metrics_util)
        worker: TaskWorker | None = None
        schedules: list[AuditAgingScheduler | MetricsScheduler] = []
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
            admin_audits = AtlasAuditService(entity_store)
            await _load_models(typedef_store, admin_audits, settings.models_dir)
            await entity_store.recover()
            app.state.typedef_store = typedef_store
            app.state.entity_store = entity_store
            audit = EntityChangeNotifier(entity_store, [EntityAuditListener(entity_audits, entity_store.now)])
            app.state.task_management = TaskManagement(entity_store, notifier=audit, audits=entity_audits)
            worker = _task_worker(app, settings, entity_store)
            await _audit_server_status(admin_audits, started)
            schedules = [
                scheduler
                for scheduler in (_audit_aging(settings, entity_store), _metrics_schedule(app, settings, entity_store))
                if scheduler is not None
            ]
            yield
        finally:
            for scheduler in schedules:
                await scheduler.stop()
            if worker is not None:
                await worker.stop()
            await store.close()
            await _close(auth, oidc)
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
    # one export or import at a time (EXP-01, DD-304)
    app.state.settings, app.state.import_export_lock = settings, asyncio.Lock()
    app.state.store = store
    app.state.type_registry, app.state.metrics_util = registry, metrics_util
    app.state.auth, app.state.oidc, app.state.sessions = auth, oidc, sessions
    _mount(app, settings)

    _telemetry(app, settings)
    LOGGER.setLevel(settings.log_level.upper())
    return app


def _telemetry(app: FastAPI, settings: ServerSettings) -> None:
    """The process's traces, metrics and logs, and the app's request spans."""
    # Telemetry (SHL-14, DD-196, DD-210): the OTLP export is the app's own
    # pipeline when the ingest credential is configured — exporters whose
    # session injects a fresh client-credentials JWT per export (the
    # collector's per-service leg, CIA-07). Unset settings mean no OTLP at
    # all: the env-driven leg is off for this server, so a server without an
    # ingest identity exports nothing (DD-196). Debug runs also print spans
    # to stdout (the dev console, DD-210). The server's and its libraries' logs ride the same leg to the
    # collector's logs pipeline, and still reach the process's output (OBS-01).
    source = _ingest_source(settings)
    ca_file = str(settings.otel_ca_file) if settings.otel_ca_file else None
    setup_telemetry(
        NAME,
        app.version,
        pipeline=None if source is None else build_otlp_pipeline(settings.otel_endpoint, ca_file, source),
        console=settings.log_level in {"trace", "debug"},
        log_processor=None if source is None else build_otlp_log_processor(settings.otel_endpoint, ca_file, source),
    )
    bridge_logging(*BRIDGED_LOGGERS, propagate=True)
    FastAPIInstrumentor.instrument_app(app)


def _mount(app: FastAPI, settings: ServerSettings) -> None:
    """The middleware, the error handler, the routers and the dashboards."""
    # Each request's user and client bound for the admin audits its changes write (ADA-02): added before the
    # authentication, so it runs inside it, once the user is known.
    app.add_middleware(RequestContextMiddleware)
    # Every request's user, or its 401 or sign-in (AUT-01 to AUT-08); added before the security headers, so
    # they wrap its answers too.
    app.add_middleware(AuthenticationMiddleware)
    # Security response headers on every answer — the API and the dashboards
    # alike (SRV-08, DD-236). Added before the routers mount, so it wraps
    # them all; the instrumentor below wraps this middleware.
    app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=settings.hsts_enabled)
    app.add_exception_handler(AtlasError, atlas_error_handler)
    for router in (ADMIN, TYPES, ENTITY, RELATIONSHIP, DISCOVERY, LINEAGE, GLOSSARY, LOGIN):
        app.include_router(router)
    if settings.dashboard_dir is not None:
        mount_dashboards(app, settings.dashboard_dir)


def _ingest_source(settings: ServerSettings) -> ClientCredentialsTokenSource | None:
    """The credential of the app-owned OTLP export on the per-service ingest leg (7.18, DD-196).

    None when the ingest credential is not configured (console-only telemetry).

    :param settings: the server settings
    :returns: the client-credentials token source, or None
    """
    if settings.otel_token_url is None or settings.otel_client_secret is None:
        return None
    return ClientCredentialsTokenSource(
        token_url=str(settings.otel_token_url),
        client_id=settings.otel_client_id,
        client_secret=settings.otel_client_secret.get_secret_value(),
        ca_file=str(settings.otel_ca_file) if settings.otel_ca_file else None,
    )


async def _close(auth: KeycloakAuth, oidc: OidcClient) -> None:
    """Close the provider clients (the application's shutdown)."""
    await oidc.close()
    auth.close()


def _authentication(
    settings: ServerSettings, auth: KeycloakAuth | None, oidc_http: httpx.AsyncClient | None
) -> tuple[KeycloakAuth, OidcClient, SessionStore]:
    """The verifier, the sign-in client and the sessions (AUT-02 to AUT-06)."""
    verifier = auth if auth is not None else build_auth(settings)
    return verifier, build_oidc(settings, verifier, oidc_http), SessionStore(settings.session_timeout_seconds)


async def _load_models(store: TypedefStore, audits: AtlasAuditService, models_dir: Path) -> None:
    """Load the models with their typedef changes audited, the start's writes held to one write (ADA-03, DD-316).

    One write per change adds a store refresh each to the start, minutes for Atlas's whole catalogue — long
    enough for the container's health check to give up before the server answers.
    """
    boot_audits = BufferedTypeDefAuditListener(audits)
    store.change_listeners.append(boot_audits)
    await ModelLoader(store).load(models_dir)
    await boot_audits.flush()


def _start(metrics_util: AtlasMetricsUtil) -> None:
    """``ActiveInstanceElectorService#start``: without high availability, the server is active as it starts (MET-03)."""
    metrics_util.on_server_start()
    metrics_util.on_server_activation()


async def _audit_server_status(audits: AtlasAuditService, started: int) -> None:
    """``auditServerStatus``: ``SERVER_START`` from the start to now, then ``SERVER_STATE_ACTIVE`` now (ADA-02).

    A failure is only logged, as Atlas logs it.
    """
    now = int(time.time() * 1000)
    try:
        await audits.add(AuditOperation.SERVER_START, None, None, 0, start_time=started, end_time=now)
        await audits.add(AuditOperation.SERVER_STATE_ACTIVE, None, None, 0, start_time=now, end_time=now)
    except AtlasError:
        LOGGER.exception("Exception occurred during audit")


def _audit_aging(settings: ServerSettings, store: EntityStore) -> AuditAgingScheduler | None:
    """The configured aging of the entity audits scheduled and started, when it is enabled (AGE-05)."""
    if not settings.audit_aging_enabled:
        return None
    aging = AuditAgingScheduler(
        AtlasAuditReductionService(store, settings.audit_aging_config()),
        frequency_days=settings.audit_aging_scheduler_frequency_in_days,
        initial_delay_minutes=settings.audit_aging_scheduler_initial_delay_in_min,
    )
    aging.start()
    return aging


def _metrics_schedule(app: FastAPI, settings: ServerSettings, store: EntityStore) -> MetricsScheduler | None:
    """The metrics stored and purged on their schedule and started, unless its interval is 0 (MHS-05)."""
    if settings.metrics_persist_interval_minutes == 0:
        return None
    search_store: ElasticsearchStore = app.state.store

    async def connected() -> bool:
        return (await search_store.health()).status is HealthStatus.UP

    service = MetricsService(
        store, app.state.metrics_util, namespace=settings.cluster_name, ttl_hours=settings.metrics_ttl_hours
    )
    scheduler = MetricsScheduler(service, connected, interval_minutes=settings.metrics_persist_interval_minutes)
    scheduler.start()
    return scheduler


def _task_worker(app: FastAPI, settings: ServerSettings, store: EntityStore) -> TaskWorker | None:
    """The worker of the application's tasks, woken by the store's writes and started, when tasks are enabled."""
    if not settings.tasks_enabled:
        return None
    worker = TaskWorker(app.state.task_management, poll_seconds=settings.task_poll_seconds)
    store.task_listeners.append(worker.wake)
    worker.start()
    app.state.task_worker = worker
    return worker
