# Backup &amp; Restore

What is backed up, how often, how long it is kept, and how a snapshot comes back ([ADR 026](<https://aureliusenterprise.github.io/dependabot-pre_commit-prettier-plugin-toml-4.1.0/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>)). The rules are those of increment 6.4e (SNP-01 to SNP-07).

## What is backed up

| Store | Backed up | When lost |
| --- | --- | --- |
| Elasticsearch: the catalogue | snapshots, every hour, for 7 days | restored from the newest snapshot |
| Keycloak: realms and clients | no | re-imported from the chart's realm file |
| Keycloak: users and credentials | no: a named gap | lost; back up Keycloak's database with its own tools |
| Prometheus, Loki, Tempo, Grafana | no: disposable | lost; the signals refill, the dashboards and rules re-provision |

The catalogue snapshot holds every index of the server, `aurelius-atlas-*`: the entities, relationships, classifications, type definitions, glossaries, audits, stored metrics and the write journal. It does not hold the cluster's global state (its users, templates and settings), which the chart sets.

The signals are kept days, not years ([Data Archiving](<https://aureliusenterprise.github.io/dependabot-pre_commit-prettier-plugin-toml-4.1.0/architecture/data-lifecycle-management/data-archiving/index.md>)), and nothing reads them for the catalogue's sake: losing them loses history, never data. Keycloak's users are the gap: a cluster whose users live in Keycloak, not in a federated directory, backs up Keycloak's database.

## How the snapshots are taken

Elasticsearch takes them by its snapshot lifecycle policy `aurelius-atlas-snapshots`, which the server puts when it starts. Its settings, in the server chart's `config`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `AURELIUS_ATLAS_SERVER_SNAPSHOT_ENABLED` | `true` (chart) | put the policy and watch it; off in dev |
| `AURELIUS_ATLAS_SERVER_SNAPSHOT_SCHEDULE` | `0 0 * * * ?` | when, as an Elasticsearch cron in UTC: hourly |
| `AURELIUS_ATLAS_SERVER_SNAPSHOT_RETENTION` | `7d` | how long each snapshot is kept |
| `AURELIUS_ATLAS_SERVER_SNAPSHOT_LOCATION` | `aurelius-atlas` | the repository's directory below `path.repo` |

The newest 24 snapshots are kept whatever their age, so a store whose snapshots have been failing for a week keeps its last good day. Snapshots are incremental: each copies only the files that changed since the last.

The repository is the store's `path.repo`, `/usr/share/elasticsearch/snapshots`, on a volume of its own: in the store chart, the claim `atlas-elasticsearch-snapshots` for a release named `atlas` (`snapshots.size`, 30 Gi by default). The claim stays when the release is uninstalled.

## How a failure is noticed

The server reads the policy's outcome every 15 minutes and logs a failed run as an error. The alert rule "Snapshot overdue" fires when the last success is more than two hours old ([Alerting](<https://aureliusenterprise.github.io/dependabot-pre_commit-prettier-plugin-toml-4.1.0/architecture/platform/observability/alerting/index.md>)). The usual causes are a full snapshots claim, the store red, or the policy deleted by hand; the error names it. A server restart puts a deleted policy back.

## Restoring

A restore brings the store back to the moment of a snapshot. Everything written after it is lost, so first take a snapshot of the store as it is, if the store still answers:

```
python -m aurelius_atlas_server.snapshots take
```

### On a cluster

The server chart's restore Job runs the restore with the Deployment's store settings. No server may run while it does, so it renders only at `replicaCount` 0. The commands below are for a release named `atlas` in the namespace `atlas`, installed from the umbrella chart.

1. Stop the servers and wait until their pods are gone:

   ```
   helm upgrade atlas <chart> --reuse-values --set atlas-server.replicaCount=0
   kubectl -n atlas wait --for=delete pod -l app.kubernetes.io/name=atlas-server --timeout=5m
   ```
2. Run the restore, of the newest successful snapshot or of one named:

   ```
   helm upgrade atlas <chart> --reuse-values --set atlas-server.replicaCount=0 \
       --set atlas-server.restore.enabled=true \
       --set atlas-server.restore.snapshot=aurelius-atlas-2026.11.05-09.00-<suffix>
   kubectl -n atlas wait --for=condition=complete job/atlas-server-restore --timeout=30m
   kubectl -n atlas logs job/atlas-server-restore
   ```

   The log names the snapshot, the indices restored and the seconds it took. A failed Job is not retried; its log says why.
3. Start the servers again, which removes the Job:

   ```
   helm upgrade atlas <chart> --reuse-values --set atlas-server.replicaCount=1 \
       --set atlas-server.restore.enabled=false
   ```

The snapshots' names are listed by the same command, run in a server pod while the servers are still up:

```
kubectl -n atlas exec deploy/atlas-server -- python -m aurelius_atlas_server.snapshots list
```

### Into a new cluster

When the store's volumes are lost but the snapshots claim is not, install the release with the snapshots claim bound to the old volume (its `PersistentVolume`, by `volumeName` or a pre-created claim of the same name), at `atlas-server.replicaCount=0`. Then run steps 2 and 3. The restore registers the repository on the new store itself. [Disaster Recovery](<https://aureliusenterprise.github.io/dependabot-pre_commit-prettier-plugin-toml-4.1.0/architecture/platform/resilience/disaster-recovery/index.md>) covers the loss of the cluster.

### In dev

The dev server keeps snapshots off: the dev store's data is disposable. To rehearse by hand, start the server with `AURELIUS_ATLAS_SERVER_SNAPSHOT_ENABLED=true`, take a snapshot, stop the server, and restore:

```
uv run --env-file apps/aurelius-atlas-server/.env python -m aurelius_atlas_server.snapshots restore --replace
```

Run it from the workspace root: the `.env` names its files relative to it.

## The rehearsal

The restore is rehearsed on every change to the server, by the e2e test `test__aurelius_atlas_server_restore_e2e.py` (SNP-06). A server writes a type and two entities on one cluster, a snapshot is taken, and the cluster is removed. On a second, empty cluster sharing the repository, the command restores the snapshot, and a server started there answers the same entities, versions, audits and searches.

At the rehearsal's size, the restore takes about 6.5 seconds and the server answers 11 seconds after the restore starts. A cluster's restore copies every file of the snapshot, so it takes about as long as reading the store's data from the snapshots volume. Rehearse it on the cluster once, at its size, and record the time in the operations log. That time is the recovery time of ADR 026's R7.

## Two clusters, one repository

Never register the same repository as writable on two running clusters: both would write its index files, and the repository would break. A restore into a new cluster is safe because the old one is gone. To restore a copy beside a running store, copy the repository's directory first.
