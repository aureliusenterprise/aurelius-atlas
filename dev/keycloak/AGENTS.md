# aurelius-dev-keycloak

Local development identity provider. This file covers wiring specific to this
project; workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — Keycloak plus its private Postgres and a
  `metrics-puller` sidecar
- `config/metrics-puller.yaml` — OTel Collector config for the puller
  (scrapes `postgres-keycloak`, pushes OTLP to dev/observability)
- `import/master.json` / `import/openmetadata-realm.json` /
  `import/kafka.json` — realms, clients, and test users, imported on startup
- `.env` / `.env.enc` — SOPS-encrypted dev settings

## Wiring Checklist

- `project.json` `implicitDependencies` on `aurelius-dev-observability`; the
  `serve` target chains `decrypt` → `docker-build` → dependency `serve`, and
  exports OTLP over TLS to `https://otel-collector:4317` (JVM truststore
  `/certs/truststore.p12` via `JAVA_OPTS`; Quarkus' gRPC sender ignores
  `OTEL_EXPORTER_OTLP_CERTIFICATE`).
- The Keycloak **metadata Postgres** is covered by the slice's
  **`metrics-puller`** service (same pattern as dev/governance and
  dev/postgres): the Collector's `postgresql` receiver scrapes
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
  the external `aurelius-dev-keycloak-network` instead.
- The `postgres-keycloak` database is TLS-only (`sslmode=verify-full` against
  the CA; server cert via the install-copy startup pattern).
- Realms/clients/test users live in `import/master.json`; edit there rather
  than mutating the running container (changes are lost on recreate otherwise).
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
- The `kafka` realm (`import/kafka.json`, imported the same way) provides
  OAUTHBEARER machine identity for `dev/kafka`: per-role confidential
  client-credentials clients with a `kafka-audience` scope mapper setting
  `aud=kafka` and `include.in.token.scope=true` (Kafka's JWT validator
  rejects an empty `scope` claim). `dev/kafka` holds the client recipes.
  Least privilege: every client has `fullScopeAllowed: false` and reaches
  `aud=kafka` only through the `kafka-audience` client scope listed in its
  `defaultClientScopes` — a new client needs the scope added explicitly,
  never full scope reopened (a realm-wide grant would defeat per-role
  identity the day broker ACLs key on groups/roles).
  Gotcha: Keycloak re-imports do NOT overwrite an existing realm — delete it
  via the admin API (`DELETE /admin/realms/kafka`) and restart before a
  changed import takes effect, and restart the broker afterwards (it caches
  the realm JWKS, which re-import rotates).
  Client secrets are NOT in the import file: it carries `${CLIENT_SECRET_*}`
  placeholders resolved from the container environment (values in `.env.enc`,
  interpolated fail-fast via `${VAR:?}` in `docker-compose.yaml`). Substitution
  needs the `-Dkeycloak.migration.replace-placeholders=true` JVM flag in
  `JAVA_OPTS` — without it, startup imports keep the literal `${...}` string
  and every client gets a garbage secret (clients exist but no grant works).
  After changing a secret in `.env.enc`: decrypt, recreate Keycloak, re-import
  the realm (delete + restart, above), sync the apps' `.env.enc`, restart the
  broker.
- The `openmetadata` realm (`import/openmetadata-realm.json`) serves
  `dev/governance`: the `openmetadata` OIDC login client plus the
  `openmetadata-bot` service-account client that mints the ingestion
  machines' short-lived tokens (`client_credentials`). OM usernames resolve
  from the default claim order (`email` > `preferred_username` > `sub`), so
  each realm subject's **email local-part must equal its OM username**: the
  admin user has `admin@aureliusenterprise.com` (→ `admin`), and the bot
  client carries a hardcoded `email=ingestion-bot@open-metadata.org` mapper
  (`oidc-hardcoded-claim-mapper` is still used there — a user-attribute
  mapper is not declarative and built-in claims cannot be overridden). Do
  NOT add an `om_user` claim or set OM's `jwtPrincipalClaimsMapping`: the
  mapping also applies to OM's own session tokens, which lack it, and breaks
  every browser login (see dev/governance/AGENTS.md). The admin user MUST carry
  `firstName`/`lastName`: `UPDATE_PROFILE` is realm-enabled and triggers at
  login when profile fields are missing, which breaks the password grant
  ("Account is not fully set up") — this also applies to any user a dev
  creates without a name. Secrets ride the same `${CLIENT_SECRET_*}`
  placeholder mechanism as the kafka realm: `CLIENT_SECRET_OPENMETADATA`
  must equal `OIDC_CLIENT_SECRET`, and `CLIENT_SECRET_OPENMETADATA_BOT`
  must equal `OIDC_BOT_CLIENT_SECRET` in `dev/governance` (both dev
  defaults, encrypted per side).

## Commands

```bash
nx serve aurelius-dev-keycloak   # decrypt + build + observability + up
```

## Conventions

- First start takes a couple of minutes to become healthy — that's normal, not
  a hang.
- Keep `import/master.json` idempotent (fixed UUIDs where needed) so re-imports
  don't churn.

## Removal

Part of the spine. Removing it means replacing auth in the FastAPI example and
dropping the Keycloak config/interceptor wiring from the frontend.
