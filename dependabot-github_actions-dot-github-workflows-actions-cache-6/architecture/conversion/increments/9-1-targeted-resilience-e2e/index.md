# 9.1 Targeted resilience e2e

- **Status:** in progress
- **Pull request:** — (follows the review of 2026-10-24, DD-214)
- **Records:** RSL-01..03 (minted here; RSL-01/RSL-02 **retired by DD-281**); DD-214 (the review that scoped this); cites 7.7 (ALR-05), 7.3 (APC-05/10), 8.2/8.5 (LM-04, LM-12), DD-200, DD-206, DD-153, DD-173

## Scope

The review's last category (infra/technical failures, category 3) is proven today only in-process: 8.6 stops a fake transport, 8.5 opens fake breakers, the webapp alert chain is unit-tested with `HttpTestingController`. No test ever takes a **real container down** and watches the product answer. This increment adds the targeted outage suite — one scenario per visible failure surface, each ≤ 2 minutes. **DD-281 retired RSL-01 and RSL-02** (and their tests, here and in the compose lane): their fixtures stop containers through the docker SDK's compose labels, which has no counterpart in the Helm/minikube lane 10.5 is rolling suites onto — and resurrecting them there means orchestrating pod outages for two browser-visible symptoms the unit suites already pin in-process. RSL-03, a browser-only scenario, stays:

- **RSL-01** *(retired, DD-281)* — the webapp's server outage, in a real browser: stop the `atlas-server` container of the running e2e stack, and the shell surfaces the outage the way ALR-05 promises (nginx 502 on `/api` → the bell's badge, the drawer's feed names the failed call); start the container and the app recovers without a reload — the next call succeeds and the panel answers (the alert stays in the feed: an outage is history, not amnesia).
- **RSL-02** *(retired, DD-281)* — the lineage chain's upstream outage, across containers: stop the fixture Atlas of the 8.2 chain; the app's real httpx call hits a refused connection and the app answers the Atlas-shaped 502 (LM-12's container-side twin — 8.6 proved it in-process with a fake transport); start the fixture and the chain answers the canned graph again.
- **RSL-03** — the logout round-trip, in a real browser against the real Keycloak: sign in, log out from the navbar, and the IdP session ends — the app lands on the sign-in page (the guard's redirect, APC-05), and signing in again returns the greeted app. The SHC-05 logout path is unit-pinned in 7.19 (the fire-and-forget contract); this proves the Keycloak round-trip the unit can never run.

It does **not** deliver: chaos testing, sustained-outage behaviour, the circuit-breaker-open e2e (8.5's unit suite owns it; one outage event is one failure, and opening needs five), Elasticsearch-loss scenarios (the server spine's deferred backlog, DD-214), or any production-code change.

## Rule definitions

| Id | Rule |
| --- | --- |
| RSL-01 | **Retired (DD-281).** Was: with the Atlas server down, the webapp surfaces the outage: an `/api` call that answers 5xx (nginx's 502) earns an error alert (ALR-05 chain), and when the server returns, the app recovers on the next call — no reload, no manual repair. |
| RSL-02 | **Retired (DD-281).** Was: with an upstream of the 8.2 chain down (fixture Atlas), the lineage-model app answers a request with the Atlas-shaped 502 (LM-12 over real transports, not a fake one), and recovers to the canned answer when the upstream returns. |
| RSL-03 | Logout ends the Keycloak session: after Logout, the app's routes answer with the sign-in redirect (APC-05), and signing in again lands the greeted app — the session round-trip is complete and repeatable. |

## Semantics

- **RSL-01** *(retired, DD-281)* (7.7 ALR-05, 7.12): the alerts interceptor reports `/api` calls that fail with 5xx or status 0 — the browser-side path stays unit-pinned (7.7's `HttpTestingController` suite); only the real-container outage proof is retired.
- **RSL-02** *(retired, DD-281)* (8.2 LM-04/05, 8.5 LM-12, DD-200): the Atlas-shaped 502 over a real `httpx.RequestError` stays unit-pinned in-process (8.5's fake-transport suite, LM-12); only the container-side twin is retired.
- **RSL-03** (SHC-05, APC-05/10, DD-153): Logout is the dropdown anchor (DD-153); `keycloak.logout()` ends the session at the IdP and returns to the app's origin. The root guard (APC-05, `check-sso`) then redirects to Keycloak's login — the same landing the `authenticated` fixture signs through — and the round-trip completes with the navbar greeting (SHC-05).

## Java origin

No Java twin: Apache Atlas' webapp ships no resilience e2e (the legacy suite is integration-level, `webapp/src/test`). The scenarios follow the review (DD-214) category 3 and the Aurelius shell/chain rules cited above.

## Deviations

None new. The outage answers ride the accepted 8.x shapes (DV-77's breaker 502, the SRV-04 error body) — cited, not restated.

## Acceptance

E2E (Docker, real containers; budgets per scenario):

- *(DD-281: the RSL-01 webapp outage test and the RSL-02 lineage outage file, and the outage fixtures they owned, are deleted from both lanes.)*
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp_resilience.py` — new, runs after the main suite (filename order):

  - `test__logout_returns_to_sign_in_and_signing_in_again_restores_the_app` (RSL-03): authenticated page → hover the account dropdown → Logout; the page lands on Keycloak's login (the guard's redirect); sign in with the dev user; the navbar greets the identity again. Budget: 60s.
- Gates: `nx e2e aurelius-atlas-webapp -c ci` green. RSL-03 is Playwright-side, named in the docstring (ADR 049's frontend convention).
- Lint: ruff clean; no `.env`/compose changes.
