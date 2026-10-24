# Increment 8.5 — lineage-model circuit breakers

| Field      | Value                                                                                                                                                                                                                         |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Status     | in progress                                                                                                                                                                                                                   |
| Author     | Aurelius Atlas maintainers                                                                                                                                                                                                    |
| Date       | 2026-10-23                                                                                                                                                                                                                    |
| ADRs       | 051 (increments), 049 (traceability), 055 (auxiliary APIs are a named data surface), 037 (the system promises nothing about staying up)                                                                                       |
| Design log | DD-108 (foundation), DD-111 (proxy app), DD-116 (clients provided externally), DD-117 (the breakers live in the app, on the `calling()` seam), DD-118 (the app's provider/route layout), DD-119 (the flow lives in the route) |

## Objective

The 8.2 app forwards every request to two upstreams — the Atlas `v2/lineage`
feed and the 8.1 data2model `/extract` — and when an upstream is down, every
request pays for it: a full connect/timeout attempt, on the app's pool, for
every caller, forever. LM-07 answers those calls 502 (DV-22), which is honest
but not protective.

Guard each upstream with a **circuit breaker** (`pybreaker`, the workspace's
existing breaker — the auth library puts one in front of the JWKS fetch,
AUX-02): after a run of upstream outages the circuit opens and further calls
fail fast with the same 502, without reaching the upstream; after a reset
timeout, one trial call probes the upstream, and success closes the circuit.

The breaker is the app's resilience policy, not the wire contract: the client
libraries of 8.4 stay transport-only (DD-116), and the response bytes, the auth
gate, and the LM-01..LM-10 rules are unchanged.

## Scope

In scope: two per-upstream breakers in `apps/aurelius-atlas-lineage-model`
(the Atlas feed, the data2model extract), the open-circuit answer, the
outage/fact counting policy, the two settings, unit tests.

Out of scope: breakers in the client libraries (DD-116 keeps them
transport-only — a breaker is the caller's policy, and each caller owns its
policy); breakers in the other aux apps (8.1 and 8.3 have no upstreams);
bulkheads/rate limits/retries (the pool cap is DD-111's, retries are a 6.x
platform topic); per-endpoint metrics for the breaker state (the listener
logs state changes — a metric leg rides with the otel increments).

## Contracts and Rules

The reference is the Aurelius source (ADR 055 R4):
`backend/m4i-lineage-model/m4i_lineage_model/lineage_model.py` calls
`requests.post` bare — no breaker, no retries; the legacy has no breaker
behaviour to port, so the rules below state the workspace convention
(the auth library's JWKS breaker, AUX-02) applied to the 8.2 chain. DV-60.

### The upstream circuit breakers

| Id    | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LM-11 | The app guards each upstream with its own circuit breaker (`pybreaker`): the Atlas lineage fetch and the data2model extract are counted separately, so one failing upstream never fast-fails calls bound for the healthy one (the 204 of LM-05 must keep flowing past a dead data2model). The breakers are built from the settings by the app's upstream factory (`providers/upstreams.py`, DD-118, DD-119) and exposed on `app.state`, guarding the route's calls. |
| LM-12 | A circuit that is open answers `502` with the Atlas error body (the LM-07 family) **without calling the upstream** — the fast-fail is the point: no pool connection, no timeout, for every request that arrives while the circuit is open.                                                                                                                                                                                                                          |
| LM-13 | Only outages count towards opening a circuit: an upstream `5xx` (`AtlasClientError`/`Data2ModelClientError` with status ≥ 500) and a transport failure (`httpx.RequestError`). An upstream `4xx` is a fact, not an outage — the 404 of LM-05 (answered 204) and the 400 of LM-07 (the caller's own guid) reset the failure counter, exactly as the auth library treats a 4xx from the issuer (AUX-02).                                                              |
| LM-14 | After the reset timeout, the next call is the half-open trial: it reaches the upstream; success closes the circuit and answers normally, a failure re-opens it and answers 502 (LM-12). The trial is one call, not a probe schedule.                                                                                                                                                                                                                                |
| LM-15 | Settings (same prefix, LM-10): `breaker_fail_max` (default 5, ≥ 1) is the outages that open a circuit, `breaker_reset_timeout` (default 60 s, > 0) is how long it stays open — the same shape and defaults as the auth library's issuer breaker (`AuthConfig.fail_max`/`reset_timeout`).                                                                                                                                                                            |

The app's behaviour for closed circuits is unchanged: LM-01 (verbatim answer),
LM-05 (404 → 204), LM-07 (5xx/unreachable → 502), LM-08 (auth gate), LM-09
(liveness) stand as specified in 8.2. The open-circuit 502 is the same wire
shape DV-22 defines, with a message naming the fast-fail.

## Aurelius origin

The legacy `m4i-lineage-model` (Flask, `requests.post` to data2model,
`m4i-atlas-core.get_lineage_by_guid`) has no resilience device — its dev
`aiocache` `@cached()` is not ported (8.2). The breaker is new behaviour,
recorded as DV-60; the workspace convention it follows is
`aurelius-atlas-auth`'s JWKS breaker (AUX-02, same `pybreaker` dependency).

## Deviations

DV-60 (`deviations.md`): the legacy has no upstream circuit breaker; the port
guards each upstream with one, opening on 5xx/transport failures only.
Technical decisions in DD-117 (`design-log.md`): the breakers live in the app
(not the client libraries — DD-116 keeps the libs transport-only); one breaker
per upstream; the `pybreaker` `calling()` generator seam is the async-safe
form (the lib's `call_async` is tornado-only and fails on this Python); the
exclude predicate counts 4xx as facts.

DV-61 (`deviations.md`, DD-124 — rides this branch, not this spec's breakers):
the lineage chain's `guid` is a `UUID` on every typed surface; a non-UUID guid
is LM-07's `400` before any upstream call, so a malformed guid never reaches
the guarded fetch.

## Acceptance

- Unit (the 8.2 app suite, fake upstream + recording transport):
  `tests/test__aurelius_atlas_lineage_model_app.py` —
  `test__the_app_carries_one_breaker_per_upstream`
  (LM-11, LM-15), `test__the_upstream_outages_open_the_circuit` (LM-11, LM-13),
  `test__an_open_circuit_answers_without_calling_the_upstream` (LM-12),
  `test__a_dead_atlas_circuit_leaves_the_extract_circuit_closed` (LM-11, LM-12),
  `test__an_upstream_4xx_is_a_fact_not_an_outage` (LM-13),
  `test__the_half_open_trial_closes_the_circuit_on_success` (LM-14),
  `test__the_half_open_trial_reopens_the_circuit_on_failure` (LM-14);
  `tests/test__aurelius_atlas_lineage_model_settings.py` —
  `test__the_breaker_settings_have_the_auth_shape` (LM-15);
  `tests/test__aurelius_atlas_lineage_model_providers_upstreams.py` —
  `test__the_breakers_are_per_upstream_and_take_the_settings` (LM-11, LM-15),
  `test__an_upstream_4xx_is_a_fact_everything_else_is_not` (LM-13).
  Every transport here is a mock, so the half-open trial is driven through
  pybreaker's management API (`half_open()`) — the wall-clock reset is the
  library's own tested behaviour, not slept through.
- The 8.2 e2e chain stays green unchanged: a healthy chain never opens a
  circuit (closed circuits are byte-identical to 8.2), and the e2e fixture
  Atlas is a static file server, so the open path is proven at unit level.
- `uv run aurelius-atlas-trace check` names every public function (LM ids resolve).
- Parity: none added — no wire behaviour changes on the closed path; the 8.2
  scenario is the guard.

Run: `uv run pytest apps/aurelius-atlas-lineage-model/tests` and
`nx e2e aurelius-atlas-lineage-model`.
