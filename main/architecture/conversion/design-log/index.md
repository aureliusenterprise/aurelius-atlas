# Design Log

Technical decisions made during the conversion that are too implementation-specific for an ADR but must not be lost: storage layout, identifiers, query translation, test tooling. Business-level decisions are ADRs in [Architecture Decisions](<https://aureliusenterprise.github.io/main/architecture/adr/index.md>).

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

### DD-001. Reference is Apache Atlas 2.4.0, and both dashboards are served

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-09

**Decision.** The behaviour to reproduce is that of the `release-2.4.0` tag of Apache Atlas. Both of its user interfaces are served unchanged at the paths Atlas uses: `dashboardv2` at `/` and `dashboardv3` at `/n/`. End-to-end tests cover `dashboardv3` in depth and `dashboardv2` with a smoke test.

**Reason.** Parity tests need one fixed reference ([ADR 048](<https://aureliusenterprise.github.io/main/architecture/adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted/index.md>)), and 2.4.0 is the latest Apache Atlas release. Atlas 2.4.0 serves the classic interface at the root and the newer one under `/n/`, and each links to the other; serving both keeps every bookmark and link working at the cost of one more static build, whereas dropping one would be a visible deviation.

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

**Reason.** Yellow means every primary shard is assigned and all data is readable and writable; only replicas are missing. A single-node cluster, the development and small-installation case ([ADR 006](<https://aureliusenterprise.github.io/main/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), is yellow as soon as an index has a replica. Reporting it down would make every single-node deployment permanently unready.

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

**Reason.** The dashboard and existing clients read fields the scenarios might not think of; an extra, missing or `null` field is a visible difference ([ADR 046](<https://aureliusenterprise.github.io/main/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). Atlas serialises its models with Jackson `NON_NULL` inclusion, so "absent" and `null` differ there and must differ here.

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

**Reason.** The store is the only system of record ([ADR 047](<https://aureliusenterprise.github.io/main/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)); a server without it cannot answer anything but the admin endpoints. Failing at start-up shows a wrong setting at once ([ADR 018](<https://aureliusenterprise.github.io/main/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)) and lets an orchestrator restart the container, while readiness covers a store that goes away later.

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

**Reason.** Pydantic is already the workspace's modelling library (settings, store) and FastAPI reads and writes it natively, so 1.4 needs no mapping layer. Atlas writes with Jackson `NON_NULL`, which is Pydantic's `exclude_none`; empty collections stay because Jackson keeps them (DD-013 compares exactly).

**Alternatives.** Dataclasses with a hand-written JSON codec: no dependency, but every rule of TDM-01 to TDM-15 would be custom code. Generating models from Atlas's JSON schema: Atlas publishes none, and the normalisations live in Java setters a schema cannot express.

**Consequences.** Response bodies must be written with `to_json` (or its `exclude_none`, `by_alias` dump), never with FastAPI's default response model serialisation. Later model packages (entities in 2.1) follow the same pattern.

### DD-021. Set-valued fields keep each name once, in first-seen order

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `superTypes`, `subTypes` and `entityTypes` are lists without duplicates, kept in the order the names were first given.

**Reason.** Java holds them in a `HashSet` and writes them in hash order, which Atlas does not define and no client can rely on. A Python `set` would make our order vary from run to run; first-seen order is stable and keeps what the client sent.

**Alternatives.** Reproduce Java's `HashSet` iteration order: possible from `String.hashCode` and the table size, but it would copy an accident of the implementation. Sorted order: stable, but reorders what clients send.

**Consequences.** The JSON order of these arrays can differ from Atlas's. Parity scenarios compare them without order, through the option DD-013 foresees, which 1.4 adds with the first scenario that needs it.

### DD-022. Typedef timestamps are aware datetimes, written as epoch milliseconds

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `createTime` and `updateTime` are timezone-aware UTC `datetime`s. They are written as integer milliseconds since the epoch and read from a number, a string of digits or an ISO-8601 date-time string.

**Reason.** Atlas's REST mapper has no date serialiser, so Jackson writes `java.util.Date` as epoch milliseconds and its `StdDateFormat` reads numbers, digit strings and ISO-8601. Pydantic would read a bare integer as seconds or milliseconds depending on its size, so the conversion is explicit.

**Alternatives.** Keep the raw integer: exact, but every caller would convert. Write ISO-8601 strings: readable, but a visible difference from Atlas.

**Consequences.** Jackson's RFC 1123 form (`Tue, 17 Oct 2026 10:00:00 GMT`) is not read. No Atlas client is known to send it; if one does, it becomes a deviation.
