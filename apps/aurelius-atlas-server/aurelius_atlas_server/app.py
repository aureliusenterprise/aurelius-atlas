"""The FastAPI application: settings, the store's lifetime, error handling and routers (DD-015, DD-016)."""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator, Callable, Sequence
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import httpx2 as httpx
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_core.app_search_governance import GovernanceIndexer
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.app_search_quality import QualityIndexer
from aurelius_atlas_core.atlas_audit_service import AtlasAuditService
from aurelius_atlas_core.audit_reduction_service import AtlasAuditReductionService
from aurelius_atlas_core.entity_documents import INDEX_PREFIX, ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_embedding_indexer import EntityEmbeddingIndexer
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.metrics_service import MetricsService
from aurelius_atlas_core.metrics_util import AtlasMetricsUtil
from aurelius_atlas_model.atlas_audit import AuditOperation
from aurelius_atlas_otel import (
    ClientCredentialsTokenSource,
    bridge_logging,
    build_otlp_log_processor,
    build_otlp_pipeline,
    setup_telemetry,
)
from aurelius_atlas_store_es import ElasticsearchStore, HealthStatus
from aurelius_atlas_store_es.snapshots import SnapshotStatus, prepare_snapshots, snapshot_status
from aurelius_atlas_typesystem.registry import TypeRegistry
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from opentelemetry import metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from aurelius_atlas_server.app_search import AppSearchWorker
from aurelius_atlas_server.audit_aging_scheduler import AuditAgingScheduler
from aurelius_atlas_server.authentication import AuthenticationMiddleware, SessionStore
from aurelius_atlas_server.embedding import EmbeddingClient, EmbeddingWorker, embedding_http
from aurelius_atlas_server.errors import AtlasError, AtlasJSONResponse, atlas_error_handler
from aurelius_atlas_server.metrics_scheduler import MetricsScheduler
from aurelius_atlas_server.oidc_client import OidcClient
from aurelius_atlas_server.openapi import install as install_openapi
from aurelius_atlas_server.request_context import RequestContextMiddleware
from aurelius_atlas_server.routes import (
    ADMIN,
    APP_SEARCH,
    DISCOVERY,
    ENTITY,
    GLOSSARY,
    LINEAGE,
    LOGIN,
    QUALITY,
    RELATIONSHIP,
    SEARCH_BY_MEANING,
    TYPES,
)
from aurelius_atlas_server.security_headers import SecurityHeadersMiddleware
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.snapshot_watcher import SnapshotWatcher
from aurelius_atlas_server.task_worker import TaskWorker
from aurelius_atlas_server.tenancy import Tenancy
from aurelius_atlas_server.tenant_stores import TenantStores, TenantStoreSets, index_prefix, open_stores
from aurelius_atlas_server.tenants import TenantDirectory, TenantsIndex

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


def build_oidc(
    settings: ServerSettings,
    auth: KeycloakAuth,
    http: httpx.AsyncClient | None = None,
    *,
    tenancy: Callable[[], Tenancy | None] | None = None,
) -> OidcClient:
    """The server's client at the provider, which browsers sign in with (AUT-05); ``tenancy`` answers the latest
    provisioned tenants while tenancy is on (TPR-07).
    """  # noqa: D205 - one sentence
    return OidcClient(
        auth,
        client_id=settings.auth_client_id,
        client_secret=settings.auth_client_secret.get_secret_value(),
        principal_claim=settings.auth_principal_claim,
        groups_claim=settings.auth_groups_claim,
        tenancy=tenancy,
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
    (TSK-04, DD-080). With snapshots enabled, the store's snapshot policy is put and its runs watched (SNP-01 to
    SNP-03).
    """
    store = store if store is not None else ElasticsearchStore(settings.store_settings())
    tenancy = settings.tenancy()
    directory = (
        None
        if tenancy is None
        else TenantDirectory(tenancy, TenantsIndex(store), refresh_seconds=settings.tenancy_refresh_seconds)
    )
    auth, oidc, sessions = _authentication(settings, auth, oidc_http, directory)
    metrics_util = AtlasMetricsUtil()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        LOGGER.info("Starting %s %s", app.title, app.version)
        started = int(time.time() * 1000)
        _start(metrics_util)
        worker: TaskWorker | None = None
        schedules: list[
            AppSearchWorker | AuditAgingScheduler | EmbeddingWorker | MetricsScheduler | SnapshotWatcher
        ] = []
        await store.open()
        try:
            opened = await _open_store_sets(store, settings, directory)
            app.state.tenant_stores = opened
            default = opened[INDEX_PREFIX]
            # the default store set, which the workers and the start audit run on alone until 15.4 (TSS-07, DD-571)
            registry, documents, entity_store = default.registry, default.documents, default.entity_store
            app.state.type_registry, app.state.entity_documents = registry, documents
            app.state.entity_audits, app.state.typedef_store = default.entity_audits, default.typedef_store
            app.state.entity_store, app.state.task_management = entity_store, default.task_management
            worker = _task_worker(app, settings, entity_store)
            await _audit_server_status(default.admin_audits, started)
            schedules = [
                scheduler
                for scheduler in (
                    _audit_aging(settings, entity_store),
                    _metrics_schedule(app, settings, entity_store),
                    _embedding_worker(app, settings, documents),
                    _app_search_worker(settings, documents, registry),
                    await _snapshots(settings, store),
                )
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

    # The OpenAPI surface answers only under development (the dev .env sets it); production serves no spec
    # and no documents (SRV-08's closed surface). The docs page fetches the spec by root-relative path,
    # so it is a root-served dev convenience, not a root_path (proxy-prefix) surface (DD-363).
    app = FastAPI(
        title=NAME,
        version=version(NAME),
        lifespan=lifespan,
        default_response_class=AtlasJSONResponse,
        docs_url="/api/atlas/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/api/atlas/openapi.json" if settings.is_development else None,
    )
    # one export or import at a time (EXP-01, DD-304)
    app.state.settings, app.state.import_export_lock = settings, asyncio.Lock()
    app.state.store = store
    app.state.metrics_util = metrics_util
    app.state.embedder = None  # the embeddings client, once embedding is on and the server has started (DD-443)
    # the tenancy and its directory are None while it is off: no request has a tenant (TEN-01, TPR-09)
    app.state.auth, app.state.oidc, app.state.sessions = auth, oidc, sessions
    app.state.tenancy, app.state.tenant_directory = tenancy, directory
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
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts_enabled=settings.hsts_enabled,
        dev_docs_enabled=settings.is_development,
    )
    app.add_exception_handler(AtlasError, atlas_error_handler)
    for router in (
        ADMIN,
        TYPES,
        ENTITY,
        RELATIONSHIP,
        DISCOVERY,
        LINEAGE,
        GLOSSARY,
        LOGIN,
        SEARCH_BY_MEANING,
        QUALITY,
        APP_SEARCH,
    ):
        app.include_router(router)
    install_openapi(app)
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
    settings: ServerSettings,
    auth: KeycloakAuth | None,
    oidc_http: httpx.AsyncClient | None,
    directory: TenantDirectory | None,
) -> tuple[KeycloakAuth, OidcClient, SessionStore]:
    """The verifier, the sign-in client naming users by the directory's tenants, and the sessions (AUT-02 to
    AUT-06, TPR-07).
    """  # noqa: D205 - one sentence
    verifier = auth if auth is not None else build_auth(settings)
    tenancy = None if directory is None else (lambda: directory.tenancy)
    oidc = build_oidc(settings, verifier, oidc_http, tenancy=tenancy)
    return verifier, oidc, SessionStore(settings.session_timeout_seconds)


async def _open_store_sets(
    store: ElasticsearchStore, settings: ServerSettings, directory: TenantDirectory | None
) -> TenantStoreSets:
    """The default store set and, with tenancy on, each provisioned tenant's, by index prefix, the models loaded
    (TSS-01, TSS-04, TPR-08); a tenant provisioned later opens on demand, without them.
    """  # noqa: D205 - one sentence

    async def opened(prefix: str, models_dirs: Sequence[Path] = ()) -> TenantStores:
        return await open_stores(
            store,
            prefix,
            models_dirs=models_dirs,
            embedding_dimensions=_dimensions(settings),
            typedef_refresh_seconds=settings.typedef_refresh_seconds,
        )

    tenancy = None
    if directory is not None:
        await directory.index.prepare()
        tenancy = await directory.load()
    tenants = [] if tenancy is None else sorted(tenancy.tenants)
    sets: dict[str, TenantStores] = {}
    for prefix in [INDEX_PREFIX, *(index_prefix(tenant, tenancy) for tenant in tenants)]:
        sets[prefix] = await opened(prefix, settings.model_dirs)
    return TenantStoreSets(sets, opened)


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


async def _snapshots(settings: ServerSettings, store: ElasticsearchStore) -> SnapshotWatcher | None:
    """The snapshot policy put, and its watcher reporting and started, when snapshots are enabled (SNP-01 to SNP-03).

    A store that cannot hold the repository fails the start: snapshots that were asked for are not skipped.
    """
    if not settings.snapshot_enabled:
        return None
    await prepare_snapshots(store.client, settings.snapshot_policy())

    async def read() -> SnapshotStatus:
        return await snapshot_status(store.client)

    watcher = SnapshotWatcher(read, interval_minutes=settings.snapshot_check_minutes)
    watcher.register(metrics.get_meter(NAME))
    watcher.start()
    return watcher


def _dimensions(settings: ServerSettings) -> int | None:
    """The dimensions the entity index maps vectors of: the configured ones when embedding is on (VEC-03, VEC-08)."""
    return settings.embedding_dimensions if settings.embedding_url is not None else None


def _embedding_worker(
    app: FastAPI, settings: ServerSettings, documents: ElasticsearchEntityDocuments
) -> EmbeddingWorker | None:
    """The worker that embeds the store's entities, started when embedding is on; its client embeds the searches'
    queries too, as ``app.state.embedder`` (VEC-07, VEC-08, DD-443).
    """  # noqa: D205 - one sentence
    if settings.embedding_url is None:
        return None
    http = embedding_http(settings.embedding_ca_file)
    client = EmbeddingClient(
        str(settings.embedding_url), settings.embedding_model, settings.embedding_dimensions, http=http
    )
    app.state.embedder = client
    indexer = EntityEmbeddingIndexer(
        documents,
        client,
        batch_size=settings.embedding_batch_size,
        wait_for_documents=settings.app_search_enabled,  # a document comes only while its indexer runs (DD-540)
    )
    worker = EmbeddingWorker(indexer, poll_seconds=settings.embedding_poll_seconds, http=http)
    worker.start()
    return worker


def _app_search_worker(
    settings: ServerSettings, documents: ElasticsearchEntityDocuments, registry: TypeRegistry
) -> AppSearchWorker | None:
    """The worker that keeps the App Search documents, results, totals and verdicts up to date, started unless
    turned off (ASU-06, ASQ-07, ASG-06, DD-521).
    """  # noqa: D205 - one sentence
    if not settings.app_search_enabled:
        return None
    indexer = AppSearchIndexer(documents, registry, batch_size=settings.app_search_batch_size)
    quality = QualityIndexer(documents, batch_size=settings.app_search_batch_size)
    governance = GovernanceIndexer(documents, registry, batch_size=settings.app_search_batch_size)
    worker = AppSearchWorker(indexer, quality, governance, poll_seconds=settings.app_search_poll_seconds)
    worker.start()
    return worker


def _task_worker(app: FastAPI, settings: ServerSettings, store: EntityStore) -> TaskWorker | None:
    """The worker of the application's tasks, woken by the store's writes and started, when tasks are enabled."""
    if not settings.tasks_enabled:
        return None
    worker = TaskWorker(app.state.task_management, poll_seconds=settings.task_poll_seconds)
    store.task_listeners.append(worker.wake)
    worker.start()
    app.state.task_worker = worker
    return worker
