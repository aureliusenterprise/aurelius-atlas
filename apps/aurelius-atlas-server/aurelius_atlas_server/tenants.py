"""The tenants index and the provisioned tenants the server reads from it (TPR-01, TPR-07, DD-572, DD-575).

``aurelius-atlas-tenants`` holds one record per tenant, its id the alias. Only a tenant recorded ``active`` is
served; provisioning and removal pass through ``provisioning`` and ``removing``, so no request reaches a tenant
half made or half removed. ``TenantDirectory`` keeps the server's view of the provisioned tenants current.
"""

import dataclasses
import time
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from aurelius_atlas_core.entity_documents import INDEX_PREFIX, WRITE_REFRESH
from aurelius_atlas_core.typedef_document import INDEX_SETTINGS, ensure_index
from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_store_es import ElasticsearchStore
from elasticsearch import NotFoundError

from aurelius_atlas_server.tenancy import Tenancy

__all__ = ["TENANTS_INDEX", "StoredTenant", "TenantDirectory", "TenantState", "TenantsIndex"]

TENANTS_INDEX = f"{INDEX_PREFIX}-tenants"
"""The alias of the tenants index; under ``aurelius-atlas-*``, so a snapshot takes it with the catalogues."""

MAX_TENANTS = 10_000
"""The most tenants a listing reads: one search page."""

TENANTS_MAPPING: dict[str, Any] = {
    "dynamic": "strict",
    "properties": {
        "alias": {"type": "keyword"},
        "state": {"type": "keyword"},
        "trustsOperators": {"type": "boolean"},
        "sample": {"type": "keyword"},
        "createdAt": {"type": "long"},
        "updatedAt": {"type": "long"},
        "updatedBy": {"type": "keyword"},
    },
}


class TenantState(StrEnum):
    """Where a tenant is in its life: only ``active`` is served (TPR-01, TPR-07)."""

    PROVISIONING = "provisioning"
    ACTIVE = "active"
    REMOVING = "removing"


class StoredTenant(AtlasModel):
    """One record of the tenants index; times in epoch milliseconds (TPR-01, DD-572)."""

    alias: str
    state: TenantState = TenantState.PROVISIONING
    trusts_operators: bool = True
    sample: str | None = None
    created_at: int = 0
    updated_at: int = 0
    updated_by: str | None = None


class TenantsIndex:
    """The tenants index of the store: its records read, written and deleted by alias (TPR-01).

    The store need not be open yet; each call uses its open client.
    """

    def __init__(self, store: ElasticsearchStore, alias: str = TENANTS_INDEX) -> None:
        self._store = store
        self.alias = alias

    async def prepare(self) -> None:
        """Create the index behind its alias unless it exists (DD-508's lost race included)."""
        if not await self._store.client.indices.exists_alias(name=self.alias):
            await ensure_index(
                self._store.client,
                index=f"{self.alias}-000001",
                aliases={self.alias: {"is_write_index": True}},
                mappings=TENANTS_MAPPING,
                settings=INDEX_SETTINGS,
            )

    async def get(self, alias: str) -> StoredTenant | None:
        """The tenant's record, or None."""
        try:
            found = await self._store.client.get(index=self.alias, id=alias)
        except NotFoundError:
            return None
        return StoredTenant.model_validate(found["_source"])

    async def put(self, tenant: StoredTenant) -> None:
        """Write the tenant's record, replacing any before it; the next read sees it."""
        await self._store.client.index(
            index=self.alias, id=tenant.alias, document=tenant.model_dump(by_alias=True), refresh=WRITE_REFRESH
        )

    async def delete(self, alias: str) -> None:
        """Delete the tenant's record; a missing one is no fault."""
        try:
            await self._store.client.delete(index=self.alias, id=alias, refresh=WRITE_REFRESH)
        except NotFoundError:
            return

    async def list(self) -> list[StoredTenant]:
        """Every recorded tenant, by alias; none while the index doesn't exist."""
        if not await self._store.client.indices.exists_alias(name=self.alias):
            return []
        found = await self._store.client.search(index=self.alias, size=MAX_TENANTS, query={"match_all": {}})
        tenants = [StoredTenant.model_validate(hit["_source"]) for hit in found["hits"]["hits"]]
        return sorted(tenants, key=lambda tenant: tenant.alias)


class TenantDirectory:
    """The server's view of the provisioned tenants: ``base`` with the ``active`` tenants of the index (TPR-07).

    The index is read by ``load`` and again by ``current`` once ``refresh_seconds`` have passed (DD-575).
    """

    def __init__(
        self,
        base: Tenancy,
        index: TenantsIndex,
        *,
        refresh_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._base = base
        self.index = index
        self._refresh = refresh_seconds
        self._clock = clock
        self._read_at: float | None = None
        self.tenancy = base

    async def load(self) -> Tenancy:
        """Read the index now: the operator organization and the ``active`` tenants are provisioned."""
        active = frozenset(tenant.alias for tenant in await self.index.list() if tenant.state is TenantState.ACTIVE)
        self.tenancy = dataclasses.replace(self._base, tenants=active)
        self._read_at = self._clock()
        return self.tenancy

    async def current(self) -> Tenancy:
        """The provisioned tenants, read again when the last read is ``refresh_seconds`` old (DD-575)."""
        if self._read_at is None or self._clock() - self._read_at >= self._refresh:
            return await self.load()
        return self.tenancy
