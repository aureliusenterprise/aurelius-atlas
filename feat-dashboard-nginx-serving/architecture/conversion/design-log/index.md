# Design Log

Technical decisions made during the conversion that are too implementation-specific for an ADR but must not be lost: storage layout, identifiers, query translation, test tooling. Business-level decisions are ADRs in [Architecture Decisions](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/index.md>).

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
| [DD-018](<#dd-018-the-server-serves-the-dashboards-from-the-apis-origin>) | The server serves the dashboards from the API's origin | 0.6 | Superseded by DD-034 |
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
| [DD-034](<#dd-034-the-dashboard-image-serves-the-dashboards-and-proxies-the-api>) | The dashboard image serves the dashboards and proxies the API | 0.6 | Proposed |
| [DD-035](<#dd-035-an-atlas-project-is-an-nx-project>) | An Atlas project is an Nx project | 0.6 | Proposed |
| [DD-036](<#dd-036-nginx-gates-page-loads-and-the-server-owns-the-oidc-flow>) | nginx gates page loads and the server owns the OIDC flow | 6.1 | Proposed |
| [DD-037](<#dd-037-the-server-is-the-relying-party-and-keeps-its-oidc-plumbing>) | The server is the relying party and keeps its OIDC plumbing | 6.1 | Proposed |
| [DD-038](<#dd-038-the-sessions-principal-comes-from-the-access-token-not-the-id_token>) | The session's principal comes from the access token, not the id\_token | 6.1 | Proposed |
| [DD-039](<#dd-039-an-authenticated-scenario-declares-needs_auth-and-skips-off-the-guard-on-stack>) | An authenticated scenario declares `needs_auth` and skips off the guard-on stack | 6.1 | Proposed |
| [DD-040](<#dd-040-the-login-page-is-served-at-loginjsp-and-resolves-to-the-dashboard-in-use>) | The login page is served at `/login.jsp` and resolves to the dashboard in use | 6.1 | Proposed |
| [DD-041](<#dd-041-the-relying-party-binds-logins-to-the-browser-and-bounds-its-sessions>) | The relying party binds logins to the browser and bounds its sessions | 6.1 | Proposed |

### DD-001. Reference is Apache Atlas 2.4.0, and both dashboards are served

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-09

**Decision.** The behaviour to reproduce is that of the `release-2.4.0` tag of Apache Atlas. Both of its user interfaces are served unchanged at the paths Atlas uses: `dashboardv2` at `/` and `dashboardv3` at `/n/`. End-to-end tests cover `dashboardv3` in depth and `dashboardv2` with a smoke test.

**Reason.** Parity tests need one fixed reference ([ADR 048](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted/index.md>)), and 2.4.0 is the latest Apache Atlas release. Atlas 2.4.0 serves the classic interface at the root and the newer one under `/n/`, and each links to the other; serving both keeps every bookmark and link working at the cost of one more static build, whereas dropping one would be a visible deviation.

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

**Reason.** Yellow means every primary shard is assigned and all data is readable and writable; only replicas are missing. A single-node cluster, the development and small-installation case ([ADR 006](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), is yellow as soon as an index has a replica. Reporting it down would make every single-node deployment permanently unready.

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

**Reason.** The dashboard and existing clients read fields the scenarios might not think of; an extra, missing or `null` field is a visible difference ([ADR 046](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). Atlas serialises its models with Jackson `NON_NULL` inclusion, so "absent" and `null` differ there and must differ here.

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

**Reason.** The store is the only system of record ([ADR 047](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)); a server without it cannot answer anything but the admin endpoints. Failing at start-up shows a wrong setting at once ([ADR 018](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)) and lets an orchestrator restart the container, while readiness covers a store that goes away later.

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

- **Status:** Superseded by DD-034
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

### DD-034. The dashboard image serves the dashboards and proxies the API

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-18

**Decision.** `apps/aurelius-atlas-dashboard` builds an nginx image (the hardened `dhi.io/nginx`) that serves the built `dashboardv2` at `/` and `dashboardv3` at `/n/` and reverse-proxies `/api/`, with the prefix kept, to the Aurelius Atlas server on a private network. The site config is a template baked to `/etc/nginx/conf.d/default.conf`, whose `${AURELIUS_ATLAS_DASHBOARD_*}` placeholders the deployment resolves when it mounts its copy — the model of `aurelius-atlas-frontend-example`. The server serves the API only: its image no longer contains the dashboards, and `AURELIUS_ATLAS_SERVER_DASHBOARD_DIR` and `mount_dashboards` are gone. This supersedes DD-018; the origin stays the dashboards' one, only its process changes.

**Reason.** The same origin DD-018 chose is still required — the dashboards derive their API base from `window.location.pathname` and ride the session cookie (their source is vendored unchanged, ADR 046) — but serving it from nginx matches the workspace's serving pattern (the frontend example), keeps the API image small and its restarts free of static content, and lets the two halves scale, upgrade and sit behind different TLS endpoints independently. DD-018 rejected the second container because it needs a proxy to keep one origin; the proxy is now the point rather than the cost: it is the same component the frontend example ships, it answers the login root (`j_spring_security_check`) the moment 6.1 adds the route without any nginx change, and a CDN or TLS terminator in front of the UI no longer has to reach the API image.

**Alternatives.** Keep DD-018's single image: one artifact less, but the template's serving pattern goes unused and every API restart re-serves static files. Serve the dashboards from the API origin through a CDN only: no proxy of ours, but the session cookie's SameSite story and the login root become the CDN's problem. Keep both serving modes: two ways to be wrong about precedence (DSH-03); one path per rule.

**Consequences.** DSH-01 to DSH-06 now hold at the dashboard origin: the tests that proved them against `mount_dashboards` in-process prove them through nginx instead, in the dashboard project's own tests and stack, which runs both images; `nx up aurelius-atlas-dashboard` brings up the whole product on `https://localhost:8080`.

Externally visible differences are recorded as DV-09: `/n` redirects 308 where the server answered 307, the hardening headers nginx adds, and per-container TLS. The server image no longer depends on the dashboard build; the dashboard image `dependsOn` it. No CSP is served: the vendored dashboards use inline scripts and `eval`, and ADR 046 keeps their look and behaviour untouched (DV-09).

### DD-035. An Atlas project is an Nx project

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-18

**Decision.** The trace check (ADR 049) discovers the Atlas projects as the Nx projects: every workspace directory with a `project.json`, except the `exclude-projects` of its configuration (TRC-07, revised here). A project without a `pyproject.toml` ships no Python and contributes no functions to the inventory; its `tests/` and `e2e/` are still collected, so the rules its tests name count. The report reads the result files from the same directories.

**Reason.** The rule is about the product's projects, not about Python: increment 0.6 proved the old derivation wrong by counterexample, when the dashboard's e2e tests moved into a project that ships no Python. Making it a uv workspace member to satisfy the check meant a `pyproject.toml` and a package holding nothing but a docstring — machinery in service of the tool, not the product. `project.json` is the one file every project in this workspace has, and `aurelius-atlas-frontend-example` already runs Python e2e tests as a project with no `pyproject.toml`, which the old rule left unchecked.

**Alternatives.** Keep uv membership: every non-Python project that owns tests needs a fake Python package. A listing in `[tool.aurelius-atlas-trace]`: explicit, but it drifts — TRC-07's point is that a new project is checked without anyone remembering to register it. Scanning for `tests/` or `e2e/` directories alone: collects test directories that belong to no project.

**Consequences.** A project's pytest `rootdir` is no longer always its own directory: without an ini file of its own, pytest walks up and finds the workspace root's, so the trace file records the rootdir and the report joins outcomes through it rather than through the project directory. The inventory loses a guard: a Python project that forgets its `[tool.hatch.build.targets.wheel]` packages now contributes no functions instead of failing the check — its tests still name the rules, and R1's functions only go missing silently for a project that declares itself Python without declaring packages, which the code review of its `pyproject.toml` owns.

### DD-036. nginx gates page loads and the server owns the OIDC flow

- **Status:** Proposed
- **Increment:** 6.1
- **Date:** 2026-10-18

**Decision.** The dashboard origin's nginx gates unauthenticated *page loads* — `auth_request` to a server check endpoint, `error_page 401 = @login`, and `@login` answers `302 /api/atlas/auth/login ?next=$request_uri` (the redirect answers through a named location rather than error\_page's own path: a path under `/api/` would re-enter the API proxy and reach the browser as the issuer's URL, and `absolute_redirect off` keeps it relative so nginx does not absolutize it from the container's own port) — and the server owns the whole OIDC flow (authorization-code, callback, session, bearer verification, CSRF). The `/api/` proxy is unchanged, so the session cookie and the CSRF header ride it. The resolved `nginx.conf` and the shipped `nginx.conf.template` gain the locations together.

**Reason.** In Java Atlas one process guards statics and API, so the entry point redirects the browser to Keycloak before the UI loads (DV-10's reason). Here nginx serves the statics (DD-034); gating them in nginx keeps that one redirect on the browser path, where it works. Answering an unauthenticated *API* request with a redirect would instead hand Keycloak's login HTML to a JSON call that fails CORS — the dashboards' own 401 handler (`CommonViewFunction.userDataFetch`) expects a status, not a redirect (AUTH-04, DV-11). The split keeps each half on the path its protocol belongs to: nginx redirects navigations, the server answers APIs.

**Alternatives.** Guard everything in the server and let nginx proxy the statics through it: one guard, but every asset request pays a proxy hop to a second container, the API image restarts discard cached pages, and DD-034's serving split — the reason the image exists — is reversed. Keycloak-side gateway or nginx `openid_connect` module (the ngx\_auth\_openidc pattern): the proxy would hold the session, but the session must live where the API reads it, so the token store, refresh, and CSRF token would sit in nginx config rather than ported code — untraceable (ADR 049), and the Java classes' behaviour would have no Python home.

**Consequences.** The vendored dashboards are untouched (ADR 046): the old form login (`j_spring_security_check`) stays unused and answers through the server's guard like any other URI, and logout's `/logout.html` answers at the origin through the server. The UI's 401 landing URI `login.jsp` (`Utils.defaultErrorHandler` navigates there on any 401/419, so it is where a logged-out browser arrives) answers the login start with the dashboard root kept — the same way in, not the Atlas form page, which OIDC replaced (DV-10). A second nginx variant appears in `aurelius-atlas-frontend-example`'s style when the frontend example retires. The auth subrequest endpoint must answer fast and never redirect (it answers 200 or 401 only); the dev stack's `nx up` / e2e compose must start `dev/keycloak` first.

### DD-037. The server is the relying party and keeps its OIDC plumbing

- **Status:** Proposed
- **Increment:** 6.1
- **Date:** 2026-10-18

**Decision.** The OIDC relying-party code (discovery, JWKS, token verification, session store, refresh) lives inside `aurelius_atlas_server` as an `auth` module, with settings under the server's own prefix. No new shared library is extracted, and the FastAPI example keeps its own `providers/auth.py` untouched until it retires (DD-019).

**Reason.** The two verifiers answer different contracts: the example checks a bearer on its own routes; the server must additionally mint a session, refresh tokens, extract groups for the session endpoint, and port the CSRF filter. A shared library would be shaped by the union of two consumers where one is leaving (DD-019), which is the premature abstraction ADR 007's R5 does not ask for — the *interface* that stays stable is OIDC itself, not our helper code.

**Alternatives.** Extract `libs/python/aurelius-atlas-auth` now: one place to fix, but the example would have to migrate too (its own increment's churn) and the lib's shape would change again when the example leaves. Reuse the example as an import: server code reaching into an example project violates the spine/optional-slice boundary in the root `AGENTS.md`.

**Consequences.** When the template examples retire (after the plan), the example's verifier dies with it and the server's `auth` module is the survivor; if a third verifier ever appears, extracting the library becomes an increment then. The Keycloak client registration, secrets, and dev users stay declarative in `dev/keycloak/import/master.json` (the slice's rule — no init sidecar, re-import needs a stack recreate).

### DD-038. The session's principal comes from the access token, not the id\_token

- **Status:** Proposed
- **Increment:** 6.1
- **Date:** 2026-10-18

**Decision.** `OidcClient.exchange` verifies the `id_token` (its `nonce` must belong to the login, so a replayed code is refused) but builds the session's `userName` and `groups` from the verified **access token**, not the `id_token`. The `id_token` proves the login happened; the access token says who it was for.

**Reason.** Keycloak keeps realm and client roles out of the `id_token` — a live realm returns `realm_access` on the access token (`aud` the resource server) and nothing on the `id_token` (`aud` the client). A session built from the `id_token` therefore reports no groups, and the ADM-06 session shows `groups: []` for a user who holds `ADMIN`. This mirrors `AtlasKeycloakAuthenticationProvider`, which authenticates on the access token; it also matches the bearer path, which already verifies the access token, and `refresh`, whose response carries no `id_token` at all — one source for both paths.

**Alternatives.** Read the groups from the `id_token`: needs a Keycloak protocol mapper to move the realm role into it, which configures the identity provider to fit our code rather than porting Atlas. Do a separate userinfo call: another round trip for data the access token already signed.

**Consequences.** `exchange` verifies two tokens (nonce check on the `id_token`, audience/exp on the access token); the exchange's unit fixture signs both. `principal_of` is unchanged and reads whichever claims it is handed.

### DD-039. An authenticated scenario declares `needs_auth` and skips off the guard-on stack

- **Status:** Proposed
- **Increment:** 6.1
- **Date:** 2026-10-18

**Decision.** A scenario may set `needs_auth: true`. `load_scenarios(..., authenticated_run=True)` takes it as it is; the default (a plain unit run) gives the scenario a `skip` mark. The server keeps one `admin/session.scenario.yaml`, run by the e2e harness with `authenticated_run=True` and skipped by the guard-off unit harness.

**Reason.** The unit harness runs the installation with no issuer configured — AUTH-01's guard-off installation, which reports no user (the DV-04 behaviour the session scenario no longer expects) and cannot verify a bearer. The authenticated expectations (ADM-06 `groups: [ADMIN]`, ADM-07 the idle timeout) are only answerable on the e2e stack, where the guard is on and a `{bearer}` can be minted. The trace check reads a scenario's `covers`/`rules` at collection time (SCN-14), so a scenario that skips at runtime still names its functions and rules; skipping it in the harness that cannot serve it costs nothing in coverage and stops the unit run from failing on an expectation it was never meant to meet.

**Alternatives.** A second scenario file for the unauthenticated case: two files that must be kept in step, and the guard-off answer is DV-04's already, which the unit endpoint tests cover directly. A `pytest.mark.skipif` in each project's test module: duplicates the reason in every project rather than once in the loader. Environment sniffing inside the loader: hidden, and a unit run must say it is not authenticated.

**Consequences.** SCN-16 is the rule; the flag is part of the scenario format (SCN-01's optional keys). `needs_auth` skips are visible in the test report as skips, not silent. The bearer seed itself stays the caller's (the e2e conftest mints it); the loader knows only *whether* a scenario needs auth, not which token.

### DD-040. The login page is served at `/login.jsp` and resolves to the dashboard in use

- **Status:** Proposed
- **Increment:** 6.1
- **Date:** 2026-10-19

**Decision.** `/login.jsp` is a gated page: an anonymous visit is redirected to the login start with `/login.jsp` kept, and a visit on a session is served `webapp/login.html` — the dashboard project's own login page. Its inline script repeats the vendored form's resolver (`atlasLogin.js`, `redirect()`): ask the session, take `atlas.ui.default.version` as the default dashboard, let the browser's `last_ui_load` win over it, carry the URL fragment, and `location.replace` to the result. Logout sends the browser to the issuer's end-session endpoint with `/login.jsp` as the post-logout redirect — Atlas's `logoutSuccessUrl`.

**Reason.** The vendored dashboards record the UI the user is on in `localStorage.last_ui_load` (v2's header and 401 handler write `"v1"`, v3's write `"v2"`) and both navigate to the same `/logout.html`, so the server cannot tell the source UI from the request. In Atlas 2.4.0 that value is read by the login page's script: logout lands on `/login.jsp` (`AtlasSecurityConfig.configure`, `logoutSuccessUrl("/login.jsp")`), and under Keycloak the URI stays off the ignore list (`if (!keycloakEnabled) matchers.add("/login.jsp")`) so the adapter runs the dance through the same page. Signing out of dashboardv3 and back in therefore returns to v3. Landing on the origin root instead — what DD-036's logout did — answers every return with dashboardv2, which the vendored UI treats as losing the user's last choice.

**Alternatives.** A `next` on the logout link built from `last_ui_load` in the page: needs a JS edit to both dashboards (ADR 046 forbids). A query marker on `/logout.html` from the header's navigate: same forbidden edit. Serving nothing at `/login.jsp` and redirecting the login start to the root: Atlas never answers the URI that way, and the UI loss is the bug being fixed.

**Consequences.** DSH-09 is the rule; AUTH-10's landing is `/login.jsp`, not the origin. The login page is a serving-project file (`apps/aurelius-atlas-dashboard/webapp/`), copied into the image next to `dist/` so `nx build` stays a pure build of the vendored source; the dashboards' JS stays untouched (ADR 046). The page resolves in the browser, so no server-side state is added; a browser without storage or a failing session call falls back to dashboardv2 as the vendored resolver's error branch does.

### DD-041. The relying party binds logins to the browser and bounds its sessions

- **Status:** Proposed
- **Increment:** 6.1
- **Date:** 2026-10-18

**Decision.** Five tightenings of the relying party, each a rule of the 6.1 spec:

1. A login flow belongs to the browser that started it. `login_start` sets `ATLASFLOWID` — a random id kept with the pending state — as an `HttpOnly`, `Secure`, `SameSite=Lax` cookie scoped to the auth paths; `login_callback` consumes the state only when the request carries the cookie of that flow, and clears it. A callback from another browser is answered 401 and mints no session.
2. A bearer credential must be an access token: `verify_access_token` requires the JWT payload's Keycloak type field (`typ: Bearer`, which Keycloak keeps in the payload — the header says `JWT`), so an `id_token` for this client is refused (AUTH-03).
3. `safe_next` refuses every shape a browser resolves off-origin despite looking like a path: scheme-relative (`//host`), the backslash forms (`/\host`, `\host`) and control characters, beside the scheme+host forms it already refused (AUTH-06).
4. A session without a refresh token authenticates only until its access token expires, then is destroyed; it cannot renew, and no idle timeout keeps it (AUTH-09).
5. The refresh window is capped to half the token's issued lifetime (`expires_in`), and a refresh verifies the new access token and re-derives the session's user and groups from its claims (AUTH-09). The session store sweeps expired and over-lifetime entries on every store activity, and no session outlives `MAX_LIFETIME_SECONDS` (8 h) even while its cookie keeps being presented (AUTH-08).

**Reason.** The review found the OIDC dance and the session store too trusting. State was consumed globally: an attacker who logged in and handed the unconsumed callback URL to a victim gave the victim the attacker's session (login CSRF) — PKCE and the nonce pass, since both live in that state entry; only a browser-held secret separates the two browsers. An `id_token` is proof of a login, not an API credential; Atlas's adapter reads roles from the access token, and accepting any signed JWT lets a long-lived ID token act as a bearer. A `Location` of `///evil.example` or `/\evil.example` leaves the origin in a browser, so a kept `next` was still an open redirect after login. A session whose issuer gave no refresh token kept authenticating after its tokens expired — with the default timeout-less configuration, forever. The dev realm issues 60 s access tokens, exactly the fixed 60 s refresh skew, so every session-authenticated request refreshed; and the session's identity was frozen at login, so a role change at the issuer never reached `/admin/session` while the adapter of Atlas 2.4.0 re-reads roles from the live token. Sessions were reclaimed only when their exact cookie was presented; an abandoned session (closed browser, replaced cookie) held memory for the process's lifetime.

**Alternatives.** Stateless login (signed state carrying the binding): the server-side entry stays for the PKCE verifier, so it saves nothing here. Checking the JWS `typ` header: Keycloak signs with `typ: JWT` there and puts `Bearer` in the payload — verified against the running dev issuer. Refreshing only at exact expiry: requests racing the expiry would use dead tokens. A background reaper task: a task to start, stop and test; store activity is the only moment the size matters. A TTL cache library: the store's rules are three (idle, absolute, per-session token expiry), not one.

**Consequences.** AUTH-03, AUTH-06, AUTH-07, AUTH-08 and AUTH-09 state the tightened rules; each has a named test (`test__a_callback_from_another_browser_mints_no_session`, `test__an_id_token_is_no_bearer_credential`, the `safe_next` table, the refresh and sweep tests). The flow cookie is a second cookie beside the session (documented with the flow in `docs/architecture/platform/security/identity-management.md`); it names no user and lives ten minutes. Dev sessions on 60 s tokens now refresh at the 30 s mark, not per request. A deployment issuing sub-minute tokens refreshes proportionally instead of storming the token endpoint. The role-change path costs one `principal_of` per refresh, not per request. 8 h matches a dev working day; it is a constructor parameter for deployments that want another bound.
