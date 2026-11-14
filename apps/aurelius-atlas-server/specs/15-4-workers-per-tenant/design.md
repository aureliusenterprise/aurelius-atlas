# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-576. Each store set runs its own workers, started and stopped with it

- **Status:** Proposed
- **Increment:** 15.4
- **Date:** 2026-11-14
- **Supersedes:** DD-571, for the workers

**Decision.** The open store sets call back as a store set opens and before it closes. The server starts that
store set's task worker, App Search worker, embedding worker, audit aging and metrics history on the opening
call, each as the settings turn it on, and stops them on the closing one. The embedding service's client is
made once per server and shared. The start audit and the snapshot watcher stay one per server, on the default
store set.

**Reason.** Each worker already reads and writes one entity store, one document store and one type registry,
so a worker per store set needs no change in the workers themselves. Tying their lifetime to the store set's
means no worker writes into a tenant whose store set is closed. The embedding service is one deployment's, with
one HTTP connection pool, whatever the tenant. The start audit records the server's start, and the snapshots
take the whole store, so neither belongs to a tenant.

**Alternatives.**

- One worker of each kind, looping over the open store sets: every worker changes, and a slow tenant holds up
  the others.
- Workers only for the store sets opened at start: a tenant provisioned later waits for the next restart.

**Consequences.** The background work grows with the tenants, as ADR 063 accepts. `app.state.task_worker` and
`app.state.import_export_lock` still name the default store set's, which the single-tenant tests read.

### DD-577. The server follows the tenants index in the background, and removal waits two intervals

- **Status:** Proposed
- **Increment:** 15.4
- **Date:** 2026-11-14
- **Supersedes:** DD-575, for when the index is read; DD-574, for the wait before deleting

**Decision.** With tenancy on, a background task reads the tenants index every `tenancy_refresh_seconds`, one
second at least, opens the store set of each tenant newly `active` with its workers, and closes those of tenants
no longer `active`. Requests still read the directory when it is due (TPR-07). `remove` waits twice the
interval before it deletes the tenant's indices.

**Reason.** A tenant provisioned with a sample needs its App Search documents and embeddings before its first
user arrives, and a removed tenant's workers must stop even when no request comes. A server's next read after
a removal is at most one interval and the time of its last pass away; the second interval covers that pass and
the workers' stop, so no worker of any server still writes when the indices go. A write after its index is
deleted would create a plain index under the alias name, outside every tenant's aliases.

**Alternatives.**

- Keep reading only on requests: an idle server never starts a new tenant's workers nor stops a removed one's.
- A notification from the command to every server: the servers share only the store, and a missed message
  leaves a worker running.

**Consequences.** Removing a tenant takes a minute with the default interval.

### DD-578. The import and export lock is per store set

- **Status:** Proposed
- **Increment:** 15.4
- **Date:** 2026-11-14
- **Supersedes:** DD-571, for the lock

**Decision.** Each store set holds its own import and export lock. An export or import refuses another only in
the same store set (EXP-01, DD-304).

**Reason.** The lock keeps two imports or exports from interleaving their writes and reads in one catalogue. Two
tenants share no catalogue, so one tenant's import has no reason to refuse another's, and with one lock a
tenant's long import would refuse every other tenant's.

**Alternatives.**

- One lock per server, as in 15.2: tenants hold each other up.

**Consequences.** With tenancy off there is one store set, so one lock, as Atlas has.

### DD-579. The chart provisions the listed tenants with a hook Job, kept out of the Service

- **Status:** Proposed
- **Increment:** 15.4
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** With `tenancy.enabled`, the chart sets the server's tenancy settings, and with `tenancy.tenants`
it renders a Job as a post-install and post-upgrade hook. The Job runs the server's image with the server's
settings: one init container per tenant runs `provision <alias> --existing-ok`, with `--no-operator-trust` when
the tenant's `trustsOperators` is false, and the main container runs `list`. Its pod carries the server's labels,
which the store's network policy admits, with its own component; the Service selects the server's component
as well, so it never routes to the Job. A render fails for an alias that is not index-safe or is the operator
organization's.

**Reason.** A tenant listed in the values exists once the release is installed, without a step by hand, and
`--existing-ok` makes every upgrade a no-op for the tenants already there. Init containers run in order and
need no shell, which the hardened image doesn't have. Removing a tenant stays a deliberate command, not the
effect of a value deleted.

**Alternatives.**

- A Job per tenant: more objects for the same work, and they run in parallel against one tenants index.
- Provisioning at the server's start: every replica races to provision, and a failed provisioning fails the
  start.
- A readiness probe that never succeeds on the Job's pod: it hides the pod from the Service by a trick, and
  the pod reads as broken.

**Consequences.** The chart imports no sample into a tenant: the export ZIP isn't in the image, and the command
by hand imports one. Changing the Service's selector is allowed on an upgrade.
