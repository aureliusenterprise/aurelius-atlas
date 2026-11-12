# aurelius-atlas-validate-entity

The governance-verdict API of the ADR 055 auxiliary APIs (8.3, made live by 12.7). This file
covers wiring specific to this app; workspace-wide rules, including the conversion workflow,
live in the root `AGENTS.md`.

## Layout

The app follows the workspace's example-app layout (DD-207/DD-208's shape,
DD-209): providers build collaborators, routes serve requests, `app.py` wires.

- `aurelius_atlas_validate_entity/app.py` — the composition root: `create_app(settings,
auth=None)` builds the verifier and the leg, mounts the routers, configures the telemetry,
  and owns the error contract (`UpstreamError`/`DraftRejectedError`/`RequestValidationError` in
  Atlas bodies, VEV-01/06). `auth` and `atlas` are injectable for tests (DD-201).
- `aurelius_atlas_validate_entity/globals.py` — `NAME`, `LOGGER`, the healthcheck
  status (VE-04), the Atlas error code
- `aurelius_atlas_validate_entity/verdicts.py` — `VerdictEngine`: the paged ACTIVE-rule
  search of `m4i_gov_data_quality`, the `RULES_CACHE_SECONDS` cache, the verdict assembly
  over the draft's attributes, the unread-rule recording (VEV-02/03/05, DD-498, DV-146)
- `aurelius_atlas_validate_entity/errors.py` — `UpstreamError` (the leg's 502, VEV-06),
  `DraftRejectedError` (VEV-01's 400), `atlas_error` (the Atlas body)
- `aurelius_atlas_validate_entity/providers/` — `auth.py` (`build_auth`, the shared
  `aurelius-atlas-auth` verifier mapped from the settings, DD-197), `telemetry.py`
  (`ingest_pipeline`/`configure_telemetry` — the app-owned OTLP leg, DD-196/DD-197), and
  `upstreams.py` (`build_upstreams`: the catalogue pool, the app's OWN client-credentials
  mint as `aurelius-atlas-validate-entity`, the leg's one circuit breaker — DD-499/DD-500,
  DD-458's pattern)
- `aurelius_atlas_validate_entity/routes/` — `validate.py` (`build_router(auth)`: the
  gated `POST /` answering the live verdicts over the draft, VEV-01/02) and `health.py`
  (the anonymous `/liveness`)
- `aurelius_atlas_validate_entity/settings.py` — `ValidateEntitySettings`
  (`AURELIUS_ATLAS_VALIDATE_ENTITY_` prefix; the auth block required; the 12.7 leg block:
  `SERVER_BASE_URL`, `TOKEN_URL`, `SERVER_CLIENT_ID`/`SERVER_CLIENT_SECRET`,
  `RULES_CACHE_SECONDS`, the breaker pair, VE-05)
- `aurelius_atlas_validate_entity/__main__.py` — the uvicorn entry point (port 21003)
- `scenarios/validation/` — the parity scenario, read from Aurelius source over the fake
  catalogue: the draft and the seeded rules in, the verdict document out. The mock-era
  scenarios retired with DV-67 (ADR 061)
- `tests/` — unit tests (app wiring on a fake issuer and 8.2's fake catalogue);
- `helm/` — the `atlas-validate-entity` chart (its own section below)
- `e2e/` — this image and a real Atlas server on the dev Keycloak and store: the suite
  seeds governance rules through the catalogue and answers them live (12.7's chain)

## Rules the app keeps

The VEV/VE rules live in
`apps/aurelius-atlas-validate-entity/specs/12-7-governance-verdicts/spec.md` (8.3's and
8.6's specs hold the history: the mock, the failure posture); tests cite them with
`@pytest.mark.covers(..., rules=["VEV-NN"])` (ADR 056). The engine half is
`aurelius-atlas-quality` (GQ, 12.6); the legacy reference is `.scratch/aurelius`
(`backend/m4i-validate-entity/`) — the mock it answered with retired at 12.7 (DV-149
supersedes DV-67, ADR 061); the trigger contract (POST the draft, read only its
`attributes`) survives in the webapp (EDT-23).

## Wiring Checklist

- `project.json` — `serve` depends on dev Keycloak (tokens) + observability (the OTLP
  leg); `test`/`build`/`docker-*`/`decrypt` are inferred by `tools/plugins/python.ts`.
  The `e2e` suite stands its own chain: a real `atlas-server` beside the app on the dev
  store and issuer (the scanner's pattern, 8.2's shape).
- The caller gate is the shared lib (`aurelius-atlas-auth`, DD-197): `auth.require_auth`
  on the route. Audience `aurelius` (the webapp's client id, AUX-04): the browser calls
  this endpoint with its own token (VE-03, DV-75) — the caller's token stops at the gate.
- The catalogue leg is the app's OWN identity (VEV-04, DD-499): the client-credentials
  mint of `aurelius-atlas-validate-entity` (`SERVER_CLIENT_SECRET`), `atlas-read` on the
  realm client, one circuit breaker for the leg (VEV-06, DD-500). Without the secret the
  leg answers 502, never invented verdicts. Nothing of the caller is forwarded.
- OTLP export is app-owned (DD-196/DD-197): `otel_*` settings, `otel-validate-entity`
  client, collector leg `https://localhost:4319`. Unset = no OTLP export (AUX-03, DD-210).
- Every HTTP call is visible (DD-210): `HTTPX2ClientInstrumentor` covers the httpx2
  calls the auth library makes to the issuer and the leg's calls to the server.
- `.env.enc` — dev settings (`nx encrypt aurelius-atlas-validate-entity` after changing
  `.env`); `AURELIUS_ATLAS_VALIDATE_ENTITY_SERVER_CLIENT_SECRET` carries the realm
  import's value, and the file mirrors the chain's guards (the server's ES/auth secrets,
  `OTEL_INGEST_CLIENT_SECRET`) for the e2e compose. The webapp suite rides the same leg
  secret — mirror it there too when it rotates.
- `tls.json` — the app's certificate and the server leaf the e2e chain stands
  (`nx certgen`), used by `serve` and `e2e`. The SANs cover the compose service names,
  so the in-network TLS calls verify.
- `Dockerfile` — installs the wheel `nx build` makes (workspace libs bundled), nonroot,
  liveness healthcheck.
- `e2e/docker-compose.yaml` — this app plus a real `atlas-server` (host port 21008) on
  the dev Elasticsearch and observability networks; the server accepts the app's client
  as an audience (DD-499); Keycloak through `keycloak.localhost:host-gateway`.

## Helm chart

`helm/` — the `atlas-validate-entity` chart (CHT-02, workloads in 10.3a):
port 21003, probes, the `AURELIUS_ATLAS_VALIDATE_ENTITY_` settings env, the
Keycloak audience (`aurelius`, the browser's client), the OTLP ingest
identity, and the 12.7 catalogue leg (CHT-113): `SERVER_BASE_URL` joined to the
co-deployed `atlas-server` Service, `TOKEN_URL` on the issuer's realm, and
`SERVER_CLIENT_SECRET` from `<release>-validate-entity-client` — the same Secret
the master realm's import resolves. Its deployment/service/sa/pdb/certificate
templates are the shipped aux-API shape, kept as a copy per chart by design
(DD-290) — no shared library chart. The `Certificate` (CHT-27) carries SANs = the
Service name + FQDNs and its whole Secret (tls.crt/key + ca.crt) mounts at
`/etc/aurelius-atlas/tls` (DD-294's closure). Chart-contract tests:
`tests/test__charts_aux.py`. Conventions: `helm/AGENTS.md`.

```bash
npx nx run aurelius-atlas-validate-entity:helm-template
```

Removing the app removes `helm/` too — plus the umbrella's dependency, values-toggle and
`secrets.validateEntityClient` rows, the chart's leg joins, the server chart's audience
entry, and the master realm's client and import env (`helm/AGENTS.md`).

## Removal

The app is one ADR 055 surface: remove `apps/aurelius-atlas-validate-entity`, its root
`pyproject.toml` entries (member, dev group, uv source), the `aurelius-atlas-validate-entity`
and `otel-validate-entity` clients in `dev/keycloak/import/master.json` (the former with
its `${VALIDATE_ENTITY_CLIENT_SECRET}` import env and the umbrella's
`secret-validate-entity-client.yaml`), the webapp compose's leg env, and the roadmap/spec
rows. `aurelius-atlas-auth` and `aurelius-atlas-otel` stay — the other 8.x apps use them.
