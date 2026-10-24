# aurelius-atlas-lineage-model

The lineage-graph API of the ADR 055 lineage chain (increment 8.2). This file covers
wiring specific to this app; workspace-wide rules, including the conversion workflow,
live in the root `AGENTS.md`.

## Layout

- `aurelius_atlas_lineage_model/app.py` — `create_app(settings, auth=None, http=None)`:
  the auth dependency (the shared `aurelius-atlas-auth` lib, DD-108), the `GET /` route
  (fetch → flatten → extract → answer verbatim, LM-01), the upstream-error/400 handlers
  (LM-05/LM-07, DV-20..DV-22), the OTLP export (the shared `aurelius-atlas-otel` lib:
  `otel-lineage-model`, DD-107/DD-108). `auth`/`http` are injectable for tests (DD-111).
- `aurelius_atlas_lineage_model/settings.py` — `LineageModelSettings`
  (`AURELIUS_ATLAS_LINEAGE_MODEL_` prefix; `atlas_base_url`/`data2model_url` required, LM-10)
- `aurelius_atlas_lineage_model/lineage.py` — the `v2/lineage` contract as pydantic models,
  the 12-column flattener (`flatten_relations`, LM-02/LM-03), the legacy `LINEAGE_RULES`
  document verbatim (LM-04), `UpstreamError` (the status mapping LM-05/LM-07)
- `aurelius_atlas_lineage_model/__main__.py` — the uvicorn entry point (port 21002)
- `scenarios/` — the parity scenario, read from the Aurelius source; `scenarios/fixtures/`
  are generated (scratch tool, not CI) and committed: `graph.lineage.json` (the canned
  Atlas answer), `graph.extract.json` (the 8.1 engine's bytes for the same rows). The
  graph is the 8.1 scenario's rows inverted: a dataset → process → dataset lineage.
- `tests/` — unit tests (flattener + app wiring on a fake issuer, a recording fake
  upstream — `tests/fake_upstream.py`); `e2e/` — the chain: this image + the real
  data2model container + a canned-file fixture Atlas (DD-111), Keycloak-minted tokens

## Rules the app keeps

The LM rules live in
`docs/architecture/conversion/increments/8-2-lineage-model-api.md`; tests cite them with
`@pytest.mark.covers(..., rules=["LM-NN"])` (ADR 049). The legacy reference is
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
  forwards browser tokens, so this app verifies them for that audience (LM-08, DV-23).
- The upstreams are settings, never hosts (DV-16): `atlas_base_url` (the server's
  lineage feed, 5.1) and `data2model_url` (the 8.1 app).
- OTLP export is app-owned (DD-107/DD-108): `otel_*` settings, `otel-lineage-model`
  client, collector leg `https://localhost:4319`. Unset = console-only (AUX-03).
- `.env.enc` — dev settings (`nx encrypt aurelius-atlas-lineage-model` after changing
  `.env`); `OTEL_CLIENT_SECRET` mirrors the server's `OTEL_INGEST_CLIENT_SECRET` (DD-107).
- `tls.json` — the app's certificate (`nx certgen`), used by `serve` and `e2e`. The SANs
  cover the compose service names, so the in-network TLS calls verify (e2e).
- `Dockerfile` — installs the wheel `nx build` makes (workspace libs bundled), nonroot,
  liveness healthcheck.
- `e2e/docker-compose.yaml` — the 8.2 chain (DD-111): this app + the **real** data2model
  image (certs mounted from its project) + a fixture Atlas (`python -m http.server` over
  `e2e/fixtures/`, where `v2/lineage/e-in` is the canned graph, generated with the
  scenario fixtures); the collector on the observability network, Keycloak through
  `keycloak.localhost:host-gateway`.

## Removal

The app is one ADR 055 surface: remove `apps/aurelius-atlas-lineage-model`, its root
`pyproject.toml` entries (member, dev group, uv source), the `otel-lineage-model` client
in `dev/keycloak/import/master.json`, and the 8.2 roadmap/spec rows. `aurelius-atlas-auth`
and `aurelius-atlas-otel` stay — 8.3 uses them; `aurelius-atlas-data2model` stays (8.1).
