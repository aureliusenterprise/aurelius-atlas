# Conversion

Aurelius Atlas re-implements Apache Atlas 2.4.0 in Python with Elasticsearch 9 as its only store, keeping the REST API and the dashboard ([ADR 046](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>), [ADR 047](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)). The work proceeds in increments ([ADR 051](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/051-the-conversion-proceeds-in-specified-increments/index.md>)); this page is the roadmap and the status of each one.

The ledger in this section is the central record of the conversion:

| Page | What it holds |
| --- | --- |
| [Design Log](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/conversion/design-log/index.md>) | Numbered technical decisions (`DD-NNN`), never edited once accepted |
| [Java to Python Map](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/conversion/java-map/index.md>) | Which Java module or class becomes which Python module, and its status |
| [Deviations from Apache Atlas](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/conversion/deviations/index.md>) | Every intended behaviour difference, referenced by the parity report |
| [Increments](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/conversion/increments/index.md>) | The semantics specification of each increment |

## Definition of done for an increment

```
graph LR
    S[Semantics spec] -->|PR| C[Code + scenarios]
    C -->|parity + trace green| R[Two approvals]
    R -->|merged| D[Done]
    D -.->|records| L[Design log, Java map, deviations]
```

An increment is specified before it is built and proven before it is accepted ([ADR 051](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/adr/051-the-conversion-proceeds-in-specified-increments/index.md>)). The checks a PR must pass:

- [ ] Semantics spec in `increments/`, every rule has an id
- [ ] Every new public function has a test that names it (`@pytest.mark.covers`)
- [ ] Every rule id is named by at least one test
- [ ] Parity scenarios for the endpoints in scope pass, each citing its Atlas source (ADR 052)
- [ ] `nx affected -t lint typecheck test e2e -c ci` is green and the coverage gate holds
- [ ] Design log, Java map and deviations updated; ADR written if a business-level decision was made
- [ ] Conventional-commit title and two human approvals

## Roadmap

Status values: *planned*, *in progress*, *in review*, *done*.

| \# | Increment | Semantics in scope | Java origin | Status |
| --- | --- | --- | --- | --- |
| 0.1 | Adopt the template | Remove unused slices, rename, ADRs 046–051, this ledger | – | done |
| 0.2 | Elasticsearch infrastructure | `dev/elasticsearch`, store library skeleton, health check | – | done |
| 0.3 | Test report and traceability | `covers` marker, function-to-test checker, HTML test report (local tools; CI gates dropped, DD-215) | – | done |
| 0.4 | Parity harness | Scenario format, runner, comparison, deviations, report section | – | in progress |
| 0.5 | Server skeleton | `apps/aurelius-atlas-server`; admin version, status, session, liveness and readiness | `AdminResource` (part) | in progress |
| 0.6 | Dashboards served | `dashboardv2` at `/` and `dashboardv3` at `/n/`, built from the vendored 2.4.0 source | `dashboardv2`, `dashboardv3` | in progress |
| 1.1 | Typedef models | Enum, struct, classification, entity, relationship, business-metadata definitions | `intg/.../model/typedef` | in progress |
| 1.2 | Type registry | Registry and its updates, built-in, array, map, enum and struct types, attribute types, constraints, errors | `AtlasTypeRegistry`, `AtlasStructType`, … | in progress |
| 1.3 | Type hierarchies | Entity and classification super and sub types, inherited attributes, relationship and business metadata types | `AtlasEntityType`, `AtlasRelationshipType`, … | in progress |
| 1.4 | Typedef store | Typedefs in Elasticsearch: create, update, delete with the store's checks; loaded at start-up | `AtlasTypeDefGraphStore`, def stores | in progress |
| 1.5 | Built-in models and patches | `addons/models` loaded at start-up, model patches | `AtlasTypeDefStoreInitializer`, model patches | in progress |
| 1.6 | Types REST | `/v2/types/...` read and write | `TypesREST` | in progress |
| 2.1a | Entity models | `AtlasEntity`, extended info, headers, object ids, classifications, mutation responses | `intg/.../model/instance` | in progress |
| 2.1b | Value types | Value side of the built-in, enum, array and map types; the Atlas JSON codec (DD-025, DD-038) | `AtlasBuiltInTypes`, `AtlasArrayType`, `AtlasMapType` | in progress |
| 2.1c | Entity validation | Value side of the struct, classification, entity, relationship and business metadata types | `AtlasStructType`, `AtlasEntityType` | in progress |
| 2.2 | Entity store | Index layout, GUIDs, unique attributes, optimistic versioning | `AtlasEntityStoreV2` | in progress |
| 2.3 | Entity read REST | By GUID, by unique attributes, bulk, headers | `EntityREST` | in progress |
| 2.4 | Entity write REST | Create/update, partial update, bulk | `EntityREST`, `EntityGraphMapper` | in progress |
| 2.5 | Delete semantics | Soft and hard delete, purge, owned-reference cascades (DD-060) | `DeleteHandlerV1`, `SoftDeleteHandlerV1` | in progress |
| 3.1a | Relationship instances | Relationship CRUD, relationship storage, entity deletes removing relationships | `RelationshipREST`, `AtlasRelationshipStoreV2` | in progress |
| 3.1b | Relationship attributes | `relationshipAttributes` in entity reads and writes, legacy ends and inverse references through relationships | `EntityGraphMapper`, `EntityGraphRetriever` | in progress |
| 3.2 | Ownership cascades | Owned entities an update replaces or drops, and their revival (composition through relationships in deletes: 3.1b, DD-067) | `DeleteHandlerV1`, `EntityGraphMapper` | in progress |
| 3.3a | Direct classifications | Add, update, remove, validity periods; classifications read with entities | `EntityREST`, `AtlasEntityStoreV2`, `EntityGraphMapper` | in progress |
| 3.3b | Bulk classifications | `bulk/setClassifications` | `ClassificationAssociator` | in progress |
| 3.4a | Classification propagation | Propagation within the request, blocked propagation, removal | `DeleteHandlerV1`, `EntityGraphRetriever` | in progress |
| 3.4b | Propagation tasks | Deferred propagation tasks, `pendingTasks`, `admin/tasks` | `ClassificationPropagateTaskFactory`, `TaskManagement` | in progress |
| 3.5a | Entity audit | Entity audit events and audit REST | `EntityAuditListenerV2`, `HBaseBasedAuditRepository` | in progress |
| 3.5b | Classification audit | Classification audit events, `bulk/headers` (DD-074) | `EntityAuditListenerV2`, `ClassificationAssociator` | in progress |
| 4.1a | Entity search | `SearchParameters`, entity filters, operators, sort, paging, search fields | `EntitySearchProcessor`, `SearchContext` | in progress |
| 4.1b | Classification search | Classification filters, wildcards, sub classifications | `ClassificationSearchProcessor` | in progress |
| 4.2a | Free text | Free-text index, basic search `query`, `search/fulltext` | `FreeTextSearchProcessor`, `SolrIndexHelper` | in progress |
| 4.2b | Quick search and suggestions | `search/quick` with facets, `search/suggestions` | `AtlasDiscoveryService`, `SearchAggregatorImpl` | in progress |
| 4.3 | DSL parser | Atlas DSL grammar to AST | `AtlasDSLParser.g4`, `query/` | planned |
| 4.4 | DSL execution | AST to search queries; declared unsupported forms | `GremlinQueryComposer` (replaced) | planned |
| 4.5 | Saved searches and user profile | Saved search CRUD | `UserProfileService` | planned |
| 5.1 | Lineage | Process inputs/outputs, depth, direction, on-demand lineage | `EntityLineageService` | planned |
| 5.2 | Glossary | Glossaries, terms, categories, term assignment | `GlossaryREST`, `GlossaryService` | planned |
| 5.3 | Business metadata and labels | Business metadata attributes, labels | `EntityREST` | planned |
| 6.1 | Authentication | Keycloak OIDC, session endpoints | `AtlasKeycloakAuthenticationProvider` | planned |
| 6.2 | Authorization | Simple authorizer policies on every endpoint | `atlas-simple-authz-policy` | planned |
| 6.3 | Import, export and migration | Atlas export ZIP format, migration of an existing Atlas | `ExportService`, `ImportService` | planned |
| 6.4 | Hardening | Metrics, observability, load test, index tuning | `AdminResource` metrics | planned |
| 7.0 | Webapp foundation (umbrella) | The rules every 7.x slice obeys: standalone, signals, shared dumb UI, Vitest and Playwright, `@angular/localize` | Aurelius `apps/atlas` | planned |
| 7.1 | Webapp shell and localisation | `apps/aurelius-atlas-webapp`: bootstrap, router, runtime config, XLIFF locale bridge, OTel telemetry | Aurelius `apps/atlas/src/app`, `libs/i18n` | in progress |
| 7.2 | Shared UI components | Legacy shared components as dumb `aurelius-atlas-ui` components, each with a story | Aurelius `libs/components` | in progress |
| 7.3 | API client and auth wiring | The Atlas REST client in `aurelius-atlas-data-access`; Keycloak providers and bearer-token interceptor | Aurelius `libs/atlas/api`, `libs/http` | in progress |
| 7.4a | Search results | Hero search bar, results screen (infinite scroll), entry into 7.6 details, browse affordances (SRH-01..11, UIC-21..23; DD-218/219) | Aurelius `apps/atlas/src/app/search/{search,results}`, browse affordances | done |
| 7.4b | Search discovery | Facet sidebar (quick-search aggregations), typeahead suggestions, advanced filters — net-new UX with no legacy copy (SDX) | Aurelius `apps/atlas/src/app/search/components/{filter}` (App Search shape, redesigned) | planned |
| 7.5 | Landing page (browse) | Hero, context cards, info modals; search affordances join 7.4 (DD-143); Shell chrome ported by 7.11 (DD-145) | Aurelius `apps/atlas/src/app/search/browse` | in progress |
| 7.6 | Entity details | Routed details skeleton (route, header, breadcrumbs, properties shell — DET-01..07); the data spine joins server 2.3 (DD-096, DD-097) | Aurelius `apps/atlas/src/app/search/details` | in progress |
| 7.7 | Entity editor | Create and edit forms with validation | Aurelius `apps/atlas/src/app/search/{create,edit}-entity` | planned |
| 7.8 | Governance quality and domains | Classifications, governance quality, domains | Aurelius `apps/atlas/src/app/dashboards` | planned |
| 7.9 | Delete, audit and detail cards | Delete flow, audit events, the remaining detail cards | Aurelius `apps/atlas/src/app/search` | planned |
| 7.10 | Webapp served | The webapp served as the product interface; the example app retires (DV-64) | – | planned |
| 7.11 | Shell chrome | Header and footer around every screen: brand, docs, language switch, account menu; search bar joins 7.4 (DD-145) | Aurelius `libs/shell` | in progress |
| 7.12 | Theme, branding and layout | Aurelius palette, legacy type ramp, forced light mode, logo, pinned navbar, footer below the fold (SHM-01..07) | Aurelius `@models4insight/styles`, `libs/shell` | in progress |
| 7.13 | UI components: details set | Breadcrumbs, entity-card, properties-item, select as dumb components (UIC-11..15, DD-154..155) | Aurelius `search/components/{bread-crumbs,cards}`, `properties-item`, `components/select` | in progress |
| 7.14 | Settings panel | Drawer with theme, language, time zone, page size, telemetry; header gear (SPL-01..13, DD-157..161) | – (new feature, DV-65) | in progress |
| 7.15 | Alerts drawer | Bell with severity badge, routed drawer, grouped alert feed, inbox bar with read tracking, runtime/HTTP error capture (ALR-01..12, DD-171..176, DD-180..185) | – (new feature, DV-66) | in progress |
| 7.16 | UI components: details chrome | classification-chip, type-name, details-navigation, section-stats as dumb components (UIC-16..20, DD-189..192) | Aurelius `search/components/classification`, `type-name`, `details/components/navigation` | in progress |
| 7.17 | Collector ingest auth | Two-leg OTLP ingest: user JWTs on the browser leg (OIDC), shared token on the service leg, loopback-pinned publishes (CIA-01..05, DD-193) | – (platform-side, extends ADR 039) | in progress |
| 7.18 | Collector ingest identity | Per-service ingest identity: client-credentials JWTs on the per-service leg (OIDC), azp-stamped writes, shared-token legacy leg (CIA-06..10, DD-196) | – (platform-side, extends ADR 039) | in progress |
| 7.19 | Frontend failure UX | Test-completeness of the frontend failure paths (DD-214): the data-access error matrix, observability branch holes, config-boot failure, editor failing save/delete, out-of-order search — no new rule ids | — (proves APC-04, SHL-02/14, SPL-03/04) | in progress |
| 8.0 | Auxiliary API foundation | Shared foundation for the ADR 055 data surface: `aurelius-atlas-otel` + `aurelius-atlas-auth` libs, per-service ingest clients (AUX-01..05, DD-108) | Aurelius server `otel_ingest`, FastAPI example app | in progress |
| 8.1 | data2model API | Legacy `/extract` as a FastAPI app: archimate rows in, ar3 model string out, native layout (ADR 055, DV-68) | Aurelius `m4i-data2model`, `m4i-analytics` | planned |
| 8.2 | lineage-model API | Legacy lineage flattening as a FastAPI app: Atlas lineage in, archimate rows out; source stubbed until 5.1 (ADR 055, DV-69) | Aurelius `m4i-lineage-model` | planned |
| 8.3 | validate-entity API | Legacy validation endpoint as a FastAPI app, shipped as the legacy mock (ADR 055, DV-67) | Aurelius `m4i-validate-entity` | in progress |
| 8.4 | API client libraries | Contract + async client library per Python API (CL-01..50, DD-114/115): models move to the lib, the app imports its own contract | Aurelius `libs/atlas/api` (the Angular twin), 8.1-8.3 apps | in progress |
| 8.5 | lineage-model circuit breakers | Per-upstream circuit breakers on the 8.2 chain: outages open the circuit, the open circuit fast-fails 502 (LM-11..15, DD-117, DV-60) | Aurelius `m4i-lineage-model` (bare `requests.post`, no breaker) | in progress |
| 8.6 | Aux API failure hardening | Test-completeness of the 8.1–8.3 failure paths (DD-125): engine view/dynamic-view paths, transport-failure 502, d2m fast-fail, timeout, negative parity scenarios — no new rule ids | — (proves DTM-04/06/07, LM-07/12/13, VE-01) | in progress |
| 8.7 | Client failure contract | Test-completeness of the four client libraries (DD-125): 2xx-with-garbage-body, timeout vs connect error, raising token source, concurrent `with_token` (adds CL-08; proves CL-03/04/05) | — (the 8.4 clients, unproven failure paths) | in progress |
| 9.1 | Targeted resilience e2e | Real-container outages, three scenarios (DD-125): server down → alert + recovery in the browser, chain upstream down → 502 + recovery, logout round-trip at the real Idp (RSL-01..03) | — (no Java twin; Atlas ships no resilience e2e) | in progress |
| 9.2 | Server hardening | TLS as a start-up requirement, opaque 5xx with trace-id requestId, security response headers (SRV-06..08, DD-234..236, DV-85/86) | `AtlasBaseExceptionMapper` (cause echo, superseded for 5xx); no header filter to port | in progress |
| 9.3 | Search cost and client IP | Refresh moves from reads to writes, nginx-edge browser rate limit, uvicorn client-IP trust (ENS-11, SRV-09/10, DD-237/238, DV-87) | — (Atlas refreshes nothing on reads, JanusGraph; no limiter to port) | in progress |
| 9.4 | Edge tracing | The webapp's nginx exports `/api/` spans to the collector's legacy leg; the OTel module builds in the image's dev-stage (ETR-01..03, DD-239) | — (no Java twin; nginx/OTLP are Aurelius infrastructure) | in progress |
| 10.1 | Deployment chart foundation | Component charts in their project folders (`apps/<app>/helm`, `dev/<name>/helm`) + the `helm/` umbrella at the workspace root, the `helm` Nx plugin (targets merge onto the owning projects — a chart is not a project), CI lint/render/publish wiring (CHT-01..07, ADR 057, DD-240..252) | — (Atlas ships compose/k8s examples for a topology this is not) | in progress |
| 10.2 | Stateful platform charts | Elasticsearch, Keycloak and its Postgres as self-managed workloads: storage, trust, health, the GKE coredump agent, deploy-time credentials, the root chart-contract suite (CHT-10..19, DD-253..260) | – | in review |
| 10.3a | App and edge charts | Server, webapp (boot-resolved nginx config + `/config.json`), the three auxiliary APIs (DD-251 closure: the CA mounts, lineage-model upstream URLs); the Gateway API edge at the umbrella (routes, browser certs, BackendTLSPolicy, DD-261 client-IP trust) (CHT-20..32, DD-261..264) | – | in review |
| 10.3b | Observability chart | Collector (three ingest legs, OIDC, one egress), Prometheus, Loki, Tempo, Grafana as workloads; the cluster-native scraping decision 10.2 deferred; the apps' and Keycloak's telemetry wiring turned on (10.2 CHT-16's dormant refs go live) (CHT-33..44) | \#160 | in review |
| 10.5 | Cluster validation | minikube install script and the smoke suite that proves the install end to end (CHT-50..59) | – | planned |

## After phase 0

> [!WARNING]
>
> **Two expat CVEs and a musl CVE are accepted on a temporary basis**
>
> CVE-2026-77214 and CVE-2026-102633 (`expat`/`libexpat` 2.8.5-r1, from the server image's hardened base) are fixed upstream in 2.9.0-r0 but accepted in SonarCloud because no hardened base image carried the fix yet; so is CVE-2026-107891 (`musl` 1.2.6-r2, from the frontend example image's hardened base, fixed in 1.2.6-r3). The acceptance expires with the next base-image refresh — the checklist below is the re-decision, and an accepted risk that nobody re-checks is drift.

To do once the last 0.x increment is done:

- [ ] **Re-check the accepted expat vulnerabilities.** CVE-2026-77214 and CVE-2026-102633 in `expat` and `libexpat` 2.8.5-r1 come from the base image `dhi.io/python:3.14-alpine3.24` of `aurelius-atlas-server`, and are fixed in 2.9.0-r0. They were accepted in SonarCloud on \#85, because no hardened image with the fix existed yet. Before closing them:

  - Check that the current base image ships expat 2.9.0 or later.
  - Check that SonarCloud has closed the four issues as fixed.
  - If either check fails, reopen the issues and decide again.
- [ ] **Re-check the accepted musl vulnerability.** CVE-2026-107891 in `musl` and `musl-utils` 1.2.6-r2 comes from the base image `dhi.io/nginx:1.30-alpine3.24` of `aurelius-atlas-frontend-example`, and is fixed in 1.2.6-r3. It was accepted in SonarCloud on \#139, because no hardened image with the fix existed yet. Before closing it:

  - Check that the current base image ships musl 1.2.6-r3 or later.
  - Check that SonarCloud has closed the two issues as fixed.
  - If either check fails, reopen the issues and decide again.

## After the plan

To do once 6.4 is done, not numbered as an increment yet ([DD-019](<https://aureliusenterprise.github.io/feat-observability-chart/architecture/conversion/design-log/#dd-019-the-template-examples-stay-until-the-plan-is-done>)):

- [ ] **Remove the template's examples.** The FastAPI example service, the Angular example screen, `aurelius-atlas-example`, `aurelius-atlas-sdk`, `libs/angular/*`, `libs/styles`, `dev/postgres` and the Angular, Storybook and Chromatic toolchain leave (ADR 050).

  - `dev/keycloak` stays for 6.1 and takes over `pg_hba.conf` from `dev/postgres`.
  - The rules are tested by a test-only `tools/workspace` project without a Sonar target.
  - They are kept until then because the project's second phase needs them again.
