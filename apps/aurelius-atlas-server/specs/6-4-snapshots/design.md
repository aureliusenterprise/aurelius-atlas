# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-355. The store takes its own snapshots; the server puts the policy

- **Status:** Proposed
- **Increment:** 6.4e
- **Date:** 2026-11-05

**Decision.** Elasticsearch's snapshot lifecycle management takes the snapshots, on the policy's schedule, and
deletes them after their retention. The server registers the repository and puts the policy when it starts,
from its settings, the way it creates its indices.

**Reason.** A schedule inside the store runs whether or not a server is up, and Elasticsearch records each run's
outcome where it can be read (R6). The server already owns what its store holds (its indices, mappings and
settings), and it is the one part that knows which indices are its own. Putting the policy again on every start
is idempotent and keeps it equal to the settings.

**Alternatives.** A Kubernetes CronJob calling the snapshot API: a second scheduler, absent from dev, and a
snapshot that no Elasticsearch retention deletes. Volume snapshots of the data claim: a copy of a running node's
files is not a consistent store (ADR 026's second alternative), and the storage class decides whether it exists.

**Consequences.** The store's user needs the snapshot privileges; the server uses `elastic`, which has them.
Several servers put the same policy; the last start wins, and they share their settings. A store without
`path.repo` fails a start with snapshots on: snapshots that were asked for are not silently skipped.

### DD-356. The snapshots live on a volume of their own, kept on uninstall

- **Status:** Proposed
- **Increment:** 6.4e
- **Date:** 2026-11-05

**Decision.** `path.repo` is a volume apart from the data: a named volume in dev, and in the chart a
`PersistentVolumeClaim` of its own, not a second `volumeClaimTemplate`, annotated `helm.sh/resource-policy:
keep`. The repository is a shared-filesystem one.

**Reason.** A lost or corrupted data volume, a bad migration or a mistaken purge leaves the snapshots. A
StatefulSet's claim templates cannot change, so an installed store could not take a second one on upgrade; a
claim of its own can be added to the pod template. Removing the release removes the store, not its backups.
The repository stays inside the system's boundary (R4).

**Alternatives.** An object store repository (S3, GCS, Azure), which Elasticsearch supports: it survives the
loss of the cluster, but it is a third party's storage and a credential to manage, a decision for each
deployment. The data volume itself: lost with what it protects.

**Consequences.** On a cluster, the claim survives the loss of the node but not of the cluster or its storage
backend; a copy elsewhere is the deployment's, named on the Disaster Recovery page. Snapshots are incremental,
so the claim holds about one copy of the indices and what changed within the retention.

### DD-357. A restore replaces the server's indices, and runs while no server does

- **Status:** Proposed
- **Increment:** 6.4e
- **Date:** 2026-11-05

**Decision.** The restore brings back every index `aurelius-atlas-*` with its aliases, never the cluster's
global state. A store that holds any of them is refused unless `--replace` deletes them all first. The command
runs from the server's image; in a cluster, the chart's restore Job runs it, and renders only at
`replicaCount` 0.

**Reason.** The server's indices are one consistent whole: an entity, its relationships, its audits and the
journal must come from the same moment, so a restore never mixes a snapshot's indices with newer ones. A server
writing during the restore would create an index that the restore must bring back, and the restore would fail
or the server would read a half-restored store. The global state holds the cluster's users, templates and
settings, which belong to the cluster, not to the catalogue.

**Alternatives.** Restoring under new names and moving the aliases: no deletion, but the server's index names
are fixed (`<alias>-000001`), and a second copy needs twice the disk. Closing the indices instead of deleting
them: Elasticsearch restores over a closed index, but one the snapshot does not hold would stay.

**Consequences.** `--replace` loses everything written after the snapshot; the Backup & Restore procedure says
to take a snapshot of the broken store first. The chart's restore needs two upgrades: scale to 0 and restore,
then scale back.

### DD-358. The server checks that the snapshots succeed and reports the last success as a gauge

- **Status:** Proposed
- **Increment:** 6.4e
- **Date:** 2026-11-05

**Decision.** With snapshots on, the server reads the policy's last success and failure every 15 minutes,
logs a failed run as an error, and reports the last success's time as the gauge
`aurelius_atlas.snapshot.last_success`. A Grafana rule fires when it is more than two hours old.

**Reason.** A snapshot that fails without anyone hearing of it is ADR 026's "backups decay" (R6), and ADR 040
says the system raises its hand. Elasticsearch exports no snapshot metrics through the store's metrics puller.
The server already exports over OTLP and runs scheduled jobs. A gauge of the last success catches every way a
snapshot goes missing: a failed run, a deleted policy, a stopped store. A count of failures misses the last two.

**Alternatives.** The Elasticsearch exporter for Prometheus, which reports SLM statistics: another workload
with its own credentials, beside the puller. An alert on the error log: misses a schedule that stopped running.

**Consequences.** The rule's two hours fit the hourly default; a slower schedule needs the rule changed with
it. No server, no gauge: then "Server silent" fires instead, and the rule's no-data state is OK, as in dev
where snapshots are off.
