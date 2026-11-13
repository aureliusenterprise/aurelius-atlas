# Plan: 15.3 Tenant provisioning

The rules are TPR-01 to TPR-09 of [the spec](./spec.md), the design DD-572 to DD-575.

## Analysis

- **The stand-in:** 15.1's `Tenancy.tenants` is a frozen set from `tenancy_tenants`, read by
  `Tenancy.is_provisioned` (TEN-04) inside `user_of`, which the middleware and the sign-in client call. 15.2 opens
  a store set per listed tenant at start (`_open_store_sets`).
- **A view that changes:** `user_of` stays synchronous; the middleware reads the directory first
  (`TenantDirectory.current`, an awaited read when due) and hands its `Tenancy` down. The sign-in client takes
  a callable answering the directory's latest `Tenancy`, and the login route reads the directory before the
  code exchange.
- **Opening on demand:** `TenantStoreSets` keeps the open store sets as a mapping, so `stores(request)` and the
  tests read it as before. The middleware opens the request's tenant's store set after the user is known, and
  closes those whose tenant left `active`.
- **The command:** `snapshots.py` is the pattern: `parser`, `run`, `main`, the settings from the environment.
  `open_stores` is the start sequence; `ImportService` with an `EntityWriter` and `AuditsWriter` is what
  `admin/import` runs.
- **Removal:** `store_aliases(prefix)` lists the aliases a store set opens, and a test pins it to what opening
  creates. The indices behind each are resolved and deleted by name (DD-574).
- **The store client:** the server now imports `elasticsearch` itself (`NotFoundError`), so it declares the
  dependency its libraries already have.

## Steps

1. `tenants.py`: `StoredTenant`, `TenantState`, `TenantsIndex`, `TenantDirectory`.
2. `tenant_stores.py`: `STORE_SUFFIXES`, `store_aliases`, `tenant_prefix`, `TenantStores.notifier`,
   `TenantStoreSets`, `open_request_stores`.
3. `settings.py`: `tenancy_tenants` and its validator removed, `tenancy_refresh_seconds` added.
4. `app.py`: the directory built with the app, the index prepared and read at start, the store sets opened from
   it; `build_oidc(..., tenancy=)`.
5. `authentication.py`, `oidc_client.py`, `routes/login.py`: the directory read per request, a session of a
   tenant no longer provisioned signed out, the request's store set opened.
6. `provisioning.py`: `provision`, `trust`, `list`, `remove`.
7. Tests: `test__aurelius_atlas_server_tenants.py`, `test__aurelius_atlas_server_provisioning.py`; the 15.1 and
   15.2 suites record their tenants in the index (`record_tenants` in `conftest.py`).
8. Ledger: roadmap status; server `AGENTS.md`.

## Verification

Level 0: `pytest apps/aurelius-atlas-server/tests`, ruff, pyright; the hooks at commit.
