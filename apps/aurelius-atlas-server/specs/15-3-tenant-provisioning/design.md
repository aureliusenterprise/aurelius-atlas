# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-572. The tenants are records of an index of their own, with a state

- **Status:** Proposed
- **Increment:** 15.3
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** `aurelius-atlas-tenants` holds one document per tenant, its id the alias: `state`
(`provisioning`, `active`, `removing`), `trustsOperators`, `sample`, `createdAt`, `updatedAt` and `updatedBy`.
The document is a pydantic model, as every document the store writes (DD-560). Only `active` tenants are served.

**Reason.** The store is the one place a deployment keeps state, and a snapshot of `aurelius-atlas-*` takes the
tenants index with the tenants' catalogues, so a restore brings back both. The state lets provisioning and
removal take several steps without a request ever reaching a half-made or half-removed tenant: the record turns
`active` last and leaves `active` first.

**Alternatives.**

- The list in a setting, as in 15.1: provisioning would mean a configuration change and a restart.
- Keycloak's organization attributes as the record: the identity provider would hold storage state, and the
  server would call its admin API on every refresh.

**Consequences.** The `tenant-` segment keeps every tenant's indices apart from `aurelius-atlas-tenants`
(DD-568).

### DD-573. Provisioning is a command in the server's image, not an endpoint

- **Status:** Proposed
- **Increment:** 15.3
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** `python -m aurelius_atlas_server.provisioning provision|trust|list|remove` runs with the server's
settings, as the snapshot command does (SNP-04). It opens a tenant's store set with the server's own start
sequence, and imports a sample by the core's import service, as the server's `admin/import` does, without a
request.

**Reason.** Provisioning and removing a tenant are operator tasks (ADR 063). A command in the image runs where
the server's store settings already are: by hand, or as a Job in the chart (15.4). An endpoint would put tenant
management behind a token, and a fault in its authorization could create or delete any tenant. Reusing the
start sequence means a provisioned tenant holds exactly what a single-tenant catalogue holds after its first
start.

**Alternatives.**

- An admin endpoint of the operator organization: a larger attack surface, and a request that runs for the
  minutes a sample import takes.
- A separate tool: it would repeat the store's start and the import.

**Consequences.** The command needs the server's full settings, as the server does. A sample is a path to an
export ZIP that the command can read.

### DD-574. Removal deletes the indices behind the tenant's aliases, never a pattern

- **Status:** Proposed
- **Increment:** 15.3
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** `remove` resolves each of the tenant's aliases, the default store set's aliases under its prefix,
to the indices behind it, and deletes those by name. It never deletes by `aurelius-atlas-tenant-<alias>-*`.

**Reason.** A tenant `acme`'s pattern also matches every index of a tenant `acme-corp`:
`aurelius-atlas-tenant-acme-corp-entities` starts with `aurelius-atlas-tenant-acme-`. A delete by pattern would
remove another tenant's catalogue (ADR 063, R4). Elasticsearch also refuses a wildcard delete by default
(`action.destructive_requires_name`). Resolving the aliases finds rolled-over indices behind them too, such as
the audits' `-000002`.

**Alternatives.**

- Forbid aliases that prefix another: a tenant's name would depend on the names taken before it.
- A separator no alias can hold: `-` is the only one Keycloak's aliases and index names share.

**Consequences.** The list of a store set's aliases is kept with the store set, and a test checks it against
the aliases opening a store set creates, so a new index can't be forgotten by removal.

### DD-575. The server reads the provisioned tenants from the tenants index, kept current

- **Status:** Proposed
- **Increment:** 15.3
- **Date:** 2026-11-13
- **Supersedes:** DD-565's stand-in setting `tenancy_tenants`, and DD-569's opening at start alone

**Decision.** With tenancy on, the provisioned tenants are the operator organization and the tenants recorded
`active`. The server reads the tenants index at start and again when a request arrives and
`tenancy_refresh_seconds` (30 by default) have passed. A tenant that became `active` meanwhile is opened on its
first request, without a model load. One that left `active` is refused and its store set dropped.
`tenancy_tenants` is removed.

**Reason.** Provisioning while the server runs must not need a restart, and a removed tenant must stop being
served. A refresh on the request path, bounded by the interval, is how the type registry stays current across
replicas already (TDS-13), with no background task to start and stop. The models are loaded once by
provisioning; the start's load keeps them upgraded with the server (TSS-04).

**Alternatives.**

- Read the index on every request: one more store call per request.
- A background poller: a lifecycle of its own, and still an interval.
- Restart on provisioning: every tenant would pay for one tenant's change.

**Consequences.** A newly provisioned tenant waits up to the interval before its first request is served. A
removed one could be served up to the interval after its record went `removing`, so `remove` waits that long
before it deletes the indices. The tests set the interval to 0.
