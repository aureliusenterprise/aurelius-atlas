# 8.24 Client route coverage — the admin reads and writes left, and the Aurelius routes

- **Status:** in review
- **Pull request:** to follow
- **Records:** DD-561 (`mininfo` travels on every metrics-stats call), DD-562
  (the Aurelius-native shapes live in the client library); cites 8.4 (CL-01..CL-08),
  8.11 (CLW-01..CLW-07), and the server's rules MET, MHS, ADA, REP, AGE, QRE,
  SBM.

A 2026-11-13 review compared the server's 141 routes against both API clients.
`AtlasClient` answered 111 and the Angular data-access lib answered 111, and
141 minus 111 leaves the same kind of gap on each side. On the Python side the
gaps are the ten routes of `routes/admin.py` that arrived after 8.11 said the
class was complete (the metrics history of 6.4, the audits and servers of 6.3),
the four Aurelius-native routes of `routes/quality.py` and
`routes/search_by_meaning.py`, and the four out-of-scope routes named below. The
Angular twin closes in [8.25](../../../../libs/angular/aurelius-atlas-data-access/specs/8-25-angular-admin-metrics-audit-routes/spec.md),
the pair pattern of 8.12 and 8.13.

After this increment and its twin, both clients answer every route of the server
except the two browser routes of CL-65 and the two App Search routes — the
deliberate set, stated here for the record.

## Scope

In scope:

- `AtlasClient.admin` completed — `metrics`, `metrics_stats`, `metrics_stat`,
  `metrics_in_range`, `metrics_charts`, `audit_details`, `server`,
  `export_import_audit`, `audits`, `ageout_audits` (10 routes).
- `AtlasClient.aurelius` — the four Aurelius-native routes: the semantic search
  and the similar-entities read of `routes/search_by_meaning.py` (SBM), the rule
  vocabulary and the rule validation of `routes/quality.py` (QRE).
- The client library's own models for the Aurelius-native shapes (DD-562), the
  `lineage.py` precedent (CL-12) repeated: the library cannot import the server
  app.

Out of scope:

- The two browser routes (`/login.jsp`, `/logout.html`) — CL-65 of 8.8 keeps
  them out, and 8.25 keeps them out of the Angular twin for the same reason.
- The two App Search routes (`POST /api/as/v1/engines/{name}/search[.json]`) —
  the emulation of Elastic App Search the original webapp's proxy calls (ASE),
  not an API a service calls. A client for it needs its own increment if a
  service ever wants it.
- Server behaviour (MET, MHS, ADA, REP, AGE, QRE, SBM stay in the server's
  specs, cited not restated).

## Semantics

Rules of this increment, with ids tests name in
`@pytest.mark.covers(..., rules=["..."])`. The 8.4 rules (CL-01..CL-08, CL-10..
CL-13) and 8.8's CL-60..CL-65 apply to every new method and are not restated.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CLW-08 | `admin.metrics()` answers `GET /metrics` and returns the `AtlasMetrics` (MET-01..MET-04). `admin.metrics_stats(min_info=True)` answers `GET /metricsstats` and returns a list of `AtlasMetricsStat`, the latest first (MHS-02). Unlike every other flag of the client, `mininfo` travels on **every** call, `true` or `false`: the route's Java default is `true`, so leaving a `false` out would ask for the wrong answer (DD-561).                                                                                                                                                                                                                                 |
| CLW-09 | `admin.metrics_stat(collection_time)` answers `GET /metricsstat/{collectionTime}` with the `long` as its parameter and returns one `AtlasMetricsStat` (MHS-02). `admin.metrics_in_range(start_time, end_time, type_names=())` answers `GET /metricsstats/range` with `startTime`, `endTime`, and each type name as a repeated `typeName` (MHS-03); the two times are required, the type names are not. `admin.metrics_charts(start_time, end_time, type_names=())` answers `GET /metricsstats/charts` with the same three parameters and returns the `AtlasMetricsCharts` map (MHS-04).                                                                              |
| CLW-10 | `admin.audit_details(audit_guid, limit=10, offset=0)` answers `GET /audit/{auditGuid}/details` and returns a list of `AtlasEntityHeader` (ADA-05). `admin.server(server_name)` answers `GET /server/{serverName}` and returns the `AtlasServer` (REP-01). `admin.export_import_audit(...)` answers `GET /expimp/audit` with the seven optional parameters `serverName`, `userName`, `operation`, `startTime`, `endTime`, `limit`, `offset` and returns a list of `ExportImportAuditEntry` (REP-05). None of the three checks an admin privilege of its own — they are entity reads on the server, and the client sends no more than the token it was given (DD-307). |
| CLW-11 | `admin.audits(parameters=None)` answers `POST /audits` with an `AuditSearchParameters` body, or none, and returns a list of `AtlasAuditEntry` (ADA-04). `admin.ageout_audits(criteria=None, use_audit_config=False)` answers `POST /audits/ageout` with an `AuditReductionCriteria` body, or none, and sends `useAuditConfig=true` only when the flag is set (AGE-01..AGE-03). The 204 of an aging that queued nothing returns `None`; a queued list returns the `AtlasTask`s — the `None` and `[]` distinction of CSD-03, repeated because "nothing queued" and "nothing matched" ride it (DD-561's second half).                                                   |
| CLW-12 | `AtlasClient.admin` keeps its twelve methods of 8.4 and 8.11 unchanged; the ten new methods join the same class (the CLW-07 pattern — the class grows by extension, the older rows of the matrices are never edited).                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| CAV-01 | `AtlasClient.aurelius` exists as a resource API (DD-203) with paths from `AURELIUS_ROOT = "api/aurelius/v1"` (the CL-60 naming, one root per mounted prefix of the server), and every method is named in a `covers` marker.                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| CAV-02 | `aurelius.semantic_search(parameters)` answers `POST /search/semantic` with a `SemanticSearchParameters` body — the client library's own model, quick search's parameters plus `mode` (DD-562) — and returns the `AtlasQuickSearchResult` (SBM-01..SBM-04, SBM-06, SBM-07). The client validates no mode and no query: `mode` and the empty query are the server's `BAD_REQUEST`s (CL-12).                                                                                                                                                                                                                                                                           |
| CAV-03 | `aurelius.similar_entities(guid, *, type_name=None, exclude_deleted_entities=False, limit=0, offset=0)` answers `GET /entity/guid/{guid}/similar` with the four page parameters as `_present` renders them (SBM-05, SBM-07), and returns the `AtlasQuickSearchResult`.                                                                                                                                                                                                                                                                                                                                                                                               |
| CAV-04 | `aurelius.quality_kinds()` answers `GET /quality/kinds` and returns the client library's `QualityVocabulary` — kinds, castable types, threshold bounds (QRE-01, DD-475). `aurelius.validate_quality_rule(attributes)` answers `POST /quality/rules/validate` with the bare attribute object and returns the `QualityRuleCheck` (QRE-02, QRE-03, DD-476). Both answers are 200s, the unreadable rule included: the client raises on neither.                                                                                                                                                                                                                          |

### The coverage matrix

`routes/admin.py` (22 routes; 5 covered by 8.4, 7 by 8.11, 10 here):

| Method and path             | Server function                 | Client method                         | Rule          |
| --------------------------- | ------------------------------- | ------------------------------------- | ------------- |
| `GET /version`              | (8.4)                           | `admin.version`                       | CL-11 (done)  |
| `GET /status`               | (8.4)                           | `admin.status`                        | CL-11 (done)  |
| `GET /session`              | (8.4)                           | `admin.session`                       | CL-11 (done)  |
| `GET /liveness`             | (8.4)                           | `admin.liveness`                      | CL-11 (done)  |
| `GET /readiness`            | (8.4)                           | `admin.readiness`                     | CL-11 (done)  |
| `GET /patches`              | (8.11)                          | `admin.patches`                       | CLW-01 (done) |
| `PUT /purge`                | (8.11)                          | `admin.purge`                         | CLW-02 (done) |
| `POST /export`              | (8.11)                          | `admin.export`                        | CLW-03 (done) |
| `POST /import`              | (8.11)                          | `admin.import_data`                   | CLW-04 (done) |
| `POST /importfile`          | (8.11)                          | `admin.import_file`                   | CLW-05 (done) |
| `GET /tasks`                | (8.11)                          | `admin.tasks`                         | CLW-06 (done) |
| `DELETE /tasks`             | (8.11)                          | `admin.delete_tasks`                  | CLW-06 (done) |
| `GET /metrics`              | `getMetrics`                    | `admin.metrics` (covered)             | CLW-08        |
| `GET /metricsstats`         | `getAllMetrics`                 | `admin.metrics_stats` (covered)       | CLW-08        |
| `GET /metricsstat/{ct}`     | `getMetricsByCollectionTime`    | `admin.metrics_stat` (covered)        | CLW-09        |
| `GET /metricsstats/range`   | `getMetricsInTimeRange`         | `admin.metrics_in_range` (covered)    | CLW-09        |
| `GET /metricsstats/charts`  | `getMetricsForChartByTypeNames` | `admin.metrics_charts` (covered)      | CLW-09        |
| `GET /audit/{guid}/details` | `getAuditDetails`               | `admin.audit_details` (covered)       | CLW-10        |
| `GET /server/{name}`        | `getCluster`                    | `admin.server` (covered)              | CLW-10        |
| `GET /expimp/audit`         | `getExportImportAudit`          | `admin.export_import_audit` (covered) | CLW-10        |
| `POST /audits`              | `getAtlasAudits`                | `admin.audits` (covered)              | CLW-11        |
| `POST /audits/ageout`       | `ageoutAuditData`               | `admin.ageout_audits` (covered)       | CLW-11        |

The Aurelius-native routes (4 routes, all here):

| Method and path                                   | Server function         | Client method                              | Rule   |
| ------------------------------------------------- | ----------------------- | ------------------------------------------ | ------ |
| `POST /api/aurelius/v1/search/semantic`           | `search_by_meaning`     | `aurelius.semantic_search` (covered)       | CAV-02 |
| `GET /api/aurelius/v1/entity/guid/{guid}/similar` | `similar_entities`      | `aurelius.similar_entities` (covered)      | CAV-03 |
| `GET /api/aurelius/v1/quality/kinds`              | `quality_kinds`         | `aurelius.quality_kinds` (covered)         | CAV-04 |
| `POST /api/aurelius/v1/quality/rules/validate`    | `validate_quality_rule` | `aurelius.validate_quality_rule` (covered) | CAV-04 |

After this increment, `routes/admin.py` is fully covered, and the client's whole
open set is CL-65's two browser routes and ASE's two App Search routes.

Bodies, reused whole (DD-309): `AtlasMetrics`, `AtlasMetricsStat`,
`AtlasMetricsCharts`, `AtlasEntityHeader`, `AtlasServer`,
`ExportImportAuditEntry`, `AtlasAuditEntry`, `AuditSearchParameters`,
`AuditReductionCriteria`, `AtlasTask`, `QuickSearchParameters` — all from
`aurelius-atlas-model`. Defined here (DD-562): `SemanticSearchParameters`,
`QualityKind`, `QualityVocabulary`, `QualityRuleCheck` in
`aurelius_atlas_server_client/aurelius.py`.

## Java origin

The route handlers already carry their Java origin (`AdminResource#getMetrics`,
`#getAllMetrics`, `#getMetricsByCollectionTime`, `#getMetricsInTimeRange`,
`#getMetricsForChartByTypeNames`, `#getAuditDetails`, `#getCluster`,
`#getExportImportAudit`, `#getAtlasAudits`, `#ageoutAuditData`). Nothing new is
ported here: the client methods send the same requests the Java
`AtlasClient`/`AdminClientV2` sends, and the Java client libraries stay dropped
(java-map, row `client`).

## Deviations

None. Each method sends what the route reads and returns the model the route
answers; the `None`-on-204 of `ageout_audits` restates CSD-03's client-side
convention, not a server difference.

## Acceptance

`libs/python/aurelius-atlas-server-client/tests/test__aurelius_atlas_server_client_admin.py`
grows the ten admin tests and `tests/test__aurelius_atlas_server_client_aurelius.py`
holds the four Aurelius ones, each named by `covers` with its rule id, on the
recording transport (CL-02). Run with `nx run aurelius-atlas-server-client:test -c ci`
or `uv run pytest libs/python/aurelius-atlas-server-client/tests`.
