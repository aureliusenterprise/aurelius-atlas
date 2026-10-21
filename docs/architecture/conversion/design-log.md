# Design Log

Technical decisions made during the conversion that are too implementation-specific for an ADR
but must not be lost: storage layout, identifiers, query translation, test tooling. Business-level
decisions are ADRs in [Architecture Decisions](../adr/index.md).

## Rules

- Entries are numbered `DD-NNN`, consecutively; numbers are never reused.
- Statuses: **Proposed** → **Accepted**, then optionally **Superseded by DD-NNN**.
- An accepted entry is never edited except its status line. A changed decision is a new entry
  that supersedes the old one.
- Every entry names the increment that introduced it, so the reasoning can be found next to the
  code and the specification it belongs to.
- An increment that makes a decision adds its entry in the same pull request.

## Entry template

```markdown
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

| #                                                                                           | Decision                                                                   | Increment | Status   |
| ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | --------- | -------- |
| [DD-001](#dd-001-reference-is-apache-atlas-240-and-both-dashboards-are-served)              | The reference is Apache Atlas 2.4.0; both dashboards are served unchanged  | 0.1       | Accepted |
| [DD-002](#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer)                | Atlas code lives in `aurelius-atlas-*` projects split by layer             | 0.1       | Accepted |
| [DD-003](#dd-003-template-projects-are-renamed-to-the-aurelius-atlas-prefix)                | All template projects carry the `aurelius-atlas-` prefix                   | 0.1       | Accepted |
| [DD-004](#dd-004-the-spa-keeps-tokens-in-memory-and-renews-them-silently)                   | The SPA keeps tokens in memory and renews them silently                    | 0.1       | Accepted |
| [DD-005](#dd-005-the-store-uses-the-official-async-elasticsearch-client)                    | The store uses the official async Elasticsearch client, one per store      | 0.2       | Proposed |
| [DD-006](#dd-006-development-and-tests-run-elasticsearch-with-security-on)                  | Development and tests run Elasticsearch with TLS and authentication on     | 0.2       | Proposed |
| [DD-007](#dd-007-the-elasticsearch-test-fixture-ships-with-the-store-library)               | The Elasticsearch test fixture ships with the store library                | 0.2       | Proposed |
| [DD-008](#dd-008-a-yellow-cluster-is-healthy)                                               | A yellow cluster is healthy                                                | 0.2       | Proposed |
| [DD-009](#dd-009-traceability-is-checked-from-collected-markers-not-from-a-test-run)        | Traceability is checked from collected markers, not from a test run        | 0.3       | Proposed |
| [DD-010](#dd-010-the-traceability-check-covers-atlas-code-from-increment-02-on)             | The traceability check covers Atlas code from increment 0.2 on             | 0.3       | Proposed |
| [DD-011](#dd-011-the-test-report-is-generated-from-junit-coverage-and-trace-files)          | The test report is generated from JUnit, coverage and trace files          | 0.3       | Proposed |
| [DD-012](#dd-012-parity-scenarios-are-yaml-files-run-as-parametrised-pytest-tests)          | Parity scenarios are YAML files run as parametrised pytest tests           | 0.4       | Proposed |
| [DD-013](#dd-013-a-scenario-response-is-compared-exactly-except-at-declared-paths)          | A scenario response is compared exactly, except at declared paths          | 0.4       | Proposed |
| [DD-014](#dd-014-scenario-facts-reach-the-report-as-test-properties)                        | Scenario facts reach the report as test properties                         | 0.4       | Proposed |
| [DD-015](#dd-015-the-server-is-a-fastapi-application-with-one-router-per-atlas-resource)    | The server is a FastAPI application with one router per Atlas resource     | 0.5       | Proposed |
| [DD-016](#dd-016-the-server-does-not-start-without-its-store)                               | The server does not start without its store                                | 0.5       | Proposed |
| [DD-017](#dd-017-the-dashboards-are-vendored-unchanged-and-built-with-dart-sass-on-node-24) | The dashboards are vendored unchanged and built with dart-sass on Node 24  | 0.6       | Proposed |
| [DD-018](#dd-018-the-server-serves-the-dashboards-from-the-apis-origin)                     | The server serves the dashboards from the API's origin                     | 0.6       | Proposed |
| [DD-019](#dd-019-the-template-examples-stay-until-the-plan-is-done)                         | The template examples stay until the plan is done                          | 0.6       | Proposed |
| [DD-020](#dd-020-typedef-models-are-pydantic-models-that-read-and-write-atlass-json)        | Typedef models are Pydantic models that read and write Atlas's JSON        | 1.1       | Proposed |
| [DD-021](#dd-021-set-valued-fields-keep-each-name-once-in-first-seen-order)                 | Set-valued fields keep each name once, in first-seen order                 | 1.1       | Proposed |
| [DD-022](#dd-022-typedef-timestamps-are-aware-datetimes-written-as-epoch-milliseconds)      | Typedef timestamps are aware datetimes, written as epoch milliseconds      | 1.1       | Proposed |
| [DD-023](#dd-023-atlas-errors-live-in-the-model-library)                                    | Atlas errors live in the model library                                     | 1.2       | Proposed |
| [DD-024](#dd-024-the-registry-is-updated-on-a-transient-copy-under-a-re-entrant-lock)       | The registry is updated on a transient copy under a re-entrant lock        | 1.2       | Proposed |
| [DD-025](#dd-025-the-type-system-ports-the-definition-side-only)                            | The type system ports the definition side only                             | 1.2       | Proposed |
| [DD-026](#dd-026-dynamic-attributes-and-search-lookups-wait-for-their-increments)           | Dynamic attributes and search lookups wait for their increments            | 1.3       | Proposed |
| [DD-027](#dd-027-derived-type-sets-keep-first-seen-order)                                   | Derived type sets keep first-seen order                                    | 1.3       | Proposed |
| [DD-028](#dd-028-the-type-definitions-are-one-elasticsearch-document)                       | The type definitions are one Elasticsearch document                        | 1.4       | Proposed |
| [DD-029](#dd-029-server-processes-share-the-type-definitions-through-the-documents-version) | Server processes share the type definitions through the document's version | 1.4       | Proposed |
| [DD-030](#dd-030-the-store-asks-the-entity-store-whether-a-type-is-in-use)                  | The store asks the entity store whether a type is in use                   | 1.4       | Proposed |
| [DD-031](#dd-031-the-patch-records-live-in-the-typedef-document)                            | The patch records live in the typedef document                             | 1.5       | Proposed |
| [DD-032](#dd-032-the-built-in-models-are-vendored-unchanged-and-read-from-a-directory)      | The built-in models are vendored unchanged and read from a directory       | 1.5       | Proposed |
| [DD-033](#dd-033-start-up-loading-is-one-change-per-model-file-and-per-patch)               | Start-up loading is one change per model file and per patch                | 1.5       | Proposed |
| [DD-034](#dd-034-lists-of-type-definitions-are-sorted-by-name)                              | Lists of type definitions are sorted by name                               | 1.6       | Proposed |
| [DD-035](#dd-035-type-scenarios-create-what-they-read-and-delete-it-at-their-end)           | Type scenarios create what they read and delete it at their end            | 1.6       | Proposed |
| [DD-036](#dd-036-start-up-loading-tries-a-raced-change-again)                               | Start-up loading tries a raced change again                                | 1.6       | Proposed |

### DD-001. Reference is Apache Atlas 2.4.0, and both dashboards are served

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-09

**Decision.** The behaviour to reproduce is that of the `release-2.4.0` tag of Apache Atlas. Both of
its user interfaces are served unchanged at the paths Atlas uses: `dashboardv2` at `/` and
`dashboardv3` at `/n/`. End-to-end tests cover `dashboardv3` in depth and `dashboardv2` with a smoke
test.

**Reason.** Parity tests need one fixed reference ([ADR 048](../adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted.md)),
and 2.4.0 is the latest Apache Atlas release. Atlas 2.4.0 serves the classic interface at the root and
the newer one under `/n/`, and each links to the other; serving both keeps every bookmark and link
working at the cost of one more static build, whereas dropping one would be a visible deviation.

**Alternatives.** Track Atlas `master`: unstable fixtures, no released artefact to compare against.
Serve only `dashboardv3` and redirect `/` to `/n/`: one build less, but breaks the switch-back link and
existing bookmarks, and would need a deviation entry.

**Consequences.** A move to a later Atlas release is a new entry plus a re-recording of all fixtures.
Features used only by `dashboardv2` still need backend support; they are found by its smoke test.

### DD-002. Atlas code lives in aurelius-atlas projects split by layer

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-09

**Decision.** Atlas code is split into workspace projects by layer, all prefixed `aurelius-atlas-`
(Python packages `aurelius_atlas_*`): `-model` (data shapes, no I/O), `-typesystem` (type registry and
validation), `-store-es` (Elasticsearch access), `-core` (stores and services), `-dsl` (query language),
`apps/aurelius-atlas-server` (REST), `apps/aurelius-atlas-dashboard` (UI),
`reports/aurelius-atlas-test-report`, plus `dev/elasticsearch` and `dev/atlas-reference`.

**Reason.** Layers that do not do I/O can be unit-tested without infrastructure; the dependency
direction (model ← typesystem ← core → store-es; server → core) keeps each increment's change local,
and each project follows an existing template recipe. The `aurelius` prefix keeps the organisation's
naming convention.

**Alternatives.** One large package mirroring the Java module tree: simpler imports, but every change
touches the same project and nothing can be tested in isolation. A package per Java module (`intg`,
`repository`, `webapp`): mirrors history rather than the dependency structure we want.

**Consequences.** Projects are created by the increment that first needs them, not up front.

### DD-003. Template projects are renamed to the aurelius-atlas prefix

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-17

**Decision.** All workspace projects inherited from the template carry the `aurelius-atlas-` prefix
(directories, Nx names, uv/npm package names, Python import packages, env-var prefixes, Sonar keys,
compose project and network names, Grafana dashboards). The org handle `aureliusenterprise`, the npm
scope `@aurelius`, the Keycloak client/realm ids (`aurelius`, `master`), and the DB name (`aurelius`)
are identities of the organisation/Keycloak and stay unchanged.

**Reason.** DD-002 fixes the `aurelius-atlas-` prefix for the Atlas projects; renaming the template
examples now, while they are the only content, avoids two naming generations in one repo and the
churn of renaming them piecemeal once Atlas code lands beside them.

**Alternatives.** Rename only new Atlas projects: leaves `aurelius-*` and `aurelius-atlas-*` side by
side, which reads as two projects with different ownership. Keep the template names entirely: makes
the eventual atlas-vs-template distinction implicit rather than visible in the project graph.

**Consequences.** Docker image names change (`ghcr.io/aureliusenterprise/aurelius-atlas-*`); Sonar
projects, Chromatic, and any external CI references must be created/renamed to match. `.env.enc`
files were re-encrypted with the new prefixed keys. Old locally built images are stale and should be
pruned (`docker image prune` / rebuild via `nx e2e`).

### DD-004. The SPA keeps tokens in memory and renews them silently

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-17

**Decision.** The Angular SPA uses Keycloak's default in-memory token store (`tokenStore: "default"`
in `provideKeycloak`, `apps/aurelius-atlas-frontend-example/src/app/app.config.ts`) with
`onLoad: "check-sso"` and a silent-SSO redirect (`/silent-check-sso.html`). Access and refresh tokens
never touch `localStorage` or any other persistent browser storage.

**Reason.** `localStorage` is readable by any script that achieves XSS on the origin, and is also
exposed to browser extensions with host permissions; a stolen refresh token there is a durable
session hijack. With the in-memory store, injected script can read the current access token but the
attacker's code dies with the page, and a reload forces a fresh authentication check against
Keycloak rather than replaying stored secrets.

**Alternatives.** `tokenStore: "sessionStorage"`: survives reload in the tab, but every XSS or
extension read is still one `getItem` away — same theft surface, no meaningful gain.
`tokenStore: "localStorage"`: survives tab close; strongest theft value, rejected. A confidential
client with a BFF holding tokens server-side: the right answer at scale, deferred as its own
increment — it changes the auth topology (new service, cookie session) rather than a setting.

**Consequences.** A page reload re-mints tokens via silent SSO; the user sees no login unless the
Keycloak SSO session itself has ended. Silent SSO relies on a third-party-cookie-acceptable (or
same-site) Keycloak deployment: where browsers block the framing cookie, `check-sso` degrades to a
not-signed-in state and the app falls back to a full redirect login (`login()`), which still works.
If per-tab token durability becomes a product requirement, supersede this entry by adding the BFF —
not by moving the tokens to storage.

### DD-005. The store uses the official async Elasticsearch client

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-store-es` talks to Elasticsearch through `AsyncElasticsearch` from the
official `elasticsearch` Python client, version 9.5 or later within major 9, matching the 9.5 server
(`dhi.io/elasticsearch:9.5-debian13`; minor upgrades are deliberate, patch releases follow the tag). A
store instance owns exactly one client, opened and closed with the store (`async with`).

**Reason.** The server is FastAPI and asynchronous; a blocking client would tie up the event loop or
need a thread pool. The official client tracks the server's API and versioning, ships typed
request helpers, and includes the query DSL module that search (4.x) will need.

**Alternatives.** `httpx` against the REST API directly: no extra dependency, but every API, retry
and error type would be rebuilt by hand. `opensearch-py`: a different server; ADR 047 names
Elasticsearch. One client per request: simple, but loses connection pooling.

**Consequences.** The client's major version moves with the server's (STO-04 guards it). Connection
pooling and retries are the client's; tuning them is part of 6.4.

### DD-006. Development and tests run Elasticsearch with security on

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** `dev/elasticsearch` and the test fixture run with `xpack.security` enabled: TLS on the
HTTP layer with a certificate from the workspace CA (dev) or an ephemeral CA (tests), and basic
authentication for the built-in `elastic` user. The store library has no option to skip certificate
verification.

**Reason.** It is the posture production needs, and the one `dev/postgres` already has; a store that
only ever ran without security would meet TLS and authentication for the first time in production.

**Alternatives.** Security disabled in development: faster start-up and simpler `curl`, but a
different code path (plain HTTP, no credentials) from production, and a verification switch in the
library that someone eventually leaves off.

**Consequences.** Dev tools need the CA file and the password
(`curl --cacert dev/elasticsearch/certs/ca.pem -u elastic:…`). A dedicated application user with
least privilege replaces `elastic` when authorization arrives (6.2).

### DD-007. The Elasticsearch test fixture ships with the store library

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** The testcontainers helper that starts a TLS-enabled Elasticsearch lives in
`aurelius_atlas_store_es.testing`, behind the library's `testing` extra, next to the code it serves.

**Reason.** Every later project with a store (`-core`, the server, the parity harness) needs the same
container; the library that defines the settings is the one that knows how to build them for a test
server, and keeping both together means a settings change cannot break the fixture unnoticed.

**Alternatives.** `aurelius-atlas-sdk.testing`, where the Postgres helper lives: would make the
generic SDK depend on Elasticsearch. A copy per project: drifts.

**Consequences.** Test-only dependencies (`testcontainers`, `trustme`) stay out of the runtime install;
consuming projects add `aurelius-atlas-store-es[testing]` to their dev dependencies.

### DD-008. A yellow cluster is healthy

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** The store's health check reports up for cluster status green or yellow and down for red
(STO-05).

**Reason.** Yellow means every primary shard is assigned and all data is readable and writable; only
replicas are missing. A single-node cluster, the development and small-installation case
([ADR 006](../adr/006-the-whole-system-runs-on-one-machine.md)), is yellow as soon as an index has a
replica. Reporting it down would make every single-node deployment permanently unready.

**Alternatives.** Green only: correct for multi-node clusters, unusable for single-node ones unless
every index is created with zero replicas. A configurable threshold: one more setting nobody sets.

**Consequences.** Lost redundancy is not visible as a health failure; it is visible in the cluster
metrics (ESD-06) and should be alerted on there.

### DD-009. Traceability is checked from collected markers, not from a test run

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-trace check` runs `pytest --collect-only` over the unit and end-to-end
tests of every Atlas project and reads the `covers` markers from the collected items. Whether the
naming tests pass is the test job's concern, not the check's.

**Reason.** CI runs `nx affected -t test e2e`, so the results of one run contain only the affected
projects' tests; a check over them would report every unaffected function as uncovered (TRC-10).
Collection imports the tests but starts no containers, so it is cheap enough to run on every change.

**Alternatives.** Merge the trace files of the run with those of the last run on `main`: needs
artifact plumbing between workflows and still goes stale when a run on `main` fails. Run every test
on every change: correct, but turns a one-minute check into the full end-to-end suite. Parse the test
sources with `ast`: misses markers applied through `pytestmark`, classes and parametrisation.

**Consequences.** A test module that fails to import fails the check, which is the right answer: its
markers are unknown. A test that names a function but is skipped still counts as naming it; the
report shows it as skipped.

### DD-010. The traceability check covers Atlas code from increment 0.2 on

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** R1 applies to the public functions, methods and properties of every uv workspace
member that the configuration does not exclude; the template projects (examples, SDK, reports) are
excluded, and so are `testing` subpackages, which are test infrastructure. R2 applies to the rules of
every specification from increment 0.2 on. The configuration is the `[tool.aurelius-atlas-trace]`
table of the root `pyproject.toml`.

**Reason.** Template code is removed or replaced by the conversion (0.5 removes the examples), so
markers on it would be written to be deleted. Excluding instead of listing makes a new Atlas project
checked by default. Increment 0.1's rules (ADO-01 to ADO-03) describe the adoption of the template and
were verified when it merged; 0.2 is the first increment with code, and its manual checks of ESD-01 to
ESD-06 are replaced by tests in this increment.

**Alternatives.** Check every workspace member: retrofits markers onto code about to be deleted.
List the Atlas projects explicitly: a new project is silently unchecked until someone adds it.

**Consequences.** A project that leaves the template set (the SDK, if it is kept) is removed from the
exclusion list and gets its markers in the same change.

### DD-011. The test report is generated from JUnit, coverage and trace files

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-trace report` turns JUnit XML (`pytest --junitxml`), Cobertura XML
(`pytest-cov`) and the plugin's trace JSON into one static HTML page and a Markdown summary. CI uploads
the page as the `test-report` artifact and appends the summary to the run page.

**Reason.** ADR 045's ladder: the input formats are the ecosystem's own, and no framework or community
tool joins test results to specification rules and to a function inventory, which is the view ADR 049
R3 asks for. The generator is a few hundred lines with the standard library only.

**Alternatives.** Allure Report: a polished viewer, but it needs its Java CLI, and the per-rule and
per-function gap view would still be ours to build as labels and post-processing. `pytest-html`: one
page of test results, nothing about rules or functions. SonarCloud: shows coverage, not traceability.

**Consequences.** The page is an artifact of the CI run, not a published site; 0.4 adds the parity
results to it. If a later need (history, trends) outgrows a static page, a viewer is chosen then.

### DD-012. Parity scenarios are YAML files run as parametrised pytest tests

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** A scenario is a `*.scenario.yaml` file in the stage shape of Tavern (`request`,
`response`, `save`), validated with pydantic. A project's test module turns a directory of them into
one parametrised test, `load_scenarios(directory)`, whose body is `await run_scenario(scenario, client)`;
the project's fixture decides whether `client` talks to the application in-process (`httpx.ASGITransport`)
or over HTTP to a running server.

**Reason.** ADR 045's ladder: the request/response/save stage is the community's shape for declarative
API tests, so reviewers who know Tavern read our scenarios at once. Running scenarios as ordinary pytest
parameters puts them in JUnit, in the trace file and under `covers` (SCN-04) with public pytest API only.

**Alternatives.** Tavern itself: speaks HTTP through `requests` only, so the in-process unit level is
lost, and the exact comparison, volatile paths and deviations (DD-013) would be hooks around it. A
custom collector for `*.scenario.yaml`: shorter test modules, but it needs pytest's private fixture
API to give the items a client. Schemathesis: generates requests from an OpenAPI document, which
Atlas 2.4.0 does not ship and which states types, not Atlas's answers.

**Consequences.** Every project with scenarios has one small test module and a `client` fixture. The
scenario format is ours to keep stable; it is versioned by its rules SCN-01 to SCN-03.

### DD-013. A scenario response is compared exactly, except at declared paths

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** The expected body must equal the actual body: the same keys, arrays in the same order,
booleans and null distinct from numbers. Only `volatile` paths (generated GUIDs, timestamps) skip the
value, and only `deviations` entries change the expectation, each naming its `DV-NN`.

**Reason.** The dashboard and existing clients read fields the scenarios might not think of; an extra,
missing or `null` field is a visible difference ([ADR 046](../adr/046-the-catalogue-keeps-its-public-contract.md)).
Atlas serialises its models with Jackson `NON_NULL` inclusion, so "absent" and `null` differ there and
must differ here.

**Alternatives.** Subset matching: short scenarios, but an extra or misnamed field passes. Snapshot
files written from our own responses: exact, but the expectation would come from the implementation,
not from Atlas (ADR 052 R1).

**Consequences.** Expectations for large responses are long; scenarios borrow Atlas's own test fixtures
for request bodies to keep writing them cheap. Arrays whose order Atlas does not define get an explicit
order-insensitive option when the first increment needs one.

### DD-014. Scenario facts reach the report as test properties

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** The parity plugin adds each scenario's endpoints and deviation ids to the test item's
`user_properties` at collection. The trace plugin writes every test's properties to the trace file, so
`check` (unknown deviations) and `report` (one row per endpoint) read them from the collection they
already do.

**Reason.** `user_properties` is pytest's own channel for facts about a test, and JUnit carries it too.
Reading it at collection keeps the report's rule of DD-009: an endpoint whose scenarios did not run in
this change is _not run_, not missing.

**Alternatives.** A separate `--parity-json` file: a second format next to the trace file for the same
tests. Make the trace library know scenarios: couples the traceability tool to one kind of test.

**Consequences.** The trace file format gains a `properties` field per test; readers of version 1 files
without it see no properties. Property names are prefixed with the plugin that sets them (`parity.`).

### DD-015. The server is a FastAPI application with one router per Atlas resource

- **Status:** Proposed
- **Increment:** 0.5
- **Date:** 2026-10-17

**Decision.** `apps/aurelius-atlas-server` is a FastAPI application built like the template's example
service (settings, uvicorn entry point, logfire, hardened image), with one router module per Atlas
REST resource class (`AdminResource` → `routes/admin.py`, later `EntityREST` → `routes/entity.py`).
Atlas errors are raised as `AtlasError` and turned into the Atlas error body by one exception handler,
as `AtlasBaseExceptionMapper` does; JSON goes out as `application/json; charset=UTF-8`.

**Reason.** ADR 045's ladder: FastAPI and the example's wiring are the workspace's convention, already
gated, observed and packaged. Mirroring the Java resource classes keeps the Java map one row per class
and lets a reviewer put a router next to its Java resource.

**Alternatives.** Starlette without FastAPI: no validation or OpenAPI for the request models later
increments need. Routers per URL prefix rather than per Java class: `admin` would still be one, but
`/v2/entity` and `/v2/entity/bulk` belong to one Java class and would split.

**Consequences.** The example service is no longer the only FastAPI app; it stays until the plan is done
(DD-019). Later
increments add routers and error codes; the error handler and media type stay.

### DD-016. The server does not start without its store

- **Status:** Proposed
- **Increment:** 0.5
- **Date:** 2026-10-17

**Decision.** The server opens the Elasticsearch store in its start-up and stops with an error when the
store cannot be opened (unreachable, rejected, or not Elasticsearch 9). Once running, `readiness`
reports the store's health on every call, and `liveness` and `status` do not depend on it.

**Reason.** The store is the only system of record ([ADR 047](../adr/047-one-search-store-is-the-system-of-record.md));
a server without it cannot answer anything but the admin endpoints. Failing at start-up shows a wrong
setting at once ([ADR 018](../adr/018-settings-arrive-at-startup-through-one-channel.md)) and lets an
orchestrator restart the container, while readiness covers a store that goes away later.

**Alternatives.** Start without the store and retry in the background: a misconfigured server would run
and only its readiness would say so. Make liveness depend on the store: an outage of Elasticsearch would
make an orchestrator restart every server, which does not help.

**Consequences.** Start-up order matters: `nx serve` and the end-to-end tests start the dev store first.

### DD-017. The dashboards are vendored unchanged and built with dart-sass on Node 24

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** `apps/aurelius-atlas-dashboard/dashboardv2` and `dashboardv3` are copies of the
`release-2.4.0` tag, byte for byte, with Atlas's `LICENSE` and `NOTICE`. Every change is a patch listed
in `PATCHES.md` and made in its own commit. The first patch replaces `node-sass` with `sass` (dart-sass)
in both `gruntfile.js` files and `package.json` files. Both dashboards are built with
`grunt build-minify`, as Atlas's Maven build does, in the hardened Node 24 image; only the built files
leave the build. The workspace's formatters, linters and hooks skip the vendored directories.

**Reason.** DD-001 asks for the dashboards unchanged; a vendored copy lets a reviewer prove that with a
diff against the tag. `node-sass` 9 is a native module with builds for Node 16 to 20 only, and Node 20
is past its end of life; dart-sass is pure JavaScript, the maintained Sass compiler, and `grunt-sass`
supports it. A trial build on Node 24 gave the same files as Atlas's toolchain on Node 20, with
identical JavaScript; only the two compiled stylesheets differ.

**Alternatives.** Build unchanged on Node 20: no patch, but an unsupported Node and a native compile in
every build. Download the tag at build time and apply patch files: a smaller repository, but the source
the build uses is not in review. Commit the built files: no legacy toolchain at all, but the shipped
files cannot be reviewed or rebuilt.

**Consequences.** The vendored `package-lock.json` files keep their 2020-era dependencies; they only run
inside the build container and are not part of the server image, so Dependabot does not watch them.
Moving to another Atlas release replaces both directories and re-applies `PATCHES.md`.

### DD-018. The server serves the dashboards from the API's origin

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** The server mounts the built `dashboardv3` at `/n/` and `dashboardv2` at `/` as static
files, after the API routes, when `AURELIUS_ATLAS_SERVER_DASHBOARD_DIR` names their directory. The
server image contains the built dashboards and sets that setting.

**Reason.** The dashboards call `api/atlas/...` with relative URLs and rely on the session cookie of the
same origin, as in Atlas's web application. Serving them from the server keeps that without a proxy or
cross-origin configuration, and one image is the whole product.

**Alternatives.** A separate static file server or the template's Angular serving: a second container
and a proxy to keep one origin. Serving through a CDN: possible later in front of the server; nothing
here prevents it.

**Consequences.** API paths must never collide with dashboard files; the API is matched first. Unit
tests build their settings without the environment and serve no dashboards unless a test sets the
directory; `nx serve` builds the dashboards first and its `.env` points at `dist/`.

### DD-019. The template examples stay until the plan is done

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** The removal of the template's examples, planned as increment 0.7, moves to a to-do
after 6.4. Until then, the FastAPI example service, the Angular example screen and its libraries,
`aurelius-atlas-example`, `aurelius-atlas-sdk` and `dev/postgres` stay in the workspace. They remain
the named deviation of ADR 050.

**Reason.** The project's second phase needs these components again. Removing them now and
restoring them from the template later would cost more than keeping them.

**Alternatives.** Remove them now, as ADR 050 plans once the server and the dashboards replace them:
this fulfils ADR 050's R1 sooner, but the components would have to be restored for the second phase.

**Consequences.** CI keeps building, testing and scanning the examples. 1.1 follows 0.6 directly.
The to-do in the roadmap records the scope already agreed for the removal: everything the catalogue
does not use, apart from `dev/keycloak`.

### DD-020. Typedef models are Pydantic models that read and write Atlas's JSON

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** Each Atlas typedef class is a Pydantic model in `aurelius_atlas_model.typedef` with
snake_case attributes and the Java getter names as aliases. `model_validate` reads a request body and
`to_json` writes a response body: aliases, null fields left out, empty collections kept. Unknown fields
are ignored. The Java setters' normalisations run as `_`-prefixed validators, so they apply when a body
is read and when a model is built in code, as the Java constructors and setters do.

**Reason.** Pydantic is already the workspace's modelling library (settings, store) and FastAPI reads and
writes it natively, so 1.6 needs no mapping layer. Atlas writes with Jackson `NON_NULL`, which is
Pydantic's `exclude_none`; empty collections stay because Jackson keeps them (DD-013 compares exactly).

**Alternatives.** Dataclasses with a hand-written JSON codec: no dependency, but every rule of TDM-01 to
TDM-15 would be custom code. Generating models from Atlas's JSON schema: Atlas publishes none, and the
normalisations live in Java setters a schema cannot express.

**Consequences.** Response bodies must be written with `to_json` (or its `exclude_none`, `by_alias`
dump), never with FastAPI's default response model serialisation. Later model packages (entities in 2.1)
follow the same pattern.

### DD-021. Set-valued fields keep each name once, in first-seen order

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `superTypes`, `subTypes` and `entityTypes` are lists without duplicates, kept in the order
the names were first given.

**Reason.** Java holds them in a `HashSet` and writes them in hash order, which Atlas does not define and
no client can rely on. A Python `set` would make our order vary from run to run; first-seen order is
stable and keeps what the client sent.

**Alternatives.** Reproduce Java's `HashSet` iteration order: possible from `String.hashCode` and the
table size, but it would copy an accident of the implementation. Sorted order: stable, but reorders
what clients send.

**Consequences.** The JSON order of these arrays can differ from Atlas's. Parity scenarios compare them
without order, through the option DD-013 foresees, which 1.6 adds with the first scenario that needs it.

### DD-022. Typedef timestamps are aware datetimes, written as epoch milliseconds

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `createTime` and `updateTime` are timezone-aware UTC `datetime`s. They are written as
integer milliseconds since the epoch and read from a number, a string of digits or an ISO-8601
date-time string.

**Reason.** Atlas's REST mapper has no date serialiser, so Jackson writes `java.util.Date` as epoch
milliseconds and its `StdDateFormat` reads numbers, digit strings and ISO-8601. Pydantic would read a
bare integer as seconds or milliseconds depending on its size, so the conversion is explicit.

**Alternatives.** Keep the raw integer: exact, but every caller would convert. Write ISO-8601 strings:
readable, but a visible difference from Atlas.

**Consequences.** Jackson's RFC 1123 form (`Tue, 17 Oct 2026 10:00:00 GMT`) is not read. No Atlas client
is known to send it; if one does, it becomes a deviation.

### DD-023. Atlas errors live in the model library

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** `AtlasErrorCode` and `AtlasError` move from `aurelius_atlas_server.errors` to
`aurelius_atlas_model.errors`. Each code keeps Atlas's HTTP status, error code and message template.
The server keeps the error handler and the response class and imports the errors from there.

**Reason.** The type system (1.2) and the stores raise Atlas errors, and they may not depend on the
server (DD-002: model ← typesystem ← core; server → core). In Java, too, `AtlasErrorCode` sits in
`intg`, below everything else.

**Alternatives.** A separate errors library: one more project for two classes. Each layer with its own
exception, mapped in the server: the mapping would repeat Atlas's error table.

**Consequences.** New error codes are added to `aurelius_atlas_model.errors` as each increment needs
them, copied from `AtlasErrorCode`.

### DD-024. The registry is updated on a transient copy under a re-entrant lock

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** `TypeRegistry.lock_for_update(timeout)` returns a `TransientTypeRegistry` built from the
registry's definitions, under a re-entrant `threading.RLock`. Changes resolve every type on the copy;
`release(transient, commit=...)` swaps the copy's types into the registry or drops them. A context
manager wraps the pair.

**Reason.** It is Atlas's `TypeRegistryUpdateSynchronizer`: readers never see a half-resolved registry,
and a failed change leaves the registry as it was (TRG-05, TRG-09). A thread lock also protects
FastAPI's thread-pool handlers; async handlers hold it only around synchronous code.

**Alternatives.** An `asyncio.Lock`: does not protect code run in threads. Copy-on-write without a lock:
two concurrent updates would each start from the same registry and one would be lost.

**Consequences.** The lock is per process. Several server processes keep their registries in step
through the store (1.4).

### DD-025. The type system ports the definition side only

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** The ported types resolve definitions: names, attribute types, cardinalities, constraints
and later the hierarchies (1.3). Their value side (`isValidValue`, `getNormalizedValue`,
`validateValue`, `createDefaultValue`, `areEqualValues`) is ported with entity validation in 2.1. Their
JanusGraph side (vertex property names, unique property names, index field names, index-query escaping)
is not ported.

**Reason.** Types REST (1.6) needs only the definition side; values first matter for entities (2.1),
which is where Atlas's tests for them can be run. The JanusGraph names have no meaning in
Elasticsearch: the index mapping is designed in 2.2.

**Alternatives.** Port each class whole: one increment several times the size limit, with value code
untested by any endpoint until 2.x.

**Consequences.** The type classes grow in 2.1. Atlas behaviour that depends on vertex property names
is designed again for Elasticsearch in 2.2 and recorded there.

### DD-026. Dynamic attributes and search lookups wait for their increments

- **Status:** Proposed
- **Increment:** 1.3
- **Date:** 2026-10-18

**Decision.** The entity type's dynamic attributes (`dynAttribute:` templates, their parsing and
evaluation order) are ported with entity writes in 2.4. The root entity type's lookup of business
attributes for search is ported with basic search in 4.1. Both resolve nothing a type definition is
checked against.

**Reason.** They are used only when entities are written or searched, and can only be tested there;
porting them now would leave them untested by any endpoint until then (as DD-025 argues for values).

**Alternatives.** Port them with the rest of `AtlasEntityType` now: a larger increment whose extra code
no rule of 1.3 can exercise.

**Consequences.** 2.4 adds the template parsing to `EntityType`; 4.1 adds the lookup to the root type.

### DD-027. Derived type sets keep first-seen order

- **Status:** Proposed
- **Increment:** 1.3
- **Date:** 2026-10-18

**Decision.** All super types are listed in the order the depth-first walk of the super types first
reaches them; sub types and relationship attributes in the order the registry resolves its types, which
is the order the definitions were added in.

**Reason.** Java keeps them in `HashSet`s and `HashMap`s, whose order Atlas does not define; first-seen
order is stable, as for the definitions' own sets (DD-021). Where the order picks a winner, as for
inherited relationship attributes, Java's winner is equally arbitrary.

**Alternatives.** Sort them by name: stable too, but unrelated to how the hierarchy was declared.

**Consequences.** `subTypes` in responses may be ordered differently from Atlas's; parity scenarios
compare them without order (DD-021, from 1.6).

### DD-028. The type definitions are one Elasticsearch document

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** All stored type definitions are one document, `typedefs`, in the index
`aurelius-atlas-typedefs` (through an alias, so a reindex can swap it). The document holds the
definitions in their stored form (TDS-05, TDS-06), grouped by kind as in `AtlasTypesDef`. Every change
replaces the whole document, guarded by `if_seq_no` and `if_primary_term`.

**Reason.** Atlas changes several definitions in one graph transaction: `createTypesDef` stores all of
a request or none (TDS-10). Elasticsearch has no transaction across documents, but writes one document
atomically, so one document makes every typedef change atomic and its sequence number a single version
of all types (DD-029). The registry, not Elasticsearch, answers every query over types; the document is
read whole at start-up and on change. Atlas's built-in models with all patches are about 1 MB of JSON,
well inside Elasticsearch's limits.

**Alternatives.** One document per definition, keyed by name: queryable, and a create can use
`op_type=create` for uniqueness, but a request touching several definitions needs a hand-written
rollback when one write fails, and other processes see half a change. A changes log of operations,
replayed at start-up: atomic per entry, but every process replays the whole history and compaction is
extra work.

**Consequences.** The document's size grows with the number of types; a deployment with tens of
thousands of custom types would revisit this. Type changes are serialised across the cluster, as
Atlas serialises them with its update lock.

### DD-029. Server processes share the type definitions through the document's version

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** Each process remembers the `_seq_no` and `_primary_term` of the `typedefs` document its
registry was built from. Before a type change it reloads when the stored document is newer; it then
writes conditionally on what it read. A conflict means another process changed types first: the process
reloads, applies the change again on the new definitions, and gives up with
`FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` after a second conflict. Readers reload when the document changed,
checked at most every `AURELIUS_ATLAS_SERVER_TYPEDEF_REFRESH_SECONDS` (default 5).

**Reason.** Atlas runs one active server and keeps its registry in memory (DD-024 is per process).
Several processes behind a load balancer must not lose each other's changes, and a change must reach the
others without a restart. Optimistic concurrency on one document gives both with one cheap `GET` of
the document's version.

**Alternatives.** A lock document: needs expiry and recovery when its holder dies. Change notification
through a message bus: a component the system does not have (ADR 050).

**Consequences.** For up to the refresh interval, a process may answer from older types than another;
a type change is visible at once only on the process that made it. 6.4 measures whether the interval
needs tuning.

### DD-030. The store asks the entity store whether a type is in use

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** The typedef store takes a `TypeUsage` callback that answers whether entities,
classifications or relationships of a type exist; deleting a type that is in use fails with
`TYPE_HAS_REFERENCES`. Until the entity store exists (2.2) the callback answers "not in use".

**Reason.** Atlas checks `typeHasInstanceVertex` before deleting a type. The instances live in the
entity store, which the typedef store must not depend on; a callback keeps the dependency pointing from
core's entity store to the typedef store.

**Alternatives.** Query the entity index from the typedef store: couples it to an index that does not
exist yet.

**Consequences.** 2.2 passes its own check when it builds the stores.

### DD-031. The patch records live in the typedef document

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** The `typedefs` document of DD-028 holds, next to `typesDef`, a list `patches` of
`AtlasPatch` records: one per typedef patch id, with its description, type, action, status and times.
A patch's record is written in the same document write as the type change it makes.

**Reason.** Atlas keeps patch records as graph vertices and commits them after the type change, so a
crash between the two applies a patch twice, which the `typeVersion` check mostly hides. One document
makes the change and its record atomic, and gives both the single version of DD-029: a process that
loses a race reloads the records with the types, and sees the patch as already applied (MDL-15).

**Alternatives.** A second document, or an index of patch records: queryable by `admin/patches`, but two
writes per patch, and a race between processes needs its own conditional write.

**Consequences.** `admin/patches` (2.2) reads the records from the document. The Java patches of 2.2,
which change entities rather than types, may keep their records elsewhere; 2.2 decides.

### DD-032. The built-in models are vendored unchanged and read from a directory

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** `addons/models` of Apache Atlas `release-2.4.0` is copied byte for byte into the package
`aurelius_atlas_core.models`, and kept out of the formatting hooks. The server loads models from
`AURELIUS_ATLAS_SERVER_MODELS_DIR`, which defaults to that package directory.

**Reason.** Atlas reads its models from `$ATLAS_HOME/models`, so operators add their own model files and
patches there;
a directory setting keeps that. Unchanged copies let a reviewer prove them unchanged with a diff against
the tag, as for the dashboards (DD-017), and ship in the wheel without a build step. The line endings are
kept too: one patch file has CRLF, so the directory is `-text` in `.gitattributes`.

**Alternatives.** Converting the models to Python data: no diff against Atlas, and no way to add models
without a release. Reading them from a checkout of Atlas at build time: the build would depend on a
second repository.

**Consequences.** A newer Atlas version's models are a new copy and a check of the new patches against
the nine actions.

### DD-033. Start-up loading is one change per model file and per patch

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** Each model file and each patch is one change of the typedef store (DD-029): what to create,
update or patch is decided inside the change, on the definitions and patch records just read, and decided
again when a conditional write loses to another process.

**Reason.** Atlas loads models only on its one active server. Here every process starts the same way,
possibly at the same moment; deciding inside the change makes a second process see the first one's types
and records, so it creates, updates and patches nothing twice. One change per file and per patch keeps
Atlas's isolation: a failing file or patch leaves the others applied (MDL-04, MDL-06).

**Alternatives.** All files and patches in one change: one write, but a failure would need the transient
registry to roll back part of a change. A lock document held while loading: needs expiry when its
holder dies (as in DD-029).

**Consequences.** The first start against an empty store writes the document once per model file and
patch, a few hundred writes of the whole document; later starts write nothing unless a model or patch is
new. Two processes starting together may each retry once per change.

### DD-034. Lists of type definitions are sorted by name

- **Status:** Proposed
- **Increment:** 1.6
- **Date:** 2026-10-18

**Decision.** `GET /v2/types/typedefs` and `GET /v2/types/typedefs/headers` list the definitions of each kind
sorted by name, compared as Java's `String.compareTo`.

**Reason.** Atlas lists them in the iteration order of the `ConcurrentHashMap`s of its registry: deterministic,
but a function of Java's string hashes and the maps' resize history, which no client can rely on and no
scenario can state without computing it. A sorted list is stable across restarts, processes and updates, which
the order of the stored document is not: an update moves a definition to its end.

**Alternatives.** The order of the stored document: changes with every update. Emulating Java's hash order:
costly, and still not something a client could use.

**Consequences.** DV-09. A scenario that lists several definitions of a kind states them sorted by name.

### DD-035. Type scenarios create what they read and delete it at their end

- **Status:** Proposed
- **Increment:** 1.6
- **Date:** 2026-10-18

**Decision.** Each types scenario creates the definitions it needs, all named `scenario_…`, and deletes them in
its last stage. Before the server e2e runs its scenarios, it deletes any `scenario_…` definition left in the
store by an earlier run that stopped half-way.

**Reason.** The in-process scenarios start each from an empty store, but the e2e runs them all against one
server on the persistent dev store, which `nx serve` uses too. Self-contained scenarios pass on both, in any
order, and a run never touches a developer's own types.

**Alternatives.** Deleting the typedef index before the e2e: also deletes the developer's types and makes the
server load the models again. A separate index per e2e run: needs an index-name setting that nothing else
needs.

**Consequences.** Scenario names must be unique across scenarios; a scenario's expectations cannot depend on
types another scenario creates.

### DD-036. Start-up loading tries a raced change again

- **Status:** Proposed
- **Increment:** 1.6 (a fix to 1.5's MDL-15)
- **Date:** 2026-10-19

**Decision.** When the typedef store gives up on a model file or patch with `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK`
(two lost conditional writes, DD-029), the model loader makes the change again, up to ten times, before it
treats the file as failed or the patch as `FAILED`. The REST endpoints keep DD-029's single retry.

**Reason.** DD-033 assumed a process starting next to another loses at most once per change. CI showed
otherwise: two processes write a few hundred changes in near lockstep, and between one's reload and its retry
the other may write its next file, so it loses twice and skipped a model file. Every lost race is another
process's write, so trying again always makes progress, and a file or patch is never skipped for a race.

**Alternatives.** More retries in the store itself: also lengthens a REST request's wait under contention,
where Atlas answers `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` at once. No limit: a store that never stops changing
would hang start-up.

**Consequences.** DD-033's "may each retry once per change" becomes "until it wins, up to ten times". A
process that loses ten times in a row still reports the file or patch as failed, as Atlas does on a lock
failure.

### DD-037. The webapp is a new project, not the Aurelius app upgraded in place

- **Status:** Proposed
- **Increment:** 7.0
- **Date:** 2026-10-20

**Decision.** The Aurelius interface is rewritten as `apps/aurelius-atlas-webapp`, a new Nx
project on this workspace's Angular 22, Nx 23, and TypeScript 6. Only source moves: the Aurelius
`project.json`, `tslint.json`, Jest config, `jest-preset-angular`, and the root dependency set are
left in the Aurelius repository. Targets are inferred by this workspace's plugins, and tests are
Vitest.

**Reason.** An in-place upgrade must cross five `ng update` majors with the custom abstractions
intact, and needs `@angular/platform-browser-dynamic`, which this workspace does not install
because its apps bootstrap with `bootstrapApplication`. Vendoring the upgraded result therefore
adds a deprecated dependency and lands the whole NgModule graph in one review. A new project lets
each slice arrive on the target's rules, and the Aurelius app keeps serving while they do
([ADR 053](../adr/053-the-webapp-is-rewritten-in-angular-idiom-slice-by-slice.md)).

**Alternatives.** Upgrade in place then modernise: fails the "no replaced pattern survives" rule
and produces one unreviewable migration. Serve the Aurelius app as an external artifact: leaves two
Angular toolchains and two dependency trees to maintain. Port into
`aurelius-atlas-frontend-example`: destroys the small legible reference the example is for.

**Consequences.** The same screens exist in two codebases until 7.10 removes the example app. The
clone is kept at `.scratch/aurelius` as the reference checkout, git-ignored and outside the Nx
graph; every `Aurelius origin` citation in the 7.x increments points into it, and it is re-fetched
by path when a citation must be checked.

### DD-038. Signals replace the custom store; each slice owns its state

- **Status:** Proposed
- **Increment:** 7.0
- **Date:** 2026-10-20

**Decision.** The Aurelius `@models4insight/redux` layer (`Store`, `BasicStore`, `StoreService`,
`ReduxModule.forRoot`) is not ported and has no adapter. Each slice rewrites its state as
`signal()` with `computed()` for derived values, in an injectable following the signal-service
pattern of `aurelius-atlas-frontend-example`. A `Subject` survives only as an event stream inside
RxJS interop (`toObservable`, `toSignal`, `takeUntilDestroyed`), never as the owner of state.

**Reason.** The wrapper is a hand-rolled Redux: 24 Aurelius files import it, and its
`BehaviorSubject` state is the main reason the app cannot run zoneless — change detection depends
on zone patches seeing the emissions. Signals give the same explicit state, the same derived
values, and change detection that needs no zone. Keeping a compatibility layer would preserve the
abstraction the rewrite exists to remove, and every reader of a screen would meet it first.

**Alternatives.** NgRx: a dependency ADR 050 removes from the system, and signals make its store,
selectors, and effects redundant here. Keep the wrapper on Angular 22: cheapest per slice, and it
leaves the custom abstraction in front of every screen, which is what the requirement forbids.
Component-local signals with no service: shares nothing, so the cross-screen state the wrapper
carries (selected entity, filters, breadcrumbs) finds no home.

**Consequences.** State behaviour is re-expressed, not inherited, so the Aurelius store specs are
read as the source of assertions (ADR 053 R5). The purity check fails a state-owning `Subject`, so
a slice cannot keep one by accident.

### DD-039. Aurelius dictionaries become XLIFF, migrated whole, with the JSON as fixture

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The Aurelius flat-JSON dictionaries (105 keys, `en-US` and `nl-NL`) are converted in
full to XLIFF catalogues for the built-in `@angular/localize` at 7.1, before any screen needs them.
The Aurelius JSON is vendored into `apps/aurelius-atlas-webapp/tests/fixtures/` and a Vitest test
asserts every key, English value, and Dutch value appears in both catalogues. `nx extract-i18n`
maintains the template catalogue from then on.

**Reason.** The Aurelius app localises through `@ngx-translate/core` and its own `I18nService`,
registered in the module constructor; this workspace localises with `@angular/localize`, whose
catalogues the build compiles and which needs no service, so no runtime translation lookup
survives. Converting all 105 keys at once keeps one slice responsible for the dictionary: a
per-screen migration scatters the work, and the missing keys surface as untranslated Dutch long
after the screen that introduced them is accepted. The vendored JSON makes completeness a checked
fact that runs offline, not a claim in a pull request.

**Alternatives.** Port `I18nService` as a shim over `$localize`: keeps a `translate` pipe and a
`@ngx-translate`-shaped API the workspace has replaced. Migrate keys per slice: no completeness
gate, and Dutch gaps found in deployment. Machine-translate the Dutch: the Aurelius `nl-NL`
dictionary is human-reviewed work, and replacing it discards that.

**Consequences.** `{{ }}` placeholders in Aurelius strings become `$localize` interpolated
expressions, and the `TranslateService.get()` call sites become static messages. Aurelius keys with
no consumer after 7.10 are dead weight until swept; the completeness test is what keeps them named
rather than silently dropped.

### DD-040. Google Analytics and clickstream are dropped, not ported

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** `@models4insight/google-analytics` and `@models4insight/services/clickstream`, both
wired by `Core.imports`, are dropped. The webapp's operational signals go to OpenTelemetry through
`aurelius-atlas-observability`, as every other app's do.

**Reason.** The workspace observes itself internally and its operational data never leaves it
([ADR 016](../adr/016-the-system-observes-itself-internally.md)). The example app's content security
policy keeps `connect-src 'self'` and names only the Keycloak origins
([ADR 039](../adr/039-data-is-protected-where-it-travels-and-where-it-rests.md)); a browser call to
a third-party analytics host would need that policy opened for a second telemetry path that
duplicates what OTel traces and metrics already carry.

**Alternatives.** Port it behind a config flag: keeps the egress and the policy exception available
in production, which is the exposure the decision avoids. Keep clickstream to OpenTelemetry:
page-view tracking is the part of it worth having, and it belongs in the observability library, not
in a port of one app's vendor integration.

**Consequences.** Product usage analytics from the browser stop when the webapp replaces the
Aurelius interface at 7.10; page views can be re-added to `aurelius-atlas-observability` as a
deliberate feature. No Aurelius code is translated, so this is the one part of `Core.imports` that
has no destination.

### DD-041. The webapp's config is a typed AppConfig, and `environment.ts` is not ported

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The Aurelius `environments/environment.ts` (and its `production` flag, Keycloak
settings, `shell.appName`, i18n, telemetry, and notifications blocks, all read by `Core.imports`)
is not ported. The webapp reads a typed `AppConfig` from `/config.json` at bootstrap, following
`apps/aurelius-atlas-frontend-example`: the file is fetched and validated before
`bootstrapApplication`, and a missing, unreachable, or malformed file throws.

**Reason.** Build-time settings make one artifact behave differently per deployment, so the unit
validated is not the unit that ships
([ADR 010](../adr/010-the-unit-validated-is-the-unit-that-ships.md)), and settings arriving through
one channel that fails loudly is the workspace rule
([ADR 018](../adr/018-settings-arrive-at-startup-through-one-channel.md)). The Aurelius app already
compiles a separate bundle per environment, and its `environment.ts` carries the Keycloak client
and realm that a deployment must be free to set.

**Alternatives.** Keep `environment.ts` for dev and add `config.json` for production: two channels,
and the dev one is the one developers exercise. Read settings from `NGINX_*` variables at container
start: the hardened runtime image has no shell tooling to render them (the example app's
`AGENTS.md` records why its nginx template is resolved by the consumer, not at start).

**Consequences.** Every Aurelius call site that read `environment.x` reads `AppConfig`, so a
setting has one shape per deployment rather than one per build. The `dev/config.json` pattern means
development assets are bundled only in the development build, so a real secret never rides in a
production bundle.

### DD-042. Webapp purity is a checked gate, not a review convention

- **Status:** Proposed
- **Increment:** 7.0
- **Date:** 2026-10-20

**Decision.** The rules that say the webapp is not the old app are enforced by a check that runs in
CI: `nx run aurelius-atlas-webapp:check-purity` greps `apps/aurelius-atlas-webapp` and
`libs/angular` for `@NgModule`, `platformBrowserDynamic`, `@models4insight/`, `@ngx-translate/`,
`environments/environment`, and a state-owning `new BehaviorSubject` outside RxJS interop, and
fails on a match. The same rules are expressed as ESLint restrictions where the plugin supports
them.

**Reason.** Four slices in, a reviewer's attention is on the feature, and a copied Aurelius file
arrives with its `NgModule` and its `BehaviorSubject` attached — the exact imports the Aurelius
codebase is full of, and the ones ADR 053 forbids. A rule that only a person can notice during
review is a rule that decays, and the gate that refuses a change is defined once and runs
everywhere ([ADR 014](../adr/014-the-gate-is-defined-once-and-runs-everywhere.md)).

**Alternatives.** Rely on code review: free, and it decays exactly when slices get large. Rely on
the compiler: it catches `@ngx-translate` when the package is absent, and catches nothing about
`Subject`-owned state, which compiles cleanly. Rely on ESLint alone: no rule exists for
"this `Subject` owns state", so the grep carries what lint cannot.

**Consequences.** The gate is a maintenance cost of its own and must be read as a floor, not as
the definition of good Angular — idioms it cannot see (`input()` versus `@Input`, control flow,
`OnPush`) stay with review. Its allow-list is where an exemption is argued in the open, so an
escape hatch is a reviewed change rather than a quiet one.

### DD-043. The wildcard fallback redirects to the destination, not through the root

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The Aurelius fallback `{ path: '**', redirectTo: '' }` is ported as
`{ path: '**', redirectTo: 'search/browse', pathMatch: 'full' }`. The chain
`'**' -> '' -> '/search/browse'` that the Aurelius router resolves in two hops is one hop here.

**Reason.** Angular 22.2's router no longer re-triggers the empty-path redirect after a wildcard
redirect lands on `''` (angular/angular router fix `e9bf52aa03`, "require outlets to match a route
before processing child segments"), so the literal port lands on `/` and renders a blank router
outlet — verified in a browser, not theorised. SHL-05 promises the observable Aurelius behaviour:
an unknown path ends on the default destination.

**Alternatives.** Keep `redirectTo: ''` and add a redirect-triggering route: a workaround whose
shape exists only to dodge a router fix. Land on `/` and let the root redirect handle it: changes
the observable URL (`/` vs `/search/browse`), which is the parity SHL-05 is written against.

**Consequences.** If a future Angular restores chained redirects, the one-hop form keeps working —
it encodes the destination, not the chain. The `''` route remains the single definition of the
default destination; the fallback names it, so a later slice that moves the default edits both
lines, and `routes.spec.ts` pins both.

### DD-044. Operational telemetry lands with 7.1; the auth wiring stays with 7.3

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The webapp's OpenTelemetry wiring — trace and metric exporters, the
tracing `ErrorHandler`, and the `traceparent` HTTP interceptor, all from
`aurelius-atlas-observability` — lands with 7.1, not with 7.3. The Keycloak
providers and the bearer-token interceptor stay in 7.3, which owns the auth wiring.

**Reason.** DD-040 attaches the telemetry replacement to this increment, and the
shell is where the Aurelius `Core.imports` (the single wiring point that carried
both GA/clickstream and the app's providers) dissolves — so the OTel half of that
dissolution belongs here. The exporter endpoint is already a 7.1 config field
(SHL-02), the image already proxies `/otel/` (SHL-11), and the CSP already allows
it (SHL-11); deferring the wiring to 7.3 left the plumbing with no consumer.
Telemetry is also the shell's own operational signal — the earlier it covers the
app, the more of the port it observes.

**Alternatives.** Wire everything in 7.3: keeps one bootstrap commit, but leaves
DD-040 unsatisfied for a whole increment and pairs telemetry with auth for no
dependency that exists — the OTel providers need only `AppConfig`. Wire traces
only, metrics in a later slice: the metrics provider is the same call with a
metrics exporter; splitting them adds no review value.

**Consequences.** The e2e `/otel/` proxy test (SHL-11) gains a producer: the
served app now exports through it. The interceptor covers the API calls 7.3 adds,
so trace propagation is in place before the first request exists. The bootstrap
in `app.config.ts` matches the example app's provider set minus Keycloak, which
is the visible difference between the two files.

### DD-045. The design-system slice ports the in-use components, not the library

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** 7.2 ports the eight `@models4insight/components` folders the Aurelius
search/browse surface imports — `accordion`, `modal`, `hero`, `simple-search-input`,
`sortable-table-shell` + `sortable-table`, with `card` + `pagination` already present —
and defers the rest of the 34-folder library to the slices that consume them:
`select`/`quickview` to 7.7, `markdown`/`tree`/`date-picker` to 7.6, the
project/branch/user/permission modal family and the two search-input engines to 7.8 at
the earliest.

**Reason.** All 29 import sites in `apps/atlas/src` live under `app/search/**`; the
deferred families are imported by screens that arrive in 7.4–7.9, and a fifth of them
by nothing in the ported surface at all. Porting a component before its screen exists
means writing its stories and its specs against a guess of its caller, and ADR 053 R4
asks each increment for one readable capability, not a bulk migration. The leaf
primitives the legacy app styles with (buttons, tags, switches, checkboxes) are Bulma
classes in templates, not components, so they need no port.

**Alternatives.** Port all 34 folders: a PR roughly four times the budget of root
AGENTS.md, most of it unexercised. Port none and build components as screens need them:
each feature slice then invents its own card and modal, which is the shared-once rule
(ADR 053 R7) dissolved into ten slices.

**Consequences.** The roadmap row for 7.2 says "legacy shared components"; it now means
the in-use set, and the deferred folders are named in the increment's not-in-scope
table with their slice. A later slice that needs a deferred component adds it under its
own increment, where its caller can be reviewed with it.

### DD-046. Component services dissolve into signal state; nothing is ported as a store

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** The services the legacy components carry are dissolved rather than
ported. `SortableTableShellService` (a redux `BasicStore` holding sort, page and
selection) becomes `model()` state on `SortableTable`; `AbstractControlShell` and its
context objects become plain inputs with Bulma markup inlined; `FuzzySearchInputService`
and the `MonitorAsync` plumbing are not ported at all; `PageScrollService` in `Hero` is
dropped for the router's own scroll restoration. Where legacy state was persisted
(sort and page survive navigation via the store), persistence moves to the caller.

**Reason.** The custom store is the pattern the port exists to remove (DD-038, ADR 053
R3), and the purity gate refuses a state-owning `BehaviorSubject` in this tree. The
state those services hold is view state — which column is sorted, which page is open —
which is exactly what a `model()` is for, and a component that owns it in a signal can
be rendered in isolation in a story. Persistence is not the component's concern: the
browse screen keeps its sort in the URL (7.5), which is also what makes it shareable.

**Alternatives.** Port the store as a signal-based service in the lib: keeps the file
count low and gives every table a store it does not need, and a lib that owns
application state is what `libs/angular/AGENTS.md` forbids. Keep persistence in the
component with a `localStorage` key: works for one screen and breaks the moment two
tables share a route, as the browse surface does.

**Consequences.** Two legacy outputs (`rowIntersectionChanged`, from the intersection
observer used for infinite scroll) are dropped: paging is explicit, so the infinite-scroll
signal has no consumer. The legacy Jest assertions about store interaction are
re-expressed as component-level assertions (UIC-06), so the behavioural knowledge
survives while the abstraction does not.

### DD-047. Shared chrome strings are localisation units keyed by the legacy dictionary paths

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** A shared component's own strings — "Previous", "Next page", "No data
available", "Toggle content", the quickview tooltips — are `i18n` units in the
component's template, and their ids reuse the legacy `components.*` dictionary paths
(`@@components.sortableTableShell.previous`). The legacy component library's
translations (7 keys, `en-US` and `nl-NL`) are vendored as fixtures beside the app
dictionaries, and the webapp's generator bridges them into the same XLIFF catalogues
that carry the app's 495 strings. Text that belongs to a caller (a modal title, a
table's column names) is passed as content nodes, not as a string input.

**Reason.** WBP-05 forbids literal prose in a template, and the Dutch translations of
these seven strings already exist — dropping them would ship an untranslated table
header in the one language the port promises. The bridge keys catalogues by dictionary
path (DD-039) so a reviewer can diff a unit against the legacy entry, and the
completeness spec proves both locales; reusing the legacy paths keeps component chrome
and app text in one catalogue with one mechanism. Content nodes for caller-owned text
is what the built-in localisation cannot do for a string input: a translated string
that arrives as an `input()` is invisible to `extract-i18n`, so it can never be
translated.

**Alternatives.** `output()` events with the app supplying every string: no component
is usable in a story without its caller's dictionary, and the example app's existing
usage breaks (UIC-09). A `$localize` call per string: works, and loses the dictionary
path that ties a unit to its legacy source.

**Consequences.** `nx extract-i18n aurelius-atlas-webapp` now emits the lib's units,
because the app builds the library from source through the `tsconfig.base.json` path
alias. A component string with no legacy key (a state the Aurelius component never
had) gets a new id under `components.*` and gains a Dutch entry in the fixtures, so the
completeness gate is the point where a new chrome string is argued.

### DD-048. The purity gate is made executable over `libs/angular`

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** `check-webapp-purity.sh` gains the `libs/angular` tree it was documented
to grep (DD-042), and `aurelius-atlas-ui` gets a `check-purity` target wired as a
`dependsOn` of its `test` target, so CI enforces the legacy-construct ban on the
library as well as the app.

**Reason.** DD-042 states the gate greps `apps/aurelius-atlas-webapp` and
`libs/angular`; the script greps only the app's `src/`. The claim was written when the
library held six hand-written components and 7.2 is the first slice to fill it with
ported code — exactly the material a copied Aurelius file arrives in, with its
`NgModule` and its `BehaviorSubject` attached. A rule that is documented and not
checked is the failure mode DD-042 was written against.

**Alternatives.** An ESLint rule set in the library: carries what a linter can see
(`@NgModule`, a banned import) and nothing about a service that owns state in a
subject, so the grep is still needed. A shared CI step over both trees: correct, and it
puts the rule outside the project that documents itself (ADR 003), where a reviewer
editing the library will not find it.

**Consequences.** The gate runs twice per CI job, over two roots, from one script — so
one list of forbidden constructs stays the definition. Any exemption is an allow-list
entry in that script, a reviewed change in the open (DD-042's consequence), and 7.2's
ported components are expected to need none: the six existing library components are
already clean.

### DD-049. The Storybook preview loads `@angular/localize/init`

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** `.storybook/preview.ts` imports `@angular/localize/init` as its first
side-effect, the same polyfill the webapp build loads through its `polyfills` option.

**Reason.** A chrome string in a component template (DD-047) compiles to a `$localize`
call. Under the app's build that global exists; under Storybook's build it does not, so
every story whose template carries an `i18n` attribute throws `$localize is not
defined` at render — the `i18n` bridge silently made every story with chrome text
unrenderable, and the failure surfaces only in the browser, not in a unit test (Vitest
never runs the compiled template through localize).

**Alternatives.** A `polyfills` option on the Storybook targets: the executor schema
does not accept one. A no-op `$localize` in a story helper: works, and re-implements the
polyfill by hand, so it drifts from the real one.

**Consequences.** Stories render the English source text, which is what a visual
baseline and the `play()` queries assert on. A story that needs the Dutch text is out
of scope — translation is a per-app build-time concern; the completeness spec (SHL-08,
UIC-04) is what proves the catalogues carry both locales.

### DD-050. The client owns the base URL; the proxy forwards the prefix untouched

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The REST client composes every URL from the injected `API_BASE_URL` token
(`/api` from runtime `/config.json`), and the webapp's proxies — dev and e2e — forward
`/api` to the Atlas server with the prefix intact. The Aurelius mechanism (relative URLs
resolved against `<base href>`, prefix injected by the deployment proxy: dev
`proxy.conf.json` rewrites `/atlas` → `:21000/api/atlas`, k8s Apache `ProxyPass` rewrites
`/<ns>/atlas/atlas/` → `atlas:21000/api/atlas/`) is not ported.

**Reason.** The 7.0 audit asked how the legacy app reaches the server and found: nowhere
in the code — the coupling lives entirely in deployment. That is invisible to the compiler,
untestable against a stub, and the reason the legacy client cannot say which API it
speaks to. Aurelius Atlas inverts it: the client names its base URL from config (DD-041's
runtime-settings channel), the proxy is a dumb forwarder, and a deployment moves the API
by serving a `config.json`, not by editing proxy tables. The server's routes already carry
the `/api/atlas/...` prefix, so a rewriting proxy would double-strip it; forwarding
untouched is the composition that type-checks (`${apiBaseUrl}` + `/atlas/v2/...`).

**Alternatives.** Port the Aurelius split (relative URLs + rewriting proxy): keeps parity
with a deployment model this workspace does not share, and re-hides the coupling. Have the
browser call the server origin directly (`https://server:21000`): needs CORS policy and
per-deployment origins in the CSP, reopening the same-origin boundary ADR 039 closes.

**Consequences.** The webapp's dev proxy no longer points at the FastAPI example's
`:8000` (the copied line retargets at `:21000`); the example app keeps its own chain
until 7.10 retires it. The e2e nginx's `/api/` placeholder comment ("the Atlas API server
joins this proxy when 7.3 wires real data") is redeemed by DD-053.

### DD-051. The REST client ports the live surface; the search client is redesigned in 7.4

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The ported client covers the endpoints the server implements today: the
typedefs of 1.6 (`/api/atlas/v2/types/**`) and the admin trio (`version`, `status`,
`session`). The legacy search stack — `AppSearchService`, the engine subclasses, the
`{provide: AppSearchService, useClass: AtlasEntitySearchService}` alias, ~300 lines of
App Search DTOs — is not ported in this slice. 7.4 designs the search client when browse
consumes it, against `/v2/search/basic` (increment 4.1), not against the App Search shape.

**Reason.** The audit found the Aurelius search posts to DuckDuckGo Enterprise App Search
engines (`/elastic`, `/gov_quality`, `/data_quality`) — a third-party search backend
Aurelius Atlas does not have and will not gain: search is Elasticsearch-native here
(ADR: the store). The server's Atlas-native search is increment 4.1, planned. Porting the
App Search DTOs now would ship typed structs for a wire format no server speaks, specs
asserting calls that answer 404, and a mapping layer 4.1 reworks anyway (DD-051's
consequence). The rest of the legacy surface (entity, glossary, relationship, lineage,
validate, dashboard) has the same property in smaller doses: endpoints 2.3+ have not
landed, and the lineage/validate/dashboard backends are separate services with no
Aurelius equivalent.

**Alternatives.** Port all 65 files now: a client that lies about the system, with dead
code at day one (the legacy app itself leaves half of it unused). Port search against the
legacy shape with an adapter: the adapter's shape is guesswork against an unbuilt
endpoint.

**Consequences.** The client grows one method-set per server increment — each method
lands testable against the real server, and the specs stay honest through 7.4–7.9. The
legacy's service+free-function duplication (e.g. `EntityAPIService.getEntityById` and
`get-entity-by-id/`) collapses to one method each as each set is ported.

### DD-052. Auth is guarded at the app root; the bearer token is stated inert until 6.1

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The webapp wires the example app's Keycloak set — `provideKeycloak`
(check-sso, silent-SSO, DD-004's in-memory token store), `createAuthGuard` on the app
root route, `includeBearerTokenInterceptor` on `/api` — and guards every route. The
Aurelius `libs/authentication` (raw `keycloak-js`, `ReplaySubject` auth state, manual
`updateToken(5)` loop, guard applied by `Shell.childRoutes`) is not ported (WBP-02). The
Atlas server does not verify tokens until 6.1; the webapp sends the bearer token anyway.

**Reason.** The legacy shell guards every search route (`Shell.childRoutes` with
`requiresAuth: true`), so parity of behaviour means guarding. keycloak-angular's
`createAuthGuard` declares the guard where routing is declared — the app root — instead
of a library wrapping routes from the outside; the Aurelius `AuthTokenProvider`
constructor-injection (each API client wiring its own auth interceptor) disappears with
the interceptor's URL-pattern config. The token is sent from day one so 6.1 activates
authentication with no webapp change, and ADR 038's precedent covers the state it
describes: "every authenticated person can do everything" is a stated condition of the
pre-6.2 system, not a security property — the same is said here of the pre-6.1 server.

**Alternatives.** Ship providers without guards until 6.1: leaves the app public in
production while the product's own UI never was; the e2e suite would also keep testing an
unauthenticated flow nobody uses. Enforce per-screen guards as each screen arrives: the
root guard is one line and no screen can forget it.

**Consequences.** Dev and e2e now need Keycloak up (serve `dependsOn` gains it; the e2e
suite gains the example's authenticated-login fixture as `aurelius-writer`). The
unauthenticated redirect-to-sign-in is itself tested (APC-05) — the sign-in page is the
app's first collaborator, and the flow is proven in CI, not assumed.

### DD-053. The webapp e2e stack runs the real Atlas server behind the proxy

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The webapp's e2e compose grows an `atlas-server` service (the image its own
`docker-build` produces, TLS, joined to the dev Elasticsearch network), and the e2e nginx
`/api/` location proxies it with CA verification. The placeholder assertion (`/api/` →
Keycloak, `{"realm": "master"}`) is replaced by `GET /api/atlas/admin/version` answered
by the real server.

**Reason.** The placeholder nginx comment records the intent: "the Atlas API server joins
this proxy when 7.3 wires real data". A proxy test that passes against a stand-in backend
proves only nginx config; with the server in the stack, one e2e request proves the whole
chain this slice builds — nginx location, TLS verify, prefix forwarding (APC-08), server
routing, ES store — against the parity-tested surface. The image and its env already
exist for the server's own e2e; reusing them is copying, not building.

**Alternatives.** Keep Keycloak as the `/api/` backend: cheapest, and the chain stays
untested until 7.4 — the same gap 7.1 accepted with a comment; 7.3 is where the comment
matures. Mock the server in nginx config: a mock that answers like the server is a second
server to maintain.

**Consequences.** Webapp e2e `dependsOn` gains `aurelius-atlas-server:docker-build` and
the dev Elasticsearch `up`; the suite's boot chain lengthens by one container (ES is
already up for the server's own e2e, so cache-hit order matters little). The dev-pair
`nx serve aurelius-atlas-server` + `nx serve aurelius-atlas-webapp` becomes the documented
development loop.

### DD-054. The landing page is ported statically; search affordances and Shell chrome join the search slice

- **Status:** Proposed
- **Increment:** 7.5
- **Date:** 2026-10-20

**Decision.** 7.5 ports the Aurelius landing page (`browse`) as the static screen it is:
hero, the three context cards, and the info modals with their hardcoded type tables. The
cards' `simple-search-input` fields and `directTo*` "explore" buttons — every affordance
that sets `SearchService.query/filters` and routes to `/search/results` — are not ported
in this slice, and the Shell chrome (header/footer, whose centrepiece is the global search
bar) is deferred with them. Both join the search slice (7.4), which the user has placed on
hold until the server search API exists (4.1 basic search, 2.3 entity read).

**Reason.** The landing page's content — cards, info modals, type tables — is entirely
static and fully keyed in the XLIFF bridge, so the screen can be ported and proven today;
its search affordances are navigation into a screen that has no API, and shipping a search
box whose results page 404s is the speculative build DD-051 refuses, one level up. The
Shell is deferred for the same reason in chrome form: Aurelius's header carries the global
search bar and session UI, so wiring the chrome is one decision taken together with the
search entry point, not two. The user's 2026-10-20 direction ("port the landing page;
hold off on any search until the API is ready") fixes exactly this seam.

**Alternatives.** Port the cards with their search fields wired to a stub: the affordance
works in dev and dies in the e2e stack's real server — a UI promise the increment cannot
keep. Ship the Shell now and hide its search bar: chrome with its main control removed is
neither the legacy screen nor a clean seam.

**Consequences.** The 7.5 page has no route out except the info modals (BRW-06); 7.4
re-adds the affordances as part of the search slice, at which point the Shell row of the
7.x ledger is taken with it. The 7.5 roadmap row is retitled to the landing page; browse
domain grids, if kept from the legacy design, follow with the search slice.

### DD-055. i18n ids carry no description suffix; the bridge key must equal the extracted id

- **Status:** Proposed
- **Increment:** 7.5
- **Date:** 2026-10-20

**Decision.** An `i18n` attribute in the webapp or `aurelius-atlas-ui` is written
`i18n="@@<dictionary.path>"` only — never `@@<id>|<description>`. Where a unit wants a
translator note, the note lives in an adjacent comment. `aurelius-atlas-ui`'s four chrome
units (`components.sortableTableShell.previous|next|noData`, `components.accordion.toggleContent`)
drop their `| … (DD-047)` suffixes, and the `SortableTable` component drops
`TableColumn`/`TableRow` from its `imports` (caller-projected directives, NG8113).

**Reason.** Angular joins the `|description` half into the extracted trans-unit id, so the
key-keyed bridge (DD-039, DD-047) can never match such a unit: `extract-i18n` emits
`components.sortableTableShell.next|Aurelius table shell …` where the catalogue carries
plain `components.sortableTableShell.next`. The nl-NL build then answers "No translation
found" for the unit — the chrome string ships untranslated in the one language the bridge
exists for. The defect was latent in 7.2 (the ui-lib has no app build of its own to
surface it; the accordion unit never matched, unnoticed) and surfaced in 7.5 when the
landing's info-modals pulled the sortable table and its pagination into the app's
translation graph. The completeness spec cannot catch it: it compares the committed
catalogues to the fixtures, and extracts ids only as a set-diff (`UIC-04` scans template
`@@components.*` literals, which include the suffix). The production build is the gate
that sees it. NG8113 has the same root as the import fix: the table's own template never
applies the column/row directives — callers do — so listing them is a lie the compiler now
flags once the table is app-compiled.

**Alternatives.** Keep the descriptions and teach the bridge to split on `|`: one more
key-mangling rule in the generator for a note the XLIFF `<note>` element (which
`extract-i18n` emits from the marker's description) already carries — the catalogue
already proves round-tripping works without it. Register the chrome strings in the
catalogues _with_ the suffix: breaks the "id equals the legacy dictionary path" invariant
DD-047 states in its title.

**Consequences.** `nx extract-i18n aurelius-atlas-webapp` output is now a strict subset of
the bridge catalogue, so `nx build aurelius-atlas-webapp` is warning-clean and can be used
as the id-parity gate; the 7.2 spec's chrome-string rule (UIC-04) is unchanged, and the
accordion's toggle-content unit starts translating in nl-NL for the first time.

### DD-056. The Shell chrome is ported search-free; the root composes header and footer

- **Status:** Proposed
- **Increment:** 7.11
- **Date:** 2026-10-20

**Decision.** The Aurelius chrome (header, footer) is ported now, on the user's request,
as its own slice (7.11), composed directly by the root component — `Header` (the 7.2
ui-lib component) over the router outlet, footer below. What is ported: the brand (app
name from `/config.json`, linking to the default route), the Documentation link, the
language dropdown, the account dropdown (identity, Keycloak account console, logout),
and the copyright footer. What is not: the global search bar and nav buttons (they join
7.4, unchanged from DD-054's reasoning), the PWA install/update buttons (no service
worker is ported), the Models4Insight services dropdown (not part of this product), the
sticky loading/pipeline block (nothing to track yet), and the login button (every route
is guarded, APC-05 — the logged-out navbar is unreachable). The navbar is not
`is-fixed-top`. Switching language is a full-page navigation into the locale tree, not
ngx-translate's runtime swap.

**Reason.** DD-054 deferred the chrome _with the search bar_ because wiring them was one
decision; the user has since asked for the shell as its own deliverable, so the seam
moves: the frame is orthogonal to search, and a screen wearing its header/footer is
strictly closer to the product than a bare outlet. DD-054's search half stands
unchanged — this entry supersedes only its Shell-chrome sentence. The deferred controls
each fail a test this workspace already enforces: an install button with no service
worker is a promise the build does not keep; a services dropdown points at products
outside this repo; a login button behind a guard is dead markup; a loading bar has no
long navigation to track while the only screen is static. Aurelius's `Shell` module,
its service (token refresh on window focus — keycloak-angular owns refresh, DD-052) and
its reusable-route strategy are Redux-era plumbing the port's idioms replace (DD-046).

**Alternatives.** Port the shell wholesale with the deferred controls hidden behind
config flags (Aurelius's own `standalone`/`hideDocumentation` knobs): config that only
one deployment ever flips is dead code (the atlas environments never set them); the
user asked for the shell, not for a feature-flag audit. Wait for 7.4: the chrome is
search-independent and the user wants it now.

**Consequences.** The 7.11 navbar is static; 7.4 adds the search bar and nav buttons to
it, at which point `is-fixed-top` and the content offset return together with the sticky
loading bar (a pinned header is a layout contract, not a class). The root's "bare
outlet" spec (SHL-03, 7.1) is superseded by SHC-01 — the Aurelius root _is_ the shell,
and the reading that motivated 7.1's placeholder retires. The shell's chrome strings are
new vendored fixtures (`shell.header.*`, `shell.footer.*`), bridged like the components
dictionary (DD-047), so UIC-04's invented-string gate extends to them.

### DD-057. Session chrome injects the keycloak-js `Keycloak` instance, not keycloak-angular's `KeycloakService`

- **Status:** Accepted
- **Increment:** 7.11
- **Date:** 2026-10-20

**Decision.** `Session` and `ShellHeader` inject the `Keycloak` client
instance (keycloak-js) — the token `provideKeycloak` registers — for the
identity read (`tokenParsed`) and for `logout()`. keycloak-angular's
`KeycloakService` is not injected anywhere.

**Reason.** `KeycloakService` is the deprecated pre-v19 class: v21's
`provideKeycloak` provides the `Keycloak` instance and the event signal
and does **not** register `KeycloakService` (the library's own services
and guards inject `Keycloak`, e.g. `includeBearerTokenInterceptor`,
`createAuthGuard`'s `AuthGuardData.keycloak`). Injecting the
not-provided class crashes the production image at boot (NG0201
NullInjectorError, found by the 7.11 e2e run: every authenticated
scenario errored in the guard, where the chrome renders). Unit specs
missed it — they mock the token; the dev server never renders the chrome
before the guard redirects, so only the built image exercised it.

**Alternatives.** Provide `KeycloakService` manually (`useExisting: Keycloak`
-style): re-provides a deprecated facade for a class slated for removal.
`inject(KEYCLOAK_EVENT_SIGNAL)`: a signal wrapper, not the client — no
`logout()` on it.

**Consequences.** SHC-05/SHC-08's "Keycloak client" is now precise: the
keycloak-js instance. Spec test providers use `{ provide: Keycloak, … }`.
7.4's session-touching code follows the same token.

### DD-059. The Aurelius brand lands on Bulma 1 tokens, light-forced, legacy metrics pinned

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** The Aurelius palette and the legacy chrome metrics ship as
Bulma 1 CSS custom properties in `@aurelius/atlas-brand` (SHM-01..04): the
Aurelius blue as `primary`/`link`, Bulma 0.9.4's greys (`#f5f5f5` light/navbar
bands, `#363636` invert), the blue footer band, BlinkMacSystemFont-first stack,
16px, 1.5 line-height, `#4a4a4a` ink, 4.25rem navbar. They are emitted after
Bulma's own `:root`, on `:root` for the global tokens and on `.navbar`/
`.footer` for the ones Bulma scopes on its components. Light is forced with
`data-theme="light"` on the document root; the brand tokens live outside the
`:root:not([data-theme])` scheme machinery so a future dark scheme keeps them.
The sticky footer is a flex-column body + `.is-tall-container` band
(`flex: 1 1 auto`), the pinned navbar is `is-fixed-top` +
`has-navbar-fixed-top`, navbar content sits in a Bulma `container` (SHM-05).

**Reason.** The legacy (Bulma 0.9.4) baked its look through SASS variables;
the workspace is on Bulma 1, which reads CSS custom properties and defaults to
a different design (Inter, 1rem, turquoise primary, white footer, 3.25rem
navbar) — without the overrides the app renders the wrong brand entirely. Two
Bulma 1 traps found by measurement against the live demo: component-scoped
tokens (`.navbar`/`.footer` re-declare their own background, shadowing
`:root`), and `hsl(var(--h), …)` requiring degree-unit hues (a percentage hue
silently drops every `has-background-*` rule — the demo's `#f5f5f5` band came
out transparent). Light-forcing is Bulma 1's scheme machinery, one attribute;
the brand colours stay scheme-independent so the switch has nothing to
re-brand. The flex-column footer replaces the legacy's
`.is-tall-container{min-height:100vh}`-inside-fixed-padding trick with the
modern equivalent (DD-056's static-navbar reading is superseded — the pinned
navbar is what the demo ships).

**Alternatives.** Stay on the Bulma-1 defaults and re-skin component by
component (the 7.2 status quo): every new surface drifts from the legacy
brand. Port `@models4insight/styles` (DD-037 reversal): a Bulma 0.9.4 theme
package, the dependency the workspace adopted away from. Pin the legacy
`has-background-*` classes only (no tokens): the demo's own utility CSS, and
the token overrides are the one lever — the utilities read the same HSL
triplets.

**Consequences.** The chrome matches the reference demo on every measured
value (SHM-06's e2e scenarios pin them). The theme switch is a later slice:
one attribute (`data-theme`), no re-brand. Bulma utilities read the brand
colours (`has-background-light` = `#f5f5f5`), so 7.4+ surfaces inherit the
look. The greys are Bulma 0.9.4's pair, not Bootstrap's — the brand library's
`$gray-*` stays for the `is-dark` pair (`#363636`).

### DD-058. Dev Keycloak users carry `default-roles-master` explicitly

- **Status:** Accepted
- **Increment:** 7.11 (dev infrastructure)
- **Date:** 2026-10-21

**Decision.** The dev users in `dev/keycloak/import/master.json`
(`aurelius-writer`, `aurelius-reader`) declare `"realmRoles":
["default-roles-master"]`.

**Reason.** The SHC-05 Account-security link opens the Keycloak Account
Console, whose REST calls (`/realms/master/account/*`) require the
`account` client's `manage-account`/`view-profile`; those roles reach a
user only through `default-roles-master`'s composites. Keycloak's realm
import does **not** auto-grant the realm default role to imported users,
so the dev users reached the console with no roles and every REST call
401s — the console renders "Something went wrong". Verified live: with
the role granted, the console's profile page renders; without it, the
same session 401s on `supportedLocales` and the account root. The Admin
REST cannot repair a running realm here (every `role-mappings/realm`
POST answers 404 "Role not found" for these users), which makes the
import file the single declarative place the grant can live.

**Alternatives.** Grant the roles per user through the admin console by
hand: invisible to new clones, lost on stack recreate. Add the account
client roles directly to the users: duplicates what
`default-roles-master` already composites and drifts when Keycloak
version changes reshape that role. A `defaultRoles` realm attribute
(makes the role default for users created after import): does not reach
the users the import itself creates.

**Consequences.** The Account Console works for both dev users, dev and
e2e. Applying the change to a running stack requires recreating the
users — a boot re-import skips an existing realm wholesale — the recipe
is in `dev/keycloak/AGENTS.md`. New realm-default-role needs (e.g.
`offline_access` for refresh tokens) arrive here, not per client.

### DD-060. Critical-CSS inlining is off: the zoneless CSR app never swaps the print sheet

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** The webapp's production build sets
`optimization.styles.inlineCritical: false`. The stylesheet loads as a
normal render-blocking `<link>`; nothing is inlined into `index.html`
and no `media="print"` swap is involved.

**Reason.** Angular's critical-CSS inliner (beasties) rewrites the
stylesheet to `media="print"` and ships a script that swaps it back at
load. In this zoneless CSR app the swap never runs (e2e measurement:
every browser, the sheet stayed on `print`, 3,024 rules inert), so the
app rendered from the ~115 rules the inliner had copied into the HTML —
Bulma base styles applied, brand overrides on `.navbar`/`.footer` and
utilities like `has-background-light` did not (transparent bands, no
blue footer). The inliner has no element to inline _for_ in a CSR shell
— `index.html`'s body is the app root and the router content appears
after boot, so "critical" is meaningless here. Dev mode (`optimization:
false`) never showed this, which is what made the demo-match in dev
coexist with broken e2e.

**Alternatives.** Keep inlining and fix the swap script (it is Angular
generated — no supported knob). Load the sheet with a forced
`media="all"` (build emits the print attribute as part of the inliner's
output — off is the supported switch). Serve with SSR/prerender so the
inliner has real content (7.x is a client-rendered SPA; the dashboard
is a separate app).

**Consequences.** First paint ships the full stylesheet (~770 kB
minified, gzip ~90 kB) — the same payload the legacy demo ships. The
e2e suite now measures the CSS the browser actually applies. If LCP
ever matters, re-measure with the inliner enabled in a browser that
executes the swap script before re-enabling.

### DD-061. The sticky footer is the legacy rule verbatim; page content sits on Bulma's grid

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** `.is-tall-container` is ported verbatim — `flex: 1 1 auto`
**and** `min-height: 100vh` (the legacy `shell.component.scss`) — so the
outlet band is a full viewport and the footer begins at the fold, off the
first screen. Page content is inset by Bulma's grid, not hand-rolled
margins: the landing wraps in `section.section > div.container` (the
anatomy every legacy routed page uses — `details`, `domains`,
`create-entity` all start with `div.container`), the footer keeps its
`container` (the legacy footer's own anatomy), and the `#f5f5f5` band
behind the content stays full-bleed. SHM-05/SHM-07.

**Reason.** Measured against the live demo: its footer starts at y=1346
in a 900px viewport (band `min-height: 900px` — the footer is never on
the first screen), while the first-cut port (flex-grow only) filled the
band to exactly the fold, pulling the footer into it. And the demo's
landing content is inset on Bulma's responsive grid (box x=56 at 1280,
the navbar brand's column), while the port rendered edge-to-edge. Both
are the legacy's own rules — the port had read `.is-tall-container`
selectively and had not ported the page wrapper at all.

**Alternatives.** Keep flex-grow-only (footer flush at the fold): it
diverges from the demo on the one axis the user measured — "the footer
should always be below the fold". Hand-rolled page padding
(`.is-tall-container { padding: … }`): invents a grid Bulma already
owns; the `container` is responsive (fixed widths per breakpoint, 32px
margins below desktop), a hand-rolled inset is not. `section.hero`
instead of `section.section` (the demo's landing hero is a hero): the
teal hero is the 7.4 search slice, out of scope here.

**Consequences.** The landing matches the demo's measured insets
(box x≈56 at 1280) and the footer is below the fold at any viewport.
The `section > container` wrapper is the pattern for 7.4+ routed pages
(details, search results) — they inherit the grid from their first
element. `min-height: 100vh` on the band means short pages scroll the
footer into view; that is the legacy behaviour the demo shows.
