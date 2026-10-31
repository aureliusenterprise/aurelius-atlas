# aurelius-atlas-server

The Atlas REST API on Elasticsearch (DD-015, DD-016). This file covers wiring specific to this app;
workspace-wide rules, including the conversion workflow, live in the root `AGENTS.md`.

## Layout

- `aurelius_atlas_server/app.py` — `create_app`: the store's lifetime, the error handler, the routers;
  `mount_dashboards`: the built dashboards after the routers (DD-018)
- `aurelius_atlas_server/settings.py` — `ServerSettings` (`AURELIUS_ATLAS_SERVER_` prefix)
- the lifespan in `app.py` opens the store, loads the type registry through `TypedefStore` (TDS-12), then
  the models of `models_dir` through `ModelLoader` (MDL-16); `app.state.type_registry` and
  `app.state.typedef_store` hold them. Tests set `models_dir` to an empty directory (`tests/conftest.py`),
  since Atlas's models take seconds to load; only the MDL-16 test loads them
- `aurelius_atlas_server/task_worker.py` — `TaskWorker`: started by the lifespan when `tasks_enabled`, woken
  by the entity store's `task_listeners` and polling every `task_poll_seconds` (DD-080). Tests and the e2e
  server run with tasks disabled so responses show propagation at once (DD-081); `tests/test__*_tasks.py`
  turns them on and runs on the module loop, where the lifespan started the worker
- `aurelius_atlas_server/errors.py` — `AtlasError`, `AtlasErrorCode`, the Atlas error body and JSON media type;
  a 5xx answer is opaque and carries the trace id as `requestId` (SRV-07, DD-235)
- `aurelius_atlas_server/security_headers.py` — `SecurityHeadersMiddleware`: security headers on every
  answer, split `/api` path vs dashboard; HSTS gated on `hsts_enabled` (SRV-08, DD-236). TLS material
  is a required setting — the server never serves plaintext (SRV-06, DD-234)
- OTLP ingest (DD-196) lives in the shared `aurelius-atlas-otel` lib (DD-197):
  `app.py::_ingest_pipeline` maps `ServerSettings.otel_*` into
  `build_otlp_pipeline`, installed by the lib's `setup_telemetry` on the
  native OTel providers (DD-210: the app owns its export; the static env
  headers cannot carry a 60s JWT)
- `aurelius_atlas_server/routes/` — one router module per Atlas resource class (`admin.py` ← `AdminResource`)
- `aurelius_atlas_server/__main__.py` — the uvicorn entry point
- `scenarios/` — parity scenarios, one directory per Atlas resource; run by `tests/` and `e2e/`
- `tests/` — unit tests on a fake Elasticsearch client; `e2e/` — the image over HTTPS on the dev store
- `helm/` — the `atlas-server` chart (its own section below)

## Porting an Atlas resource

1. Write the increment's spec, then the scenarios under `scenarios/<resource>/`, each citing the
   `release-2.4.0` code it was read from (ADR 052; the source is at `github.com/apache/atlas`).
2. Add `routes/<resource>.py` and include its router in `app.py`. Raise `AtlasError` with an
   `AtlasErrorCode` member copied from Atlas's `AtlasErrorCode` (status, code and message template).
3. Add the Java class to `docs/architecture/conversion/java-map.md`; every visible difference goes to
   `deviations.md` and into the scenario as a `deviations` entry.

## Wiring Checklist

- `project.json` — `implicitDependencies` and `serve` `dependsOn` (dev Elasticsearch,
  **dev Keycloak**, observability, the dashboard build — Keycloak joins for DD-196: the
  OTLP export mints its ingest JWT from the issuer, so `serve` needs it up).
  `docker-build` and `docker-publish` repeat the plugin's `dependsOn` and add the dashboard
  build: the plugin only chains the dependencies' `docker-build`, which the dashboard has not.
- OTLP export is app-owned (DD-196): `ServerSettings.otel_*` (`otel_token_url`,
  `otel_client_id`=`otel-atlas-server`, `otel_client_secret`,
  `otel_endpoint`=`https://localhost:4319`, `otel_ca_file`) — **not** the
  `OTEL_EXPORTER_*` env (static headers cannot carry the dev realm's 60s token).
  With no `otel_token_url`/`otel_client_secret` the server logs telemetry only
  (no OTLP), so the un-instrumented dev path stays zero-config.
- `.env.enc` — dev settings; the Elasticsearch password mirrors `dev/elasticsearch/.env`. Re-run
  `nx encrypt aurelius-atlas-server` after changing `.env`.
- `tls.json` — the server's certificate (`nx certgen`), used by `serve` and `e2e`.
- `Dockerfile` — installs the wheel `nx build` makes, with the workspace libraries bundled in, and copies
  the built dashboards (`aurelius-atlas-dashboard/dist`).
- `e2e/docker-compose.yaml` — the image on the dev store's network, reached as `elasticsearch:9200`.
  Its OTLP export uses the shim settings; the mint rides the TLS `:8443`
  issuer, pinned to `/certs/ca.pem` (DD-202: every producer mints there, the
  collector validates both listeners), so the server needs `extra_hosts:
keycloak.localhost:host-gateway` and the `otel-atlas-server` client imported
  (a long-lived dev Keycloak needs a recreate for a new client — see
  dev/keycloak/AGENTS.md).

## Commands

```bash
npx nx serve aurelius-atlas-server
npx nx test aurelius-atlas-server -c ci
npx nx e2e aurelius-atlas-server -c ci    # builds the image, starts the dev store
uv run pytest apps/aurelius-atlas-server/tests
```

## Helm chart

`helm/` — the `atlas-server` chart (10.3a, CHT-20/21/22): the Deployment and
ClusterIP Service on 21000 with **HTTPS** probes (the server never serves
plaintext, SRV-06); every settings value naming a peer is a join — the store
Service (`ELASTICSEARCH_HOSTS` + its password Secret), the issuer URL (the
OTLP token-URL join), the CA/TLS file paths on the whole-Secret mount of the
chart's own `Certificate` (SANs = Service name + FQDNs, which is exactly what
the webapp's nginx pins with `proxy_ssl_name`). `telemetry.enabled` is off by
default — with it on, the collector leg joins (`:4319`, client `otel-atlas-server`,
Secret `atlas-otel-clients`; the join key is the client id on the prod realm,
the shared `OTEL_INGEST_CLIENT_SECRET` on `global.realm=master` — CHT-90,
DD-277). `forwardedAllowIps` feeds `FORWARDED_ALLOW_IPS`
— stock render is loopback-only; the environment overlays name the pod CIDRs
(the two-hop client-IP trust, DD-261/CHT-32). The chart renders standalone
(test values) and through the umbrella (`helm/`); the chart-contract tests are
`tests/test__charts_server.py`. 10.6 adds the ingress allow (CHT-65): 21000
from the webapp and lineage-model pods only (`networkPolicy.peers.*` rename
the pod-name labels); the dashboard's gateway allow belongs to the umbrella.
Chart conventions and gotchas: `helm/AGENTS.md`.

```bash
npx nx run aurelius-atlas-server:helm-template
```

Removing the app removes `helm/` too — plus the umbrella's dependency and
values-toggle rows (`helm/AGENTS.md`).

## Removal

Not removable: this is the product.
