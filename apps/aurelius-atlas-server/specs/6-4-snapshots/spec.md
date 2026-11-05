# 6.4e Snapshots and restore

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-355, DD-356, DD-357, DD-358; ADR 026 (its acceptance trigger)

Nothing is backed up. The store's data volume surviving a recreated container is the only protection, and
no path brings the catalogue back when that volume is lost. This increment takes snapshots of the store on a
schedule, keeps them on a volume apart from the data, checks that they succeed, and restores one into a
clean cluster by one command. The restore is rehearsed by a test: a snapshot of a running server's store comes
back as a working server on a second cluster
([Backup & Restore](../../../../docs/architecture/platform/resilience/backup-and-restore.md)).

## Scope

No endpoint changes. The changes are:

| Project                               | What changes                                                                                |
| ------------------------------------- | ------------------------------------------------------------------------------------------- |
| `libs/python/aurelius-atlas-store-es` | `snapshots`: the repository, the policy, its status, a snapshot on request, the restore     |
| `apps/aurelius-atlas-server`          | the `snapshot_*` settings, `SnapshotWatcher`, the command `aurelius_atlas_server.snapshots` |
| `apps/aurelius-atlas-server/helm`     | snapshots on; the restore Job                                                               |
| `dev/elasticsearch`                   | `path.repo` on a `snapshots` volume, in dev and in the chart (a claim of its own)           |
| `dev/observability`                   | the rule `aurelius-atlas-snapshot-overdue`, and its chart copy                              |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SNP-01 | The store's node has `path.repo: [/usr/share/elasticsearch/snapshots]`, on a volume apart from its data: the named volume `snapshots` in dev, and in the chart the claim `<fullname>-snapshots`, which is kept when the release is uninstalled. With `snapshot_enabled`, the server registers the shared-filesystem repository `aurelius-atlas-snapshots` at `snapshot_location` (`aurelius-atlas`) when it starts; a store that cannot hold it fails the start. The chart turns `snapshot_enabled` on; the dev server keeps it off |
| SNP-02 | With the repository, the server puts the snapshot lifecycle policy `aurelius-atlas-snapshots`: every index `aurelius-atlas-*` with its aliases, without the cluster's global state, on `snapshot_schedule` (`0 0 * * * ?`, every hour in UTC). A snapshot is named by its minute (`aurelius-atlas-yyyy.MM.dd-HH.mm-<suffix>`) and deleted `snapshot_retention` (`7d`) after it was taken; the newest 24 are always kept, and never more than 200. Elasticsearch runs the schedule, with or without a server                         |
| SNP-03 | The server reads the policy's last success and last failure when it starts and every `snapshot_check_minutes` (15). A failure later than the last success is logged as an error with its details. The gauge `aurelius_atlas.snapshot.last_success` reports the last success's time in seconds since the epoch. The rule `aurelius-atlas-snapshot-overdue` (critical) fires when it is more than two hours old for 15 minutes; no data, snapshots off, is OK                                                                         |
| SNP-04 | `python -m aurelius_atlas_server.snapshots take` runs the policy now, waits until the snapshot has finished, and prints its name; a snapshot that ends other than `SUCCESS` fails the command. `list` prints each snapshot, oldest first: its name, state, start and number of indices. The command reads the store's settings alone, from the server's environment                                                                                                                                                                 |
| SNP-05 | `restore [--snapshot NAME] [--replace]` registers the repository, then restores the server's indices with their aliases from the named snapshot, by default the newest successful one. A store that holds any index `aurelius-atlas-*` is refused unless `--replace`, which deletes every such index first, those the snapshot does not hold too. A failed shard fails the restore. It prints the snapshot, the indices restored and deleted, and the seconds it took                                                               |
| SNP-06 | A snapshot of a running server's store, restored into a clean cluster that mounts the same repository, gives a server that answers the same entities, versions, audits and searches. The time from the restore's start to that server's first answer is the recovery time                                                                                                                                                                                                                                                           |
| SNP-07 | The server chart's Job `<fullname>-restore` renders with `restore.enabled`, and only with `replicaCount` 0: the render fails otherwise. It runs the server's image with `restore --replace`, and `--snapshot` when `restore.snapshot` names one, with the Deployment's store settings and the server's pod labels, which the store's network policy admits                                                                                                                                                                          |

## Origin

No Java class is ported. Atlas leaves the backups of its stores, HBase and Solr, to their deployment. Here the
store is the system of record (ADR 047), so its snapshots are the catalogue's backup.

## Deviations

None from Atlas.

## Findings

The rehearsal of SNP-06, on two single-node containers with 512 MB of heap:

| Step                                                    | Time   |
| ------------------------------------------------------- | ------ |
| The restore of the server's 8 indices                   | 6.5 s  |
| The restore's start to the second server's first answer | 11.0 s |

The catalogue was a type and two entities on Atlas's models. A restore copies every file of the snapshot, so
its time grows with the store's size and the volume's throughput; the cluster's rehearsal measures it at its own
size (see the Backup & Restore page).

In dev the gauge reached Prometheus as `aurelius_atlas_snapshot_last_success_seconds{exported_job="aurelius-atlas-server"}`,
the series the rule reads, and Grafana loaded the rule.

## Acceptance

- `libs/python/aurelius-atlas-store-es/tests/test__aurelius_atlas_store_es_snapshots.py` — SNP-01 to SNP-05.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_snapshots.py` — SNP-01 to SNP-05.
- `tests/test__snapshots.py` — SNP-01, SNP-03, SNP-07.
- `apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_restore_e2e.py` — SNP-04 to SNP-06, on two
  containers of its own, never the shared dev store (DD-223).
- `uv run aurelius-atlas-trace check`.
