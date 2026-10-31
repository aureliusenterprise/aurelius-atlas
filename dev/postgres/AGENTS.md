# aurelius-atlas-dev-postgres

Local development Postgres. This file covers wiring specific to this project;
workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — Postgres + the `metrics-puller` sidecar
- `config/metrics-puller.yaml` — OTel Collector config for the puller
  (scrapes this database, pushes OTLP to dev/observability)
- `.env` / `.env.enc` — SOPS-encrypted dev settings (credentials, port)

## Wiring Checklist

- Exposes the external Docker network `aurelius-atlas-dev-postgres-network` for
  consumers that attach to it (the template's JDBC sink slice is gone, ADR 050).
- The **`metrics-puller`** service scrapes
  this database with the Collector's `postgresql` receiver and pushes OTLP to
  the dev collector over the external `aurelius-atlas-dev-observability-network`
  (Postgres speaks no OTLP, so a puller sidecar is the only push option;
  dev/observability stays slice-agnostic). `implicitDependencies` on
  `aurelius-atlas-dev-observability` make `nx up`/`serve` create that network
  first. Prometheus series carry `exported_job="dev-postgres"`.
- The puller exports on the collector's **per-service leg** with its own
  identity (DD-196): the `oauth2client` extension mints client-credentials
  JWTs as the `otel-postgres` realm client (dev/keycloak import) and attaches
  them per export — mint, cache, refresh, no custom code. Env in
  compose: `OTEL_INGEST_CLIENT_ID`/`_SECRET` (from `.env.enc`) +
  `OTEL_INGEST_TOKEN_URL`/`_CA_FILE` — **literals**, the dev Keycloak's TLS
  `:8443` listener + this slice's CA (DD-202: the mint issuer is baked into
  the container at creation, so an env default let suite order split it from
  the collector's validator; the collector validates both listeners, and
  every producer mints at :8443). The puller carries
  `restart: on-failure`, unbounded (the DD-195 boot race, issuer-shaped: the
  mint needs Keycloak up; DD-226 — an attempt count burns out before
  Keycloak is reliably up). The slice no longer carries the shared ingest
  token — its puller was the only consumer.
- Database `aurelius`, credentials from `.env` dev defaults. Atlas persists in
  Elasticsearch, so this database is on standby for Postgres-backed additions;
  `dev/keycloak`'s compose borrows this slice's `pg_hba.conf` for its own
  `postgres-keycloak` container.

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

Part of the spine. Its template consumers (the example apps, the JDBC sink)
are gone (ADR 050, DD-284); what still references it is `dev/keycloak`'s
compose mount of `../postgres/pg_hba.conf` and the umbrella's
`dev-postgres` image pin — unwire those together if the slice ever goes.
