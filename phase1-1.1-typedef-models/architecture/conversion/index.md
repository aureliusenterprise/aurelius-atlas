# Conversion

Aurelius Atlas re-implements Apache Atlas 2.4.0 in Python with Elasticsearch 9 as its only store, keeping the REST API and the dashboard ([ADR 046](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>), [ADR 047](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)). The work proceeds in increments ([ADR 051](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/adr/051-the-conversion-proceeds-in-specified-increments/index.md>)); this page is the roadmap and the status of each one.

The ledger in this section is the central record of the conversion:

| Page | What it holds |
| --- | --- |
| [Design Log](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/conversion/design-log/index.md>) | Numbered technical decisions (`DD-NNN`), never edited once accepted |
| [Java to Python Map](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/conversion/java-map/index.md>) | Which Java module or class becomes which Python module, and its status |
| [Deviations from Apache Atlas](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/conversion/deviations/index.md>) | Every intended behaviour difference, referenced by the parity report |
| [Increments](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/conversion/increments/index.md>) | The semantics specification of each increment |

## Definition of done for an increment

- [ ] Semantics spec in `increments/`, every rule has an id
- [ ] Every new public function has a test that names it (`@pytest.mark.covers`)
- [ ] Every rule id is named by at least one test
- [ ] Parity scenarios for the endpoints in scope pass, each citing its Atlas source (ADR 052)
- [ ] `nx affected -t lint typecheck test e2e -c ci` is green and the coverage gate holds
- [ ] Design log, Java map and deviations updated; ADR written if a business-level decision was made
- [ ] The test report shows the increment's rules and endpoints as green
- [ ] Conventional-commit title and two human approvals

## Roadmap

Status values: *planned*, *in progress*, *in review*, *done*.

| \# | Increment | Semantics in scope | Java origin | Status |
| --- | --- | --- | --- | --- |
| 0.1 | Adopt the template | Remove unused slices, rename, ADRs 046–051, this ledger | – | done |
| 0.2 | Elasticsearch infrastructure | `dev/elasticsearch`, store library skeleton, health check | – | done |
| 0.3 | Test report and traceability | `covers` marker, function-to-test checker, HTML test report in CI | – | in progress |
| 0.4 | Parity harness | Scenario format, runner, comparison, deviations, report section | – | in progress |
| 0.5 | Server skeleton | `apps/aurelius-atlas-server`; admin version, status, session, liveness and readiness | `AdminResource` (part) | in progress |
| 0.6 | Dashboards served | `dashboardv2` at `/` and `dashboardv3` at `/n/`, built from the vendored 2.4.0 source | `dashboardv2`, `dashboardv3` | in progress |
| 1.1 | Typedef models | Enum, struct, classification, entity, relationship, business-metadata definitions | `intg/.../model/typedef` | in progress |
| 1.2 | Type registry | Attribute types, supertypes, constraints, validation errors | `AtlasTypeRegistry`, `AtlasStructType`, … | planned |
| 1.3 | Typedef storage and bootstrap | Typedef index, built-in models at start-up, typedef versions | `AtlasTypeDefGraphStore`, model patches | planned |
| 1.4 | Types REST | `/v2/types/...` read and write | `TypesREST` | planned |
| 2.1 | Entity models and validation | `AtlasEntity`, extended info, headers, validation | `intg/.../model/instance`, `AtlasEntityType` | planned |
| 2.2 | Entity store | Index layout, GUIDs, unique attributes, optimistic versioning | `AtlasEntityStoreV2` | planned |
| 2.3 | Entity read REST | By GUID, by unique attributes, bulk, headers | `EntityREST` | planned |
| 2.4 | Entity write REST | Create/update, partial update, bulk | `EntityREST`, `EntityGraphMapper` | planned |
| 2.5 | Delete semantics | Soft and hard delete, purge | `DeleteHandlerV1`, `SoftDeleteHandlerV1` | planned |
| 3.1 | Relationship instances | Relationship CRUD and relationship attributes | `RelationshipREST`, `AtlasRelationshipStoreV2` | planned |
| 3.2 | Ownership cascades | Composition and owned-reference cascades | `DeleteHandlerV1` | planned |
| 3.3 | Direct classifications | Add, update, remove, validity periods | `EntityREST` | planned |
| 3.4 | Classification propagation | Propagation, blocked propagation, removal | `ClassificationPropagateTaskFactory` | planned |
| 3.5 | Entity audit | Audit events and audit REST | `EntityAuditRepository` | planned |
| 4.1 | Basic search | `SearchParameters`, filters, operators, sort, paging | `EntitySearchProcessor`, `SearchContext` | planned |
| 4.2 | Quick search and suggestions | Free text, facets, suggestions | `AtlasDiscoveryService` | planned |
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

## After phase 0

To do once the last 0.x increment is done:

- [ ] **Re-check the accepted expat vulnerabilities.** CVE-2026-77214 and CVE-2026-102633 in `expat` and `libexpat` 2.8.5-r1 come from the base image `dhi.io/python:3.14-alpine3.24` of `aurelius-atlas-server`, and are fixed in 2.9.0-r0. They were accepted in SonarCloud on \#85, because no hardened image with the fix existed yet. Check that the current base image ships expat 2.9.0 or later, and that SonarCloud has closed the four issues as fixed. If not, reopen them and decide again.

## After the plan

To do once 6.4 is done, not numbered as an increment yet ([DD-019](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/conversion/design-log/#dd-019-the-template-examples-stay-until-the-plan-is-done>)):

- [ ] **Remove the template's examples.** The FastAPI example service, the Angular example screen, `aurelius-atlas-example`, `aurelius-atlas-sdk`, `libs/angular/*`, `libs/styles`, `dev/postgres` and the Angular, Storybook and Chromatic toolchain leave (ADR 050). `dev/keycloak` stays for 6.1 and takes over `pg_hba.conf` from `dev/postgres`. The rules are tested by a test-only `tools/workspace` project without a Sonar target. They are kept until then because the project's second phase needs them again.
