# 6.4d Retention and index tuning

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-322, DD-323, DD-324; ADR 025 (its acceptance trigger)

No store states how long it keeps its data. Loki and Keycloak's events keep theirs forever, Tempo and
Prometheus at their vendors' defaults, and the entity audits as long as Atlas's aging is off, which is its
default. This increment names each kind's lifetime, configures the mechanism that enforces it in dev and in the
charts, and writes the lifetimes on one page
([Data Archiving](../../../../docs/architecture/data-lifecycle-management/data-archiving.md)).

It also takes up 6.4c's finding: each write waited for the store's next scheduled refresh, about a second
for a create and two for an update. Writes now refresh what they wrote. And every index asks for a replica the
single node cannot place, so the store is never green; the indices now expand their replicas to the cluster.

Snapshots and the rehearsed restore of ADR 026 follow in 6.4e.

## Scope

No endpoint changes. The changes are:

| Project                               | What changes                                                                                  |
| ------------------------------------- | --------------------------------------------------------------------------------------------- |
| `libs/python/aurelius-atlas-core`     | `WRITE_REFRESH`; `INDEX_SETTINGS` on the indices of the entities, the audits and the typedefs |
| `libs/python/aurelius-atlas-store-es` | the fake client keeps each index's settings                                                   |
| `apps/aurelius-atlas-server`          | the chart turns the audit aging on                                                            |
| `dev/observability`                   | the lifetimes of metrics, logs, traces and alert history, in dev and in the chart             |
| `dev/keycloak`                        | the production realm's event lifetimes                                                        |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                 |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RET-01 | The Data Archiving page names each kind of data, its lifetime, what removes it and its store. Every named volume of a dev stack has a row, as `dev/<stack>:<volume>`. A lifetime is a period, or "unbounded" with its reason                                                                         |
| RET-02 | Prometheus keeps metrics 15 days. The compose passes `--storage.tsdb.retention.time=15d`; the chart's `prometheus.retention` is `15d` and renders the same flag                                                                                                                                      |
| RET-03 | Loki deletes logs 30 days old: its compactor has retention on (`delete_request_store: filesystem`) and `limits_config.retention_period` is `720h`. The chart's copy is byte-identical                                                                                                                |
| RET-04 | Tempo deletes traces 7 days old: the default per-tenant override `compaction.block_retention` is `168h`. The chart's copy is byte-identical                                                                                                                                                          |
| RET-05 | Grafana deletes alert state history 30 days old: `GF_UNIFIED_ALERTING_STATE_HISTORY_ANNOTATIONS_MAX_AGE` is `30d` in the compose, and the chart renders `grafana.alerting.historyMaxAge` (`30d`) into it                                                                                             |
| RET-06 | The production realm records login and admin events and expires both after 30 days: `eventsExpiration` is 2592000 and the realm attribute `adminEventsExpiration` is `"2592000"`. A realm that exists keeps its settings (Keycloak imports only a new realm)                                         |
| RET-07 | The server chart turns Atlas's audit aging on, at the default TTL of 90 days, swept every day (AGE-05). Events other than an entity's creation then age out after 90 days (AGE-04). The dev stack keeps Atlas's default, aging off                                                                   |
| IDX-01 | Every write a search reads refreshes the shards it wrote before it answers (`refresh="true"`, ENS-11), so the next read sees it. No write waits for the index's scheduled refresh                                                                                                                    |
| IDX-02 | Every index the server creates, of the entities, their linked documents, the journal, the reservations, the audits and the typedefs, has `index.auto_expand_replicas: 0-1`. An index that exists gets the setting when the server prepares it. On one node the indices have no replica and are green |

## Origin

No Java class is ported. Atlas leaves its stores' retention to their deployment, and its audit aging is
`AtlasAuditReductionService` (6.3c4), whose defaults RET-07 keeps. Its graph is visible to the next read on
commit, which IDX-01 keeps at a lower cost.

## Deviations

None from Atlas. RET-07 changes a default of the chart, not of the server: the server's settings keep Atlas's
`atlas.audit.aging.enabled=false`.

## Findings

The load test of 6.4c, run on the dev store before and after IDX-01:

| Operation | p50 before | p95 before | p50 after | p95 after |
| --------- | ---------- | ---------- | --------- | --------- |
| create    | 1,018 ms   | 1,131 ms   | 202 ms    | 551 ms    |
| update    | 887 ms     | 984 ms     | 190 ms    | 479 ms    |
| search    | 45 ms      | 68 ms      | 41 ms     | 205 ms    |

The run served 1,213 requests in 20 seconds instead of 391. A search's 95th percentile rises because it now
shares the store with three times as many writes, each with its refresh.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_documents.py`, `test__entity_audit_repository.py` —
  IDX-01, IDX-02; `test__typedef_document.py` — IDX-02.
- `tests/test__retention.py` — RET-01 to RET-07.
- `apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_load_e2e.py` — IDX-01's cost, by the findings above.
- On the dev stack: Prometheus, Loki, Tempo and Grafana report the lifetimes of RET-02 to RET-05.
- `uv run aurelius-atlas-trace check`.
