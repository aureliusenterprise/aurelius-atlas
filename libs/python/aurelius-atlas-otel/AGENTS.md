# aurelius-atlas-otel

The OTLP ingest credential and the native OTel provider setup of the
collector's per-service leg (7.18, DD-196, DD-210), extracted from the Atlas
server so every service on the leg shares one mechanism (8.0, DD-197). This
file covers wiring specific to this lib; workspace-wide rules live in the root
`AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_otel/telemetry.py` — `setup_telemetry` (the native OTel
  providers: the app leg, the env leg, the log bridge, the debug console, the
  per-process system instruments)
- `aurelius_atlas_otel/ingest.py` — `ClientCredentialsTokenSource` (refresh-ahead
  mint), `_IngestSession` (per-request bearer), `build_otlp_pipeline`
  (span processor + metric reader for `setup_telemetry`'s `pipeline`)

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`).
- Consumers pass settings in as parameters — the library reads no app settings
  from the environment. Each app maps its own `AURELIUS_ATLAS_*_OTEL_*` settings
  into the pipeline (see the server's `_ingest_pipeline`). The one environment
  read is the standard `OTEL_EXPORTER_OTLP_ENDPOINT` switch that turns on the
  env leg (DD-210: the legacy shared-token producer, CIA-10) — a
  third-party-runtime name, bare by workspace rule.
- The rules it keeps (CIA-07) are specified by the 7.18 spec
  (`docs/architecture/conversion/increments/7-18-collector-ingest-identity.md`).

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-otel/tests
```

## Conventions

- A service on the per-service leg needs a `otel-<service>` confidential
  client in `dev/keycloak/import/master.json` (copy the `otel-atlas-server`
  block; `defaultClientScopes` must carry `otel-ingest`). Applying an import
  change to a running stack needs `docker compose down -v && up -d`
  (the boot import is IGNORE_EXISTING).

## Removal

Not removable while the per-service leg (DD-196) stands: the server's export
depends on it.
