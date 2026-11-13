# Plan: 15.2 Tenant-scoped stores

The rules are TSS-01 to TSS-09 of [the spec](./spec.md), the design DD-568 to DD-571.

## Analysis

- **The stores take a prefix already:** `ElasticsearchEntityDocuments(client, prefix)` names the entities,
  unique values, journal, relationships, classifications, tasks and governance verdicts under it;
  `ElasticsearchEntityAuditRepository(client, prefix)` the audit alias; and
  `ElasticsearchTypedefDocument(client, index)` takes the typedef index whole, `aurelius-atlas-typedefs` by
  default, which is `<prefix>-typedefs`.
- **The start:** the lifespan in `app.py` builds the documents, the entity store, the audits, the typedef store
  and the task management, loads the models and recovers. That sequence becomes
  `open_stores(store, prefix, ...)`, run for the default and for each tenant.
- **The routes:** `routes/entity.py::entity_store` and `routes/types.py::typedef_store` are the dependencies
  nearly every route uses; direct `app.state` reads are in `entity.py` (audits), `admin.py` (patches, audit
  details, tasks) and `app_search.py` (documents). Readiness and metrics read `app.state.store`, the cluster,
  which stays shared (TSS-08).
- **The workers:** started by the lifespan on the default's stores; unchanged (TSS-07).

## Steps

1. `tenant_stores.py`: `TenantStores`, `index_prefix(tenant, tenancy)`, `open_stores`, `stores(request)`.
2. `app.py`: the lifespan opens the default store set through `open_stores` and, with tenancy on, each tenant's;
   `app.state.tenant_stores`; the default's members stay on `app.state` for the workers.
3. Routes: `entity_store`, `typedef_store`, the audits, patches, audit details, tasks and App Search read
   `stores(request)`.
4. Tests: `test__aurelius_atlas_server_tenant_stores.py`; the existing suite for TSS-09.
5. Ledger: DV-164, roadmap status, server `AGENTS.md`.

## Verification

Level 0: `pytest apps/aurelius-atlas-server/tests`, ruff, pyright; the hooks at commit.
