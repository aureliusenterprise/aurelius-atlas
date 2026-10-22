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

### DD-062. The brand re-emits Bulma 0.9.4's text ramp, not just the body metrics

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** SHM-03 covers the whole type ramp, not only the body. The
brand library emits Bulma 0.9.4's neutral greys on Bulma 1's **channels**
(`--bulma-text-h/s/l`, `--bulma-text-strong-*`, `--bulma-text-weak-*`), so
every derived token — `text`, `text-strong`, `text-weak`, the navbar and
dropdown ink chain — resolves to the legacy ramp: `#4a4a4a` body/box/
content ink, `#363636` headings, `#7a7a7a` weak. The weights Bulma 1 moved
are pinned back on the selectors that scope them (`.title`/`.subtitle`
600, `.button` 400) plus `--bulma-strong-weight: 700` and
`--bulma-navbar-item-color: #4a4a4a` (the demo's navbar ink is the body
ink, links and `strong` alike). `.content` is `#4a4a4a` with `#363636`
600 headings. SHM-03.

**Reason.** Reviewing the font story against the live demo: DD-059 pinned
the body (stack, 16px/1.5, `#4a4a4a`) and the chrome bands, and every
body-level value matched — but Bulma 1 re-tinted its whole grey ramp 221
degrees (`text` `#4a5568`, `text-strong` `#2e333d`) and re-weighted the
ramp (title 600→800, strong 700→600, button 400→500). The app rendered
with a blue-grey cast: titles `rgb(46,51,61)` at 800, box ink
`rgb(64,70,84)`, navbar links `#535353`, dropdown ink `#404654` — none of
them the demo's values. The size scale (`is-2` 40px/45, `is-6` 16/18,
dropdown 14px, the 4.25rem bar) was already identical; only the ramp
diverged. Pinning the channels (not the derived tokens) fixes the entire
chain at once, including selectors the brand file does not enumerate.

**Alternatives.** Override each derived token at every use site
(`.title { color }`, `.box { color }`, …): whack-a-mole across Bulma's
long hsl-composed chains (the navbar dropdown composes `h`/`s` from the
scheme with the `text` lightness — enumerating all compositions misses
them, as the first cut did). Pin only the body (DD-059 as landed): the
user-visible difference is exactly what the review found — a blue-grey
app where the demo is neutral grey.

**Consequences.** Every landing text/weight pair is demo-parity, pinned
by `test__type_ramp_matches_the_legacy_page`. The emission is
scheme-independent (channels live outside Bulma's `data-theme` blocks),
so a future dark scheme inherits Aurelius' neutral ramp machinery
unchanged. `--bulma-text-rgb`-style companions are emitted for
`text`/`text-strong`/`text-weak` (consumers read them raw).

### DD-063. The accent ramp: primary stays Bulma teal, the accents take the Bootstrap map

**Decision.** The brand library overrides the **accent** colours, not
primary. `--bulma-primary` keeps Bulma's own teal `#00d1b2` (identical
in 0.9.4 and 1.x — the demo's landing icons, hero buttons and `.is-primary`
fills are teal, measured `rgb(0,209,178)`, hover `rgb(0,196,167)`), with
only `--bulma-primary-invert-l: 100%` pinned: Bulma 1 derives solid-fill
ink from `primary-05-l` (6 % — near-black) where 0.9.4 and the demo use
white. The Bootstrap map the legacy theme applied to its accents is
re-emitted from `$bulma-accent-overrides`: `link` `#0073dd`, `info`
`#17a2b8`, `success` `#28a745`, `warning` `#ffc107`, `danger` `#dc3545`,
each with its value, `-base`/`-rgb` and `h`/`s`/`l` channels, and its
solid-fill ink pinned white — except `warning`, which keeps Bulma's dark
ink (the demo's `btn-warning` text is `rgba(0,0,0,.7)`). The navbar's
hover/active band renders `#f5f5f5` with `#000` ink (the demo's
`.navbar-link:hover`); Bulma 1 derives it from the hero chain and renders
a blue-tinted plate. The plate composes `hsl(navbar-h/s,
navbar-item-background-l + hover-delta, a)`, so the brand neutralises
the `navbar` hue/saturation channels (the DD-062 pattern) and sets the
hover/active deltas to the band grey's 96 % lightness; Bulma 1 has **no**
hover-ink token at all (0.9.4's `navbar-item-hover-color` is gone), so
the black ink rides on a scoped hover rule mirroring Bulma's plate
triggers. SHM-04.

**Reason.** The 7.12 first cut mapped `"primary": $blue` onto
`--bulma-primary` as a placeholder (the shell chrome is blue-banded, so
primary _looked_ like `#0073dd`). Measuring the demo's landing page
shows the icons the user flagged — the business/technical/governance
card glyphs, `has-text-primary` — are Bulma teal `rgb(0,209,178)`, not
blue: `#0073dd` in the legacy theme is `$link` (anchors) and the footer
band, never `$primary`. Bulma 1's defaults for the untouched accents
(its own cyan/green/yellow/red) are likewise not the demo's — the demo
carries the Bootstrap palette, which the legacy `@models4insight/styles`
theme mapped onto Bulma's accents (the same map SHM-04 already uses for
`link`/footer). Fixing primary and leaving the accents on Bulma's
defaults keeps half the deviation.

**Alternatives.** Keep primary `#0073dd` (as landed): every
`has-text-primary`/`is-primary` surface — the landing icons the user
compared side by side — stays blue where the demo is teal. Port all of
Bulma 0.9.4's derived accent tokens (each family emits ~30 variables):
unnecessary, the channel triple plus `-base`/`-rgb`/`-invert-l` covers
what Bulma 1 composes at runtime.

**Consequences.** The landing page's icon highlights match the demo.
`$bulma-token-overrides` shrinks to the four chrome greys; accents have
their own `$bulma-accent-overrides` map (value + ink lightness). The
navbar hover/active emission joins the navbar block (DD-059's "scope on
`.navbar`" pattern), with the one ink rule outside the token machinery —
the first brand rule that must set a state colour Bulma 1 never tokenised.
Pinned by `test__accent_ramp_matches_the_demo`.

### DD-064. The mobile burger chrome: grey burger, blended dropdowns, legacy logout anchor

**Decision.** The brand carries the legacy theme's mobile navbar on Bulma
1: `--bulma-navbar-burger-color: #4a4a4a` with the burger **channels** set
black (the hover/active plate composes them at 10 %/20 % alpha — 0.9.4's
plate is `rgba($black, .1)` over the band, Bulma 1 tints it from link),
and `--bulma-navbar-dropdown-arrow: #000` (the legacy pins
`$navbar-dropdown-arrow: $black`; Bulma 1 derives it from link). The
selected plate (`.is-active`, the locale's current item) lands on
white/`#000` (the demo's measured pair — 0.9.4's, Bulma 1's default is the
link-blue plate). Under `max-width: 1023px` the burger menu's
`.navbar-dropdown` blends into the band (0.9.4 zeroes its
background/colour/padding — Bulma 1's dropdown-item plate rule is **not**
media-scoped, so its items render as white tiles on the grey band) and the
dropdown chevron is hidden (Bulma 1 regression jgthms/bulma#4173: the
`%arrow` placeholder's `:not(.is-arrowless)` display beats the media
rule's plain `.navbar-link::after`). The Logout item is the legacy
`a.navbar-item[role=button]` — navbar ink, no `has-text-danger` (the
legacy shell has none; the dropdown ink chain styles anchors, a
`<button>` keeps the UA's centred text and the dropdown plate's white
tile). SHM-04/SHC-05.

**Reason.** Reviewing the mobile chrome: the burger and its hover plate
rendered Aurelius blue, the logout item sat centred on a white tile
inside the grey menu, and the menu's dropdowns showed as white panels
with blue chevrons. The legacy theme (`.scratch/aurelius`
`libs/styles/src/styles/_theme.scss`) sets exactly four navbar rules —
height, background, dropdown-arrow black, hover `#f5f5f5`/`#000` (DD-063)
— and inherits 0.9.4's defaults for the rest; every mobile deviation is
Bulma 1 changing those defaults (burger/arrow from link, unscoped
dropdown plates, the chevron regression) or the port deviating from the
legacy markup (Logout as a red `<button>`).

**Alternatives.** Restyle the red logout `button` (padding/background
overrides): the legacy ink is navbar grey, not red — the red was never in
the product; the anchor is the legacy element and rides the dropdown's
own ink chain for free. Ship the blue burger (Bulma 1's default): the
demo's chrome is the greys, and the blue plate on the grey band is the
mismatch the review flagged.

**Consequences.** The mobile menu reads as one grey band with grey ink,
as the demo. The media block is the brand's first responsive emission;
the chevron rule documents the upstream regression it mirrors. Pinned by
`test__burger_menu_matches_the_legacy_mobile_chrome`.

### DD-066. The entity card emits `entityClicked`; the caller navigates

The ported `entity-card` (7.13) emits `entityClicked(guid)` on a title click and
does not navigate. The legacy `DetailsCardComponent` injected `Router` and, on a
title click with no parent listener attached, navigated to
`search/details/{guid}` itself — its template probed `entityClicked.observers`
to choose emit-or-navigate.

**Reason.** The ui lib is dumb by workspace rule (ADR 053, user rule: components
are dumb and live in `aurelius-atlas-ui`); an injected `Router` inside a lib
component re-creates the coupling the port exists to remove, and the
`observers.length` probe is a side-channel, not an API. Emitting always and
letting the app route is the DD-046 pattern (`SearchField` emits, the caller
filters).

**Alternatives.** Port the probe (emit-if-observed, else navigate): keeps the
legacy one-liner call sites, at the cost of a Router in the lib and behaviour
that changes with the parent's subscription list. A `routerLink` on the title
anchor: the details route belongs to 7.6, the lib must not know its path.

**Consequences.** 7.6 wires `entityClicked` to the router. The card is
testable and storyable with zero app services.

### DD-067. The select is one field with a `searchRequested` output

The ported `select` (7.13) is the Bulma select field plus a search button that
emits `searchRequested`. The legacy `SelectComponent` embedded a
`SearchModalComponent` (a repository-fed `sortable-table-shell` inside a modal,
selected row confirmed into the field) and sat on the reactive-form
`AbstractControlShell` base.

**Reason.** The modal's data comes from `@models4insight/repository` — exactly
the API coupling 7.2 set aside for the app slices (7.7 owns the editor
anatomy). The presentation half (field, options, null/no-data messages,
timestamp display, required help) is pure, so it ports now; the modal half
arrives as app wiring listening to `searchRequested`. The reactive form
dissolves into `value = model()` exactly as DD-046 did for `SearchField`, and
the `compareWith` default becomes strict equality — the lodash `isEqual` deep
compare was a legacy default the Aurelius callers never relied on.

**Alternatives.** Port the whole component including the modal: drags the
repository and `task-manager` into the lib. Defer the select entirely to 7.7,
per 7.2's table: the details screens want a pure select today, and the
presentation/data split lets 7.7 wire only the modal.

**Consequences.** 7.7 composes select + modal; the lib stays pure. Option
identity is strict reference equality — callers pass stable objects.

### DD-068. The brand ships a dark ink ramp on Bulma's dark hosts

The brand theme (DD-059/062) pins the light ink chain in `:root` — body
`#4a4a4a`, the neutral text ramp, `.content` — and `:root` out-cascades
Bulma's own `[data-theme=dark]` block (equal specificity, later source).
The result: under a dark scheme (the storybook theme switch, any future
`DarkModeService` use) the surfaces flip to Bulma's dark scheme and the
ink stays light-mode grey — illegible. This adds a dark ink ramp emitted
on both of Bulma's dark hosts, `[data-theme="dark"]` (the explicit
toggle, `DarkModeService`'s attribute) and `:root:not([data-theme])`
inside `prefers-color-scheme: dark` (the OS path, Bulma's `system-theme`
pattern): the text chain re-pins to Bulma's dark-scheme lightnesses over
the DD-062 neutral hue (text 71% `#b5b5b5`, strong 93% `#ededed`, weak
53% `#878787` — ~9:1 on the 9% surface), the body ink/background return
to the scheme tokens, `.content` follows, the link lifts to Bulma's own
dark adaptation (`link-on-scheme-l`, 73% — `#0073dd` is ~3.9:1 dark-on-
dark), and the ui lib's legacy `.technical` type ink (pure `#0000ff`,
~2:1) lifts to the same 75% lightness Bulma's contrast loop derives.
`.technical` is the only legacy type colour that fails on dark: orange,
teal and the grey all read 8:1+ and stay.

**Reason.** The switch must show the real app theme, and the app's dark
mode (7.11's `DarkModeService` ships the toggle, 7.12 defers the theme)
has no usable ink. Bulma 1's scheme machinery is the platform: its dark
lightnesses are the WCAG-calibrated defaults, and its `generate-on-scheme-
colors` contrast loop is the exact precedent for lifting `#0073dd`/
`#0000ff` — the ramp mirrors those numbers instead of inventing greys.
The chrome bands stay pinned (SHM-01: "the brand colours do not follow
the scheme"): the navbar's `#f5f5f5`/`#4a4a4a` and the footer's blue/
white are the legacy chrome in either scheme, and a light navbar over a
dark page is Bulma's own `.navbar.is-light` idiom.

**Alternatives.** Unpin the ink from `:root` and let Bulma's schemes own
it: correct, but it deletes the DD-062 legacy ramp (Bulma 1's dark ink is
221°-tinted, the demo's is neutral) and out-of-scope churn on a light-
only slice. A full brand dark palette (every accent re-tuned): the demo
has no dark mode to measure against (the legacy Aurelius is light-only —
verified in `.scratch/aurelius`), so every value would be invented; only
the ink that fails contrast is lifted, the rest of SHM-04 stays.

**Consequences.** The storybook switch previews a legible app; a future
theme-switch slice inherits the ramp. The webapp's `index.html` keeps
pinning `data-theme="light"` (SHM-01 untouched) — the dark ramp reaches
the app only through an explicit switch. Play tests cover the ramp on
the entity-card/breadcrumbs dark composition stories; the light ramp is
unchanged (SHM-03's measurements stand).

### DD-069. The drawer is a new ui-lib component, not a Modal or a dropdown

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The settings panel opens in a new `Drawer` component in
`aurelius-atlas-ui`: a fixed right-side panel with a scrim, styled with custom
SCSS on Bulma tokens, carrying the `Modal`'s dismissal set (`active` as
`model()`, backdrop click, close button, Escape → `dismiss()`).

**Reason.** The user chose a side drawer for the settings panel, and Bulma
1.0.4 ships no drawer — `sass/elements/` has no such layer; the overlay
primitives are modal and navbar-dropdown. A drawer keeps the page content
visible beside the settings (the point of a side panel), which the centred
modal does not. Building it on Bulma tokens (`--bulma-scheme-main`, the text
chain, the border ramp) makes DD-068's dark ink ramp apply to it for free.
The dismissal semantics copy the `Modal` because that component proved the
a11y pattern this repo accepts: the backdrop is the pointer path, Escape on
the dialog is the keyboard path (the S1077 precedent in `modal.component.html`).

**Alternatives.** Reuse `Modal`: centred, occludes the page — the user's
choice ruled it out, and a right-docked modal fights Bulma's centred
`.modal-content`. A Bulma `has-dropdown` under the gear (the navbar idiom
today): cramped for radios, selects and toggles, hover-open (unusable on
touch), and it dismisses on every outside click the panel needs to survive
while a control is used. `@angular/cdk`'s drawer/overlay: a new
third-party dependency the purity gate and the ui-lib's zero-overlay-dependency
standing do not justify for one panel.

**Consequences.** The drawer owns its focus choreography (focus moves to the
panel on open, Escape returns it to the opener) — the `Modal` defers this to
its buttons, the drawer has a focusable form. The component is generic
(`title`, projected content), so the 7.6 filters/detail side panels can reuse
it. Stories carry an OnDark variant like every overlay the lib ships.

### DD-070. The telemetry switch stops exports immediately and starts them on reload

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The telemetry setting is honoured asymmetrically: switching it
**off** calls the OpenTelemetry providers' shutdown (`trace.disable()` + the
meter provider's shutdown) so exports stop within the session; switching it
**on** stores the preference and takes effect on the next reload, and the
panel says so.

**Reason.** The SDK is assembled at bootstrap in `app.config.ts`: the
`NodeTracerProvider`/`MeterProvider` are built in `createAureliusOpenTelemetry`
provider factories and the propagation interceptor is registered with
`withInterceptors` — both are startup-time DI, not swappable at runtime.
Stopping is the one direction the SDK API supports cleanly (`shutdown()`
flushes and closes the exporter); starting needs a provider re-assembly DI
will not do mid-session. An honest one-way switch (off now, on after reload,
stated in the panel) beats a switch that silently does nothing until restart
in both directions.

**Alternatives.** Auto-reload the page on toggle: jars the user out of their
session (lost form state) to start telemetry — the least urgent reason to
reload. A runtime gate via a no-op proxy exporter/provider registered at
bootstrap: the real machinery the SDK hides (span processors, batch
exporters, the interceptor's active-span context) then runs with the toggle
off, which is exactly what "telemetry off" promises not to do. No toggle at
all: the user asked for one, and an off switch for browser telemetry is a
reasonable privacy affordance.

**Consequences.** The stored preference is read by `app.config.ts` before the
providers are built (off at bootstrap = providers are never created — not
even the no-op path). The panel's reload hint is a rule with a test (SPL-11).
A served-app scenario (no OTLP requests after off) lands with the 7.10 e2e
set that serves the app.

### DD-071. The theme choice is applied pre-render; SHM-01's light pin is superseded by a light default

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The `data-theme="light"` pin on `index.html`'s root is removed.
A two-line inline script in the head applies the stored theme before the
first paint: the stored value (`light`/`dark`) is written, `auto` (or no
stored key with no value) **removes** the attribute and — because the app's
default must stay light (SHM-01's promise) — the script writes
`data-theme="light"` when nothing is stored. `DarkModeService.initialize()`
reads the same attribute, so the service and the page agree from the first
frame.

**Reason.** `DarkModeService.initialize()` treats the root attribute as the
highest-priority explicit choice; the 7.12 pin therefore outvoted a stored
`dark`/`auto` on every load — the switch could not survive it. The pin can
also not just move to runtime service code: Angular bootstraps after CSS,
so a service effect paints one frame in the wrong scheme (the classic
dark-mode flash). The inline script is the standard pre-render pattern and
keeps SHM-01's user-visible promise exactly — no stored choice ⇒ light under
any OS preference — with the default in the script + the service, not in
static html. 7.12's scope note anticipated the switch ("a later slice flips
the `data-theme` attribute"); this is that slice superseding the mechanism,
not the promise.

**Alternatives.** Keep the pin and let the service overwrite it after
bootstrap: not a flash problem only — `initialize()` returns the pin as the
user's explicit choice, so stored Dark is ignored outright. Drop the light
default and let no-stored-key follow the OS (Bulma's native behaviour):
breaks SHM-01 — the legacy app is light-only and the demo renders light
under a dark OS; the pin's promise was measured, and 7.12's specs assert it.

**Consequences.** SHM-01's row in 7.12 gains a supersede note (the promise
stands, the mechanism moves). The service's `updateDataThemeAttribute` must
**remove** the attribute for `auto` rather than write `data-theme=""` — the
empty attribute does not match Bulma's `:root:not([data-theme])` OS path, so
Auto would never follow the OS. The 7.12 spec's html-attribute assertions
keep passing because the script writes `light` when nothing is stored.

### DD-072. Settings are a facade over one owner service per category

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** `SettingsService` (webapp) is a thin facade: it exposes each
setting's signal and setter and delegates to exactly one **owner** service
per category — theme → `DarkModeService` (the ui-lib's existing owner),
language → `LocaleNavigationService`, time zone → `TimezoneService`, page
size → `PageSizeService`, telemetry → `TelemetryService`. Each persistence-
backed owner stores through a shared `UserPreference` helper (signal +
synchronous `localStorage` read at construction + write-through), which is
the only code touching `localStorage`.

**Reason.** The user asked for the `DarkModeService` facade pattern to extend
to the other categories. It generalises what the lib already does:
`DarkModeService` is the sanctioned persistence owner and the AGENTS.md
exception to the dumb-component rule, and it owns its key (`data-theme`).
One owner per key keeps a single writer per storage slot; the panel consumes
only the facade (one injectable, one test double); the bootstrap providers
(`DATE_PIPE_DEFAULT_TIMEZONE`, the telemetry gate) read the owners directly, which is
legal because `UserPreference` reads storage synchronously at construction.
The seam for the promised server-side persistence is the helper's internals
(GET/PUT behind the same signal API) — owners, facade, and panel do not
change then.

**Alternatives.** One monolithic `SettingsService` owning every key:
it would write `data-theme`, a key `DarkModeService` already owns — two
writers, and the webapp would fork the theme mechanism the lib ships. Panel
injecting the owners directly: no facade to double in tests, and every
setting change touches the panel's imports. A global signal store/ngrx: the
webapp has no global-store convention (AGENTS.md: feature state lives in
signal stores under the feature folder).

**Consequences.** The `SPL-10` rule is testable per owner: each owner is the
sole writer of its key. Adding a setting = one owner + one facade member;
the 7.6/7.7 screens consume owners directly (a table reads
`PageSizeService`, not the facade) — the facade serves the panel, owners
serve consumers. Server-side sync, when it lands, adds the PUT path in
`UserPreference` and a hydrate step at bootstrap (DD-073).

### DD-073. Settings are browser-scoped localStorage; server-side persistence is the follow-up slice

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The v1 settings store in `localStorage` under `data-theme`
(the theme's existing key) and `aurelius-atlas.settings.{timezone,pageSize,telemetry}`.
They are user-experience conveniences, scoped to the browser: nothing that
identifies a user, grants a permission, or belongs to the catalogue is kept
there. Server-side per-user persistence (Keycloak profile attributes, or the
Atlas session settings ADM-05 exposes) is a deliberate later slice behind the
`UserPreference` seam (DD-072).

**Reason.** The user chose localStorage for now and named Keycloak's user
profile as the server-side direction. The two server channels are not ready:
`GET /atlas/admin/session` (ADM-05) publishes settings but Atlas 2.4.0 has
no settings-write endpoint, and Keycloak profile writes need admin
token-roles — both are increments of their own. The privacy line matters for
DD-070's off switch: a browser-scoped store keeps the promise simple (off
means this browser sends nothing; nothing was sent about a user).

**Alternatives.** Cookies: sent to the server on every request for data the
server never reads. IndexedDB: asynchronous for values this small — the
synchronous bootstrap read SPL-07/SPL-11 need becomes an ordering problem.
Server-first now: blocks the panel on the 6.1 identity + a new endpoint,
putting a UI feature behind API work the user scoped later.

**Consequences.** DV-12 records the panel as a deliberate addition (Atlas has
none). A shared browser shares its settings — acceptable for v1, named for
the server-side slice to fix. Key names are documented in this entry so the
server-side slice can migrate them.

### DD-074. The drawer animates in and out; the layer's life is the exit animation's

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The `Drawer`'s panel slides in from the right edge over a
fading scrim (200ms, ease-out) and plays the reverse on close (ease-in,
`forwards`). Dismissal is state-first: `active` flips to false at once —
focus restoration, the caller's binding, and `cancelRequested` all land
immediately — and a `closing` signal keeps the layer rendered for the exit
pass; the panel's `animationend` (name-checked, so content animations
bubbling out of the projected body are ignored) drops it. Reopening
mid-slide-out clears the flag and the enter animation plays on the layer
that never left. `prefers-reduced-motion: reduce` shortens the animations
to 0.01ms; it does not remove them. Plain CSS keyframes — no
`@angular/animations`, and the component stays a dumb
`aurelius-atlas-ui` component (its AGENTS convention): the animation is
styling, not service work.

**Reason.** The user asked for the drawer to be animated. A `@if (active())`
template removes the DOM on close, so an exit animation needs a second
signal to keep the layer alive; keying the layer's life to the exit
animation's end is the CSS-native answer (the same lifecycle modal
libraries use). State-first dismissal keeps every rule SPL-02 states —
focus returns on close, `active` is false on dismissal — true _on close_,
not 200ms later; tests and consumers never wait on motion. 0.01ms rather
than `animation: none` under reduced motion because the exit's
`animationend` is what removes the layer: no animation, no event, a
drawer stranded on screen.

**Alternatives.** `@angular/animations`: a new dependency for the lib's
peer set and a second styling system, for two translate keyframes. Enter
only (keep `@if (active())`): simplest, and the snap-out reads as a bug
next to the slide-in. Hiding with `visibility` after a timer: timers
instead of the animation's own event, to race on every speed. Transition
on a class toggle: keyframes were needed because the enter plays on
element creation, where a transition has no start state.

**Consequences.** Focus restoration fires when `active` flips, so it lands
before the slide-out finishes — the panel animates out behind the focus
move; acceptable, named. The drawer spec drives `animationend` manually
(jsdom runs no CSS animations, and ships no `AnimationEvent` constructor).
Storybook's polling `expect` absorbs the 200ms close in the `play()`
functions. Keyframe names are prefixed `aurelius-drawer-`; the exit's
`animationend` is matched by containment, because Angular's emulated
encapsulation decorates keyframe names (computed
`_ngcontent-ng-…_aurelius-drawer-out`), not by prefix.

### DD-075. The drawer styles itself with fallbacks; Bulma's modal tokens are `.modal`-scoped

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The drawer's head/body padding, scrim colour and z-band keep
the Bulma token names for the override seam, and add explicit fallbacks:
`var(--bulma-modal-card-head-padding, 2rem)`, a scrim spelled from the
root-scoped scheme ramp at Bulma's 0.86 alpha, and the existing z fallback.
The drawer ships no padding of its own beyond this.

**Reason.** The user asked for edge padding; measuring the live drawer
showed the real bug: Bulma 1 emits `--bulma-modal-*` on the
`.modal`/`.modal-card-*` selectors, not on `:root` — verified in
`node_modules/bulma/css/bulma.css` — so outside a modal the tokens are
undefined: bare `var(...)` collapsed the head/body padding to 0 and
painted the scrim transparent. A plain literal padding would fix the
symptom; the `var(name, literal)` form keeps the brand's override seam
(open the drawer's tokens to the brand ramp later) and documents the
scope trap.

**Alternatives.** Import Bulma's modal layer in the brand (it drags the
whole component's CSS for three tokens). Define the tokens on `:root`
in the brand (duplicates Bulma's values, and a brand-wide change to fix
one component). Plain literals (loses the seam).

**Consequences.** The drawer's computed padding is 2rem; the scrim is
Bulma's modal-background recipe, dark-ramp aware (DD-068). The fallbacks
drift if a future Bulma changes the modal defaults — named, low-risk,
the component owns its layer (DD-069).

### DD-076. The Appearance picker is the ui-lib Select; the Select gains `searchVisible`

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The settings panel's Appearance section is the ui-lib
`Select` with `searchVisible` off — the section heading is the control's
own label, the rows are the three modes (Auto first, selected). The
Select gains the `searchVisible` input (default on: the Aurelius modal
opener stays for repository pickers); off, the addons layout collapses
with the button and the field is a plain labelled dropdown.

**Reason.** The user asked for the component library's select. The
Select is the lib's only select, ported from Aurelius with a search
button welded in; an input is the minimal honest generalisation — the
button is the legacy `activateSearchModal` affordance, not part of
"pick one of three themes".

**Alternatives.** Keep the radios (rejected by the user). Native Bulma
select markup, as the Time zone section uses (duplicates the lib's
control, and loses the UIC-14 label pairing). Fork a plain select
component (a second select in the lib, no).

**Consequences.** The panel's `.select select` list gains a first
element (specs index it). The Select gains a `NoSearch` story. A
selected row can never be cleared — the placeholder is `hidden` and
`setTheme` ignores null; the panel always has a theme.

### DD-077. About shows one version; the server is not fetched

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The About section shows the app name and the app version
from the runtime config, and nothing else. The `getVersion` fetch and the
server line are removed, with them the `shell.settings.server` and
`shell.settings.serverUnavailable` strings (catalogues: 533 units).

**Reason.** The user set the rule: app and server always carry the same
number — one Nx release cuts the workspace, and the image labels derive
from it — so the server line can only echo the app version, and a
version the panel has to fetch can only be _shown_ to differ while the
fetch is in flight. Removing the row removes the question.

**Alternatives.** Show the fetched server version (states a known-true
equality, and adds an ADM-01 call per open). Show "app (server: same)"
(noise). Keep the fetch, show it on mismatch only (two code paths for a
state the release strategy rules out).

**Consequences.** The panel's construction fetch is `getSession` only
(SPL-07 keeps its degradation test). ADM-01's endpoint stands on the
server; the panel is no longer its consumer, and DV-03's parity scope
does not change.

### DD-078. The settings panel is a routed overlay in the `drawer` aux outlet

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The `drawer` named outlet at the app root carries routed
overlays (SPL-14). The settings panel is a route (`(drawer:settings)`):
the header gear is a `routerLink` to it — with the panel open the link
targets the URL it is on, and the router cancels that duplicate
navigation, so the gear is a no-op; dismissal (backdrop, close, Escape)
navigates the segment away. The component opens at construction
(`active` starts true) and loads its chrome data then. Future drawers —
an alerts drawer is named — get their own outlet segments and compose in
the URL: `(settings:…)(alerts:…)`.

**Reason.** Switching language is a full-page navigation into the locale
tree (DD-039), and the user wants the reload to land on the same page
with the settings open. The URL is the only state that survives a full
reload, and named outlets are Angular's mechanism for putting an
overlay in the URL — the segment rides `localeHref()` untouched, so the
requirement falls out. (The term: auxiliary routes.)

**Alternatives.** A query param (`?settings=1`) — works, and invents a
parallel navigation system outside the router; the outlet form is the
router-native one, composable, and the Angular idiom. localStorage
"open" flag — reloads open, survives everything, unbookmarkable and
sticky. A service + effect — doesn't survive the reload, which is the
requirement.

**Consequences.** Closing destroys the panel, so the drawer's exit
animation (DD-074) is not awaited there — accepted, named; the DD-074
lifecycle remains for the drawer's own API (`close()` on a non-routed
drawer), and the enter animation plays on open, including after the
locale reload. Dismissal is destructive (no panel state to keep — the
facade owns it, DD-072). Deep links work: visiting
`/search/browse(drawer:settings)` opens the panel on that page. The
`serverUnavailable` fallback and the `open()` API are gone; the panel
spec drives the component directly (as the routed-component test
pattern prescribes).

### DD-079. Settings-drawer polish: lit gear, scheme-following band, Browser-default picker, `.label` headings

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** Four fixes from the user's review of the open drawer.
(1) The gear carries `routerLinkActive="is-active"`: Bulma styles
`a.navbar-item.is-active`, and the active state keys off the `drawer`
outlet segment — the gear is lit exactly while the panel route is open
(SPL-01). (2) The outlet band drops `has-background-light` for Bulma's
bare `.has-background` (`var(--bulma-background)`): the legacy light in
light mode, the dark scheme's surface in dark (SPL-05's theme switch
now repaints the page, not just the drawer). SHM-05's pinned chrome
bands are unchanged. (3) The time-zone picker binds the stored zone
directly — `null` when unset selects the "Browser default" option
(SPL-07); the browser's resolved zone is no longer injected into the
select, where it rendered blank whenever it was not one of the server's
ADM-05 ids. (4) Every settings section heading is a Bulma `.label` —
the form-controls guide's field label (the guide the user linked) —
replacing `.menu-label`; the Appearance heading already renders as
`.label` through the Select, so all six now match.

**Reason.** The gear gives no affordance that it owns the open panel.
`has-background-light` is Bulma's fixed light colour family, not a
scheme role, so a dark page kept a light band. A select whose value
matches no option renders empty — the "Browser default" option is the
honest display of an unset zone, since its effective value _is_ the
browser's, applied at the date pipe. `.menu-label` is the sidebar-menu
heading (uppercase, small, weak); inside a form column it reads as a
different component than the `.label` the Select shows.

**Alternatives.** (1) A signal shared header→panel — state the URL
already carries. (2) `has-background-scheme-main` — the body colour,
leaving no surface distinction from the footer band; `--bulma-background`
is Bulma's surface role and matches what cards/tables sit on. (3) Add
the resolved zone as an extra option — the list is the server's
(ADM-05), and a local zone the server may not accept is a false
promise. (4) Keep `.menu-label` — the inconsistency the user flagged.

**Consequences.** The band's computed background follows the scheme
(verified live in both modes). `timezoneValue` narrows to
`string | null` — the same value the facade stores, making the panel a
pure pass-through. The `.label` heads are normal-case and stronger
ink; the panel scss comment follows. No string ids change.

### DD-080. The navbar follows the scheme: the dark slate band

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** In dark mode the navbar leaves the pinned light band
(SHM-01's "the brand colours do not follow the scheme", for the navbar
only) for a neutral slate, #72757d — hsl(224, 4%, 47%), the faint cool
cast of $blue. The bar's chrome composes on the slate: ink #000 (5.6:1),
hover/active the light plate (Bulma's +8%/+12% deltas, DD-063's deltas
inverted for a dark band), the gear's `is-active` the white plate
(DD-063's selected pair), the `is-dark` Documentation button's
ink/border black (its pinned #363636 rides at 2.5:1 on the slate). The
account dropdown keeps Bulma's scheme composition. The footer stays
pinned (SHM-07 — blue/white reads the same in either scheme). The logo
keeps its brand size in both schemes.

**Reason.** The user's review: dark mode kept a light navbar. The
binding constraint is the logo, measured from the PNG: its wordmark is
navy `#151487` at ~11% lightness, so every dark surface (the scheme's
`#1f2229`, the brand blue `#0073dd`) collides with it (1.0–1.3:1) and the
wordmark's WCAG-3:1 floor (graphics) sets the bar's ceiling at ~47%
lightness. The slate is the darkest background that keeps the mark
legible (3.1:1); the user chose it over the brand blue, then over the
first bluer/lighter cut — 4% saturation, one step under the floor.

**Alternatives.** Brand blue #0073dd (the footer's blue — wordmark
3.5:1, the user declined: reads as a blue bar). A true dark band
(#131a26) with a light logo variant — the proper dark-mode look, needs
a design asset; the seam is this mixin's token block. Keeping the navbar
pinned light (the status quo the user rejected). Darkening the slate
below 47% (the wordmark falls under 3:1).

**Consequences.** The navbar tokens are a brand-theme block on both of
Bulma's dark hosts (0,2,0, out-cascading the light `.navbar` pins). The
logo's navy/cyan palette is now load-bearing across schemes: a future
rebrand or light-variant asset replaces this decision (supersede, don't
edit). The light band is untouched (SHM-05 stays the light-mode chrome).

### DD-081. Settings headings are the controls' accessible names

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** Every settings control's `.label` heading is its
accessible name (the Bulma form guide's labelled control, the guide
DD-079 adopted): Time zone and Page size are `label[for]`/`id` pairs on
the native selects, Telemetry on the checkbox (the label moves from the
old wrapping `.checkbox` — the checkbox is a plain control on the
section grid), Appearance rides the ui-lib Select's own
`label[for]`/`aria-labelledby`, and the language links — not a form
control — are a `role="group"` labelled by their heading. About is a
section title, not a field, and is not associated.

**Reason.** The user's review of the DD-079 layout: the headings looked
right and were wired to nothing — clicking a label did nothing, and a
screen reader announced bare "combobox"/"checkbox". The Bulma form
guide the headings already follow prescribes the association; DD-079
adopted the shape and left out the link.

**Alternatives.** `aria-labelledby` everywhere (works, and the
`label[for]` is the HTML-native form the guide shows; the group and the
Select use it where no single labelable control exists). Keeping the
wrapping `.checkbox` label (an accessible name, and the Bulma checkbox
idiom — rejected: the guide's stacked label/field shape is what DD-079
just standardised on, and the checkbox label had no text to wrap).

**Consequences.** Fixed ids (`settings-timezone`, …): the panel is a
singleton route, so collision is impossible. The checkbox loses
Bulma's `.checkbox` hover affordance (the label click replaces it). The
panel spec asserts each pair.

### DD-082. The active locale is filled with the Aurelius blue

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The active locale link in the settings drawer's Language
section is a solid Aurelius-blue plate (`#0073dd`, white ink): the
panel scss fills the `is-selected` button the template already marks
(SPL-06). The pair is pinned, not scheme-following — the same
`#0073dd`/white the footer's brand block pins (SHM-07).

**Reason.** The user's review: "For the locales can we ensure the
current locale is highlighted?" The SHC-04 port carries the
`is-selected`/`aria-current` marking (7.12), and the template binds
it — but Bulma 1 styles a selected button with nothing (verified:
`.button.is-selected` has no rule, and the rendered active and
inactive links measure identical ink and plate). The marker is
semantic, invisible; the highlight the user asked for is the missing
visual half of it.

**Alternatives.** `is-active` (Bulma composes an `l-delta` from it —
a shadow on the plate, not a fill; the same non-result). A check-mark
icon on the active link (a decoration needing a string and an id on
both locales, for what a fill says for free). `var(--bulma-link)`
(the scheme-following accent — rejected: DD-068 lightens it to 73%
in dark, and white ink on a 73% light-blue fails; the pinned pair
holds 4.6:1 in either scheme).

**Consequences.** `.buttons.has-addons` keeps the links joined, and
the fill joins them visually as a segmented control: the active plate
is blue, its neighbours stay plain. The panel spec asserts the
`is-selected` class on the active link (the scss fill itself is a
style, not a testable DOM fact).

### DD-083. The alerts store groups by a quiet window

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** `AlertsService` is the app's one alert door (ALR-03): an
in-memory signal list of groups, newest first, capped at 30 (oldest
evicted). Grouping is a quiet window — an alert whose key (severity +
source + message) matches the **newest** group's merges into it while
the window is open (60 s from that group's last alert: `count` +1,
`lastSeen` moves); after the gap, a new group starts. A `newGroups`
counter counts arrivals, not alerts (merges do not move it — ALR-02a's
ring signal). The clock is an injectable token (`ALERT_CLOCK`), not
fake timers.

**Reason.** The user's review of the plan: "Sometimes the same error
occurs multiple times in quick succession. I'd like to be able to group
notifications so the user doesn't get overloaded." A flapping endpoint
fails per retry — ungrouped, one drawer row per failure. Merging by key
shows a burst as one row with a count (×7, 14:20–14:22). The window
bound keeps history honest: merging session-wide would weld an hour-old
error to a new burst of the same message; after the gap the old burst
is context, and the new one needs its own row. The newest-only merge
keeps the store append-only (a burst ends when anything else arrives —
the row's count is the burst's, not the message's total).

**Alternatives.** Merge into any group with the same key, session-wide
(one row per message forever — the user's phrasing "in quick
succession" named a window, and history loses its timestamps).
Timestamp-bucketed grouping (fixed 60 s bins split a burst at a bin
edge). A capped ring of raw alerts, grouped at render (the store then
knows nothing, and every consumer re-derives the same groups; the
bell's ring needs arrival counting, which raw-alert caps lose).
`fakeAsync`/`tick` for the window (the token clock makes the window a
constructor argument of the test, no zone patching under zoneless).

**Consequences.** In-memory: alerts die with the tab — session events,
not preferences; the persisted lane is DD-073's and this stays out of
it. `AlertGroup` (the ui-lib model, ALR-10) is the store's public row;
the merge-key `source` is internal to the store. A 60 s constant;
raising it is a one-line change. The cap's eviction is silent (alerts
are cheap, the drawer is not an archive).

### DD-084. The app's ErrorHandler chains: alert, then trace

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The root `ErrorHandler` is `AlertsErrorHandler`,
composing the trace handler: record the uncaught error as an `error`
alert (source `app`), then delegate to `AureliusTraceErrorHandler`,
which keeps its own delegation to Angular's default (ALR-04).
Recording is wrapped in try/catch — alerting must never break the
error path. The composition is a factory in `app.config.ts`
(`useFactory: alertsErrorHandlerFactory`), not a class the app
subclasses.

**Reason.** SHL-14's telemetry (7.1) owns the root handler; the alerts
drawer (ALR-04) needs the same event. Composition keeps both promises
exactly: the trace handler sees the untouched error, the user sees the
alert. The order is record-first: a delegate that throws (the default
handler re-throws in dev mode) must not cost the user the alert.

**Alternatives.** Subclass the trace handler (`super.handleError` then
record — the user's alert would depend on the delegate surviving, and
the app inherits a library's constructor). A second `ErrorHandler`
provider (DI: one token, one value). `provideEnvironmentInitializer`
with `window.addEventListener("error")` (the listeners are the DI
handler's input, `provideBrowserGlobalErrorListeners` already wires
them; a second listener double-records).

**Consequences.** Every uncaught error is now user-visible — noisy
runtime bugs surface in the drawer (the intent, ALR-04; the store's
window, DD-083, absorbs repeat spam). The trace path is unchanged: the
`app.config.spec.ts` provider-set specs keep SHL-14's shape.

### DD-085. The HTTP reporter: 5xx and network failures on /api

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** A functional interceptor, last of the three on
`provideHttpClient`, watches the response and reports the reportable
set (ALR-05): `5xx` responses and status-0 network failures on URLs
matching `/api/` — the bearer interceptor's pattern (APC-06), not a
hardcoded prefix. The message names method, path, and status (`no
response` for status 0) and rides the server's plain `error` message
when it sends one. The interceptor reports and re-throws; the caller's
observable is untouched. 4xx is silent.

**Reason.** The user asked for "any app error messages if they occur"
— a failing catalogue call is the app's most common real error. The
`5xx`-plus-network cut is the plan's standing default, accepted: a 4xx
is a client-side correction the calling feature already handles (its
form, its not-found view), and reporting it would train users to
ignore the drawer. The report is the drawer's, not the caller's:
7.4+ features keep their own `onError` UX; DD-083's window folds the
pairs into one row.

**Alternatives.** Per-call `onError` reporting at each feature (every
slice re-wires it, and un-wired calls go missing). Reporting 4xx too
(the noise the plan asked about; Atlas proxies 404 through the 6.x
ramp). A `HttpInterceptorFn` on the data-access library (the SDK is
feature code's door; the app owns chrome-level alerting — the
interceptor sits in the webapp's provider chain, where the bearer and
OTLP interceptors sit).

**Consequences.** A failed `/api` call is visible twice when the
feature also shows its own error (accepted: the drawer is the
collected record). The status-0 case cannot tell an offline browser
from a refused connection — one message covers both.

### DD-086. The bell: severity badge and ring, one outlet

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The header bell is the gear's pattern (DD-078, DD-079):
a `navbar-item` routerLink to `(drawer:alerts)`, `is-active` while
open, and the one `drawer` outlet swaps the settings panel and the
alerts drawer (ALR-01). It carries the ui-lib `Badge`: a presence dot,
visible while the store is non-empty, coloured by the highest severity
present — presence, not a count, no read-state (ALR-02). The dot is
`aria-hidden`: inside the bell's link it would join the link's
accessible name. New groups animate the bell, a ~650 ms Web Animations
pendulum swing on the icon (the effect watches `newGroups`, so a burst
rings once, ALR-02a); `prefers-reduced-motion: reduce` skips it.

**Reason.** The user asked for a badge "to indicate notifications are
available", the "color of the highest severity notification available",
and "a little animation on the bell whenever an alert becomes
available" — the ring is the arrival, the dot is the presence, the
colour is the worst. Presence beats a count: the store caps at 30 and
merges bursts, so a count badge overflows its own model. The
single-outlet swap is DD-078's mechanism with a second segment (the
URL owns which drawer is open; the locale switch's reload keeps it,
SPL-14's mechanic reused). The ring is WAAPI, not a CSS class: the
animation restarts cleanly mid-swing (a class re-trigger needs a
reflow hack); the pivot (`transform-origin: top center`) is scss on
the icon, the keyframes are the component's.

**Alternatives.** A count badge (Bulma's `.tag`, overflow-prone,
read-state invented for it). An unread-only dot (the user's word was
"available", not "unread"). A CSS `@keyframes` class toggle (the
re-trigger hack; reduced-motion media queries alone cannot skip a
JS-driven replay). `@angular/animations` (not a dependency; the zoneless
app has no animation renderer, WAAPI is the browser's).

**Consequences.** The dot's contrast on the navbar bands is the
Badge's problem (its ring, DD-087's note); the header keeps the
DD-080 slate. The dot is a component, not Bulma's `.badge` idiom (the
lib has no Bulma DOM assumptions). A future read-model (server events,
6.x) adds a source to the store, not a new door.

### DD-087. AlertList and Badge are ui-lib presentational components

- **Status:** Accepted (the `clearAll()` half of the contract superseded by DD-088)
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The feed and the dot live in `aurelius-atlas-ui` as
presentational components (ALR-10): `AlertList` renders a
caller-supplied `AlertGroup[]` (the model the lib exports — the row's
shape is presentation vocabulary) and emits `dismiss(id)`/`clearAll()`;
`Badge` wraps content, shows a severity dot on `visible`. Labels are
inputs with English defaults (the `Drawer.ariaLabel` pattern), so the
lib keeps no translation dependency and the app passes `@@shell.alerts.*`
strings (ALR-08). The store, the window, and the routing stay app-side.

**Reason.** The user: "let's ensure we make a reusable ui component
for alerts." The feed has a second consumer by the plan's own logic
(7.6+ feature slices push alerts through the same store, and the
drawer is the product's surface); the dot generalises to any nav item.
The lib's rule is the same one `Drawer` keeps (DD-069): Bulma-shaped
presentational markup, state in the caller. The lib's chrome-strings
lane (DD-047: legacy dictionary paths) has no alert keys to reuse —
these are Aurelius's own strings (DV-13) — so the inputs carry
defaults and the app's catalogue owns the translations; the XLIFF
gate (SHL-08) and the purity gate (DD-048) stay app-side, the lib
stays service-free (its AGENTS.md convention).

**Alternatives.** App-local components under `src/app/alerts` (not
reusable — the user's ask). A smart `AlertsDrawer` in the lib that
injects a store (the lib owns no app state, no xlf dependency).
`model()` for the alerts array (the list never edits rows; dismiss is
an event, not a two-way value).

**Consequences.** The `AlertGroup` type is public API of the lib
(`src/index.ts`). The stories ship per UIC-15's bar (visual regression
covers the feed and the dot). The badge's ring is Bulma-token ink
(`--bulma-navbar-item-color`, currentColor fallback) — a future non-
navbar host keeps a visible edge without a new input.

### DD-088. The chip's pinned pair; Clear all in the drawer head

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** Two live-review fixes to the alert feed (ALR-06, ALR-07):
the burst chip's pair is pinned — `#f5f5f5` plate, `#363636` ink — not
Bulma's `tag is-light`; and the "Clear all" button is a content action
in the drawer's head, not part of the feed. The Drawer grows a
`drawer-actions` projection slot between the title and the close button
and AlertList loses its `clearLabel`/`clearAll` — clearing a store the
list does not own was the list's borrowed business (DD-087's
presentational rule).

**Reason.** The user's review of the live drawer: "the counter text is
not visible on the white background" and the "clear all" button
"will become buried" on a long feed — "let's keep it above the
notifications". The chip's invisibility is a scheme trap, measured: the
brand pins the `light` colour pair at `:root`, outside Bulma's scheme
machinery (SHM-04, so the chrome colours survive), while Bulma 1's dark
theme re-pins `light`'s invert to a scheme-following ink — the
`is-light` tag composed the brand's white plate under dark-mode white
ink (white-on-white). The pinned `#f5f5f5`/`#363636` pair is the
footer's idiom (SHM-07): the same marker in either scheme, 9.3:1. The
first fix placed Clear all above the rows inside the scrolling body
(DD-088's first pass, unit-tested); on review the head is the stronger
answer — the body scrolls, so the hatch must ride the sticky head.

**Alternatives.** Pin `light-invert` in the brand's `dark-ink` ramp
(fixes the tag and every `is-light` surface app-wide — rejected as
wider than the bug: DD-068's ramp re-pins the ink chain Bulma itself
adapts; `light` is a colour pair SHM-04 pins deliberately, and
dark-adapting it reopens SHM-01's promise). A severity-coloured chip
(the row is already severity-coloured; the chip is metadata, not a
second signal). Clear all above the rows inside the body (the first
pass: on a long feed the drawer body scrolls, taking the hatch away —
rejected on review). A `clearLabel`/`clearAll` on AlertList kept "for
reusability": a feed that owns a store-clearing button presumes the
store's shape — the head slot keeps the list the rows.

**Consequences.** The chip is the third pinned pair in the product
(footer SHM-07, active locale DD-082, chip DD-088) — the growing list
of surfaces that read the same in both schemes. The Drawer's head
anatomy (DD-069's, shared with settings) gains an optional slot: the
settings panel projects nothing and is unchanged. The alerts drawer's
tab order is close, then Clear all (both in the head), then the rows.

### DD-090 — The inbox bar: severity chips, read tracking, Clear all in the bar

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The drawer head's Clear all grows into a full-width inbox
bar (ALR-11): a new ui-lib `AlertInbox`, a Bulma `buttons has-addons`
group of one chip per severity (`is-expanded`, feed order, an empty
severity's chip included), each chip a filter toggle showing that
severity's **total** group count, a dot riding the DD-063 ramp while any
of its groups is unread, and the caller's Clear all projected into the
bar's end. The Drawer grows a second projection slot, `drawer-subhead`,
a strip between the head and the body; the bar rides it. Read tracking
lands with it (ALR-12): every `AlertGroup` carries `read`; an arrival —
or a merge bumping a read burst — marks unread, and the panel's effect
marks every group read while the drawer is open (visible-is-read). The
bell badge answers unread presence in the highest **unread** severity's
colour, superseding ALR-02's store-top reading.

**Reason.** The user's ask: a bar showing the count per severity, each
severity a show/hide button, Clear all kept, "keep track of whether
notifications have been read", and the question of totals vs unread on
the chips. Totals won: the chips are filters, and a filter's number is
what it covers — unread counts on filter chips make the bar flicker
under reading (the chips zero out as the drawer reads the feed, the
turn the user is mid-reading through vanishes). Unread stays where the
attention question is asked: the bell dot, the row, the chip's dot.
Visible-is-read won over a per-row read toggle: the drawer is 28rem of
rows the user came to read; a list that requires marking each row read
is a queue, not a feed, and the merge-re-unreads rule means a returning
burst re-asks for attention on its own. Filter state is the panel's,
not the store's: the store's counts and the bell must answer with the
whole store, and a view filter is not data.

**Alternatives.** Chips showing unread counts (rejected above — the
number changes under the user's eyes as the drawer reads). Filter state
in the store (rejected: the bell's badge and the chips' totals must see
everything, and persistence of a view toggle is scope the in-memory
store does not have). A per-group read button (a queue; rejected).
`markAllRead` on close (rejected: the badge would stay lit while the
user is reading, and the ring/dot answers "has this been seen" — seen
means seen). Clear all staying in the head beside the bar (two fixed
strips stacked, the head's action orphaned from the bar it serves; the
bar is the feed's command strip — the hatch belongs at its end).

**Consequences.** The Drawer has two content slots, actions (head) and
subhead (the strip); the settings panel uses neither. The alerts
drawer's tab order is close, the three chips, Clear all, then the
rows. `AlertGroup.read` joins the lib's model — the third field the
store owns and the list renders (ALR-10's vocabulary grows). The bell
badge goes quiet on open, which is the point: it asked for attention
and got it. DD-088's Clear all in the head is superseded in placement
(its "above the notifications" requirement keeps holding — the bar
never scrolls, DD-091); DD-088's chip-pair pinning stands.

### DD-091 — The drawer's body is the scroll container

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The Drawer's panel clips (`overflow: hidden`) and its
body scrolls (`min-height: 0`, `overflow-y: auto`): the head and the
`drawer-subhead` strip are fixed, the content scrolls under them
(DD-090's inbox bar, ALR-06/ALR-11's escape hatch).

**Reason.** Found while answering the user's question about a long
feed: the panel carried `overflow-y: auto`, so the whole drawer
scrolled — the head, title, close button, and DD-088's Clear all slid
away with the feed, and the "head does not scroll" clause ALR-06 cited
was not true. A drawer whose chrome scrolls away is a page, not a
drawer: the close control and the command strip must be reachable at
any scroll depth, and the inbox bar (DD-090) only pays off fixed.

**Alternatives.** A sticky head inside the scrolling panel (`position:
sticky`: works, but the scrim/panel geometry makes it fragile with the
slide animation, and the head's border composes over scrolled content
under the rounded corners). Two scroll containers (rejected: nested
scrolling on a 28rem panel is a trap).

**Consequences.** The settings panel's long body (six sections) now
scrolls under a fixed head — the intended drawer reading, and the
settings drawer's head carries its accessible name, so the panel
reading it never loses it. jsdom runs no layout, so the scroll split is
pinned by the spec's slot-placement test (DD-090) and the dev-server
check, not by a unit assertion.

### DD-092 — The inbox bar is one joined group, severity-coloured, ramp order

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** Three follow-ups to the inbox bar (ALR-11, DD-090), from
the user's review: every segment of the bar — the three chips, show
all, and the projected Clear all — is an `is-expanded` member of the
one `buttons has-addons` group (the actions join the joined bar, not
beside it); the chip order flips to the ramp ascending — `info`,
`warning`, `error`, calm to urgent (SEVERITIES, the countSeverities
output, and the chips all follow); and a shown chip rides its
severity's fill — the DD-063 pinned ramp (`#17a2b8`/`#ffc107`/`#dc3545`)
with the ramp's own inks (black on warning and info, white on danger),
not a single Aurelius blue. The unread dot rides the chip's ink
(currentColor) with a hairline ring in the chip's plate, and the fill
rides `is-sev-*` classes, not Bulma's `is-info`/`is-warning`/`is-danger`
button colours.

**Reason.** The user's review of the live bar. The ramp order reads a
bar the way the feed reads a stack — the urgent end lands beside the
feed's own newest-first errors, and a bar whose colour intensifies
left-to-right says "here is the dial". The severity fills carry the
bar's own information: a chip IS a severity, and one blue bar made the
chips interchangeable — the colours are the legend. Bulma's own
`.button.is-info`-family fills are scheme-following token tints, and
the brand pins `light` outside Bulma's scheme machinery (SHM-04): the
pinned ramp is the product's severity vocabulary (DD-063, DD-080) and
reads the same in both schemes, like the badge's dot and the footer's
pair. The dot flips to ink for the same reason DD-088 pinned the
count chip: a ramp-coloured dot on a ramp-coloured chip rides its own
colour and vanishes.

**Alternatives.** Bulma's `.button.is-info`/`.is-warning`/`.is-danger`
fills (scheme-following: the tints shift with the theme and collide
with the brand's pinned plates — DD-088's trap, measured once on this
very bar). Severity text ink on a plain chip, fill reserved (the user
asked for coloured buttons; an outline bar reads disabled, not
filtered). Ramp descending (error first, DD-090's first pass — kept
for the feed's rows, newest/urgest-first; the bar is a dial, not a
feed). The actions outside the group, flush right (DD-090's first
pass: two visual systems on one strip — the user asked for one joined
bar).

**Consequences.** `SEVERITIES` is the inbox's order and the bar is the
model's only consumer of it; the feed's order is the store's own
(newest first), untouched. The clear-all button's contract is "an
expanded member of the group" — the panel's button and the host test
carry `is-expanded`. The unread dot loses its severity classes
(`is-*`): the chip's face is the severity, the dot only marks news.
The bar's tab order is info, warning, error, [show all], clear all.

### DD-093 — The inbox bar is one height: the count badge is compacted

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** The inbox bar's count badge sheds Bulma's `.tag` height:
`height: auto`, `line-height: 1`, `0.125em` vertical padding — the
badge is compacted to the small button's scale, so every member of the
group (chips, show all, Clear all) computes to the plain small-button
height (ALR-11, DD-092).

**Reason.** The user's review of the live bar: Show all and Clear all
sat a step shorter than the severity chips. The cause was the badge,
not the actions: Bulma's `.tag` is a 2em control, and at the small
button's font that is 1.5rem of content inside a chip whose own line
is 1.125rem — the badge stretched its chip, and the group's flex
stretch dragged Show all and Clear all up to match. DD-092's
"is-expanded everywhere" made the step visible: joined segments
expose each other's heights.

**Alternatives.** `align-items: flex-start` on the group (leaves the
tall chips and short actions as they are, the join shows the gap). A
plain `<span>` instead of a Bulma `.tag` (the tag's plate/rounding is
the chip vocabulary, DD-088's pinned pair; the height is the only
part to shed). `is-normal` on the tag (the size modifiers are font
sizes, the `2em` height rides them all).

**Consequences.** The badge reads as the button's own metadata (a
superscript plate) rather than a control sharing the row. The unit
test pins the compaction's two properties; the equal height across
segments is the group's stretch, verified on the dev server.
