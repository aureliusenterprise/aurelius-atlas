# 9.1 Targeted resilience e2e

- **Status:** in progress
- **Pull request:** — (follows the review of 2026-10-24, DD-125)
- **Records:** RSL-01..03 (minted here); DD-125 (the review that scoped this);
  cites 7.7 (ALR-05), 7.3 (APC-05/10), 8.2/8.5 (LM-04, LM-12), DD-111, DD-117,
  DD-153, DD-173

## Scope

The review's last category (infra/technical failures, category 3) is proven
today only in-process: 8.6 stops a fake transport, 8.5 opens fake breakers,
the webapp alert chain is unit-tested with `HttpTestingController`. No test
ever takes a **real container down** and watches the product answer. This
increment adds the targeted outage suite — three scenarios, one per visible
failure surface, each ≤ 2 minutes:

- **RSL-01** — the webapp's server outage, in a real browser: stop the
  `atlas-server` container of the running e2e stack, and the shell surfaces
  the outage the way ALR-05 promises (nginx 502 on `/api` → the bell's badge,
  the drawer's feed names the failed call); start the container and the app
  recovers without a reload — the next call succeeds and the panel answers
  (the alert stays in the feed: an outage is history, not amnesia).
- **RSL-02** — the lineage chain's upstream outage, across containers: stop
  the fixture Atlas of the 8.2 chain; the app's real httpx call hits a
  refused connection and the app answers the Atlas-shaped 502 (LM-12's
  container-side twin — 8.6 proved it in-process with a fake transport);
  start the fixture and the chain answers the canned graph again.
- **RSL-03** — the logout round-trip, in a real browser against the real
  Keycloak: sign in, log out from the navbar, and the IdP session ends — the
  app lands on the sign-in page (the guard's redirect, APC-05), and signing
  in again returns the greeted app. The SHC-05 logout path is unit-pinned in
  7.19 (the fire-and-forget contract); this proves the Keycloak round-trip
  the unit can never run.

It does **not** deliver: chaos testing, sustained-outage behaviour, the
circuit-breaker-open e2e (8.5's unit suite owns it; one outage event is one
failure, and opening needs five), Elasticsearch-loss scenarios (the server
spine's deferred backlog, DD-125), or any production-code change.

## Rule definitions

| Id     | Rule                                                                                                                                                                                                                                         |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RSL-01 | With the Atlas server down, the webapp surfaces the outage: an `/api` call that answers 5xx (nginx's 502) earns an error alert (ALR-05 chain), and when the server returns, the app recovers on the next call — no reload, no manual repair. |
| RSL-02 | With an upstream of the 8.2 chain down (fixture Atlas), the lineage-model app answers a request with the Atlas-shaped 502 (LM-12 over real transports, not a fake one), and recovers to the canned answer when the upstream returns.         |
| RSL-03 | Logout ends the Keycloak session: after Logout, the app's routes answer with the sign-in redirect (APC-05), and signing in again lands the greeted app — the session round-trip is complete and repeatable.                                  |

## Semantics

- **RSL-01** (7.7 ALR-05, 7.12): the alerts interceptor reports `/api` calls
  that fail with 5xx or status 0; a stopped container makes nginx answer 502
  (its `/api/` proxy resolves the upstream per request, DD-142 + the resolver
  pattern), so the browser's failed call follows the unit-tested path: bell
  badge, drawer feed row naming `Request failed: GET /api/... 502`. Recovery
  is the same stack's readiness probe (the conftest's version-endpoint poll,
  ATLAS_SERVER_HOST_PORT) after `container.start()`.
- **RSL-02** (8.2 LM-04/05, 8.5 LM-12, DD-111): the app calls the fixture
  Atlas over the compose network; a stopped container answers connection
  refused, the app's `httpx.RequestError` handler answers the Atlas 502 body
  (`errorCode` ATLAS-500-00-001 family, DD-20's 8.x shape). The container
  handle is found by compose labels (the collector fixture's pattern, CIA-03
  suite). Restart + the compose healthcheck (5s interval) restores the chain.
- **RSL-03** (SHC-05, APC-05/10, DD-153): Logout is the dropdown anchor
  (DD-153); `keycloak.logout()` ends the session at the IdP and returns to
  the app's origin. The root guard (APC-05, `check-sso`) then redirects to
  Keycloak's login — the same landing the `authenticated` fixture signs
  through — and the round-trip completes with the navbar greeting (SHC-05).

## Java origin

No Java twin: Apache Atlas' webapp ships no resilience e2e (the legacy suite
is integration-level, `webapp/src/test`). The scenarios follow the review
(DD-125) category 3 and the Aurelius shell/chain rules cited above.

## Deviations

None new. The outage answers ride the accepted 8.x shapes (DV-60's breaker
502, the SRV-04 error body) — cited, not restated.

## Acceptance

E2E (Docker, real containers; budgets per scenario):

- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp_resilience.py`
  — new, runs after the main suite (filename order) so the outage touches
  only itself:
    - `test__a_server_outage_surfaces_an_alert_and_the_app_recovers`
      (RSL-01): stop the `atlas-server` container (fixture
      `atlas_server_page_down`, compose-label lookup like
      `collector_container`); poll `/api/atlas/admin/version` through nginx
      until 502 (≤ 60s — the nginx resolver's 10s cache); open the settings
      panel with the authenticated page; the bell badge dot is visible and the
      alerts drawer names the failed `GET ... 502` (ALR-12 clears the dot on
      open); start the container, poll readiness; reopen the panel and the
      session answers (no alert added after the recovery). Budget: 120s + the
      session stack.
    - `test__logout_returns_to_sign_in_and_signing_in_again_restores_the_app`
      (RSL-03): authenticated page → hover the account dropdown → Logout;
      the page lands on Keycloak's login (the guard's redirect); sign in with
      the dev user; the navbar greets the identity again. Budget: 60s.
    - The outage fixture's finalizer always starts the container (a crashed
      test must not leave the dev stack down) and the resilience file owns
      the suite's only stop/start pair.
- `apps/aurelius-atlas-lineage-model/e2e/test__aurelius_atlas_lineage_model_resilience_e2e.py`
  — new:
    - `test__a_fixture_atlas_outage_answers_502_and_the_chain_recovers`
      (`@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app",
"aurelius_atlas_lineage_model_client.client.LineageModelClient.get",
rules=["RSL-02", "LM-12", "CL-30"])`): the module fixture
      `fixture_atlas_down` stops the `fixture-atlas` container
      (compose-label lookup); `api.get(E_IN)` raises
      `LineageModelClientError` with `status_code` 502 and an Atlas error
      body whose `errorCode` the client parsed — a raw `httpx` `GET /?guid=`
      answers the identical body, proving the shape is the app's, not the
      client's; the test then starts the container and polls (≤ 90s) until
      `api.get(E_IN)` returns the canned extract again. Budget: 120s. The
      fixture's finalizer restarts the container as a crash-net so the
      scenarios file, which sorts after, always rides a live chain.
- Gates: `nx e2e aurelius-atlas-webapp -c ci` and `nx e2e
aurelius-atlas-lineage-model -c ci` green (the suites already gate in CI —
  these files join them); budgets are bounded by the in-test polls
  (deadline loops, no `pytest-timeout` dependency — it is not installed in
  this workspace), ≤ 2 min per scenario added. RSL-02 shows PASSED
  in the trace report (its marker); RSL-01/RSL-03 are Playwright-side, named
  in the docstrings (ADR 049's frontend convention — the gap baseline grows
  by exactly those two, the webapp rule-id family).
- Lint: ruff clean on both files; no `.env`/compose changes (the fixed ports
  18444/18445 already exist; the chain's fixture needs no host port — the
  outage is observed through the app's own published answer).
