# aurelius-atlas-dev-keycloak

Local development identity provider. This file covers wiring specific to this
project; workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — Keycloak plus its private Postgres and a
  `metrics-puller` sidecar
- `config/metrics-puller.yaml` — OTel Collector config for the puller
  (scrapes `postgres-keycloak`, pushes OTLP to dev/observability)
- `import/master.json` — realm, clients, and test users, imported on startup
- `.env` / `.env.enc` — SOPS-encrypted dev settings

## Wiring Checklist

- `project.json` `implicitDependencies` on `aurelius-atlas-dev-observability`; the
  `serve` target chains `decrypt` → `docker-build` → dependency `serve`, and
  exports OTLP over TLS to `https://otel-collector:4317` (JVM truststore
  `/certs/truststore.p12` via `JAVA_OPTS`; Quarkus' gRPC sender ignores
  `OTEL_EXPORTER_OTLP_CERTIFICATE`).
- The Keycloak **metadata Postgres** is covered by the slice's
  **`metrics-puller`** service (same pattern as dev/postgres): the Collector's `postgresql` receiver scrapes
  `postgres-keycloak` and pushes OTLP over the observability network the
  stack already joins — the server itself exports natively, the database
  speaks no OTLP, so the puller complements rather than duplicates.
  Prometheus series carry `exported_job="keycloak-infra"`.
- Dual listeners (ADR 039): `http://keycloak.localhost:8080` (dev browser) and
  `https://keycloak.localhost:8443` (E2E/CI, certs from `nx certgen`). The
  issuer each client uses must match the auth settings the FastAPI example
  validates and the frontend's `/config.json` advertises — change them
  together (`e2e/config/config.json` and the e2e compose use 8443).
- The default network carries the `keycloak.localhost` **alias** so
  in-network OAuth clients (Kafka broker, e2e stacks) resolve it without
  `extra_hosts: host-gateway` — that mapping points at `docker0`, which is
  link-down inside the dev container and fails intermittently. Clients join
  the external `aurelius-atlas-dev-keycloak-network` instead.
- The `postgres-keycloak` database is TLS-only (`sslmode=verify-full` against
  the CA; server cert via the install-copy startup pattern).
- Realms/clients/test users live in `import/master.json`; edit there rather
  than mutating the running container (changes are lost on recreate otherwise).
    - The `aurelius-atlas` client (6.1) is the Atlas server's OIDC
      relying party — a confidential client (secret `${ATLAS_RP_CLIENT_SECRET}`,
      mirrored in the dashboard and server stacks' `.env.enc`) with PKCE S256,
      the dashboard-origin and direct-server callback URIs registered, and each
      installation's `/login.jsp` landing allowlisted for post-logout redirects
      (dashboard origin and direct-server stack, DD-040). The issuer each
      consumer names must be `keycloak.localhost:8443` — the advertised
      hostname — or the tokens fail `iss` verification.
    - `import/master.json` declares the dev identities: `aurelius-writer`
      (carries the `aurelius-write` client role on the `aurelius` client — the
      FastAPI example's write gate, `AURELIUS_ATLAS_FASTAPI_AUTH_WRITE_ROLE`) and
      `aurelius-reader` (read-only), so the authorization model is declarative —
      no init sidecar. Passwords are `${DEV_USER_*_PASSWORD}` placeholders
      resolved from the container env (`.env.enc`, `${VAR:?}` guards) by the same
      `replace-placeholders` flag as the client secrets; the apps' `.env` files
      point at `aurelius-writer`. The bootstrap `admin` account
      (`KC_BOOTSTRAP_ADMIN_*`) stays reserved for the admin console. Gotcha (same
      as secrets): after changing a user/role, delete the realm (or recreate the
      stack) and re-import — re-imports don't overwrite, and placeholder values
      never re-resolve for existing users.
- The `aurelius` client (frontend SPA, public) has explicit loopback redirect
  URIs and web origins: `http(s)://localhost|127.0.0.1:4200` (`nx serve`) and
  `https://localhost:18443` (frontend e2e's fixed host port). Keep them in
  sync when ports change. Two Keycloak gotchas learned the hard way:
  redirect URIs support port wildcards (`http://localhost:*` works), but
  CORS **web origins do not** — `originEquals` compares the port suffix
  literally, so a wildcard or `+` derived from a wildcarded redirect fails
  with "Invalid origin" on every token exchange. List origins exactly.
    - Re-imports do NOT overwrite an existing realm/client: delete it
      (`DELETE /admin/realms/master/clients/<id>` is too blunt — recreate the
      stack or PUT via the admin API) before a changed import takes effect.
- The frontend's `serve` target depends on this project's `serve`.
- Realm imports can carry `${VAR}` placeholders resolved from the container
  environment; substitution needs the
  `-Dkeycloak.migration.replace-placeholders=true` JVM flag in `JAVA_OPTS`
  (without it the literal `${...}` string is imported). Used by the dev user
  passwords in `import/master.json` (see above); the Kafka and OpenMetadata
  realms that also used this were removed with those stacks (ADR 050).

## Commands

```bash
nx serve aurelius-atlas-dev-keycloak   # decrypt + build + observability + up
```

## Conventions

- First start takes a couple of minutes to become healthy — that's normal, not
  a hang.
- Keep `import/master.json` idempotent (fixed UUIDs where needed) so re-imports
  don't churn.

## Removal

Part of the spine. Removing it means replacing auth in the FastAPI example and
dropping the Keycloak config/interceptor wiring from the frontend.
