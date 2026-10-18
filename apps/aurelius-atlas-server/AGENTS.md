# aurelius-atlas-server

The Atlas REST API on Elasticsearch (DD-015, DD-016). This file covers wiring specific to this app;
workspace-wide rules, including the conversion workflow, live in the root `AGENTS.md`.

## Layout

- `aurelius_atlas_server/app.py` — `create_app`: the store's lifetime, the error handler, the routers;
  `mount_dashboards`: the built dashboards after the routers (DD-018)
- `aurelius_atlas_server/settings.py` — `ServerSettings` (`AURELIUS_ATLAS_SERVER_` prefix)
- the lifespan in `app.py` opens the store, then loads the type registry through `TypedefStore` (TDS-12);
  `app.state.type_registry` and `app.state.typedef_store` hold them
- `aurelius_atlas_server/errors.py` — `AtlasError`, `AtlasErrorCode`, the Atlas error body and JSON media type
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

- `project.json` — `implicitDependencies` and `serve` `dependsOn` (dev Elasticsearch, observability, the
  dashboard build). `docker-build` and `docker-publish` repeat the plugin's `dependsOn` and add the
  dashboard build: the plugin only chains the dependencies' `docker-build`, which the dashboard has not.
- `.env.enc` — dev settings; the Elasticsearch password mirrors `dev/elasticsearch/.env`. Re-run
  `nx encrypt aurelius-atlas-server` after changing `.env`.
- `tls.json` — the server's certificate (`nx certgen`), used by `serve` and `e2e`.
- `Dockerfile` — installs the wheel `nx build` makes, with the workspace libraries bundled in, and copies
  the built dashboards (`aurelius-atlas-dashboard/dist`).
- `e2e/docker-compose.yaml` — the image on the dev store's network, reached as `elasticsearch:9200`.

## Commands

```bash
npx nx serve aurelius-atlas-server
npx nx test aurelius-atlas-server -c ci
npx nx e2e aurelius-atlas-server -c ci    # builds the image, starts the dev store
uv run pytest apps/aurelius-atlas-server/tests
```

## Removal

Not removable: this is the product.
