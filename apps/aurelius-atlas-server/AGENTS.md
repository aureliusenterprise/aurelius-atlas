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
- `aurelius_atlas_server/errors.py` — `AtlasError`, `AtlasErrorCode`, the Atlas error body and JSON media type
- `aurelius_atlas_server/otel_ingest.py` — the OTLP ingest credential (DD-107): a
  client-credentials token source (mint/cache/refresh-ahead) feeding a
  `requests.Session` that stamps a fresh bearer per OTLP export, wired into
  logfire's `additional_span_processors`/`additional_readers` (the app owns its
  export; the static env headers cannot carry a 60s JWT)
- `aurelius_atlas_server/routes/` — one router module per Atlas resource class (`admin.py` ← `AdminResource`)
- `aurelius_atlas_server/__main__.py` — the uvicorn entry point
- `scenarios/` — parity scenarios, one directory per Atlas resource; run by `tests/` and `e2e/`
- `tests/` — unit tests on a fake Elasticsearch client; `e2e/` — the image over HTTPS on the dev store

## Porting an Atlas resource

1. Write the increment's spec, then the scenarios under `scenarios/<resource>/`, each citing the
   `release-2.4.0` code it was read from (ADR 052; the source is at `github.com/apache/atlas`).
2. Add `routes/<resource>.py` and include its router in `app.py`. Raise `AtlasError` with an
   `AtlasErrorCode` member copied from Atlas's `AtlasErrorCode` (status, code and message template).
3. Add the Java class to `docs/architecture/conversion/java-map.md`; every visible difference goes to
   `deviations.md` and into the scenario as a `deviations` entry.

## Wiring Checklist

- `project.json` — `implicitDependencies` and `serve` `dependsOn` (dev Elasticsearch,
  **dev Keycloak**, observability, the dashboard build — Keycloak joins for DD-107: the
  OTLP export mints its ingest JWT from the issuer, so `serve` needs it up).
  `docker-build` and `docker-publish` repeat the plugin's `dependsOn` and add the dashboard
  build: the plugin only chains the dependencies' `docker-build`, which the dashboard has not.
- OTLP export is app-owned (DD-107): `ServerSettings.otel_*` (`otel_token_url`,
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
  Its OTLP export uses the shim settings; the mint rides the plaintext `:8080`
  issuer (this suite leaves the collector on its dev-default issuer, unlike the
  webapp e2e's `:8443` flip), so the server needs `extra_hosts:
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

## Removal

Not removable: this is the product.
