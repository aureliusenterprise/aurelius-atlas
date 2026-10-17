# Design Log

Technical decisions made during the conversion that are too implementation-specific for an ADR but must not be lost: storage layout, identifiers, query translation, test tooling. Business-level decisions are ADRs in [Architecture Decisions](<https://aureliusenterprise.github.io/chore-ci-setup-speedup/architecture/adr/index.md>).

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

### DD-001. Reference is Apache Atlas 2.4.0, and both dashboards are served

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-09

**Decision.** The behaviour to reproduce is that of the `release-2.4.0` tag of Apache Atlas. Both of its user interfaces are served unchanged at the paths Atlas uses: `dashboardv2` at `/` and `dashboardv3` at `/n/`. End-to-end tests cover `dashboardv3` in depth and `dashboardv2` with a smoke test.

**Reason.** Parity tests need one fixed reference ([ADR 048](<https://aureliusenterprise.github.io/chore-ci-setup-speedup/architecture/adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted/index.md>)), and 2.4.0 is the latest Apache Atlas release. Atlas 2.4.0 serves the classic interface at the root and the newer one under `/n/`, and each links to the other; serving both keeps every bookmark and link working at the cost of one more static build, whereas dropping one would be a visible deviation.

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

**Reason.** Yellow means every primary shard is assigned and all data is readable and writable; only replicas are missing. A single-node cluster, the development and small-installation case ([ADR 006](<https://aureliusenterprise.github.io/chore-ci-setup-speedup/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), is yellow as soon as an index has a replica. Reporting it down would make every single-node deployment permanently unready.

**Alternatives.** Green only: correct for multi-node clusters, unusable for single-node ones unless every index is created with zero replicas. A configurable threshold: one more setting nobody sets.

**Consequences.** Lost redundancy is not visible as a health failure; it is visible in the cluster metrics (ESD-06) and should be alerted on there.
