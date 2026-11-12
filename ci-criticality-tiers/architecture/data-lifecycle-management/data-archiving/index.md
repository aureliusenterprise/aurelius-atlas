# Data Archiving

How long Aurelius Atlas keeps each kind of data, what removes it, and where that is configured ([ADR 025](<https://aureliusenterprise.github.io/ci-criticality-tiers/architecture/adr/025-data-has-a-stated-lifetime/index.md>)). A lifetime is either a period that a mechanism enforces on a schedule, or "unbounded", stated with its reason. The periods were set in increment 6.4d. A store that arrives without a row here fails the lifetimes suite (`tests/test__retention.py`).

## Lifetimes

| Data | Lifetime | Removed by | Store |
| --- | --- | --- | --- |
| Catalogue: entities, relationships, classifications | unbounded | a delete, then a purge | `dev/elasticsearch:data` |
| Type definitions, glossaries, saved searches, profiles | unbounded | a delete | `dev/elasticsearch:data` |
| Entity audits, except an entity's creation | 90 days | the audit aging, daily | `dev/elasticsearch:data` |
| An entity's creation audit | with the entity | the entity's purge | `dev/elasticsearch:data` |
| Admin audits, export and import audits | unbounded | — | `dev/elasticsearch:data` |
| Stored metrics (`admin/metricsstats`) | 14 days | the metrics purge, hourly | `dev/elasticsearch:data` |
| The write journal, finished tasks | until the write finishes | the write, recovery, the task | `dev/elasticsearch:data` |
| Users, realms, clients | unbounded | an administrator | `dev/keycloak:data` |
| Login and admin events (production realm) | 30 days | Keycloak's event expiry | `dev/keycloak:data` |
| Metrics | 15 days | Prometheus's retention | `dev/observability:prometheus-data` |
| Logs | 30 days | Loki's compactor | `dev/observability:loki-data` |
| Traces | 7 days | Tempo's retention jobs | `dev/observability:tempo-data` |
| Alert state history | 30 days | Grafana's annotation cleanup | `dev/observability:grafana-data` |
| Grafana's users and preferences | unbounded, disposable | — | `dev/observability:grafana-data` |
| Messages on the dev broker (topics, offsets) | unbounded, disposable | — | `dev/kafka:kafka-data` |
| The dev cluster's metadata (the KRaft log) | unbounded, disposable | — | `dev/kafka:kafka-kraft` |
| Snapshots of the store (chart; none in dev) | 7 days, the newest 24 | the snapshot retention | `dev/elasticsearch:snapshots` |

The store column names the dev volume. On a cluster each is the persistent volume of the same component in its chart.

## Why these periods

- **The catalogue is unbounded.** It is the record the product exists to keep, and its entries are owned by the people who answer for each dataset ([ADR 042](<https://aureliusenterprise.github.io/ci-criticality-tiers/architecture/adr/042-every-dataset-has-an-owner-who-answers-for-it/index.md>)). A deleted entity stays, marked deleted, until it is purged, as in Atlas. The cost grows with the catalogue, not with time.
- **Audits are kept 90 days, creations with their entity.** These are Atlas's aging defaults (`atlas.audit.default.ageout.ttl.in.days`, and creation events left out). Atlas ships aging off; the chart turns it on and sweeps daily, so no event outlives 91 days. The dev stack keeps Atlas's default, aging off, because its data is disposable.
- **Admin audits are unbounded.** They record purges, imports and exports, which are rare and small, and they are the trail for the deletions every other lifetime makes. Atlas gives them no lifetime either.
- **Signals are kept long enough to look back on an incident.** Metrics are kept 15 days for trends across two weeks. Logs are kept 30 days, which covers an incident reported late. Traces are kept 7 days: they are the largest signal and are read while an incident is fresh.
- **Identity events are kept 30 days.** Login and admin events name people and their addresses. Thirty days answers "who signed in" for a recent incident without building a history of each person.

## Where each lifetime is configured

| Lifetime | Dev | Chart |
| --- | --- | --- |
| Entity audits | off (`AURELIUS_ATLAS_SERVER_AUDIT_AGING_ENABLED`) | the server chart's `config`, `AUDIT_*` keys |
| Stored metrics | `AURELIUS_ATLAS_SERVER_METRICS_TTL_HOURS` (336) | the same setting |
| Identity events | the dev realm records none | `files/aurelius-atlas.json`, `eventsExpiration` |
| Metrics | `--storage.tsdb.retention.time` in the compose | `prometheus.retention` |
| Logs | `config/loki.yaml`, `limits_config.retention_period` | the same file, copied |
| Traces | `config/tempo.yaml`, `overrides.defaults.compaction` | the same file, copied |
| Alert state history | `GF_UNIFIED_ALERTING_STATE_HISTORY_ANNOTATIONS_MAX_AGE` | `grafana.alerting.historyMaxAge` |

A change to a period is a change to one of these files, reviewed like any other (R5).

> [!WARNING]
>
> **An existing realm keeps its event settings**
>
> Keycloak imports a realm only when it does not exist yet. A cluster installed before 6.4d keeps its events until an administrator sets the expiry in the admin console (Realm settings, Events).

## Deleting and purging

An entity delete marks the entity deleted; a purge (`PUT admin/purge`) or a hard delete removes it, with its relationships and classifications, in one write. The rules are those of increment 2.5, the delete semantics.

## Snapshots

The store is snapshotted every hour and each snapshot is kept 7 days ([Backup &amp; Restore](<https://aureliusenterprise.github.io/ci-criticality-tiers/architecture/platform/resilience/backup-and-restore/index.md>)). A snapshot holds what the store held when it was taken, so data a lifetime has removed can live on in a snapshot for up to 7 more days: a stored metric, for example, until 21 days after it was taken. A restore brings such data back, and the next sweep removes it again.
