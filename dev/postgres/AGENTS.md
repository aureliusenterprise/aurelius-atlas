# aurelius-atlas-dev-postgres

Local development Postgres. This file covers wiring specific to this project;
workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — Postgres + the `metrics-puller` sidecar
- `config/metrics-puller.yaml` — OTel Collector config for the puller
  (scrapes this database, pushes OTLP to dev/observability)
- `.env` / `.env.enc` — SOPS-encrypted dev settings (credentials, port)

## Wiring Checklist

- Exposes the external Docker network `aurelius-atlas-dev-postgres-network`; the
  FastAPI example and the JDBC sink connector attach to it.
- The FastAPI example's `serve` target starts this project via `dependsOn`.
- The **`metrics-puller`** service scrapes
  this database with the Collector's `postgresql` receiver and pushes OTLP to
  the dev collector over the external `aurelius-atlas-dev-observability-network`
  (Postgres speaks no OTLP, so a puller sidecar is the only push option;
  dev/observability stays slice-agnostic). `implicitDependencies` on
  `aurelius-atlas-dev-observability` make `nx up`/`serve` create that network first
  — e2e fixtures inherit the guarantee through their dependents (the fastapi
  and sink `postgres` fixtures take the `observability` fixture). Prometheus
  series carry `exported_job="dev-postgres"`.
- The puller exports on the collector's **per-service leg** with its own
  identity (DD-107): the `oauth2client` extension mints client-credentials
  JWTs as the `otel-postgres` realm client (dev/keycloak import) and attaches
  them per export — mint, cache, refresh, no custom code. Env quartet in
  compose: `OTEL_INGEST_CLIENT_ID`/`_SECRET` (from `.env.enc`) +
  `OTEL_INGEST_TOKEN_URL`/`_CA_FILE` (defaults: the dev Keycloak's plaintext
  `:8080` listener via `keycloak.localhost:host-gateway` — this slice has no
  Keycloak of its own; the e2e conftests flip both to the suite's TLS `:8443`
  issuer + CA). The puller carries `restart: on-failure:15` (the DD-106 boot
  race, issuer-shaped: the mint needs Keycloak up). The slice no longer
  carries the shared ingest token — its puller was the only consumer.
- Database `aurelius`, credentials from `.env` dev defaults — the same values
  the FastAPI example's settings model reads.
- The `Entity` table is created by the application at startup in dev; there are
  no migration files here. After an `Entity` model change, drop/recreate the
  dev table (see `libs/python/aurelius-atlas-example/AGENTS.md`).

## Commands

```bash
nx serve aurelius-atlas-dev-postgres   # compose up (foreground)
nx up aurelius-atlas-dev-postgres      # detached, waits for healthy
```

## Conventions

- Keep it a blank database: schema belongs to the applications, not to compose
  init scripts.
- `DATABASE_PORT` (default 5432) is part of the workspace contract — coordinate
  before changing.

## Removal

Part of the spine. Removing it means replacing persistence in the FastAPI
example (and the JDBC sink's target table, if that slice is present).
