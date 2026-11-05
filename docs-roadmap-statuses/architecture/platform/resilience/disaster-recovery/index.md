# Disaster Recovery

How the system comes back when more than one part is lost, and the bounds on what that costs ([ADR 026](<https://aureliusenterprise.github.io/docs-roadmap-statuses/architecture/adr/026-the-system-can-be-brought-back-from-a-named-snapshot/index.md>)). The parts come back from two sources: the released images and charts reproduce the machinery, and the store's snapshots reproduce the catalogue ([Backup &amp; Restore](<https://aureliusenterprise.github.io/docs-roadmap-statuses/architecture/platform/resilience/backup-and-restore/index.md>)).

## The objectives

| Objective | Value | Where it comes from |
| --- | --- | --- |
| Maximum data loss (R3) | one hour of catalogue writes, proposed | the hourly snapshot schedule (SNP-02); the overdue alert at two |
| Recovery time (R7) | measured by the cluster's rehearsal | 11 seconds at the e2e rehearsal's size (SNP-06) |
| Oldest point to restore to | 7 days, and at least the newest 24 | the snapshot retention (SNP-02) |

The values are ADR 026's to name. The maximum data loss follows from the schedule: a snapshot every hour, and an alert when the newest is two hours old. The recovery time is the cluster's: the time of its restore, measured at its size, plus the servers' start.

## What fails, and what comes back

| Lost | Comes back by | Lost for good |
| --- | --- | --- |
| A server pod | its Deployment | nothing |
| The store's data volume | a restore of the newest snapshot | writes since that snapshot |
| The catalogue, by a bad change | a restore of the last snapshot before it | writes since that snapshot |
| The store's node | its StatefulSet, on its volumes | nothing, if the volumes survive |
| The cluster, its storage survives | a new install bound to the old volumes, then a restore | writes since the snapshot |
| The cluster and its storage | a new install and a restore from a copy kept elsewhere, if there is one | the catalogue, without such a copy |

The last row is the gap: the snapshots live inside the cluster (DD-356). A deployment that must survive the loss of its cluster copies the snapshots claim elsewhere on its own schedule, or registers an object store repository of its own. Keycloak's users are not backed up (see [Backup &amp; Restore](<https://aureliusenterprise.github.io/docs-roadmap-statuses/architecture/platform/resilience/backup-and-restore/index.md>)).

## Rebuilding

1. Install the umbrella chart of the same release as the lost one, with its values, at `atlas-server.replicaCount=0`. The store's schema comes from the snapshot, so the release must be the one that wrote it or a later one (ADR 023).
2. Bind the snapshots claim to the surviving volume, or put the copy of the repository on it.
3. Restore, then start the servers: steps 2 and 3 of [Backup &amp; Restore](<https://aureliusenterprise.github.io/docs-roadmap-statuses/architecture/platform/resilience/backup-and-restore/#on-a-cluster>).
4. Check the catalogue: the newest entities, and `admin/metrics` for its counts.
