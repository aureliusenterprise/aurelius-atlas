# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-568. A tenant's indices are the default names under `aurelius-atlas-tenant-<alias>`

- **Status:** Proposed
- **Increment:** 15.2
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** A tenant other than the operator organization stores its catalogue in the indices a single-tenant
deployment has, with the prefix `aurelius-atlas` replaced by `aurelius-atlas-tenant-<alias>`:
`aurelius-atlas-tenant-acme-entities`, `aurelius-atlas-tenant-acme-typedefs`, and so on. The stores already take
their prefix or index name as a parameter, so a tenant's store set is the default one built with another prefix.

**Reason.** Isolation holds by construction: a store built for acme can only name acme's indices, so no query
can forget a filter (ADR 063). The `tenant-` segment keeps a tenant's names from ever being a default name
(DD-565). The prefix stays under `aurelius-atlas-*`, so the snapshot policy, which takes every index of that
pattern (SNP-01), and one store role cover every tenant.

**Alternatives.**

- A tenant field on every document of shared indices: rejected by ADR 063.
- An Elasticsearch filtered alias per tenant over shared indices: the filter is still one missed alias away
  from a leak, and removing a tenant is a delete-by-query.

**Consequences.** Each tenant adds about ten indices to the cluster. A tenant's removal (15.3) deletes
`aurelius-atlas-tenant-<alias>-*`.

### DD-569. The provisioned tenants' store sets are opened when the server starts

- **Status:** Proposed
- **Increment:** 15.2
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** With tenancy on, the server opens the store set of each tenant in `tenancy_tenants` when it starts,
in the same way it opens the default: it creates the indices that are missing, loads the type registry and the
models, and recovers interrupted writes. A request reads a store set that is already open.

**Reason.** The list of provisioned tenants is a setting until 15.3, so it is known at start and changes only
with a restart. Opening at start keeps a request from paying for index creation and model loading, and keeps
creation away from any token: only a configured tenant gets indices (DD-565). Reusing the default's start
sequence means a tenant's catalogue behaves as a single-tenant one does from its first request.

**Alternatives.**

- Open a tenant's store set on its first request: the first request waits seconds for the models, and two
  replicas race to create it.
- Create the indices and load the models in 15.3's CLI already: that is 15.3's scope, and until then a tenant
  could not be tried.

**Consequences.** Each tenant adds a model load to the start, a few seconds with Atlas's models. 15.3 moves the
creation and the model load to provisioning, and the server then only opens what the tenants index lists.

### DD-570. The routes read the request's store set through one lookup

- **Status:** Proposed
- **Increment:** 15.2
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** `app.state.tenant_stores` maps each tenant to its `TenantStores`: the type registry, the typedef,
entity and entity audit stores, the entity documents and the task management. `stores(request)` answers the
request's store set: the default one without a tenant or for the operator organization, else the tenant's. Every
route and route dependency that read a store from `app.state` reads it from `stores(request)`. The default store
set stays on `app.state` too, for the workers and the start.

**Reason.** The routes already reach the stores through a handful of dependencies and `app.state` reads. Changing
those few places moves every route to its tenant at once, and a test can check the lookup instead of each
route. A request whose tenant has no store set is a server fault, since 15.1 refuses every tenant that isn't
provisioned.

**Alternatives.**

- A store set bound in a context variable, read by the stores themselves: the core would learn of tenants, and
  a store could act for a tenant other than the one it was built for.
- One application per tenant, mounted by path: the dashboards' and the API's paths would change.

**Consequences.** A new route must read its stores through `stores(request)`. The server's `AGENTS.md` says so.

### DD-571. Workers and the deployment's own state stay on the default until 15.4

- **Status:** Proposed
- **Increment:** 15.2
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** The task worker, the App Search, embedding, audit-aging and metrics-history workers, and the
server's start audit keep running on the default store set alone. The store's health, the import and export
lock and the server's statistics stay one per deployment.

**Reason.** Each worker needs its own lifecycle per tenant, which is 15.4's scope. With them on the default
alone, a tenant's catalogue answers every read and write, and only the derived data waits: deferred tasks, App
Search documents, embeddings and metrics history. Tenancy is not offered until 15.4 (DD-566), so no deployment
sees the gap. The store's health is the cluster's, and the server's statistics describe the process, so neither
belongs to a tenant.

**Alternatives.**

- Start the workers per tenant now: doubles this increment and splits the workers' change across two pull
  requests.

**Consequences.** With tasks on, a tenant's propagation waits for 15.4. The tests run with tasks off, where a
request propagates at once (DD-081).
