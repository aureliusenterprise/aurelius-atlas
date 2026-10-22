# Design Log

Technical decisions made during the conversion that are too implementation-specific for an ADR but must not be lost: storage layout, identifiers, query translation, test tooling. Business-level decisions are ADRs in [Architecture Decisions](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/index.md>).

## Rules

- Entries are numbered `DD-NNN`, consecutively; numbers are never reused.
- Statuses: **Proposed** → **Accepted**, then optionally **Superseded by DD-NNN**.
- An accepted entry is never edited except its status line. A changed decision is a new entry that supersedes the old one.
- Every entry names the increment that introduced it, so the reasoning can be found next to the code and the specification it belongs to.
- An increment that makes a decision adds its entry in the same pull request.

## Entry template

```
### DD-NNN. Decision as a statement

- **Status:** Proposed | Accepted | Superseded by DD-NNN
- **Increment:** N.N
- **Date:** YYYY-MM-DD

**Decision.** What we do, in one or two sentences.

**Reason.** Why, in terms of the requirements of the increment.

**Alternatives.** What else was considered and why it lost.

**Consequences.** What follows, including what must be revisited and when.
```

## Log

| \# | Decision | Increment | Status |
| --- | --- | --- | --- |
| [DD-001](<#dd-001-reference-is-apache-atlas-240-and-both-dashboards-are-served>) | The reference is Apache Atlas 2.4.0; both dashboards are served unchanged | 0.1 | Accepted |
| [DD-002](<#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>) | Atlas code lives in `aurelius-atlas-*` projects split by layer | 0.1 | Accepted |
| [DD-003](<#dd-003-template-projects-are-renamed-to-the-aurelius-atlas-prefix>) | All template projects carry the `aurelius-atlas-` prefix | 0.1 | Accepted |
| [DD-004](<#dd-004-the-spa-keeps-tokens-in-memory-and-renews-them-silently>) | The SPA keeps tokens in memory and renews them silently | 0.1 | Accepted |
| [DD-005](<#dd-005-the-store-uses-the-official-async-elasticsearch-client>) | The store uses the official async Elasticsearch client, one per store | 0.2 | Proposed |
| [DD-006](<#dd-006-development-and-tests-run-elasticsearch-with-security-on>) | Development and tests run Elasticsearch with TLS and authentication on | 0.2 | Proposed |
| [DD-007](<#dd-007-the-elasticsearch-test-fixture-ships-with-the-store-library>) | The Elasticsearch test fixture ships with the store library | 0.2 | Proposed |
| [DD-008](<#dd-008-a-yellow-cluster-is-healthy>) | A yellow cluster is healthy | 0.2 | Proposed |
| [DD-009](<#dd-009-traceability-is-checked-from-collected-markers-not-from-a-test-run>) | Traceability is checked from collected markers, not from a test run | 0.3 | Proposed |
| [DD-010](<#dd-010-the-traceability-check-covers-atlas-code-from-increment-02-on>) | The traceability check covers Atlas code from increment 0.2 on | 0.3 | Proposed |
| [DD-011](<#dd-011-the-test-report-is-generated-from-junit-coverage-and-trace-files>) | The test report is generated from JUnit, coverage and trace files | 0.3 | Proposed |
| [DD-012](<#dd-012-parity-scenarios-are-yaml-files-run-as-parametrised-pytest-tests>) | Parity scenarios are YAML files run as parametrised pytest tests | 0.4 | Proposed |
| [DD-013](<#dd-013-a-scenario-response-is-compared-exactly-except-at-declared-paths>) | A scenario response is compared exactly, except at declared paths | 0.4 | Proposed |
| [DD-014](<#dd-014-scenario-facts-reach-the-report-as-test-properties>) | Scenario facts reach the report as test properties | 0.4 | Proposed |
| [DD-015](<#dd-015-the-server-is-a-fastapi-application-with-one-router-per-atlas-resource>) | The server is a FastAPI application with one router per Atlas resource | 0.5 | Proposed |
| [DD-016](<#dd-016-the-server-does-not-start-without-its-store>) | The server does not start without its store | 0.5 | Proposed |
| [DD-017](<#dd-017-the-dashboards-are-vendored-unchanged-and-built-with-dart-sass-on-node-24>) | The dashboards are vendored unchanged and built with dart-sass on Node 24 | 0.6 | Proposed |
| [DD-018](<#dd-018-the-server-serves-the-dashboards-from-the-apis-origin>) | The server serves the dashboards from the API's origin | 0.6 | Proposed |
| [DD-019](<#dd-019-the-template-examples-stay-until-the-plan-is-done>) | The template examples stay until the plan is done | 0.6 | Proposed |
| [DD-020](<#dd-020-typedef-models-are-pydantic-models-that-read-and-write-atlass-json>) | Typedef models are Pydantic models that read and write Atlas's JSON | 1.1 | Proposed |
| [DD-021](<#dd-021-set-valued-fields-keep-each-name-once-in-first-seen-order>) | Set-valued fields keep each name once, in first-seen order | 1.1 | Proposed |
| [DD-022](<#dd-022-typedef-timestamps-are-aware-datetimes-written-as-epoch-milliseconds>) | Typedef timestamps are aware datetimes, written as epoch milliseconds | 1.1 | Proposed |
| [DD-023](<#dd-023-atlas-errors-live-in-the-model-library>) | Atlas errors live in the model library | 1.2 | Proposed |
| [DD-024](<#dd-024-the-registry-is-updated-on-a-transient-copy-under-a-re-entrant-lock>) | The registry is updated on a transient copy under a re-entrant lock | 1.2 | Proposed |
| [DD-025](<#dd-025-the-type-system-ports-the-definition-side-only>) | The type system ports the definition side only | 1.2 | Proposed |
| [DD-026](<#dd-026-dynamic-attributes-and-search-lookups-wait-for-their-increments>) | Dynamic attributes and search lookups wait for their increments | 1.3 | Proposed |
| [DD-027](<#dd-027-derived-type-sets-keep-first-seen-order>) | Derived type sets keep first-seen order | 1.3 | Proposed |
| [DD-028](<#dd-028-the-type-definitions-are-one-elasticsearch-document>) | The type definitions are one Elasticsearch document | 1.4 | Proposed |
| [DD-029](<#dd-029-server-processes-share-the-type-definitions-through-the-documents-version>) | Server processes share the type definitions through the document's version | 1.4 | Proposed |
| [DD-030](<#dd-030-the-store-asks-the-entity-store-whether-a-type-is-in-use>) | The store asks the entity store whether a type is in use | 1.4 | Proposed |
| [DD-031](<#dd-031-the-patch-records-live-in-the-typedef-document>) | The patch records live in the typedef document | 1.5 | Proposed |
| [DD-032](<#dd-032-the-built-in-models-are-vendored-unchanged-and-read-from-a-directory>) | The built-in models are vendored unchanged and read from a directory | 1.5 | Proposed |
| [DD-033](<#dd-033-start-up-loading-is-one-change-per-model-file-and-per-patch>) | Start-up loading is one change per model file and per patch | 1.5 | Proposed |
| [DD-034](<#dd-034-lists-of-type-definitions-are-sorted-by-name>) | Lists of type definitions are sorted by name | 1.6 | Proposed |
| [DD-035](<#dd-035-type-scenarios-create-what-they-read-and-delete-it-at-their-end>) | Type scenarios create what they read and delete it at their end | 1.6 | Proposed |
| [DD-036](<#dd-036-start-up-loading-tries-a-raced-change-again>) | Start-up loading tries a raced change again | 1.6 | Proposed |
| [DD-037](<#dd-037-instance-models-are-one-module-per-java-class>) | Instance models are one module per Java class | 2.1 | Proposed |
| [DD-038](<#dd-038-attribute-values-stay-plain-json-values-until-their-types-read-them>) | Attribute values stay plain JSON values until their types read them | 2.1 | Proposed |
| [DD-039](<#dd-039-one-atlas-json-codec-reads-floats-as-decimals-and-writes-them-with-their-digits>) | One Atlas JSON codec reads floats as decimals and writes them with their digits | 2.1 | Proposed |
| [DD-040](<#dd-040-java-values-are-held-as-the-python-values-closest-to-them>) | Java values are held as the Python values closest to them | 2.1 | Proposed |
| [DD-041](<#dd-041-the-type-system-is-one-module-per-java-type-class-too>) | The type system is one module per Java type class too | 2.1 | Proposed |
| [DD-042](<#dd-042-a-validity-period-without-a-time-zone-is-in-utc>) | A validity period without a time zone is in UTC | 2.1 | Proposed |
| [DD-043](<#dd-043-entities-are-documents-of-one-index-their-attributes-under-qualified-names>) | Entities are documents of one index, their attributes under qualified names | 2.2 | Proposed |
| [DD-044](<#dd-044-a-guid-is-a-random-uuid>) | A GUID is a random UUID | 2.2 | Proposed |
| [DD-045](<#dd-045-unique-values-are-reserved-by-create-only-documents>) | Unique values are reserved by create-only documents | 2.2 | Proposed |
| [DD-046](<#dd-046-a-multi-entity-write-is-all-or-nothing-through-a-journal>) | A multi-entity write is all or nothing, through a journal | 2.2 | Proposed |
| [DD-047](<#dd-047-entities-are-written-conditionally-on-their-elasticsearch-version>) | Entities are written conditionally on their Elasticsearch version | 2.2 | Proposed |
| [DD-048](<#dd-048-a-type-is-in-use-while-the-entity-index-holds-one-of-it>) | A type is in use while the entity index holds one of it | 2.2 | Proposed |
| [DD-049](<#dd-049-attribute-values-are-stored-normalised-a-struct-inline-a-reference-as-a-guid>) | Attribute values are stored normalised; a struct inline, a reference as a GUID | 2.3 | Proposed |
| [DD-050](<#dd-050-relationship-attributes-read-empty-until-relationships-are-stored>) | Relationship attributes read empty until relationships are stored | 2.3 | Proposed |
| [DD-051](<#dd-051-entity-reads-are-tested-on-entities-written-through-the-store-until-24>) | Entity reads are tested on entities written through the store until 2.4 | 2.3 | Proposed |
| [DD-052](<#dd-052-a-request-is-mapped-in-memory-and-written-once-a-lost-race-runs-it-again>) | A request is mapped in memory and written once; a lost race runs it again | 2.4 | Proposed |
| [DD-053](<#dd-053-relationship-attribute-values-are-resolved-but-stored-only-as-legacy-attributes-until-31>) | Relationship attribute values are resolved, but stored only as legacy attributes until 3.1 | 2.4 | Proposed |
| [DD-054](<#dd-054-dynamic-attributes-are-evaluated-in-first-seen-dependency-order>) | Dynamic attributes are evaluated in first-seen dependency order | 2.4 | Proposed |
| [DD-055](<#dd-055-scenarios-name-what-they-create-with-a-per-run-value>) | Scenarios name what they create with a per-run value | 2.4 | Proposed |
| [DD-056](<#dd-056-an-entity-write-also-removes-documents-journaled-like-the-others>) | An entity write also removes documents, journaled like the others | 2.5 | Proposed |
| [DD-057](<#dd-057-entities-referring-to-one-are-found-through-an-indexed-field-of-guids>) | Entities referring to one are found through an indexed field of GUIDs | 2.5 | Proposed |
| [DD-058](<#dd-058-a-stored-reference-stands-for-an-edge-active-for-a-delete-deleted-for-a-purge>) | A stored reference stands for an edge: active for a delete, deleted for a purge | 2.5 | Proposed |
| [DD-059](<#dd-059-the-delete-type-and-its-override-are-server-settings>) | The delete type and its override are server settings | 2.5 | Proposed |
| [DD-060](<#dd-060-the-owned-reference-cascade-moves-from-32-to-25>) | The owned-reference cascade moves from 3.2 to 2.5 | 2.5 | Proposed |

### DD-001. Reference is Apache Atlas 2.4.0, and both dashboards are served

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-09

**Decision.** The behaviour to reproduce is that of the `release-2.4.0` tag of Apache Atlas. Both of its user interfaces are served unchanged at the paths Atlas uses: `dashboardv2` at `/` and `dashboardv3` at `/n/`. End-to-end tests cover `dashboardv3` in depth and `dashboardv2` with a smoke test.

**Reason.** Parity tests need one fixed reference ([ADR 048](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted/index.md>)), and 2.4.0 is the latest Apache Atlas release. Atlas 2.4.0 serves the classic interface at the root and the newer one under `/n/`, and each links to the other; serving both keeps every bookmark and link working at the cost of one more static build, whereas dropping one would be a visible deviation.

**Alternatives.** Track Atlas `master`: unstable fixtures, no released artefact to compare against. Serve only `dashboardv3` and redirect `/` to `/n/`: one build less, but breaks the switch-back link and existing bookmarks, and would need a deviation entry.

**Consequences.** A move to a later Atlas release is a new entry plus a re-recording of all fixtures. Features used only by `dashboardv2` still need backend support; they are found by its smoke test.

### DD-002. Atlas code lives in aurelius-atlas projects split by layer

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-09

**Decision.** Atlas code is split into workspace projects by layer, all prefixed `aurelius-atlas-` (Python packages `aurelius_atlas_*`): `-model` (data shapes, no I/O), `-typesystem` (type registry and validation), `-store-es` (Elasticsearch access), `-core` (stores and services), `-dsl` (query language), `apps/aurelius-atlas-server` (REST), `apps/aurelius-atlas-dashboard` (UI), `reports/aurelius-atlas-test-report`, plus `dev/elasticsearch` and `dev/atlas-reference`.

**Reason.** Layers that do not do I/O can be unit-tested without infrastructure; the dependency direction (model ← typesystem ← core → store-es; server → core) keeps each increment's change local, and each project follows an existing template recipe. The `aurelius` prefix keeps the organisation's naming convention.

**Alternatives.** One large package mirroring the Java module tree: simpler imports, but every change touches the same project and nothing can be tested in isolation. A package per Java module (`intg`, `repository`, `webapp`): mirrors history rather than the dependency structure we want.

**Consequences.** Projects are created by the increment that first needs them, not up front.

### DD-003. Template projects are renamed to the aurelius-atlas prefix

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-17

**Decision.** All workspace projects inherited from the template carry the `aurelius-atlas-` prefix (directories, Nx names, uv/npm package names, Python import packages, env-var prefixes, Sonar keys, compose project and network names, Grafana dashboards). The org handle `aureliusenterprise`, the npm scope `@aurelius`, the Keycloak client/realm ids (`aurelius`, `master`), and the DB name (`aurelius`) are identities of the organisation/Keycloak and stay unchanged.

**Reason.** DD-002 fixes the `aurelius-atlas-` prefix for the Atlas projects; renaming the template examples now, while they are the only content, avoids two naming generations in one repo and the churn of renaming them piecemeal once Atlas code lands beside them.

**Alternatives.** Rename only new Atlas projects: leaves `aurelius-*` and `aurelius-atlas-*` side by side, which reads as two projects with different ownership. Keep the template names entirely: makes the eventual atlas-vs-template distinction implicit rather than visible in the project graph.

**Consequences.** Docker image names change (`ghcr.io/aureliusenterprise/aurelius-atlas-*`); Sonar projects, Chromatic, and any external CI references must be created/renamed to match. `.env.enc` files were re-encrypted with the new prefixed keys. Old locally built images are stale and should be pruned (`docker image prune` / rebuild via `nx e2e`).

### DD-004. The SPA keeps tokens in memory and renews them silently

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-17

**Decision.** The Angular SPA uses Keycloak's default in-memory token store (`tokenStore: "default"` in `provideKeycloak`, `apps/aurelius-atlas-frontend-example/src/app/app.config.ts`) with `onLoad: "check-sso"` and a silent-SSO redirect (`/silent-check-sso.html`). Access and refresh tokens never touch `localStorage` or any other persistent browser storage.

**Reason.** `localStorage` is readable by any script that achieves XSS on the origin, and is also exposed to browser extensions with host permissions; a stolen refresh token there is a durable session hijack. With the in-memory store, injected script can read the current access token but the attacker's code dies with the page, and a reload forces a fresh authentication check against Keycloak rather than replaying stored secrets.

**Alternatives.** `tokenStore: "sessionStorage"`: survives reload in the tab, but every XSS or extension read is still one `getItem` away — same theft surface, no meaningful gain. `tokenStore: "localStorage"`: survives tab close; strongest theft value, rejected. A confidential client with a BFF holding tokens server-side: the right answer at scale, deferred as its own increment — it changes the auth topology (new service, cookie session) rather than a setting.

**Consequences.** A page reload re-mints tokens via silent SSO; the user sees no login unless the Keycloak SSO session itself has ended. Silent SSO relies on a third-party-cookie-acceptable (or same-site) Keycloak deployment: where browsers block the framing cookie, `check-sso` degrades to a not-signed-in state and the app falls back to a full redirect login (`login()`), which still works. If per-tab token durability becomes a product requirement, supersede this entry by adding the BFF — not by moving the tokens to storage.

### DD-005. The store uses the official async Elasticsearch client

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-store-es` talks to Elasticsearch through `AsyncElasticsearch` from the official `elasticsearch` Python client, version 9.5 or later within major 9, matching the 9.5 server (`dhi.io/elasticsearch:9.5-debian13`; minor upgrades are deliberate, patch releases follow the tag). A store instance owns exactly one client, opened and closed with the store (`async with`).

**Reason.** The server is FastAPI and asynchronous; a blocking client would tie up the event loop or need a thread pool. The official client tracks the server's API and versioning, ships typed request helpers, and includes the query DSL module that search (4.x) will need.

**Alternatives.** `httpx` against the REST API directly: no extra dependency, but every API, retry and error type would be rebuilt by hand. `opensearch-py`: a different server; ADR 047 names Elasticsearch. One client per request: simple, but loses connection pooling.

**Consequences.** The client's major version moves with the server's (STO-04 guards it). Connection pooling and retries are the client's; tuning them is part of 6.4.

### DD-006. Development and tests run Elasticsearch with security on

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** `dev/elasticsearch` and the test fixture run with `xpack.security` enabled: TLS on the HTTP layer with a certificate from the workspace CA (dev) or an ephemeral CA (tests), and basic authentication for the built-in `elastic` user. The store library has no option to skip certificate verification.

**Reason.** It is the posture production needs, and the one `dev/postgres` already has; a store that only ever ran without security would meet TLS and authentication for the first time in production.

**Alternatives.** Security disabled in development: faster start-up and simpler `curl`, but a different code path (plain HTTP, no credentials) from production, and a verification switch in the library that someone eventually leaves off.

**Consequences.** Dev tools need the CA file and the password (`curl --cacert dev/elasticsearch/certs/ca.pem -u elastic:…`). A dedicated application user with least privilege replaces `elastic` when authorization arrives (6.2).

### DD-007. The Elasticsearch test fixture ships with the store library

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** The testcontainers helper that starts a TLS-enabled Elasticsearch lives in `aurelius_atlas_store_es.testing`, behind the library's `testing` extra, next to the code it serves.

**Reason.** Every later project with a store (`-core`, the server, the parity harness) needs the same container; the library that defines the settings is the one that knows how to build them for a test server, and keeping both together means a settings change cannot break the fixture unnoticed.

**Alternatives.** `aurelius-atlas-sdk.testing`, where the Postgres helper lives: would make the generic SDK depend on Elasticsearch. A copy per project: drifts.

**Consequences.** Test-only dependencies (`testcontainers`, `trustme`) stay out of the runtime install; consuming projects add `aurelius-atlas-store-es[testing]` to their dev dependencies.

### DD-008. A yellow cluster is healthy

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** The store's health check reports up for cluster status green or yellow and down for red (STO-05).

**Reason.** Yellow means every primary shard is assigned and all data is readable and writable; only replicas are missing. A single-node cluster, the development and small-installation case ([ADR 006](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), is yellow as soon as an index has a replica. Reporting it down would make every single-node deployment permanently unready.

**Alternatives.** Green only: correct for multi-node clusters, unusable for single-node ones unless every index is created with zero replicas. A configurable threshold: one more setting nobody sets.

**Consequences.** Lost redundancy is not visible as a health failure; it is visible in the cluster metrics (ESD-06) and should be alerted on there.

### DD-009. Traceability is checked from collected markers, not from a test run

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-trace check` runs `pytest --collect-only` over the unit and end-to-end tests of every Atlas project and reads the `covers` markers from the collected items. Whether the naming tests pass is the test job's concern, not the check's.

**Reason.** CI runs `nx affected -t test e2e`, so the results of one run contain only the affected projects' tests; a check over them would report every unaffected function as uncovered (TRC-10). Collection imports the tests but starts no containers, so it is cheap enough to run on every change.

**Alternatives.** Merge the trace files of the run with those of the last run on `main`: needs artifact plumbing between workflows and still goes stale when a run on `main` fails. Run every test on every change: correct, but turns a one-minute check into the full end-to-end suite. Parse the test sources with `ast`: misses markers applied through `pytestmark`, classes and parametrisation.

**Consequences.** A test module that fails to import fails the check, which is the right answer: its markers are unknown. A test that names a function but is skipped still counts as naming it; the report shows it as skipped.

### DD-010. The traceability check covers Atlas code from increment 0.2 on

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** R1 applies to the public functions, methods and properties of every uv workspace member that the configuration does not exclude; the template projects (examples, SDK, reports) are excluded, and so are `testing` subpackages, which are test infrastructure. R2 applies to the rules of every specification from increment 0.2 on. The configuration is the `[tool.aurelius-atlas-trace]` table of the root `pyproject.toml`.

**Reason.** Template code is removed or replaced by the conversion (0.5 removes the examples), so markers on it would be written to be deleted. Excluding instead of listing makes a new Atlas project checked by default. Increment 0.1's rules (ADO-01 to ADO-03) describe the adoption of the template and were verified when it merged; 0.2 is the first increment with code, and its manual checks of ESD-01 to ESD-06 are replaced by tests in this increment.

**Alternatives.** Check every workspace member: retrofits markers onto code about to be deleted. List the Atlas projects explicitly: a new project is silently unchecked until someone adds it.

**Consequences.** A project that leaves the template set (the SDK, if it is kept) is removed from the exclusion list and gets its markers in the same change.

### DD-011. The test report is generated from JUnit, coverage and trace files

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-trace report` turns JUnit XML (`pytest --junitxml`), Cobertura XML (`pytest-cov`) and the plugin's trace JSON into one static HTML page and a Markdown summary. CI uploads the page as the `test-report` artifact and appends the summary to the run page.

**Reason.** ADR 045's ladder: the input formats are the ecosystem's own, and no framework or community tool joins test results to specification rules and to a function inventory, which is the view ADR 049 R3 asks for. The generator is a few hundred lines with the standard library only.

**Alternatives.** Allure Report: a polished viewer, but it needs its Java CLI, and the per-rule and per-function gap view would still be ours to build as labels and post-processing. `pytest-html`: one page of test results, nothing about rules or functions. SonarCloud: shows coverage, not traceability.

**Consequences.** The page is an artifact of the CI run, not a published site; 0.4 adds the parity results to it. If a later need (history, trends) outgrows a static page, a viewer is chosen then.

### DD-012. Parity scenarios are YAML files run as parametrised pytest tests

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** A scenario is a `*.scenario.yaml` file in the stage shape of Tavern (`request`, `response`, `save`), validated with pydantic. A project's test module turns a directory of them into one parametrised test, `load_scenarios(directory)`, whose body is `await run_scenario(scenario, client)`; the project's fixture decides whether `client` talks to the application in-process (`httpx.ASGITransport`) or over HTTP to a running server.

**Reason.** ADR 045's ladder: the request/response/save stage is the community's shape for declarative API tests, so reviewers who know Tavern read our scenarios at once. Running scenarios as ordinary pytest parameters puts them in JUnit, in the trace file and under `covers` (SCN-04) with public pytest API only.

**Alternatives.** Tavern itself: speaks HTTP through `requests` only, so the in-process unit level is lost, and the exact comparison, volatile paths and deviations (DD-013) would be hooks around it. A custom collector for `*.scenario.yaml`: shorter test modules, but it needs pytest's private fixture API to give the items a client. Schemathesis: generates requests from an OpenAPI document, which Atlas 2.4.0 does not ship and which states types, not Atlas's answers.

**Consequences.** Every project with scenarios has one small test module and a `client` fixture. The scenario format is ours to keep stable; it is versioned by its rules SCN-01 to SCN-03.

### DD-013. A scenario response is compared exactly, except at declared paths

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** The expected body must equal the actual body: the same keys, arrays in the same order, booleans and null distinct from numbers. Only `volatile` paths (generated GUIDs, timestamps) skip the value, and only `deviations` entries change the expectation, each naming its `DV-NN`.

**Reason.** The dashboard and existing clients read fields the scenarios might not think of; an extra, missing or `null` field is a visible difference ([ADR 046](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). Atlas serialises its models with Jackson `NON_NULL` inclusion, so "absent" and `null` differ there and must differ here.

**Alternatives.** Subset matching: short scenarios, but an extra or misnamed field passes. Snapshot files written from our own responses: exact, but the expectation would come from the implementation, not from Atlas (ADR 052 R1).

**Consequences.** Expectations for large responses are long; scenarios borrow Atlas's own test fixtures for request bodies to keep writing them cheap. Arrays whose order Atlas does not define get an explicit order-insensitive option when the first increment needs one.

### DD-014. Scenario facts reach the report as test properties

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** The parity plugin adds each scenario's endpoints and deviation ids to the test item's `user_properties` at collection. The trace plugin writes every test's properties to the trace file, so `check` (unknown deviations) and `report` (one row per endpoint) read them from the collection they already do.

**Reason.** `user_properties` is pytest's own channel for facts about a test, and JUnit carries it too. Reading it at collection keeps the report's rule of DD-009: an endpoint whose scenarios did not run in this change is *not run*, not missing.

**Alternatives.** A separate `--parity-json` file: a second format next to the trace file for the same tests. Make the trace library know scenarios: couples the traceability tool to one kind of test.

**Consequences.** The trace file format gains a `properties` field per test; readers of version 1 files without it see no properties. Property names are prefixed with the plugin that sets them (`parity.`).

### DD-015. The server is a FastAPI application with one router per Atlas resource

- **Status:** Proposed
- **Increment:** 0.5
- **Date:** 2026-10-17

**Decision.** `apps/aurelius-atlas-server` is a FastAPI application built like the template's example service (settings, uvicorn entry point, logfire, hardened image), with one router module per Atlas REST resource class (`AdminResource` → `routes/admin.py`, later `EntityREST` → `routes/entity.py`). Atlas errors are raised as `AtlasError` and turned into the Atlas error body by one exception handler, as `AtlasBaseExceptionMapper` does; JSON goes out as `application/json; charset=UTF-8`.

**Reason.** ADR 045's ladder: FastAPI and the example's wiring are the workspace's convention, already gated, observed and packaged. Mirroring the Java resource classes keeps the Java map one row per class and lets a reviewer put a router next to its Java resource.

**Alternatives.** Starlette without FastAPI: no validation or OpenAPI for the request models later increments need. Routers per URL prefix rather than per Java class: `admin` would still be one, but `/v2/entity` and `/v2/entity/bulk` belong to one Java class and would split.

**Consequences.** The example service is no longer the only FastAPI app; it stays until the plan is done (DD-019). Later increments add routers and error codes; the error handler and media type stay.

### DD-016. The server does not start without its store

- **Status:** Proposed
- **Increment:** 0.5
- **Date:** 2026-10-17

**Decision.** The server opens the Elasticsearch store in its start-up and stops with an error when the store cannot be opened (unreachable, rejected, or not Elasticsearch 9). Once running, `readiness` reports the store's health on every call, and `liveness` and `status` do not depend on it.

**Reason.** The store is the only system of record ([ADR 047](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)); a server without it cannot answer anything but the admin endpoints. Failing at start-up shows a wrong setting at once ([ADR 018](<https://aureliusenterprise.github.io/phase2-2.5-delete-semantics/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)) and lets an orchestrator restart the container, while readiness covers a store that goes away later.

**Alternatives.** Start without the store and retry in the background: a misconfigured server would run and only its readiness would say so. Make liveness depend on the store: an outage of Elasticsearch would make an orchestrator restart every server, which does not help.

**Consequences.** Start-up order matters: `nx serve` and the end-to-end tests start the dev store first.

### DD-017. The dashboards are vendored unchanged and built with dart-sass on Node 24

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** `apps/aurelius-atlas-dashboard/dashboardv2` and `dashboardv3` are copies of the `release-2.4.0` tag, byte for byte, with Atlas's `LICENSE` and `NOTICE`. Every change is a patch listed in `PATCHES.md` and made in its own commit. The first patch replaces `node-sass` with `sass` (dart-sass) in both `gruntfile.js` files and `package.json` files. Both dashboards are built with `grunt build-minify`, as Atlas's Maven build does, in the hardened Node 24 image; only the built files leave the build. The workspace's formatters, linters and hooks skip the vendored directories.

**Reason.** DD-001 asks for the dashboards unchanged; a vendored copy lets a reviewer prove that with a diff against the tag. `node-sass` 9 is a native module with builds for Node 16 to 20 only, and Node 20 is past its end of life; dart-sass is pure JavaScript, the maintained Sass compiler, and `grunt-sass` supports it. A trial build on Node 24 gave the same files as Atlas's toolchain on Node 20, with identical JavaScript; only the two compiled stylesheets differ.

**Alternatives.** Build unchanged on Node 20: no patch, but an unsupported Node and a native compile in every build. Download the tag at build time and apply patch files: a smaller repository, but the source the build uses is not in review. Commit the built files: no legacy toolchain at all, but the shipped files cannot be reviewed or rebuilt.

**Consequences.** The vendored `package-lock.json` files keep their 2020-era dependencies; they only run inside the build container and are not part of the server image, so Dependabot does not watch them. Moving to another Atlas release replaces both directories and re-applies `PATCHES.md`.

### DD-018. The server serves the dashboards from the API's origin

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** The server mounts the built `dashboardv3` at `/n/` and `dashboardv2` at `/` as static files, after the API routes, when `AURELIUS_ATLAS_SERVER_DASHBOARD_DIR` names their directory. The server image contains the built dashboards and sets that setting.

**Reason.** The dashboards call `api/atlas/...` with relative URLs and rely on the session cookie of the same origin, as in Atlas's web application. Serving them from the server keeps that without a proxy or cross-origin configuration, and one image is the whole product.

**Alternatives.** A separate static file server or the template's Angular serving: a second container and a proxy to keep one origin. Serving through a CDN: possible later in front of the server; nothing here prevents it.

**Consequences.** API paths must never collide with dashboard files; the API is matched first. Unit tests build their settings without the environment and serve no dashboards unless a test sets the directory; `nx serve` builds the dashboards first and its `.env` points at `dist/`.

### DD-019. The template examples stay until the plan is done

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** The removal of the template's examples, planned as increment 0.7, moves to a to-do after 6.4. Until then, the FastAPI example service, the Angular example screen and its libraries, `aurelius-atlas-example`, `aurelius-atlas-sdk` and `dev/postgres` stay in the workspace. They remain the named deviation of ADR 050.

**Reason.** The project's second phase needs these components again. Removing them now and restoring them from the template later would cost more than keeping them.

**Alternatives.** Remove them now, as ADR 050 plans once the server and the dashboards replace them: this fulfils ADR 050's R1 sooner, but the components would have to be restored for the second phase.

**Consequences.** CI keeps building, testing and scanning the examples. 1.1 follows 0.6 directly. The to-do in the roadmap records the scope already agreed for the removal: everything the catalogue does not use, apart from `dev/keycloak`.

### DD-020. Typedef models are Pydantic models that read and write Atlas's JSON

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** Each Atlas typedef class is a Pydantic model in `aurelius_atlas_model.typedef` with snake\_case attributes and the Java getter names as aliases. `model_validate` reads a request body and `to_json` writes a response body: aliases, null fields left out, empty collections kept. Unknown fields are ignored. The Java setters' normalisations run as `_`-prefixed validators, so they apply when a body is read and when a model is built in code, as the Java constructors and setters do.

**Reason.** Pydantic is already the workspace's modelling library (settings, store) and FastAPI reads and writes it natively, so 1.6 needs no mapping layer. Atlas writes with Jackson `NON_NULL`, which is Pydantic's `exclude_none`; empty collections stay because Jackson keeps them (DD-013 compares exactly).

**Alternatives.** Dataclasses with a hand-written JSON codec: no dependency, but every rule of TDM-01 to TDM-15 would be custom code. Generating models from Atlas's JSON schema: Atlas publishes none, and the normalisations live in Java setters a schema cannot express.

**Consequences.** Response bodies must be written with `to_json` (or its `exclude_none`, `by_alias` dump), never with FastAPI's default response model serialisation. Later model packages (entities in 2.1) follow the same pattern.

### DD-021. Set-valued fields keep each name once, in first-seen order

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `superTypes`, `subTypes` and `entityTypes` are lists without duplicates, kept in the order the names were first given.

**Reason.** Java holds them in a `HashSet` and writes them in hash order, which Atlas does not define and no client can rely on. A Python `set` would make our order vary from run to run; first-seen order is stable and keeps what the client sent.

**Alternatives.** Reproduce Java's `HashSet` iteration order: possible from `String.hashCode` and the table size, but it would copy an accident of the implementation. Sorted order: stable, but reorders what clients send.

**Consequences.** The JSON order of these arrays can differ from Atlas's. Parity scenarios compare them without order, through the option DD-013 foresees, which 1.6 adds with the first scenario that needs it.

### DD-022. Typedef timestamps are aware datetimes, written as epoch milliseconds

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `createTime` and `updateTime` are timezone-aware UTC `datetime`s. They are written as integer milliseconds since the epoch and read from a number, a string of digits or an ISO-8601 date-time string.

**Reason.** Atlas's REST mapper has no date serialiser, so Jackson writes `java.util.Date` as epoch milliseconds and its `StdDateFormat` reads numbers, digit strings and ISO-8601. Pydantic would read a bare integer as seconds or milliseconds depending on its size, so the conversion is explicit.

**Alternatives.** Keep the raw integer: exact, but every caller would convert. Write ISO-8601 strings: readable, but a visible difference from Atlas.

**Consequences.** Jackson's RFC 1123 form (`Tue, 17 Oct 2026 10:00:00 GMT`) is not read. No Atlas client is known to send it; if one does, it becomes a deviation.

### DD-023. Atlas errors live in the model library

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** `AtlasErrorCode` and `AtlasError` move from `aurelius_atlas_server.errors` to `aurelius_atlas_model.errors`. Each code keeps Atlas's HTTP status, error code and message template. The server keeps the error handler and the response class and imports the errors from there.

**Reason.** The type system (1.2) and the stores raise Atlas errors, and they may not depend on the server (DD-002: model ← typesystem ← core; server → core). In Java, too, `AtlasErrorCode` sits in `intg`, below everything else.

**Alternatives.** A separate errors library: one more project for two classes. Each layer with its own exception, mapped in the server: the mapping would repeat Atlas's error table.

**Consequences.** New error codes are added to `aurelius_atlas_model.errors` as each increment needs them, copied from `AtlasErrorCode`.

### DD-024. The registry is updated on a transient copy under a re-entrant lock

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** `TypeRegistry.lock_for_update(timeout)` returns a `TransientTypeRegistry` built from the registry's definitions, under a re-entrant `threading.RLock`. Changes resolve every type on the copy; `release(transient, commit=...)` swaps the copy's types into the registry or drops them. A context manager wraps the pair.

**Reason.** It is Atlas's `TypeRegistryUpdateSynchronizer`: readers never see a half-resolved registry, and a failed change leaves the registry as it was (TRG-05, TRG-09). A thread lock also protects FastAPI's thread-pool handlers; async handlers hold it only around synchronous code.

**Alternatives.** An `asyncio.Lock`: does not protect code run in threads. Copy-on-write without a lock: two concurrent updates would each start from the same registry and one would be lost.

**Consequences.** The lock is per process. Several server processes keep their registries in step through the store (1.4).

### DD-025. The type system ports the definition side only

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** The ported types resolve definitions: names, attribute types, cardinalities, constraints and later the hierarchies (1.3). Their value side (`isValidValue`, `getNormalizedValue`, `validateValue`, `createDefaultValue`, `areEqualValues`) is ported with entity validation in 2.1. Their JanusGraph side (vertex property names, unique property names, index field names, index-query escaping) is not ported.

**Reason.** Types REST (1.6) needs only the definition side; values first matter for entities (2.1), which is where Atlas's tests for them can be run. The JanusGraph names have no meaning in Elasticsearch: the index mapping is designed in 2.2.

**Alternatives.** Port each class whole: one increment several times the size limit, with value code untested by any endpoint until 2.x.

**Consequences.** The type classes grow in 2.1. Atlas behaviour that depends on vertex property names is designed again for Elasticsearch in 2.2 and recorded there.

### DD-026. Dynamic attributes and search lookups wait for their increments

- **Status:** Proposed
- **Increment:** 1.3
- **Date:** 2026-10-18

**Decision.** The entity type's dynamic attributes (`dynAttribute:` templates, their parsing and evaluation order) are ported with entity writes in 2.4. The root entity type's lookup of business attributes for search is ported with basic search in 4.1. Both resolve nothing a type definition is checked against.

**Reason.** They are used only when entities are written or searched, and can only be tested there; porting them now would leave them untested by any endpoint until then (as DD-025 argues for values).

**Alternatives.** Port them with the rest of `AtlasEntityType` now: a larger increment whose extra code no rule of 1.3 can exercise.

**Consequences.** 2.4 adds the template parsing to `EntityType`; 4.1 adds the lookup to the root type.

### DD-027. Derived type sets keep first-seen order

- **Status:** Proposed
- **Increment:** 1.3
- **Date:** 2026-10-18

**Decision.** All super types are listed in the order the depth-first walk of the super types first reaches them; sub types and relationship attributes in the order the registry resolves its types, which is the order the definitions were added in.

**Reason.** Java keeps them in `HashSet`s and `HashMap`s, whose order Atlas does not define; first-seen order is stable, as for the definitions' own sets (DD-021). Where the order picks a winner, as for inherited relationship attributes, Java's winner is equally arbitrary.

**Alternatives.** Sort them by name: stable too, but unrelated to how the hierarchy was declared.

**Consequences.** `subTypes` in responses may be ordered differently from Atlas's; parity scenarios compare them without order (DD-021, from 1.6).

### DD-028. The type definitions are one Elasticsearch document

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** All stored type definitions are one document, `typedefs`, in the index `aurelius-atlas-typedefs` (through an alias, so a reindex can swap it). The document holds the definitions in their stored form (TDS-05, TDS-06), grouped by kind as in `AtlasTypesDef`. Every change replaces the whole document, guarded by `if_seq_no` and `if_primary_term`.

**Reason.** Atlas changes several definitions in one graph transaction: `createTypesDef` stores all of a request or none (TDS-10). Elasticsearch has no transaction across documents, but writes one document atomically, so one document makes every typedef change atomic and its sequence number a single version of all types (DD-029). The registry, not Elasticsearch, answers every query over types; the document is read whole at start-up and on change. Atlas's built-in models with all patches are about 1 MB of JSON, well inside Elasticsearch's limits.

**Alternatives.** One document per definition, keyed by name: queryable, and a create can use `op_type=create` for uniqueness, but a request touching several definitions needs a hand-written rollback when one write fails, and other processes see half a change. A changes log of operations, replayed at start-up: atomic per entry, but every process replays the whole history and compaction is extra work.

**Consequences.** The document's size grows with the number of types; a deployment with tens of thousands of custom types would revisit this. Type changes are serialised across the cluster, as Atlas serialises them with its update lock.

### DD-029. Server processes share the type definitions through the document's version

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** Each process remembers the `_seq_no` and `_primary_term` of the `typedefs` document its registry was built from. Before a type change it reloads when the stored document is newer; it then writes conditionally on what it read. A conflict means another process changed types first: the process reloads, applies the change again on the new definitions, and gives up with `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` after a second conflict. Readers reload when the document changed, checked at most every `AURELIUS_ATLAS_SERVER_TYPEDEF_REFRESH_SECONDS` (default 5).

**Reason.** Atlas runs one active server and keeps its registry in memory (DD-024 is per process). Several processes behind a load balancer must not lose each other's changes, and a change must reach the others without a restart. Optimistic concurrency on one document gives both with one cheap `GET` of the document's version.

**Alternatives.** A lock document: needs expiry and recovery when its holder dies. Change notification through a message bus: a component the system does not have (ADR 050).

**Consequences.** For up to the refresh interval, a process may answer from older types than another; a type change is visible at once only on the process that made it. 6.4 measures whether the interval needs tuning.

### DD-030. The store asks the entity store whether a type is in use

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** The typedef store takes a `TypeUsage` callback that answers whether entities, classifications or relationships of a type exist; deleting a type that is in use fails with `TYPE_HAS_REFERENCES`. Until the entity store exists (2.2) the callback answers "not in use".

**Reason.** Atlas checks `typeHasInstanceVertex` before deleting a type. The instances live in the entity store, which the typedef store must not depend on; a callback keeps the dependency pointing from core's entity store to the typedef store.

**Alternatives.** Query the entity index from the typedef store: couples it to an index that does not exist yet.

**Consequences.** 2.2 passes its own check when it builds the stores.

### DD-031. The patch records live in the typedef document

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** The `typedefs` document of DD-028 holds, next to `typesDef`, a list `patches` of `AtlasPatch` records: one per typedef patch id, with its description, type, action, status and times. A patch's record is written in the same document write as the type change it makes.

**Reason.** Atlas keeps patch records as graph vertices and commits them after the type change, so a crash between the two applies a patch twice, which the `typeVersion` check mostly hides. One document makes the change and its record atomic, and gives both the single version of DD-029: a process that loses a race reloads the records with the types, and sees the patch as already applied (MDL-15).

**Alternatives.** A second document, or an index of patch records: queryable by `admin/patches`, but two writes per patch, and a race between processes needs its own conditional write.

**Consequences.** `admin/patches` (2.2) reads the records from the document. The Java patches of 2.2, which change entities rather than types, may keep their records elsewhere; 2.2 decides.

### DD-032. The built-in models are vendored unchanged and read from a directory

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** `addons/models` of Apache Atlas `release-2.4.0` is copied byte for byte into the package `aurelius_atlas_core.models`, and kept out of the formatting hooks. The server loads models from `AURELIUS_ATLAS_SERVER_MODELS_DIR`, which defaults to that package directory.

**Reason.** Atlas reads its models from `$ATLAS_HOME/models`, so operators add their own model files and patches there; a directory setting keeps that. Unchanged copies let a reviewer prove them unchanged with a diff against the tag, as for the dashboards (DD-017), and ship in the wheel without a build step. The line endings are kept too: one patch file has CRLF, so the directory is `-text` in `.gitattributes`.

**Alternatives.** Converting the models to Python data: no diff against Atlas, and no way to add models without a release. Reading them from a checkout of Atlas at build time: the build would depend on a second repository.

**Consequences.** A newer Atlas version's models are a new copy and a check of the new patches against the nine actions.

### DD-033. Start-up loading is one change per model file and per patch

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** Each model file and each patch is one change of the typedef store (DD-029): what to create, update or patch is decided inside the change, on the definitions and patch records just read, and decided again when a conditional write loses to another process.

**Reason.** Atlas loads models only on its one active server. Here every process starts the same way, possibly at the same moment; deciding inside the change makes a second process see the first one's types and records, so it creates, updates and patches nothing twice. One change per file and per patch keeps Atlas's isolation: a failing file or patch leaves the others applied (MDL-04, MDL-06).

**Alternatives.** All files and patches in one change: one write, but a failure would need the transient registry to roll back part of a change. A lock document held while loading: needs expiry when its holder dies (as in DD-029).

**Consequences.** The first start against an empty store writes the document once per model file and patch, a few hundred writes of the whole document; later starts write nothing unless a model or patch is new. Two processes starting together may each retry once per change.

### DD-034. Lists of type definitions are sorted by name

- **Status:** Proposed
- **Increment:** 1.6
- **Date:** 2026-10-18

**Decision.** `GET /v2/types/typedefs` and `GET /v2/types/typedefs/headers` list the definitions of each kind sorted by name, compared as Java's `String.compareTo`.

**Reason.** Atlas lists them in the iteration order of the `ConcurrentHashMap`s of its registry: deterministic, but a function of Java's string hashes and the maps' resize history, which no client can rely on and no scenario can state without computing it. A sorted list is stable across restarts, processes and updates, which the order of the stored document is not: an update moves a definition to its end.

**Alternatives.** The order of the stored document: changes with every update. Emulating Java's hash order: costly, and still not something a client could use.

**Consequences.** DV-09. A scenario that lists several definitions of a kind states them sorted by name.

### DD-035. Type scenarios create what they read and delete it at their end

- **Status:** Proposed
- **Increment:** 1.6
- **Date:** 2026-10-18

**Decision.** Each types scenario creates the definitions it needs, all named `scenario_…`, and deletes them in its last stage. Before the server e2e runs its scenarios, it deletes any `scenario_…` definition left in the store by an earlier run that stopped half-way.

**Reason.** The in-process scenarios start each from an empty store, but the e2e runs them all against one server on the persistent dev store, which `nx serve` uses too. Self-contained scenarios pass on both, in any order, and a run never touches a developer's own types.

**Alternatives.** Deleting the typedef index before the e2e: also deletes the developer's types and makes the server load the models again. A separate index per e2e run: needs an index-name setting that nothing else needs.

**Consequences.** Scenario names must be unique across scenarios; a scenario's expectations cannot depend on types another scenario creates.

### DD-036. Start-up loading tries a raced change again

- **Status:** Proposed
- **Increment:** 1.6 (a fix to 1.5's MDL-15)
- **Date:** 2026-10-19

**Decision.** When the typedef store gives up on a model file or patch with `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` (two lost conditional writes, DD-029), the model loader makes the change again, up to ten times, before it treats the file as failed or the patch as `FAILED`. The REST endpoints keep DD-029's single retry.

**Reason.** DD-033 assumed a process starting next to another loses at most once per change. CI showed otherwise: two processes write a few hundred changes in near lockstep, and between one's reload and its retry the other may write its next file, so it loses twice and skipped a model file. Every lost race is another process's write, so trying again always makes progress, and a file or patch is never skipped for a race.

**Alternatives.** More retries in the store itself: also lengthens a REST request's wait under contention, where Atlas answers `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` at once. No limit: a store that never stops changing would hang start-up.

**Consequences.** DD-033's "may each retry once per change" becomes "until it wins, up to ten times". A process that loses ten times in a row still reports the file or patch as failed, as Atlas does on a lock failure.

### DD-037. Instance models are one module per Java class

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-20

**Decision.** The entity models live in the package `aurelius_atlas_model.instance`, one module per Java class, nested classes and enums included (`entity`, `entity_status`, `entity_with_ext_info`, …). The package re-exports every model. The JSON conventions all models share (`AtlasModel`, the timestamp, Java boolean, int and set types) move from `typedef` to `aurelius_atlas_model.base`; `typedef` imports them from there.

**Reason.** Atlas organises its models as one class per file; a reader who knows a Java class finds its port by name, and each module stays small enough to read whole. The typedef models were ported into one module (1.1); the instance models are more numerous and depend on each other in one direction only (struct, then entity, header, ext info), which modules make visible.

**Alternatives.** One `instance.py`, as `typedef.py`: about as long as all of `typedef.py` again, mixing seventeen classes. Importing the shared conventions from `typedef`: makes the instance models depend on the typedef module for reasons unrelated to type definitions.

**Consequences.** Tests follow the layout, one file per module under `tests/instance/`; the four enums, which have no behaviour of their own, share one. Splitting `typedef.py` the same way is possible later without changing its imports, through its re-exports.

### DD-038. Attribute values stay plain JSON values until their types read them

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-20

**Decision.** The models of 2.1a keep attribute values (`attributes`, `relationshipAttributes`, `uniqueAttributes`, business attributes) as the JSON values Python reads: objects, arrays, strings, integers, floats, booleans and null. Atlas's REST mapper reads floats as `BigDecimal` (`USE_BIG_DECIMAL_FOR_FLOATS`) and writes them back with their digits (`1.10`, `1E+3`); that is designed with the `bigdecimal`, `float` and `double` types in 2.1b.

**Reason.** An untyped value reaches a response only after its attribute's type normalised it (2.1b, then the stores), so the digits of a float matter only where a type keeps them. Keeping them in 2.1a would need a JSON reader and writer of its own for every model before any type needs it.

**Alternatives.** Read every float as `Decimal` now: Pydantic writes a `Decimal` as a JSON string, so every writer would need a custom encoder, designed without the type that motivates it.

**Consequences.** 2.1b decides how a `bigdecimal` value is read from a body and written back exactly, and applies it to these models.

### DD-039. One Atlas JSON codec reads floats as decimals and writes them with their digits

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-21

**Decision.** `aurelius_atlas_model.codec` holds Atlas's JSON reading and writing. `loads` reads every number with a fraction or exponent as a `Decimal`, as Jackson's `USE_BIG_DECIMAL_FOR_FLOATS` does. `dumps` writes a `Decimal` with its digits, a `datetime` as epoch milliseconds, NaN as the string `"NaN"`, and map keys as Java's text of the key. `AtlasModel.to_json` dumps in Pydantic's Python mode, so attribute values keep these types for the codec; typed timestamps are written as epoch milliseconds in both modes. The server's `AtlasJSONResponse` writes its content with `dumps`. This settles DD-038.

**Reason.** A `bigdecimal` attribute keeps the digits it was given (`1.10`), and normalised dates are Java `Date` values that Jackson writes as numbers, even inside untyped attribute maps. Python's `json` turns a `Decimal` into a float, and Pydantic's JSON mode turns it, and a `datetime`, into a string.

**Alternatives.** A custom Pydantic serializer per field: values inside `dict[str, Any]` have no field of their own. Converting decimals to floats: loses digits a client sent.

**Consequences.** A double is written with Python's shortest form (`10000000.0`), where Jackson writes `Double.toString` (`1.0E7`): the same number in another notation, equal for every JSON reader and for the parity comparison. Request bodies with entity values are read with `loads` from 2.3 on.

### DD-040. Java values are held as the Python values closest to them

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-21

**Decision.** A Java `Integer`, `Long`, `BigInteger`, `Byte` or `Short` is a Python `int`; which of them it was follows from its size, as Jackson chooses by size (`Integer` within 32 bits, `Long` within 64, `BigInteger` beyond). A `BigDecimal` is a `Decimal`, a `Double` a `float`, and a `Float` a `float` holding the shortest decimal of the 32-bit value. A `Boolean` is a `bool`, never a number. A `Date` is an aware UTC `datetime` with millisecond precision. The conversions Java applies between them (`longValue`, `intValue`, `floatValue`, `toBigInteger`, `BigDecimal.valueOf(double)`, `valueOf(String)`, `String.valueOf`) are functions of `aurelius_atlas_typesystem.java`, each named after its Java original.

**Reason.** The types branch on the Java class of a value (`instanceof Long`, `instanceof BigDecimal`), and their results depend on Java's arithmetic: truncation, saturation, 32-bit rounding. Values from a JSON body can only be integers, decimals, strings, booleans, lists and maps, so the Python types need only tell those apart; Java `Float` and `Double` arise from Atlas's own code and from Atlas's tests.

**Alternatives.** Wrapper classes for every Java number type: every value would need wrapping on reading and unwrapping on writing, for distinctions JSON cannot express.

**Consequences.** A `float` value written and read back is the same 32-bit value. An `Integer` and a `Long` of equal value cannot be told apart, and give the same result in every type. A `BigInteger` within 64 bits cannot be told apart from a `Long` either; `bigdecimal` treats them differently (`1` against `1.0`), but JSON never yields one, because Jackson reads such integers as `Integer` or `Long`.

### DD-041. The type system is one module per Java type class too

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-21

**Decision.** As DD-037 for the models: the types the value side adds or changes get one module each, `atlas_type`, `enum_type`, `array_type`, `map_type`, and `builtin/<name>_type` for each nested class of `AtlasBuiltInTypes`. `types.py` keeps the struct, classification, entity, relationship and business metadata types, which 2.1c moves the same way, and re-exports the moved classes.

**Reason.** The value side roughly doubles the type classes; one file of all of them would pass two thousand lines. A reader who knows Atlas's `AtlasArrayType` finds `array_type`.

**Alternatives.** Adding the value side to `types.py`: one module far beyond what anyone reads whole.

**Consequences.** `from aurelius_atlas_typesystem.types import ArrayType` keeps working; new code imports from the class's own module.

### DD-042. A validity period without a time zone is in UTC

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-22

**Decision.** A classification's validity period without a `timeZone` is read in UTC, where Atlas reads it in its JVM's default time zone (`TimeZone.getDefault()`). Java's time zone ids are matched with Python's tz database (`zoneinfo`), Java's legacy three-letter ids (`ZoneId.SHORT_IDS`, such as `PST` and `IST`) and its custom `GMT±h[h][[:]mm]` offsets.

**Reason.** Atlas's default zone is whatever its host is set to; the server image runs in UTC, so UTC is the same answer for a container deployment, and it does not change with where the code happens to run. The tz database holds every zone Java's `TimeZone` resolves except the legacy short ids, which Java maps to tz ids.

**Alternatives.** The local zone of the Python process: makes validation depend on the developer's machine. A setting for the default zone: nothing asks for one yet.

**Consequences.** A validity period of `2026/01/01 00:00:00` without a zone means midnight UTC. The time zone list must stay in step with Java's; the tz database of the image (the `tzdata` package) supplies it.

### DD-043. Entities are documents of one index, their attributes under qualified names

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** Every entity, of every type, is one document of the index behind the alias `aurelius-atlas-entities`, with its GUID as the document id. The document holds the system properties Atlas keeps on a vertex (GUID, type name, super type names, state, times, users, version, labels, custom attributes) as top-level fields, mapped for exact lookup, and the attribute values in an `attributes` object keyed by each attribute's qualified name (`Referenceable.qualifiedName`, `hive_table.createTime`), as the vertex properties are named. The `attributes` object is stored but not indexed (`dynamic: false`) until 4.1 designs the search mapping.

**Reason.** A GUID is how Atlas reads, writes and refers to an entity, and a get by id is Elasticsearch's only real-time read. One index serves every type, as one graph holds every vertex; per-type indices would multiply shards with the number of types. A qualified name is defined by one attribute definition, whose type may not change (TDS-08), so one field never holds two value types, which Elasticsearch could not map. Leaving attributes unindexed until search needs them keeps 2.2 from deciding analysis and field types it cannot yet test.

**Alternatives.** Attributes keyed by their plain names: the same name with different types in two entity types cannot share one mapping. An index per entity type: thousands of small indices for Atlas's models alone, and queries across a super type touch them all.

**Consequences.** The store's client reads floats as decimals and is given documents as the codec's bytes (DD-039), so values keep their digits through Elasticsearch. 4.1 adds attribute mappings and indexes the existing documents again (an `update_by_query`), the first change ADR 023 records as a migration if data exists by then. Reading an entity back maps qualified names to attribute names through the type registry (2.3).

### DD-044. A GUID is a random UUID

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** The store gives a new entity a random (version 4) UUID in canonical lower-case text, as Atlas's `UUID.randomUUID().toString()`.

**Reason.** Atlas's clients see and keep GUIDs of this form; any process can make one without coordination, and the chance of two equal ones is negligible.

**Alternatives.** Time-ordered UUIDs (version 7): better index locality, but a GUID would reveal its creation time and differ in form from Atlas's.

**Consequences.** None beyond Atlas's.

### DD-045. Unique values are reserved by create-only documents

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** For each unique attribute value an `ACTIVE` entity has, the store keeps a reservation document in `aurelius-atlas-unique-values`, whose id is a SHA-256 of the entity type name, the attribute's qualified name and the value as the codec writes it, and which names the GUID holding it. A reservation is made with `op_type=create`, so of two processes reserving the same value one fails, and is deleted when the entity changes the value or leaves `ACTIVE`. A lookup by unique attributes reads the reservations by id, in real time.

**Reason.** Atlas enforces unique attributes with a JanusGraph unique index on a shadow property (`__u_Referenceable.qualifiedName`), composite with the type name (`PER_TYPE_UNIQUE`), removed when an entity is deleted. Elasticsearch has no unique constraint except the document id, and a search would see neither a value written a moment ago nor one being written concurrently. A create-only document with a deterministic id is atomic across processes.

**Alternatives.** Search the entity index before writing: races between processes, and misses unrefreshed writes. The value itself as the document id: limited to 512 bytes, while a `qualifiedName` may be longer.

**Consequences.** Every write of an entity with unique attributes writes one more document per changed value. Reservations belong to the write that made them until it ends (DD-046), so recovery can release those of a write that never finished.

### DD-046. A multi-entity write is all or nothing, through a journal

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** A write of several entities runs in steps:

1. a journal entry in `aurelius-atlas-entity-journal` records the write's id, a lease time and the state of every entity before it (or that it is new);
2. every unique value the write needs is reserved; a value held by another entity ends the write, before any entity is written, with an error 2.4 turns into an answer;
3. all entities are written in one bulk request, each conditionally (DD-047) and marked with the write's id;
4. if any entity fails, every entity written is restored to its state before, and the write's reservations are released;
5. the journal entry is marked committed; values no longer held are released and the entry is deleted.

Recovery, at start-up, finds journal entries whose lease has passed. A committed entry only has its releases finished; any other is undone as in step 4: it restores an entity only while it still carries that write's id, and releases only reservations made by that write.

**Reason.** Atlas commits all entities of a request in one graph transaction (`GraphTransactionInterceptor`). Elasticsearch writes one document atomically but no more (ADR 047). The user chose an all-or-nothing outcome, also after a crash, over per-entity writes or full isolation (2026-10-22): the journal makes the outcome recoverable at the cost of one document per write, while isolation would make every read look up write states.

**Alternatives.** Per-entity atomicity: a failed batch leaves part of it written. Isolation through pending versions and a committed flag: no reader sees a partial write, but every read pays for it.

**Consequences.** Between steps 3 and 4 another reader may see part of a write (DV-16). A write must finish within its lease (60 seconds) or recovery may undo it; a write that finds its lease passed before step 3 gives up. Recovery runs at start-up, so a crash's leftovers stay until a process starts.

### DD-047. Entities are written conditionally on their Elasticsearch version

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** A changed entity is written with the `if_seq_no` and `if_primary_term` it was read with, and a new one with `op_type=create`. A conflict fails the write (DD-046 restores the rest) with a version conflict the caller handles by reading again. Atlas's `version` field is stored as the entity has it and plays no part.

**Reason.** Atlas serialises writes inside one JanusGraph transaction per request; several server processes writing to one Elasticsearch need optimistic concurrency, as the type definitions do (DD-029). Atlas never increments an entity's `version` itself (`getEntityVersion` takes the entity's or 0), so it cannot serve as a concurrency token without changing what clients see.

**Alternatives.** A lock document per entity: needs expiry when its holder dies. Incrementing `version`: changes Atlas's responses.

**Consequences.** 2.4 decides how a write request retries after a conflict and what it answers when it gives up.

### DD-048. A type is in use while the entity index holds one of it

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** The typedef store's usage check (DD-030) refreshes the entity index and counts the documents whose type name is the type, in any state, as Atlas's `typeHasInstanceVertex` counts vertices of the type. Classification and relationship types join the check when their instances are stored (3.1, 3.3).

**Reason.** A count is near real time; the refresh makes an entity written a moment ago count. Deleting a type is rare, so the refresh's cost does not matter.

**Alternatives.** Keeping a counter per type: one more document to update atomically with every write.

**Consequences.** Until 3.1 and 3.3, a classification or relationship type is never in use.

### DD-049. Attribute values are stored normalised; a struct inline, a reference as a GUID

- **Status:** Proposed
- **Increment:** 2.3
- **Date:** 2026-10-22

**Decision.** An entity document holds each attribute value as its attribute's type normalises it (`getNormalizedValue`), in the codec's JSON (DD-039): a date as epoch milliseconds, an enum as its value's name, numbers with their digits. A struct value is held inline as `{"typeName": …, "attributes": {…}}`, its attributes by name and normalised the same way. A reference to an entity, whether an `objectid` attribute, an element of an array or a value of a map, is held as the referenced entity's GUID; a soft reference (`isSoftReference`) is held as Atlas holds it, `typeName:guid`. Reading an entity gets the entities its attributes refer to by GUID, in one request, to build their object ids and owned entities; a GUID that finds no entity reads as nothing, as an edge to a removed vertex does.

**Reason.** Atlas keeps a struct in a vertex of its own and a reference as an edge; Elasticsearch has neither, and one document per entity is what DD-043 decided. A struct belongs to its entity alone, so it stays inside it. A reference's GUID never changes, where the referenced entity's unique attributes and type may, so the GUID is the only stable thing to store; everything else the object id shows is read from the referenced entity, as `toAtlasObjectId` reads it from the vertex.

**Alternatives.** Storing the object id with its unique attributes: stale once the referenced entity changes. Structs as documents of their own: a second read per struct, and nothing ever refers to one.

**Consequences.** 2.4 writes values in this form, resolving every object id it is given, by GUID or by unique attributes, to a GUID first. A reference read needs a second `mget` per nesting level of owned entities. 3.1 decides how relationship attributes are stored; references that are also relationship ends (legacy attributes) move there then.

### DD-050. Relationship attributes read empty until relationships are stored

- **Status:** Proposed
- **Increment:** 2.3
- **Date:** 2026-10-22

**Decision.** Until 3.1 stores relationships, an entity reads as Atlas reads one without relationship edges: `relationshipAttributes` names every relationship attribute of its type, null for a `SINGLE` end and `[]` for a `LIST` or `SET` end, the end chosen as Atlas chooses it without edges (the attribute's first relationship type). `ignoreRelationships=true` leaves `relationshipAttributes` out.

**Reason.** The keys and the empty values are what Atlas answers for an entity no relationship has reached yet; answering them now keeps the response's shape, and 3.1 only fills values in.

**Alternatives.** Leaving `relationshipAttributes` out until 3.1: a different shape for every entity, which clients that read the keys would notice.

**Consequences.** Until 3.1, a reference given as a legacy relationship attribute (DD-049) reads in `attributes` but not in `relationshipAttributes` (DV-18).

### DD-051. Entity reads are tested on entities written through the store until 2.4

- **Status:** Proposed
- **Increment:** 2.3
- **Date:** 2026-10-22

**Decision.** 2.3's HTTP tests write the entities they read through `EntityStore` (2.2), in the stored form of DD-049, and check every read rule on them. Its parity scenarios cover what needs no entity: unknown GUIDs and types, invalid and missing unique attributes, values that find nothing. 2.4 adds scenarios that create entities over REST and read them back.

**Reason.** A parity scenario only reaches the server over REST, and entities can be created over REST from 2.4 on. Seeding through the store tests the read path now without porting the write path early.

**Alternatives.** Merging 2.3 into 2.4: one pull request far above the size limit. Moving 2.4 before 2.3: a write increment whose responses could not be read back.

**Consequences.** Until 2.4, the stored form the tests write is checked against Atlas's responses only by the expectations read from the Java source; 2.4's scenarios check both directions.

### DD-052. A request is mapped in memory and written once; a lost race runs it again

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** `EntityWriter` reads every stored entity a create or update request names, discovers and resolves its references, and maps its entities to their new stored form in memory, together with the entities EWR-12 touches. The response's headers are built from that form. The result is one `EntityStore.write` (ENS-07), each changed entity conditional on the version it was read in (ENS-08). When the write loses a race, the whole request is read, mapped and written again, once; a second loss, or a unique value another entity holds, is answered with `INTERNAL_ERROR` naming the cause (DV-20).

**Reason.** Atlas maps a request onto vertices inside one graph transaction and commits at the end; mapping onto documents in memory and writing them in one all-or-nothing write is the same shape on Elasticsearch (DD-046). Running the request again on the newer state is what a client would do, as DD-029 does for types.

**Alternatives.** Writing each entity as it is mapped: a failure part-way would leave a half-written request for recovery to undo, and headers would be read from the index. Answering a lost race with an error at once: two clients updating different attributes of an entity would fail where Atlas, serialising them, succeeds.

**Consequences.** A request's memory grows with its entities, as Atlas's transaction does. A unique value clash is no `400`: Atlas resolves an entity by its unique values before writing, so a clash needs an update that moves a value onto another entity, or two new entities with the same value in one request.

### DD-053. Relationship attribute values are resolved, but stored only as legacy attributes until 3.1

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** Until 3.1 stores relationships, a relationship attribute's value in a write is discovered, resolved, checked and normalised as Atlas does, so its errors are Atlas's. It is stored only when the entity's type has an attribute of the same name (a legacy relationship end, such as `hive_table.db`), as that attribute's value (DD-049); a relationship attribute without such an attribute is not stored (DV-22).

**Reason.** A legacy end is read from `attributes` (DD-050, DV-18); storing it there keeps what clients write readable. Storing other relationship values needs relationship instances, their GUIDs and both ends, which is 3.1's.

**Alternatives.** Rejecting relationship attributes until 3.1: requests Atlas accepts, such as the hook models', would fail. Storing them as plain references on one end: 3.1 would have to migrate them.

**Consequences.** 3.1 replaces this: relationship values become relationships, and the legacy attributes' values move to them.

### DD-054. Dynamic attributes are evaluated in first-seen dependency order

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** An entity type's dynamic attributes are ordered by a depth-first topological sort over their templates, visiting them in the order their `dynAttribute:` options appear, so that an attribute another template names is evaluated first.

**Reason.** Java sorts the same graph but starts from the keys of a `HashMap`; where the dependencies leave the order open, first-seen order is stable, as DD-027 chooses for derived type sets.

**Alternatives.** Sorting by name: stable too, but unrelated to the definition.

**Consequences.** Independent dynamic attributes may be evaluated in another order than Atlas's; their values do not depend on it.

### DD-055. Scenarios name what they create with a per-run value

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** The parity harness provides `{run}`, a value unique to each run of a scenario, in letters and digits, before any stage has saved a value. Entity scenarios name their types and entities with it, and leave them in the store until 2.5 lets them delete what they created (DD-035).

**Reason.** The dev store keeps its contents between runs. A scenario that creates an entity again on a second run would find it, update it and get a different answer; a type in use cannot be deleted.

**Alternatives.** Deleting the entity index before scenarios: other tests and a developer's data share the dev store. Waiting for 2.5: 2.4's writes would have no parity check (DD-051).

**Consequences.** Each run of the entity scenarios leaves a few types and entities in the dev store until 2.5; CI starts from an empty store.

### DD-056. An entity write also removes documents, journaled like the others

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** An `EntityChange` may remove its entity instead of writing a new state. The removal is a `delete` action of the same bulk request, conditional on the version read (DD-047); the journal entry records the entity's state before and lists the removed GUIDs. A failed write restores a removed entity; recovery restores a removed entity of an unfinished write when no document has its GUID. A removed entity holds no unique value: its reservations are released as for one that left `ACTIVE`.

**Reason.** A hard delete or a purge removes entities and changes those referring to them in one request; the all-or-nothing write of DD-046 already covers the changes, and removals need the same guarantee.

**Alternatives.** Marking removed entities and deleting them in a second step: a reader would see them in between, and a crash would leave them. Removing them after the write commits: a crash in between leaves entities the response called purged.

**Consequences.** Recovery cannot tell a removal undone by it from a later write's removal of the same GUID; a GUID is removed once, so this does not arise.

### DD-057. Entities referring to one are found through an indexed field of GUIDs

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** Every entity document holds `references`, a keyword field of the GUIDs its references name (its own object id attributes and the elements and values of its arrays and maps of object ids; not soft references, not references in structs), set by `EntityStore` on every write. Deleting an entity refreshes the entity index, then searches `references` for its GUID, in pages. Preparing the store adds the field's mapping to an existing entity index; documents written before it have no `references` until they are written again.

**Reason.** Atlas follows an entity's incoming edges; documents have none. Of the alternatives offered, the indexed field keeps writes to the entities written (DD-052), and the refresh makes every write finished before the delete visible.

**Alternatives.** A reverse list on each referenced entity, kept by the same write: exact, but every write that adds or drops a reference rewrites the entities it names, and popular entities become write hot spots.

**Consequences.** A referrer written while the delete runs may be missed (DV-27). Lineage (5.1) and relationships (3.1) can use the same field.

### DD-058. A stored reference stands for an edge: active for a delete, deleted for a purge

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** A stored reference has no state of its own. A delete treats the references to the entities it deletes, and those of an `ACTIVE` owner to its owned entities, as active edges; a purge treats them as deleted edges, which a soft delete left behind.

**Reason.** Atlas soft-deletes an entity's edges with it: the edges a purge finds deleted are those of entities a delete made `DELETED`, which is what this rule reads from the entities' states.

**Alternatives.** A state per reference in the stored form (DD-049): an exact copy of the edges' states, at the cost of a second representation of every reference until 3.1 stores relationships.

**Consequences.** A reference written to an entity after it was deleted counts as deleted for a purge, where Atlas would hold an active edge and leave it.

### DD-059. The delete type and its override are server settings

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** `AURELIUS_ATLAS_SERVER_DELETE_TYPE` (`soft` by default, or `hard`) stands for `atlas.DeleteHandlerV1.impl`; `AURELIUS_ATLAS_SERVER_DELETE_TYPE_OVERRIDE` (`false` by default) for `atlas.rest.enable.delete.type.override`, which lets a request's `deleteType` choose.

**Reason.** Atlas configures both in `atlas-application.properties`; the server's settings are its equivalent.

**Alternatives.** Soft deletes only: deployments that configure Atlas for hard deletes could not move.

**Consequences.** None beyond two settings with Atlas's defaults.

### DD-060. The owned-reference cascade moves from 3.2 to 2.5

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** Deleting an entity deletes the entities its owned reference attributes name (`ownedRef`), as `DeleteHandlerV1.getOwnedVertices` does, from 2.5. Composition through `relationshipDefs` and deleting an owned entity whose reference an update drops stay with 3.2.

**Reason.** Owned references are stored as GUIDs (DD-049); following them needs no relationships, and without them a delete would leave owned entities `ACTIVE`, unlike Atlas.

**Alternatives.** All cascades in 3.2, as the roadmap first had it: deletes would differ from Atlas until then.

**Consequences.** The roadmap's 2.5 and 3.2 rows change accordingly.
