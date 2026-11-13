"""Tenant stores: each tenant's own indices and type registry, and the request's store set (TSS-01 to TSS-08).

With tenancy off, or for the operator organization, the store set is the default one, the indices of a
single-tenant deployment (TSS-01, TSS-02). Another tenant's indices carry its alias in their prefix (TSS-03,
DD-568). The provisioned tenants' store sets are opened at start, as the default is (TSS-04), and a tenant
provisioned later on its first request (TPR-08). The routes read their stores through ``stores(request)`` (TSS-06,
DD-570).
"""

import asyncio
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from aurelius_atlas_core.atlas_audit_service import AtlasAuditService
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_audit_repository import ElasticsearchEntityAuditRepository
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_documents import GOV_QUALITY, INDEX_PREFIX, ElasticsearchEntityDocuments, LinkedKind
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.model_loader import ModelLoader
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.typedef_audit_listener import BufferedTypeDefAuditListener
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_typesystem.registry import TypeRegistry
from fastapi import Request

from aurelius_atlas_server.tenancy import Tenancy

__all__ = [
    "STORE_SUFFIXES",
    "TENANT_SEGMENT",
    "TenantStoreSets",
    "TenantStores",
    "index_prefix",
    "load_models",
    "open_request_stores",
    "open_stores",
    "store_aliases",
    "stores",
    "tenant_prefix",
]

TENANT_SEGMENT = "tenant"
"""What sets a tenant's indices apart from the default ones: ``aurelius-atlas-tenant-<alias>-*`` (DD-565, DD-568)."""

STORE_SUFFIXES = (
    "entities",
    "unique-values",
    "entity-journal",
    *(kind.value for kind in LinkedKind),
    GOV_QUALITY,
    "entity-audits",
    "typedefs",
)
"""The alias of each index a store set opens, after its prefix; removal deletes what is behind them (DD-574)."""

type Opener = Callable[[str], Awaitable["TenantStores"]]
"""Opens the store set of an index prefix."""


@dataclass(frozen=True)
class TenantStores:
    """One tenant's catalogue: its type registry and the stores over its indices (TSS-03, TSS-05)."""

    prefix: str
    registry: TypeRegistry
    documents: ElasticsearchEntityDocuments
    entity_store: EntityStore
    entity_audits: ElasticsearchEntityAuditRepository
    typedef_store: TypedefStore
    task_management: TaskManagement
    admin_audits: AtlasAuditService
    notifier: EntityChangeNotifier


def index_prefix(tenant: str | None, tenancy: Tenancy | None) -> str:
    """The prefix of a tenant's indices: the default for no tenant or the operator organization, else the tenant's
    (TSS-01 to TSS-03).
    """  # noqa: D205 - one sentence
    if tenant is None or tenancy is None or tenant == tenancy.operator_organization:
        return INDEX_PREFIX
    return tenant_prefix(tenant)


def tenant_prefix(alias: str) -> str:
    """The prefix of the indices of a tenant other than the operator organization (TSS-03, DD-568)."""
    return f"{INDEX_PREFIX}-{TENANT_SEGMENT}-{alias}"


async def open_stores(
    store: ElasticsearchStore,
    prefix: str,
    *,
    models_dirs: Sequence[Path],
    embedding_dimensions: int | None,
    typedef_refresh_seconds: float,
) -> TenantStores:
    """Open the store set of the prefix on the open store: its indices created when missing, its registry loaded
    from its type definitions, the models loaded, interrupted writes recovered (TSS-04, ENS-01, ENS-07, TDS-12,
    MDL-16).
    """  # noqa: D205 - one sentence
    client = store.client
    registry = TypeRegistry()
    documents = ElasticsearchEntityDocuments(client, prefix, embedding_dimensions=embedding_dimensions)
    entity_store = EntityStore(registry, documents)
    await entity_store.prepare()
    entity_audits = ElasticsearchEntityAuditRepository(client, prefix)
    await entity_audits.prepare()
    typedef_store = TypedefStore(
        registry,
        ElasticsearchTypedefDocument(client, f"{prefix}-typedefs"),
        usage=entity_store.type_in_use,
        refresh_seconds=typedef_refresh_seconds,
    )
    await typedef_store.load()
    admin_audits = AtlasAuditService(entity_store)
    await load_models(typedef_store, admin_audits, models_dirs)
    await entity_store.recover()
    notifier = EntityChangeNotifier(entity_store, [EntityAuditListener(entity_audits, entity_store.now)])
    return TenantStores(
        prefix=prefix,
        registry=registry,
        documents=documents,
        entity_store=entity_store,
        entity_audits=entity_audits,
        typedef_store=typedef_store,
        task_management=TaskManagement(entity_store, notifier=notifier, audits=entity_audits),
        admin_audits=admin_audits,
        notifier=notifier,
    )


def store_aliases(prefix: str) -> list[str]:
    """The alias of each index of the prefix's store set (TPR-05, DD-574)."""
    return [f"{prefix}-{suffix}" for suffix in STORE_SUFFIXES]


class TenantStoreSets(Mapping[str, TenantStores]):
    """The open store sets by index prefix: the default always, a tenant's opened on demand (TPR-08).

    ``opener`` opens a store set that provisioning made, without loading the models again.
    """

    def __init__(self, opened: dict[str, TenantStores], opener: Opener) -> None:
        self._opened = opened
        self._opener = opener
        self._lock = asyncio.Lock()

    def __getitem__(self, prefix: str) -> TenantStores:
        return self._opened[prefix]

    def __iter__(self) -> Iterator[str]:
        return iter(self._opened)

    def __len__(self) -> int:
        return len(self._opened)

    async def ensure(self, prefix: str) -> TenantStores:
        """The store set of the prefix, opened first when it isn't open; one opening at a time."""
        if prefix in self._opened:
            return self._opened[prefix]
        async with self._lock:
            if prefix not in self._opened:
                self._opened[prefix] = await self._opener(prefix)
            return self._opened[prefix]

    def retain(self, prefixes: frozenset[str]) -> None:
        """Close to requests every tenant's store set whose prefix isn't among ``prefixes``; never the default's."""
        for prefix in [prefix for prefix in self._opened if prefix != INDEX_PREFIX and prefix not in prefixes]:
            del self._opened[prefix]


async def open_request_stores(request: Request, tenancy: Tenancy | None) -> None:
    """Open the store set of the request's tenant when it isn't, and close those of tenants no longer provisioned
    (TPR-07, TPR-08).
    """  # noqa: D205 - one sentence
    if tenancy is None:
        return
    sets: TenantStoreSets = request.app.state.tenant_stores
    sets.retain(frozenset(index_prefix(tenant, tenancy) for tenant in tenancy.tenants))
    tenant: str | None = getattr(request.state, "tenant", None)
    if tenant is not None:
        await sets.ensure(index_prefix(tenant, tenancy))


async def load_models(store: TypedefStore, audits: AtlasAuditService, models_dirs: Sequence[Path]) -> None:
    """Load the models directories in order, changes audited, the start's writes held to one (ADA-03, DD-316, MDD-01).

    One write per change adds a store refresh each to the start, minutes for Atlas's whole catalogue — long
    enough for the container's health check to give up before the server answers.
    """
    boot_audits = BufferedTypeDefAuditListener(audits)
    store.change_listeners.append(boot_audits)
    loader = ModelLoader(store)
    for models_dir in models_dirs:
        await loader.load(models_dir)
    await boot_audits.flush()


def stores(request: Request) -> TenantStores:
    """The store set of the request's tenant: the default without one or for the operator organization (TSS-06).

    Raises:
        LookupError: When the tenant has no store set open; 15.1 refuses a tenant that isn't provisioned, so this
            is a server fault.
    """
    tenant: str | None = getattr(request.state, "tenant", None)
    prefix = index_prefix(tenant, request.app.state.tenancy)
    opened: Mapping[str, TenantStores] = request.app.state.tenant_stores
    if prefix not in opened:
        msg = f"no store set is open for tenant {tenant}"
        raise LookupError(msg)
    return opened[prefix]
