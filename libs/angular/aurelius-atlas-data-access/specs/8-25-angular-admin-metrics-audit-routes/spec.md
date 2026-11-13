# 8.25 Angular admin twin: the metrics history and the audit reads

- **Status:** in review
- **Pull request:** to follow
- **Records:** cites 8.14 (AAC-01..07, the admin writes), DD-561 (the `mininfo`
  that always travels, the ageout 204 that stays `null`), and the server's rules
  MET, MHS, ADA, REP, AGE.

The review of [8.24](../../../../libs/python/aurelius-atlas-server-client/specs/8-24-client-admin-aurelius-routes/spec.md)
found both clients short of the same ten routes of `routes/admin.py`: the five
metrics reads of 6.4, the three audit and server reads of 6.3, and the two audit
writes. `AdminService` covers the writes of 8.14 and the five health reads of
8.4; these ten close the class. The Aurelius-native routes are not part of this
twin — `QualityRuleService` and `SearchByMeaningService` already answer all four
(EDT-30, SBW-01), which is what the Python client lacked and 8.24 adds.

## Scope

In scope:

- `AdminService` completed — `metrics`, `metricsStats`, `metricsStat`,
  `metricsInRange`, `metricsCharts`, `auditDetails`, `server`,
  `exportImportAudit`, `audits`, `ageoutAudits` (10 routes).
- The wire types the ten routes need, in a new `atlas-metrics.ts` (metrics,
  stats, charts) and additions to `atlas-impexp.ts` (the server, the
  export/import audit entry) and `atlas-audit.ts` (the admin audit entry, its
  search parameters, the reduction criteria).

Out of scope:

- The two browser routes (`/login.jsp`, `/logout.html`) and the two App Search
  routes — the same deliberate set 8.24 names.
- Server behaviour (MET, MHS, ADA, REP, AGE stay in the server's specs, cited
  not restated).

## Semantics

Rules of this increment, with ids tests name in the `it(...)` text. The 8.14
rules (AAC-01..07) apply to every new method and are not restated. The method
names, shapes, and the two `null` decisions mirror `AtlasClient.admin`
(CLW-08..CLW-12, DD-561) — the pair stays a pair.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AAC-08 | `metrics()` answers `GET /metrics` with an `AtlasMetrics` (MET-01..MET-04). `metricsStats(minInfo = true)` answers `GET /metricsstats` with an `AtlasMetricsStat[]`, the latest first (MHS-02). `mininfo` travels on **every** call, `true` or `false` — the route's Java default is true, so an absent parameter is the wrong answer for `false` (DD-561).                                                                                                   |
| AAC-09 | `metricsStat(collectionTime)` answers `GET /metricsstat/{collectionTime}` with one `AtlasMetricsStat` (MHS-02). `metricsInRange(startTime, endTime, typeNames = [])` answers `GET /metricsstats/range` with `startTime`, `endTime`, and each type name as a repeated `typeName` (MHS-03). `metricsCharts(startTime, endTime, typeNames = [])` answers `GET /metricsstats/charts` with the same three parameters and an `AtlasMetricsCharts` map (MHS-04).     |
| AAC-10 | `auditDetails(auditGuid, limit = 10, offset = 0)` answers `GET /audit/{auditGuid}/details` with an `AtlasEntityHeader[]` (ADA-05). `server(serverName)` answers `GET /server/{serverName}` with an `AtlasServer` (REP-01). `exportImportAudit(query)` answers `GET /expimp/audit` with the seven optional parameters of `ExportImportAuditQuery` and an `ExportImportAuditEntry[]` (REP-05).                                                                  |
| AAC-11 | `audits(parameters?)` answers `POST /audits` with an `AuditSearchParameters` body, or none, and an `AtlasAuditEntry[]` (ADA-04). `ageoutAudits(criteria?, useAuditConfig = false)` answers `POST /audits/ageout` with an `AuditReductionCriteria` body, or none, and sends `useAuditConfig=true` only when the flag is set (AGE-01..AGE-03). The 204 of an aging that queued nothing answers `null`; `null` and `[]` stay apart (DD-561, the DD-314 pattern). |

### The coverage matrix

`AdminService` after 8.14 held 12 of the 22 routes of `routes/admin.py`; the ten
rows of CLW-08..CLW-12 land on the same names as in 8.24's matrix, so this
increment adds no table of its own. After it, `AdminService` covers
`routes/admin.py` in full, and the lib's open set is the browser pair and the
App Search pair (8.24's Scope).

## Java origin

The Angular twin of the Python client's CLW-08..CLW-12; the Java client
libraries stay dropped (java-map, row `client`).

## Deviations

None. Each method sends what the route reads; the `null`-on-204 restates DD-314's
client-side convention.

## Acceptance

`admin.service.spec.ts` grows one test per method with the rule id in its name,
on `HttpTestingController` (`expectOne`). Run with
`nx run aurelius-atlas-data-access:test -c ci`.
