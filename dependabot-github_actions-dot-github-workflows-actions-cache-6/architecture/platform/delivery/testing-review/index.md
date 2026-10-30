# Test Suite Review (2026-10-24)

A workspace-wide review of every test suite: coverage, and — the part a coverage number cannot show — **representativeness**: do the tests cover the non-happy flows as well as the happy ones? The methodology and the layers are [Testing](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/platform/delivery/testing/index.md>); this page records what the review found and what it committed to build next ([DD-214](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/conversion/design-log/#dd-125-the-test-suite-review-of-2026-10-24-scopes-the-hardening-increments>)).

Coverage is reported to SonarQube, whose quality gate is the enforcement ([Testing](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/platform/delivery/testing/index.md>) step 6). This page carries measured baselines as reference figures, not as gates: the Python apps' from their generated `coverage.xml`, the frontend's from the `lcov.info` files under `coverage/`. The Python libraries' coverage is generated in CI only, so their figures live in Sonar, not here.

## The verdict, per project

Unit counts are test functions (an `it.each` expands to more at runtime); "non-happy today" lists the failure categories the suite already proves.

### Python apps

| Project | Unit | E2E | Lines | Non-happy today | Gap found |
| --- | --- | --- | --- | --- | --- |
| server | 29 + 11 scenarios | 4 + 11 scenarios (Chromium) | 98.6% | 400 / 404 / 409, ES-red readiness, store-unreachable boot | a store failure **mid-request** surfacing as a raw 500, not an Atlas body |
| data2model | 47 | 3 + 1 scenario | 92.1% | 401, body-shape 400, rule-ref 400 | view-edge selection and dynamic views are at 0% — a whole documented feature (DTM-06/07) untested |
| lineage-model | 56 | 5 + 1 scenario | 98.7% | 502 / 204, breaker open / half-open, fail-before-call (the best suite) | the transport-failure handler and the data2model-side fast-fail are the two uncovered lines |
| validate-entity | 25 | 4 + 1 scenario | 99.3% | 401, any-body-accepted (DV-67) | a mock app: 405 and oversized body only |
| fastapi-example | 102 | 21 | — | 401/403/503, SSE cancellation, breaker | template code: out of scope (see [Scope](<#scope-and-exemptions>)) |

### Python libraries

All 14 have offline suites; totals in brackets.

| Library | Tests | Note |
| --- | --- | --- |
| core | 97 + 4 e2e | domain rules are deep; no ES transport/5xx failure on the typedef document, no concurrent `_change` |
| model | 49 | coercion-rejection strength; no I/O by design |
| typesystem | 57 | hierarchy/rollback rules; lock-contention readers unproven |
| store-es | 31 + 7 e2e | infra is its core (red cluster, TLS, wrong password); request-timeout untested |
| auth | 20 | the reference issuer-failure suite; circuit recovery and JWKS TTL unproven |
| otel | 12 | mint-failure cache path good; concurrent `bearer()` untested |
| parity | 29 | exact-diff tests are excellent; transport raising mid-scenario untested |
| trace | 57 | the meta-library is its own best customer |
| server-client | 25 | typed errors on 4xx; **2xx-with-garbage-body untested per resource** |
| d2m / lm / ve clients | 18 / 14 / 12 | same shape; timeouts, 5xx, non-JSON 200 thin |
| sdk | 29 | `aws.py`, `msal.py`, `logger.py` have zero tests — template, out of scope |
| example | 16 | template, out of scope |

### Frontend

| Project | Unit | Stmts | Branch | Non-happy today | Gap found |
| --- | --- | --- | --- | --- | --- |
| webapp | 177 | 81.9% | 75.0% | the ALR layer: 5xx interceptor, error handler, silent 4xx | session lifecycle (logout, refresh, expiry) at zero; no out-of-order-response tests |
| ui | 191 (+73 stories, 57 `play()`) | 95.9% | 94.7% | keyboard/a11y dismissal, drawer reopen-mid-close | `dark-mode.component` spec is a create-check only |
| data-access | 46 | 97.0% | 97.3% | Atlas-error body on 404/400 (two services) | `admin.service` / `entities.service`: **zero** failure tests |
| observability | 58 | 88.5% | 67.2% | 3xx–502 spans, timeout, network | the branch hole is init/teardown; `opentelemetry-session.ts` has no own spec |
| frontend-example | 67 | 82.2% | 79.4% | debounce, search error | `app.config.ts initialize()` untested; editor save/delete never fail |
| webapp e2e | 32 × 3 browsers | — | — | unauthenticated redirect, collector 401s, deep link, unknown route | no server-500 → alert-panel proof; no logout round-trip |
| example e2e | 14 | — | — | proxy 401s, zero results | CRUD is happy-path-only against a DB-seeded stack |
| dashboard | 0 | — | — | the server e2e drives both dashboards in Chromium | accepted policy gap (DD-017, ADR 046) |

## The five-category matrix

Each suite scored per non-happy category: **●●** proven · **○** partial · **—** absent · **n/a** no such surface exists.

| Suite | Input &amp; validation | Business rule / auth | Infrastructure | Interrupted / async | Edge-case behaviour |
| --- | --- | --- | --- | --- | --- |
| server | ●● | ●● | ○ startup/readiness only | — | ○ |
| data2model | ●● | ●● auth | n/a stateless | — | ●● engine nulls |
| lineage-model | ●● | ●● auth | ●● the reference | ○ breakers; timeout missing | ●● fail-before-call |
| validate-entity | ○ accepts-any by design | ●● | n/a | — | ●● |
| core / typesystem | ●● | ●● deep | ○ write-failure, conflicts | ○ two-process e2e | ●● |
| store-es / auth / otel | ●● settings | ●● 401/403 matrix | ●● | ○ close/cleanup | ●● |
| client libraries | ●● model validation | ●● typed 4xx | ○ connect-only | — | thin |
| webapp | ○ form validation thin | ○ guards only | ●● the ALR layer | ○ preferences rehydrate | ○ a11y; no rage/double-click |
| data-access | ●● api-config | ○ | ○ two services | ○ | ○ |
| observability | ○ | ●● ingest-auth | ●● | ○ session-id reload | ○ branch hole |
| ui | ●● states | n/a | n/a | ●● drawer/modal | ●● |
| frontend-example | ○ editor never validated | ○ | ○ one service | ○ debounce | ○ |

The pattern: **infrastructure failures are a strength** (lineage-model, store-es, auth set the house style — fakes with recording seams, breakers proven through the management API). **The systematic holes** are: mid-request infra failures (server, core), business-rule states in the frontend (session lifecycle, RBAC-driven UI as 6.x lands), interrupted/async states (timeouts, out-of-order responses, concurrent callers), and the client libraries' response-shape failures (2xx-with-garbage, timeout vs connect error).

## Deferred backlog (ranked)

The review's priority was the frontend, the auxiliary APIs, and the client libraries. These findings are ranked backlog, not drops:

1. **Server spine — store failure mid-request** (surface as an Atlas-body 500, pin the parity of Java's behaviour; test `routes/types.py` against a raising `TypedefStore`, plus `typedef_store` refresh failure and concurrent `POST /typedefs`). Natural fit for the 2.x instance-store track.
2. **core** — ES transport/`ApiError` propagation on `ElasticsearchTypedefDocument.read`/`write`; two concurrent `_change` callers on one store.
3. **store-es** — `request_timeout` elapsing → `TransportError`; double-open race; `_major` of a `-SNAPSHOT` version.
4. **auth** — circuit recovery (half-open → closed), JWKS TTL expiry, malformed discovery/JWKS documents.
5. **otel** — concurrent `bearer()` mint under the lock; mint responses missing `access_token`/`expires_in`.
6. **parity** — the transport raising mid-scenario.
7. **dashboard** — stays as-is by policy; the server e2e is its net.
8. **Storybook gate** — `test-storybook` runs 73 stories as real Playwright tests but is opt-in; wiring it into the PR gate is an open call.

## Scope and exemptions

Template code stays out of the hardening scope (the trace check already excludes it; this review confirms the exemption):

- `aurelius-atlas-fastapi-example` — the template's example app; broad tests already, no parity contract, not trace-checked.
- `aurelius-atlas-sdk`'s `aws.py`, `msal.py`, `logger.py` and `aurelius-atlas-example` — template starting points (ADR 050 removed the slices that used them).
- `aurelius-atlas-dashboard` — vendored Apache Atlas source (DD-017); its regression net is the server e2e, by policy.

## The hardening increments

Spec-first, one PR each, per the conversion workflow ([ADR 051](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/051-the-conversion-proceeds-in-specified-increments/index.md>)):

| Increment | Scope | Rules named |
| --- | --- | --- |
| 8.6 Aux API failure hardening | lineage-model transport handler + d2m fast-fail + timeout; data2model view-edge/dynamic-view engine paths; validate-entity 405/oversized; negative parity scenarios | DTM-04/06/07, LM-07/11/12/13, VE-01/03 (existing) |
| 8.7 Client failure contract | 2xx-with-garbage per resource, timeout vs connect, 5xx ± Atlas body, token callable, pool under concurrency | CL-04/05/06, adds **CL-08** |
| 7.19 Frontend failure UX | data-access error matrix, observability branch hole + session spec, webapp session lifecycle, editor DOM validation, races | APC-04/05, ALR-04/05, SHC-05, SPL-11; example plain |
| 9.1 Resilience e2e | stop-the-container scenarios: server-500 → alert panel, upstream-down → 502, logout + deep link | adds **RSL-01…** |

## Reading the numbers

- App figures: `coverage.xml` as regenerated by `nx test <app> -c ci` (2026-10-24 run). Line coverage only — the Sonar gate also weighs new-code coverage, which is where a hardening PR is measured.
- Frontend figures: `coverage/<project>/lcov-report` from the Vitest runs; the webapp aggregate includes imported lib sources it never exercises — its own directories sit at 95–100%.
- Test counts drift with every increment; the trace report (`uv run aurelius-atlas-trace report`) is the live system of record for rule/function coverage.
