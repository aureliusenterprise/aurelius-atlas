# 6.4a Metrics

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-317, DV-135; relies on DV-01 (no notifications consumed) and the type filter (AUZ-14)

`admin/metrics` answers what the dashboards' statistics show: how many types, entities and classifications the
catalogue holds, the server's start, up time and store status, and the system it runs on. The stored history of
these metrics (`admin/metricsstats`, its charts and schedule) is 6.4b.

## Scope

| Endpoint                       | Needs            |
| ------------------------------ | ---------------- |
| `GET /api/atlas/admin/metrics` | a signed-in user |

In `aurelius-atlas-model`, `metrics` (`AtlasMetrics` and its stat keys). In `aurelius-atlas-core`,
`metrics_service`, `metrics_util`, and the entity documents' `type_counts` and `linked_type_counts` with the
store's `type_counts` and `classification_type_counts`. In `aurelius-atlas-store-es`, the fake client's
`composite` aggregations. In `aurelius-atlas-server`, the route in `routes/admin` and the start times in `app`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MET-01 | `GET admin/metrics` answers `AtlasMetrics`: `data` of the groups `general` (`collectionTime`, `stats`, `typeCount`, `tagCount`, `typeUnusedCount`, `entityCount`), `entity` (`entityActive`, `entityDeleted`, `entityShell` and each `-typeAndSubTypes`), `tag` (`tagEntities`) and `system` (`memory`, `os`, `runtime`). `typeCount` is every registered type, built-in ones included; `tagCount` every classification type                                                                                                                                                     |
| MET-02 | The types counted are the entity types not directly under `__internal` and the classification types, those the user may not read left out (`filterTypesDef`). Per entity type: its `ACTIVE` and its `DELETED` entities, and its shells (`isIncomplete`, in any state); with sub types, the sum over the type and all its sub types. Per classification type: its instances. A count of zero is left out. `entityCount` sums the active and deleted entities counted; `typeUnusedCount` counts the entity types with neither                                                      |
| MET-03 | `stats` holds `Server:startTimeStamp` and `Server:activeTimeStamp` (both set as the server starts, as without high availability), `Server:upTime` (`<n> day <n> hour <n> min <n> sec`, each part of zero left out), `Server:statusBackendStore` and `Server:statusIndexStore` (`connected` when the store's health is up, else `not-connected`), and the `Notification:` stats of counters never counted: every count and average 0, `lastMessageProcessedTime` 0, `topicDetails` empty, `currentDayStartTime` and `currentHourStartTime` the current UTC day's and hour's start |
| MET-04 | `system` describes the server's process: `runtime` its Python implementation and version, `memory` its largest resident set in bytes, `os` (`os.spec` the system, machine and release, `os.vcpus` the processors)                                                                                                                                                                                                                                                                                                                                                                |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/resources/AdminResource.java`: `getMetrics`
- `webapp/.../web/service/ActiveInstanceElectorService.java`: `start` (`onServerStart`, `onServerActivation`)
- `repository/.../services/MetricsService.java`: `getMetrics`, `getTypeCount`, `getTypeShellCount`, `getTypesDef`
- `repository/.../util/AtlasMetricsUtil.java`: `getStats`, `millisToTimeDiff`; `AtlasMetricsCounter.java`
- `repository/.../util/AtlasMetricJVMUtil.java`
- `intg/.../model/metrics/AtlasMetrics.java`

## Deviations

- **DV-135:** `system` describes the Python process: its runtime, its largest resident set for the JVM's
  heap and memory pools, and the operating system as Python names it.
- No notification is consumed (DV-01), so the notification stats are always those of counters never
  counted.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__metrics_service.py` — MET-01 to MET-04: the counts, the type filter,
  the stats and up time, the system details, the store's counts.
- `libs/python/aurelius-atlas-core/e2e/test__entity_store_e2e.py` — MET-02, the counts on Elasticsearch.
- `libs/python/aurelius-atlas-model/tests/test__metrics.py` — `AtlasMetrics`.
- `libs/python/aurelius-atlas-store-es/tests/test__aurelius_atlas_store_es_fake.py` — the fake's composite
  aggregations.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_metrics.py` — MET-01, MET-03 through the route.
- `apps/aurelius-atlas-server/scenarios/admin/metrics.scenario.yaml`.
- `uv run aurelius-atlas-trace check`.
