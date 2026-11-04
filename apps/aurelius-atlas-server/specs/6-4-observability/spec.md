# 6.4c Observability, alerting and load test

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-319, DD-320, DD-321; ADR 040 (its acceptance trigger), ADR 041 (the detection gap it names)

The server already sends its traces and metrics to the collector, but not its logs. No dashboard shows its
signals, and no rule reads anything the collector holds, so a failure is noticed only by whoever happens to
look. This increment sends the server's logs over the same ingest leg and adds a server dashboard. It adds the
alert rules of [ADR 040](../../../../docs/architecture/adr/040-the-system-raises-its-hand-when-it-is-broken.md),
with a destination for them, and a load test that runs concurrent users against the server on the dev store.
Retention, index tuning, snapshots and restore follow in 6.4d.

## Scope

No endpoint changes. The changes are:

| Project                           | What changes                                                                                                            |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `libs/python/aurelius-atlas-otel` | `build_otlp_log_processor`; a `log_processor` for `build_providers` and `setup_telemetry`; `bridge_logging(propagate=)` |
| `apps/aurelius-atlas-server`      | `app._telemetry` and `BRIDGED_LOGGERS`; the load driver `e2e/load.py` and its test                                      |
| `dev/observability`               | the `aurelius-atlas-server` dashboard, `config/grafana/alerting/rules.yaml`, their chart copies, `grafana.alerting`     |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| OBS-01 | With its ingest credential set, the server exports its log records over OTLP on the per-service leg (`/v1/logs`), with the same credential as its traces and metrics. The records come from its own logger, `aurelius_atlas_core`, `aurelius_atlas_store_es` and `uvicorn.error`. They still reach the process's output. Without the credential nothing is exported                                                      |
| OBS-02 | The dashboard `Aurelius Atlas Server` shows the server's requests by status class, its 95th-percentile latency, 5xx answers and busiest routes, and its requests in flight. It shows its process's memory, CPU and garbage collections, and its logs and traces. Requests are keyed by `http_route`, never by the raw path. The chart's copy is byte-identical to dev's                                                  |
| OBS-03 | Seven Grafana alert rules, evaluated every minute, read the signals the collector holds. Each carries `severity` (`critical` or `warning`) and `team: maintainers`, and the chart's copy is byte-identical to dev's. The rules are listed in [the conditions below](#the-conditions)                                                                                                                                     |
| OBS-04 | When `grafana.alerting.webhookSecret` names a Secret, the chart provisions the contact point `maintainers`, a webhook whose URL Grafana reads from the Secret's key `url` through its env. The root notification policy routes every rule to it, grouped by `alertname` and repeated every `repeatInterval` (4h). Without the Secret, and in dev, there is no contact point: the rules fire in Grafana's alert list only |
| LOD-01 | A load run drives `users` concurrent users for `seconds`, each looping through a mix of five operations from its own offset. The operations are reading a seeded entity, a basic search and a quick search of the run's type, updating the user's own seeded entity, and creating an entity. The run's type, its seeds and what it created are deleted and purged afterwards                                             |
| LOD-02 | Every request is a sample of its operation, its status (0 when no answer came) and its duration. A sample fails unless its status is 2xx. The report gives each operation its count, its failures, its 50th and 95th percentiles (nearest rank) and its maximum                                                                                                                                                          |
| LOD-03 | The run passes when no request failed and every operation's 95th percentile is within the budget. The defaults are 8 users, 20 seconds and 3,000 ms, set by `AURELIUS_ATLAS_LOAD_USERS`, `_SECONDS` and `_P95_MS`. The report is printed and recorded as the junit property `load_report`                                                                                                                                |

### The conditions

The rules of OBS-03. "For" is how long the condition must hold before the rule fires. "No data" says what the
rule does when its query returns nothing.

| Rule                                       | Severity | Fires when                                                                               | For | No data |
| ------------------------------------------ | -------- | ---------------------------------------------------------------------------------------- | --- | ------- |
| `aurelius-atlas-server-silent`             | critical | the server sent no process metrics in the last 5 minutes                                 | 1m  | fires   |
| `aurelius-atlas-part-silent`               | warning  | a part (`exported_job`) sent signals in the last 6 hours and none in the last 10 minutes | —   | OK      |
| `aurelius-atlas-server-errors`             | critical | more than 5% of the server's answers over 5 minutes are 5xx                              | 5m  | OK      |
| `aurelius-atlas-server-latency`            | warning  | the 95th percentile of the server's requests over 5 minutes is over 2 seconds            | 10m | OK      |
| `aurelius-atlas-store-health`              | critical | Elasticsearch reports `red`                                                              | 2m  | fires   |
| `aurelius-atlas-collector-down`            | critical | Prometheus cannot scrape the collector                                                   | 2m  | fires   |
| `aurelius-atlas-collector-export-failures` | warning  | the collector failed to send spans, metric points or log records in the last 10 minutes  | 5m  | OK      |

A query that fails (Prometheus unreachable) fires the rule too. The three silence rules are ADR 040's R3:
the server's never resolves, the part rule covers every part that exports through the collector (R7), and
the collector rule covers the collection point.

## Origin

No Java class is ported: Atlas leaves observability to its deployment. The conditions come from ADR 040's
requirements and from the signals the dev stack already holds.

## Deviations

None from Atlas. One gap stays open: no rule watches the observability stack's own storage. Prometheus, Loki
and Tempo report no free space, and their retention is 6.4d's.

## Findings

The first runs of the load test give each create about one second, and each update up to two. Every write waits
for the store's next refresh (`refresh=wait_for`, DD-237): one wait for the entity, one for its audit.
Reads and searches take 30 to 120 ms. The write cost is the index-tuning question of 6.4d. The default budget
holds it, so the test guards errors and regressions, not the tuning.

## Acceptance

- `libs/python/aurelius-atlas-otel/tests/test__ingest.py`, `test__telemetry.py` — OBS-01.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_app.py` — OBS-01.
- `tests/test__charts_observability.py` — OBS-02 to OBS-04.
- `apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_load_e2e.py` — LOD-01 to LOD-03.
- In dev Grafana: the seven rules load, and `aurelius-atlas-server-silent` fires while no server runs
  (ADR 040 R6).
- `uv run aurelius-atlas-trace check`.
