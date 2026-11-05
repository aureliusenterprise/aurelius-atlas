# 6.4b Metrics history

- **Status:** done
- **Pull request:** #261
- **Records:** DD-318, DV-136, DV-137; relies on the metrics (MET-01 to MET-04) and the data access (DD-307)

The dashboards' statistics timeline reads the metrics of the past: every hour the server stores the metrics of
`admin/metrics` as a `__AtlasMetricsStat` entity and deletes those older than their time to live. Four endpoints
list them, read one by its time, and answer a range of them as counts per type or as chart series.

## Scope

| Endpoint                                            | Needs            |
| --------------------------------------------------- | ---------------- |
| `GET /api/atlas/admin/metricsstats`                 | a signed-in user |
| `GET /api/atlas/admin/metricsstat/{collectionTime}` | a signed-in user |
| `GET /api/atlas/admin/metricsstats/range`           | a signed-in user |
| `GET /api/atlas/admin/metricsstats/charts`          | a signed-in user |

In `aurelius-atlas-model`, `AtlasMetricsStat`, `AtlasMetricsMapToChart` and `METRICSSTAT_ALREADY_EXISTS`. In
`aurelius-atlas-core`, `MetricsStatDTO` and the stored metrics of `MetricsService`. In `aurelius-atlas-server`,
the routes in `routes/admin`, the `metrics_*` settings and the `MetricsScheduler`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MHS-01 | A stored metric is an `AtlasMetricsStat`: `guid`, `metricsId` (`atlas_metrics_<collectionTime>@<cluster_name>`), `collectionTime` (the metrics' own), `timeToLiveMillis` (`metrics_ttl_hours`, 336), and `metrics`; it is a `__AtlasMetricsStat` entity with the metrics as JSON. Storing one without an id is `BAD_REQUEST` (`MetricsStat definition missing.`), one whose id is stored already `METRICSSTAT_ALREADY_EXISTS`                                                                         |
| MHS-02 | `metricsstats` answers every stored metric not deleted, the latest first; with `mininfo` (the default; `true` in any case, anything else is false) without `metrics`. `metricsstat/{collectionTime}` answers the one of that time's id, `INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND` for none                                                                                                                                                                                                             |
| MHS-03 | `metricsstats/range` needs `startTime` and `endTime` (`BAD_REQUEST` `startTime or endTime is null/empty.` when either is missing or blank) and takes any `typeName`s. A start not before the end is `INVALID_PARAMETERS`. It answers the metrics collected from the start to the end, both included, the latest first, each made anew: a new negative `guid`, no `metrics`, and `typeData` of each type name its `Active`, `Deleted` and `Shell` counts (0 when not counted), none without type names |
| MHS-04 | `metricsstats/charts` takes the parameters of a range and answers, per type name, the series `Active`, `Deleted` and `Shell`, each `{key, values}` with `values` the `[collectionTime, count]` pairs of the range, the earliest first; a range of no metrics has no series                                                                                                                                                                                                                            |
| MHS-05 | Every `metrics_persist_interval_minutes` (60), at its multiples since the epoch, the server stores the metrics of now, then deletes the stored metrics whose `collectionTime` plus `timeToLiveMillis` is before now; a failure of either is only logged. An interval of 0 stores none                                                                                                                                                                                                                 |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/resources/AdminResource.java`: `scheduleSaveAndDeleteMetrics`, `saveMetrics`, `getAllMetrics`,
  `getMetricsByCollectionTime`, `getMetricsInTimeRange`, `getMetricsForChartByTypeNames`, `getCronExpression`
- `repository/.../services/MetricsService.java`: `saveMetricsStat`, `purgeMetricsStats`,
  `getMetricsStatByCollectionTime`, `deleteMetricsStatByCollectionTime`, `getAllMetricsStats`,
  `getMetricsInRangeByTypeNames`, `getMetricsForChartByTypeNames`, `mapToStatusCategoryByOneType`
- `repository/.../ogm/metrics/AtlasMetricsStatDTO.java`
- `intg/.../model/metrics/AtlasMetricsStat.java`, `AtlasMetricsMapToChart.java`; `intg/.../utils/AtlasEntityUtil.java`
  (`metricsToTypeData`); `intg/.../AtlasConfiguration.java` (`atlas.metrics.ttl.hours`)

## Deviations

- **DV-136:** a time that is no `long` is `BAD_REQUEST`; Atlas fails on its `Long.parseLong` with a server
  error.
- **DV-137:** the schedule is an interval in minutes, run at its multiples since the epoch, 0 for none;
  Atlas's is a cron expression. The default, 60, runs at the start of every hour as Atlas's does.

As in Atlas, every server process stores its own metrics on the schedule.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__metrics_service.py` — MHS-01 to MHS-05.
- `libs/python/aurelius-atlas-core/e2e/test__metrics_history_e2e.py` — MHS-01, MHS-02, MHS-05 on Elasticsearch.
- `libs/python/aurelius-atlas-model/tests/test__metrics.py` — `AtlasMetricsStat`, `AtlasMetricsMapToChart`.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_metrics_history.py` — MHS-02 to MHS-05 through
  the routes and the schedule.
- `apps/aurelius-atlas-server/scenarios/admin/metrics-history.scenario.yaml`.
- `uv run aurelius-atlas-trace check`.
