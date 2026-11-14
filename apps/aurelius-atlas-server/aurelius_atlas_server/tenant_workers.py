"""The background work of each store set, and the store sets kept in step with the tenants index (WPT-01 to WPT-04).

Every open store set runs its own task worker, App Search worker, embedding worker, audit aging and metrics
history, as the settings turn them on (DD-576). They start as the store set opens and stop before it closes. With
tenancy on, ``TenantFollower`` reads the tenants index in the background, so a tenant's store set opens and closes
without a request (DD-577).
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol

from aurelius_atlas_core.app_search_governance import GovernanceIndexer
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.app_search_quality import QualityIndexer
from aurelius_atlas_core.audit_reduction_service import AtlasAuditReductionService
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_embedding_indexer import EntityEmbeddingIndexer
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.metrics_service import MetricsService
from aurelius_atlas_core.metrics_util import AtlasMetricsUtil
from aurelius_atlas_store_es import ElasticsearchStore, HealthStatus
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_server.app_search import AppSearchWorker
from aurelius_atlas_server.audit_aging_scheduler import AuditAgingScheduler
from aurelius_atlas_server.embedding import EmbeddingClient, EmbeddingWorker
from aurelius_atlas_server.metrics_scheduler import MetricsScheduler
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.task_worker import TaskWorker
from aurelius_atlas_server.tenancy import Tenancy
from aurelius_atlas_server.tenant_stores import TenantStores, TenantStoreSets
from aurelius_atlas_server.tenants import TenantDirectory

__all__ = [
    "MIN_FOLLOW_SECONDS",
    "StoreSetWorkers",
    "TenantFollower",
    "WorkerFactory",
    "app_search_worker",
    "audit_aging",
    "embedding_worker",
    "metrics_schedule",
    "task_worker",
]

LOGGER = logging.getLogger("aurelius-atlas-server")

MIN_FOLLOW_SECONDS = 1.0
"""The shortest interval between two background reads of the tenants index (WPT-04)."""


class Worker(Protocol):
    """A background worker: stopped when its store set closes."""

    async def stop(self) -> None:
        """Stop; a second stop does nothing."""
        ...


@dataclass
class StoreSetWorkers:
    """The workers of one store set; ``task_worker`` is woken by its entity store's writes (TSK-04)."""

    task_worker: TaskWorker | None = None
    others: list[Worker] = field(default_factory=list[Worker])

    async def stop(self) -> None:
        """Stop every worker of the store set (WPT-02)."""
        for worker in [*self.others, *([] if self.task_worker is None else [self.task_worker])]:
            await worker.stop()


class WorkerFactory:
    """Starts and stops the workers of each store set, as ``settings`` turn them on (WPT-01 to WPT-03).

    ``store`` answers the metrics history's health check; ``embedder``, shared by every store set, is None while
    embedding is off.
    """

    def __init__(
        self,
        settings: ServerSettings,
        store: ElasticsearchStore,
        metrics_util: AtlasMetricsUtil,
        embedder: EmbeddingClient | None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._metrics_util = metrics_util
        self._embedder = embedder
        self.running: dict[str, StoreSetWorkers] = {}

    async def started(self, stores: TenantStores) -> None:
        """Start the store set's workers (WPT-01, WPT-02)."""
        settings = self._settings
        workers = StoreSetWorkers(task_worker=task_worker(settings, stores))
        workers.others = [
            worker
            for worker in (
                audit_aging(settings, stores.entity_store),
                metrics_schedule(settings, self._store, self._metrics_util, stores.entity_store),
                embedding_worker(settings, self._embedder, stores.documents),
                app_search_worker(settings, stores.documents, stores.registry),
            )
            if worker is not None
        ]
        self.running[stores.prefix] = workers

    async def stopping(self, stores: TenantStores) -> None:
        """Stop the store set's workers, before it closes (WPT-02)."""
        workers = self.running.pop(stores.prefix, None)
        if workers is not None:
            await workers.stop()

    async def stop(self) -> None:
        """Stop every store set's workers: the server stops (WPT-02)."""
        for prefix in list(self.running):
            await self.running.pop(prefix).stop()


class TenantFollower:
    """Reads the tenants index every ``seconds``, one at least, and keeps the open store sets in step with it
    (WPT-04, DD-577).
    """  # noqa: D205 - one sentence

    def __init__(
        self,
        directory: TenantDirectory,
        sets: TenantStoreSets,
        *,
        seconds: float,
        sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
    ) -> None:
        self._directory = directory
        self._sets = sets
        self._seconds = max(seconds, MIN_FOLLOW_SECONDS)
        self._sleep = sleep
        self._running: asyncio.Task[None] | None = None

    async def follow_once(self) -> Tenancy | None:
        """Read the index and open and close the store sets it calls for; a failure is logged, tried again later."""
        try:
            tenancy = await self._directory.load()
            await self._sets.follow(tenancy)
        except Exception:
            LOGGER.exception("Following the tenants index failed")
            return None
        return tenancy

    def start(self) -> None:
        """Run in the background, the first read one interval from now: the start has just read the index."""
        self._running = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop following."""
        if self._running is not None:
            self._running.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._running
            self._running = None

    async def _loop(self) -> None:
        while True:
            await self._sleep(self._seconds)
            await self.follow_once()


def task_worker(settings: ServerSettings, stores: TenantStores) -> TaskWorker | None:
    """The worker of the store set's tasks, woken by its entity store's writes and started, when tasks are enabled
    (TSK-04).
    """  # noqa: D205 - one sentence
    if not settings.tasks_enabled:
        return None
    worker = TaskWorker(stores.task_management, poll_seconds=settings.task_poll_seconds)
    stores.entity_store.task_listeners.append(worker.wake)
    worker.start()
    return worker


def audit_aging(settings: ServerSettings, store: EntityStore) -> AuditAgingScheduler | None:
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


def metrics_schedule(
    settings: ServerSettings, search_store: ElasticsearchStore, metrics_util: AtlasMetricsUtil, store: EntityStore
) -> MetricsScheduler | None:
    """The metrics stored and purged on their schedule and started, unless its interval is 0 (MHS-05)."""
    if settings.metrics_persist_interval_minutes == 0:
        return None

    async def connected() -> bool:
        return (await search_store.health()).status is HealthStatus.UP

    service = MetricsService(store, metrics_util, namespace=settings.cluster_name, ttl_hours=settings.metrics_ttl_hours)
    scheduler = MetricsScheduler(service, connected, interval_minutes=settings.metrics_persist_interval_minutes)
    scheduler.start()
    return scheduler


def embedding_worker(
    settings: ServerSettings, embedder: EmbeddingClient | None, documents: ElasticsearchEntityDocuments
) -> EmbeddingWorker | None:
    """The worker that embeds the store set's entities through the shared client, started when embedding is on
    (VEC-07, WPT-03).
    """  # noqa: D205 - one sentence
    if embedder is None:
        return None
    indexer = EntityEmbeddingIndexer(
        documents,
        embedder,
        batch_size=settings.embedding_batch_size,
        wait_for_documents=settings.app_search_enabled,  # a document comes only while its indexer runs (DD-540)
    )
    worker = EmbeddingWorker(indexer, poll_seconds=settings.embedding_poll_seconds)
    worker.start()
    return worker


def app_search_worker(
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
