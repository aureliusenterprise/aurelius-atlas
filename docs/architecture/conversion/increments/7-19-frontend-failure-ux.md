# 7.19 Frontend failure UX

- **Status:** in progress
- **Pull request:** — (follows the review of 2026-10-24, DD-125)
- **Records:** DD-125 (the review that scoped this); cites 7.1, 7.3, 7.7, 7.14, 7.16, 7.17

## Scope

Test-completeness, no new rule ids (DD-125): the frontend's failure semantics
are stated (APC-04, SHL-02, SPL-03/04, SHL-14, DD-103) with unproven paths.
The review measured the frontend's systematic hole: only 7 of 71 webapp-side
specs assert an HTTP error, `admin.service` and `entities.service` have zero
failure tests, and the observability lib sits at 67% branch. This increment
closes the measured holes:

- `aurelius-atlas-data-access` — the **error matrix** for `AdminService` and
  `EntitiesService` (every method today answers success only): 4xx with the
  Atlas body through `atlasErrorFrom`, 5xx, and the status-0 network failure
  (APC-04). The `TypeDefsService`/`AtlasEntitiesService` error paths stay as
  they are — already proven.
- `aurelius-atlas-observability` — the **branch holes** at 67%: the provider
  `resource` merge, the metrics options (web-vitals off, interval, pagehide
  flush), the error handler's non-`Error` conversions and no-active-span path,
  the interceptor's no-traceId and status-less-`HttpErrorResponse` branches,
  the ingest-auth token-less authenticated session, and a **new
  `opentelemetry-session.spec.ts`** for the storage-denied branches (SHL-14,
  DD-103).
- `aurelius-atlas-webapp` — `app.config.spec.ts` gains `initialize()`'s loud
  failure when `/config.json` answers non-2xx (SHL-02's other half — today
  only the success path runs) and `metricsUrl`'s two branches; the header's
  logout proves a rejecting `keycloak.logout()` does not surface as an
  unhandled rejection (SHC-05's failure edge).
- `aurelius-atlas-ui` — `dark-mode.component.spec.ts` gains the real
  component assertions the one-create-test lacks: the title names the mode and
  a click cycles it (SPL-03, SPL-04's component side).
- `aurelius-atlas-frontend-example` — the editor's save/delete against a
  **real failing server** (HttpTestingController, not a spy on the service
  under test): a 500 keeps the entity open, a 404 on delete surfaces the
  status; the form's validation gates `save()` (no request fires);
  `app.config.spec.ts` mirrors the webapp's config-failure pair;
  `search.service.spec.ts` proves the out-of-order response (late first
  answer discarded, `switchMap` cancellation — the interrupted/async
  category's proof, no production change).

It does **not** deliver: production-code changes (every test pins behaviour
the shipped code has), new e2e scenarios (9.1), the server spine (deferred
backlog #1), the context-card parametrised suite (representativeness polish,
not failure coverage — deferred with the dashboard notes).

## Semantics

No new rule ids. The paths proven here, as stated:

- **APC-04** (7-3): a failed call surfaces `{errorCode, errorMessage,
errorCause}` as the typed Atlas body — the matrix names each service method
  against 404/400 (Atlas body), 500 (Atlas body), and status 0 (network:
  `atlasErrorFrom` yields `null`, the interceptor's alert path).
- **SHL-02** (7-1): a `/config.json` that is missing, unreachable, or the
  wrong shape fails the boot loudly — proven for the non-2xx answer (the
  parse-rejection half stays in `config.spec.ts`).
- **SPL-03 / SPL-04** (7-14): the toggle's title states the current theme and
  a click cycles `auto → dark → light`; the component renders the service's
  mode (the service's storage/persistence tests are 7.14's).
- **SHL-14 / DD-103 / CIA-02** (7.16–7.17): the observability branch holes —
  each named by its own spec (metrics options, resource merge, pagehide
  flush, exception conversions, traceparent skip, token-less session,
  storage-denied session id).
- (no rule id — the example app ships no increment spec, DD-125): the
  editor's failing save/delete, the form's validation gate, the search
  service's out-of-order response. Tests carry plain names.

## Java origin

None new: this increment proves frontend rules whose 7.x specs cite the
Aurelius `libs/atlas/api` (APC), the Aurelius shell boot (SHL-02), and the
legacy theme toggle (SPL-03). The example app's editor is workspace
boilerplate (no legacy twin, DD-001 lineage).

## Deviations

None.

## Acceptance

Unit (Vitest, run per project; ids in `it()` titles per the webapp convention):

- `libs/angular/aurelius-atlas-data-access/src/lib/admin.service.spec.ts` —
  appended: `surfaces the Atlas error body on a failed call (APC-04)`
  (404, all three methods), `surfaces the server fault body (APC-04)` (500),
  `surfaces a network failure as a status-0 response (APC-04)`
  (`flush(unknown, { status: 0, statusText: "Unknown Error" })`).
- `libs/angular/aurelius-atlas-data-access/src/lib/entities.service.spec.ts` —
  appended: the same three, over `createOrUpdate`/`delete`/`findAll`/`findOne`,
  each asserting `atlasErrorFrom` types the body (APC-04).
- `libs/angular/aurelius-atlas-observability/src/lib/` — appended specs
  naming the branch (SHL-14, DD-103): provider `resource` merge; metrics
  `webVitals: false`, custom interval, pagehide flush; error handler
  string/serialisable/non-serialisable conversions and the no-active-span
  span; interceptor no-traceId passthrough and status-less error; ingest-auth
  authenticated-without-token; new `opentelemetry-session.spec.ts`
  (reuse, getItem-denied, setItem-denied).
- `apps/aurelius-atlas-webapp/src/app/app.config.spec.ts` — appended:
  `initialize fails loudly when /config.json answers 500 (SHL-02)`,
  `metricsUrl prefers the explicit endpoint / derives it from traces (SHL-14)`.
- `apps/aurelius-atlas-webapp/src/app/shell/header.component.spec.ts` —
  appended: `ends the session fire-and-forget even when logout rejects (SHC-05)`.
- `libs/angular/aurelius-atlas-ui/src/lib/dark-mode/dark-mode.component.spec.ts`
  — appended: title names the mode; click cycles auto→dark→light; icon follows
  the mode (SPL-03, SPL-04).
- `apps/aurelius-atlas-frontend-example/src/app/editor/editor.component.spec.ts`
  — appended (real server, no spies on `EntitiesService`): a 500 on save keeps
  the entity open and surfaces the status; a 404 on delete surfaces the status;
  an over-long name makes the form invalid and `save()` sends nothing.
- `apps/aurelius-atlas-frontend-example/src/app/app.config.spec.ts` — new:
  the config-failure pair (mirrors the webapp's).
- `apps/aurelius-atlas-frontend-example/src/app/services/search.service.spec.ts`
  — appended: `discards a late answer for a superseded query` (two queries,
  first flushed last, the second answer wins).

Gates: `nx test aurelius-atlas-data-access -c ci`, `nx test
aurelius-atlas-observability -c ci` (branch coverage rises toward the 85% the
Sonar gate wants — the review's measurement), `nx test aurelius-atlas-ui
-c ci`, `nx test aurelius-atlas-webapp -c ci`, `nx test
aurelius-atlas-frontend-example -c ci` green; lint clean. No production-code
change, so no new-code coverage dip and no trace-check change (frontend rule
ids are named by `it()` titles, not covers markers — the 117-gap baseline is
the trace tool's Python-side scope, unchanged).
