# aurelius-atlas-validate-entity

The validation mock of the ADR 055 auxiliary APIs (increment 8.3). This file covers
wiring specific to this app; workspace-wide rules, including the conversion workflow,
live in the root `AGENTS.md`.

## Layout

The app follows the workspace's example-app layout (DD-118/DD-119's shape,
DD-120): providers build collaborators, routes serve requests, `app.py` wires.

- `aurelius_atlas_validate_entity/app.py` — the composition root: `create_app(settings,
auth=None)` builds the verifier, mounts the routers, and configures the telemetry.
  `auth` is injectable for tests (DD-112).
- `aurelius_atlas_validate_entity/globals.py` — `NAME`, `LOGGER`, the healthcheck
  status (VE-04)
- `aurelius_atlas_validate_entity/providers/` — `auth.py` (`build_auth`, the shared
  `aurelius-atlas-auth` verifier mapped from the settings, DD-108) and `telemetry.py`
  (`ingest_pipeline`/`configure_telemetry` — the app-owned OTLP leg, the shared
  `aurelius-atlas-otel` lib: `otel-validate-entity`, DD-107/DD-108)
- `aurelius_atlas_validate_entity/routes/` — `validate.py` (`build_router(auth)`: the
  gated `POST /` answering the fixed mock, VE-01) and `health.py` (the anonymous
  `/liveness`)
- `aurelius_atlas_validate_entity/mock.py` — `MOCK_VALIDATION`: the legacy's `output`
  dict verbatim, as data (VE-02, DV-14, DD-112). The ids, `raw` strings, names and
  verdicts are the webapp governance cards' contract — changing them is a visible
  contract change, not a refactor.
- `aurelius_atlas_validate_entity/settings.py` — `ValidateEntitySettings`
  (`AURELIUS_ATLAS_VALIDATE_ENTITY_` prefix; the auth block required, no upstreams, VE-05)
- `aurelius_atlas_validate_entity/__main__.py` — the uvicorn entry point (port 21003)
- `scenarios/` — the parity scenario, read from the Aurelius source: the caller's
  entity in, the full mock document out (byte equality, no volatile fields)
- `tests/` — unit tests (app wiring on a fake issuer, the mock document's shape);
  `e2e/` — this image on the dev Keycloak, Keycloak-minted tokens, real TLS

## Rules the app keeps

The VE rules live in
`docs/architecture/conversion/increments/8-3-validate-entity-api.md`; tests cite them
with `@pytest.mark.covers(..., rules=["VE-NN"])` (ADR 049). The legacy reference is
`.scratch/aurelius` (`backend/m4i-validate-entity/m4i_validate_entity/m4i_validate_entity.py`):
cite the file in any behaviour change — the `output` dict's keys, `doc-…` ids,
`Attribute - <key>` names and string `compliant` flags are what the webapp's
`GovQualityApi` cards parse.

## Wiring Checklist

- `project.json` — `serve` depends on dev Keycloak (tokens) + observability (the OTLP
  leg); `test`/`build`/`docker-*`/`decrypt` are inferred by `tools/plugins/python.ts`.
  No `e2e` override: the suite is this app alone (no upstream chain, unlike 8.2).
- Auth is the shared lib (`aurelius-atlas-auth`, DD-108): `auth.require_auth` on the
  route; nothing is forwarded (the app has no upstreams). Audience `aurelius` (the
  webapp's client id, AUX-04): the browser calls this endpoint with its own token, so
  this app verifies tokens for that audience (VE-03, DV-24).
- OTLP export is app-owned (DD-107/DD-108): `otel_*` settings, `otel-validate-entity`
  client, collector leg `https://localhost:4319`. Unset = console-only (AUX-03).
- `.env.enc` — dev settings (`nx encrypt aurelius-atlas-validate-entity` after changing
  `.env`); `OTEL_CLIENT_SECRET` mirrors the server's `OTEL_INGEST_CLIENT_SECRET` (DD-107).
- `tls.json` — the app's certificate (`nx certgen`), used by `serve` and `e2e`. The SANs
  cover the compose service name, so the in-network TLS calls verify (e2e).
- `Dockerfile` — installs the wheel `nx build` makes (workspace libs bundled), nonroot,
  liveness healthcheck.
- `e2e/docker-compose.yaml` — this app alone: the collector on the observability
  network, Keycloak through `keycloak.localhost:host-gateway`.

## Removal

The app is one ADR 055 surface: remove `apps/aurelius-atlas-validate-entity`, its root
`pyproject.toml` entries (member, dev group, uv source), the `otel-validate-entity`
client in `dev/keycloak/import/master.json` (it ships with the 8.0 realm import), and
the 8.3 roadmap/spec rows. `aurelius-atlas-auth` and `aurelius-atlas-otel` stay — the
other 8.x apps use them.
