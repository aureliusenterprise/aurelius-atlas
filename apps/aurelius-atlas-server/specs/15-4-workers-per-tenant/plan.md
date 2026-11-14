# Plan: 15.4 Workers per tenant

The rules are WPT-01 to WPT-11 of [the spec](./spec.md), the design DD-576 to DD-579.

## Analysis

- **The workers:** `app.py` builds them from the default store set in its lifespan (`_task_worker`,
  `_audit_aging`, `_metrics_schedule`, `_embedding_worker`, `_app_search_worker`). Each takes one entity store,
  document store or registry, so they move unchanged into a module that starts them for any store set.
- **Their lifetime:** `TenantStoreSets` opens a store set on demand (`ensure`) and drops one (`retain`). It takes
  two callbacks, opened and closing, and `retain` becomes awaited, so the workers start and stop with the set.
- **The background read:** `TenantDirectory.load` and the store sets' `ensure` and `retain` already do the work
  a request does; a loop calls them every interval.
- **The lock:** `routes/admin.py` reads `app.state.import_export_lock` in two places; the request's store set
  holds it instead.
- **The chart:** `job-restore.yaml` is the pattern for a Job in the server's image with its store settings; the
  Service and the store's network policy select by name and instance, so the Job's pod needs its own component.

## Steps

1. `tenant_workers.py`: `StoreSetWorkers` and `WorkerFactory` (the workers moved from `app.py`), `TenantFollower`.
2. `tenant_stores.py`: `TenantStores.import_export_lock`; `TenantStoreSets` with its callbacks, `add`, `follow`,
   `close`, and `retain` awaited.
3. `app.py`: the shared embedding client, the store sets' workers, the follower.
4. `routes/admin.py`: the request's store set's lock.
5. `provisioning.py`: `--existing-ok`; removal waits twice the interval.
6. Chart: `tenancy` values, the Deployment's settings, `job-provision-tenants.yaml`, the Service's selector.
7. Standalone: `ATLAS_TENANCY_ENABLED`, the README's tenants section.
8. Tests; ledger: roadmap status, `AGENTS.md` of the server and the chart.

## Verification

Level 0: `pytest apps/aurelius-atlas-server/tests tests`, ruff, pyright; the hooks at commit.
