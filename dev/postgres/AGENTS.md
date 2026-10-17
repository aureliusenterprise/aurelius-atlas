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
