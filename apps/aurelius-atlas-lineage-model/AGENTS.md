# aurelius-atlas-lineage-model

The lineage-graph API of the ADR 055 lineage chain (increment 8.2). This file covers
wiring specific to this app; workspace-wide rules, including the conversion workflow,
live in the root `AGENTS.md`.

## Layout

The structure follows the FastAPI example app (DD-118): providers build
collaborators, routes serve, `app.py` composes.

- `aurelius_atlas_lineage_model/app.py` — the composition root:
  `create_app(settings, auth=None, atlas=None, d2m=None)` builds the verifier,
  the upstream clients and their breakers, mounts the routers, wires the
  upstream-error/400 handlers (LM-05/LM-07, DV-55..DV-22, LM-12's open-circuit
  502 — the mapping is the app's own contract, kept at the root) and the
  telemetry. The `auth`/`atlas`/`d2m` arguments are injectable for tests
  (DD-111); the lifespan closes the httpx2 pools the app built (DD-116).
- `aurelius_atlas_lineage_model/providers/` — the factories: `auth.py` (the
  shared `aurelius-atlas-auth` verifier, DD-108), `upstreams.py` (the httpx2
  pools, the per-upstream breakers with the `is_upstream_fact` exclude, the
  clients — LM-11/LM-13), `telemetry.py` (the native OTel providers + the
  OTLP ingest leg, the shared `aurelius-atlas-otel` lib: `otel-lineage-model`,
  DD-107/DD-108/DD-121; the FastAPI + httpx2 instrumentors stitch the chain —
  the caller's `traceparent` rides the upstream calls, DD-121).
- `aurelius_atlas_lineage_model/routes/` — `lineage.py` (`build_router(auth)`:
  the gated `GET /` composes the use case — fetch → flatten → extract → answer
  verbatim (LM-01), each upstream call behind its `pybreaker` breaker via the
  `calling()` seam (8.5, DD-117), failures mapped to `UpstreamError`;
  LM-01/LM-08), `health.py` (the anonymous liveness, LM-09).
- `aurelius_atlas_lineage_model/globals.py` / `errors.py` — the name, logger
  and wire constants; `UpstreamError` and the Atlas-shaped `atlas_error` body.
- `aurelius_atlas_lineage_model/settings.py` — `LineageModelSettings`
  (`AURELIUS_ATLAS_LINEAGE_MODEL_` prefix; `atlas_base_url`/`data2model_url` required, LM-10;
  `breaker_fail_max`/`breaker_reset_timeout`, LM-15 — the auth library's issuer-breaker shape)
- `aurelius_atlas_lineage_model/lineage.py` — the 12-column flattener
  (`flatten_relations`, LM-02/LM-03), the legacy `LINEAGE_RULES` document
  verbatim (LM-04); re-exports the `v2/lineage` contract models (the client
  lib's, 8.4) and `UpstreamError` so their import paths stay
- `aurelius_atlas_lineage_model/__main__.py` — the uvicorn entry point (port 21002)
- `scenarios/` — the parity scenario, read from the Aurelius source; `scenarios/fixtures/`
  are generated (scratch tool, not CI) and committed: `graph.lineage.json` (the canned
  Atlas answer), `graph.extract.json` (the 8.1 engine's bytes for the same rows). The
  graph is the 8.1 scenario's rows inverted: a dataset → process → dataset lineage.
- `tests/` — unit tests, one file per module (ADR 049 names every public
  function): the flattener, the chain, the providers, the routes, the app
  wiring and breakers — all on a fake issuer and a recording fake upstream
  (`tests/fake_upstream.py`); `e2e/` — the chain: this image + the real
  data2model container + a canned-file fixture Atlas (DD-111), Keycloak-minted tokens

## Rules the app keeps

The LM rules live in
`docs/architecture/conversion/increments/8-2-lineage-model-api.md`; the circuit-breaker
rules (LM-11..LM-15) in
`docs/architecture/conversion/increments/8-5-lineage-model-circuit-breakers.md`; tests cite
them with `@pytest.mark.covers(..., rules=["LM-NN"])` (ADR 049). The legacy reference is
`.scratch/aurelius` (`backend/m4i-lineage-model/m4i_lineage_model/lineage_model.py`):
cite the file in any behaviour change — the 12 column names (`m4i_*_process`, LM-03)
and the `LINEAGE_RULES` ids (LM-04) are the webapp lineage screen's parser's input.

## Wiring Checklist

- `project.json` — `serve` depends on dev Keycloak (tokens) + observability (the OTLP
  leg); `test`/`build`/`docker-*`/`decrypt` are inferred by `tools/plugins/python.ts`.
  The `e2e` target overrides `dependsOn` to add the **data2model** project's `certgen`
    - `docker-build` (its container runs in this suite).
- Auth is the shared lib (`aurelius-atlas-auth`, DD-108): `auth.require_auth` +
  `auth.require_bearer` on the route — the caller's **raw** token is forwarded to both
  upstreams (LM-04). Audience `aurelius` (the webapp's client id, AUX-04): the chain
  forwards browser tokens, so this app verifies them for that audience (LM-08, DV-57).
- The upstreams are settings, never hosts (DV-52): `atlas_base_url` (the server's
  lineage feed, 5.1) and `data2model_url` (the 8.1 app).
- Each upstream is guarded by its own `pybreaker` breaker (8.5, LM-11..LM-14, DV-60,
  DD-117): the documented `with breaker.calling():` seam at each call site, the callable
  `exclude` predicate (4xx is a fact, not an outage — the auth library's AUX-02 shape),
  one breaker per integration point. The breakers live in the app, not the client
  libraries (DD-116 keeps the libs transport-only). pybreaker's `call_async` is
  tornado-only — do not use it.
- OTLP export is app-owned (DD-107/DD-108): `otel_*` settings, `otel-lineage-model`
  client, collector leg `https://localhost:4319`. Unset = no OTLP export (AUX-03, DD-121).
- The chain is one trace (DD-121): `HTTPX2ClientInstrumentor` carries the caller's W3C
  `traceparent` on the Atlas fetch and the `/extract` call (LM-04), so browser →
  lineage-model → data2model share a trace id in Tempo. The e2e stitch probe reads
  that trace back from Tempo (published loopback :3200, CIA-03).
- `.env.enc` — dev settings (`nx encrypt aurelius-atlas-lineage-model` after changing
  `.env`); `OTEL_CLIENT_SECRET` mirrors the server's `OTEL_INGEST_CLIENT_SECRET` (DD-107).
- `tls.json` — the app's certificate (`nx certgen`), used by `serve` and `e2e`. The SANs
  cover the compose service names, so the in-network TLS calls verify (e2e).
- `Dockerfile` — installs the wheel `nx build` makes (workspace libs bundled), nonroot,
  liveness healthcheck.
- `e2e/docker-compose.yaml` — the 8.2 chain (DD-111): this app + the **real** data2model
  image (certs mounted from its project) + a fixture Atlas (`python -m http.server` over
  `e2e/fixtures/`, where `v2/lineage/<guid>` is the canned graph, named for the fixed
  UUID guid the scenario fixtures carry (DV-61)); the collector on the observability network, Keycloak through
  `keycloak.localhost:host-gateway`.

## Removal

The app is one ADR 055 surface: remove `apps/aurelius-atlas-lineage-model`, its root
`pyproject.toml` entries (member, dev group, uv source), the `otel-lineage-model` client
in `dev/keycloak/import/master.json`, and the 8.2 roadmap/spec rows. `aurelius-atlas-auth`
and `aurelius-atlas-otel` stay — 8.3 uses them; `aurelius-atlas-data2model` stays (8.1).
