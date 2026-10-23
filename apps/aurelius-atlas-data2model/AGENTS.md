# aurelius-atlas-data2model

The model-extraction API of the ADR 055 lineage chain (increment 8.1). This file covers
wiring specific to this app; workspace-wide rules, including the conversion workflow,
live in the root `AGENTS.md`.

## Layout

The app follows the workspace's example-app layout (DD-118/DD-119's shape,
DD-120): providers build collaborators, routes serve requests, `app.py` wires.

- `aurelius_atlas_data2model/app.py` — the composition root: `create_app(settings,
auth=None)` builds the verifier, mounts the routers and the 400 handler (the app's
  own contract, kept at the root), and configures the telemetry. `auth` is injectable
  for tests (DD-111's seam).
- `aurelius_atlas_data2model/globals.py` — `NAME`, `LOGGER`, the status and error-code
  constants (DTM-01, DTM-11)
- `aurelius_atlas_data2model/providers/` — `auth.py` (`build_auth`, the shared
  `aurelius-atlas-auth` verifier mapped from the settings, DD-108) and `telemetry.py`
  (`ingest_pipeline`/`configure_telemetry` — the app-owned OTLP leg, the shared
  `aurelius-atlas-otel` lib: `otel-data2model`, DD-107/DD-108)
- `aurelius_atlas_data2model/routes/` — `extract.py` (`build_router(auth)`: the gated
  `POST /extract`, the route calling the engine and answering its bytes, DTM-01) and
  `health.py` (the anonymous `/liveness`)
- `aurelius_atlas_data2model/settings.py` — `Data2ModelSettings` (`AURELIUS_ATLAS_DATA2MODEL_` prefix)
- `aurelius_atlas_data2model/rules.py` — the request contract as pydantic models
  (`ExtractionRequest`…; DTM-11/DTM-12, DD-109: no pandas, `data` is plain row maps)
- `aurelius_atlas_data2model/types.py` — the Archimate element/relationship type tables
  (ported from `m4i-analytics` `Concepts.py` as data)
- `aurelius_atlas_data2model/extract.py` — the extraction engine: per-rule node/edge/metadata
  parse (DTM-02..DTM-05), view selection (DTM-07), the native LR/ BT layout (DTM-08, DV-15),
  the ar3 writer (DTM-09)
- `aurelius_atlas_data2model/__main__.py` — the uvicorn entry point
- `scenarios/` — parity scenarios, read from the Aurelius source (the lineage caller's
  fixed rules are the payload); run by `tests/`
- `tests/` — unit tests (rules + engine + app wiring on a fake issuer); `e2e/` — the image
  over HTTPS, Keycloak-minted tokens

## Rules the app keeps

The DTM rules live in
`docs/architecture/conversion/increments/8-1-data2model-api.md`; tests cite them with
`@pytest.mark.covers(..., rules=["DTM-NN"])` (ADR 049). The legacy reference is
`.scratch/aurelius` (`backend/m4i-data2model`, `libs/m4i-analytics`): cite the file in
any behaviour change — the browser contract (`{model, metadata}`, the ar3 shape) is
the webapp's parser's input.

## Wiring Checklist

- `project.json` — `serve` depends on dev Keycloak (tokens) + observability (the OTLP
  leg); `test`/`e2e`/`build`/`docker-*`/`decrypt` are inferred by `tools/plugins/python.ts`.
- Auth is the shared lib (`aurelius-atlas-auth`, DD-108): `auth.require_auth` on the
  route, audience `aurelius-atlas-data2model` (tokens minted for another client are
  rejected, AUX-04/AUX-05). `/extract` is read-only, so no write role.
- OTLP export is app-owned (DD-107/DD-108): `otel_*` settings, `otel-data2model` client,
  collector leg `https://localhost:4319`. Unset = console-only (AUX-03).
- `.env.enc` — dev settings (`nx encrypt aurelius-atlas-data2model` after changing `.env`);
  `OTEL_INGEST_CLIENT_SECRET` mirrors `apps/aurelius-atlas-server/.env`.
- `tls.json` — the app's certificate (`nx certgen`), used by `serve` and `e2e`.
- `Dockerfile` — installs the wheel `nx build` makes (workspace libs bundled), nonroot,
  liveness healthcheck.
- `e2e/docker-compose.yaml` — the app on the observability network (`otel-collector:4319`),
  Keycloak reached through `keycloak.localhost:host-gateway` (the loopback-pinned mint).

## Removal

The app is one ADR 055 surface: remove `apps/aurelius-atlas-data2model`, its root
`pyproject.toml` entries (member, dev group, uv source), the `otel-data2model` client in
`dev/keycloak/import/master.json`, and the 8.1 roadmap/spec rows. `aurelius-atlas-auth`
and `aurelius-atlas-otel` stay — 8.2/8.3 use them.
