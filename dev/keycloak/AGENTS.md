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
- `helm/` — the `atlas-keycloak` chart (its own section below)
- `import/master.json` — the dev realm; the **single authored source** the
  chart's `files/master.json` byte-copies (a chart-contract test fails on drift — re-run the copy after editing)

## Wiring Checklist

- `project.json` `implicitDependencies` on `aurelius-atlas-dev-observability`; the
  `serve` target chains `decrypt` → `docker-build` → dependency `serve`. The
  server's native OTLP rides the collector's **legacy leg**
  (`https://otel-collector:4320`, shared token — the issuer cannot present a
  Keycloak JWT at its own cold boot, DD-196; JVM truststore
  `/certs/truststore.p12` via `JAVA_OPTS`; Quarkus' gRPC sender ignores
  `OTEL_EXPORTER_OTLP_CERTIFICATE`).
- The Keycloak **metadata Postgres** is covered by the slice's
  **`metrics-puller`** service (same pattern as dev/postgres): the Collector's `postgresql` receiver scrapes
  `postgres-keycloak` and pushes OTLP over the observability network the
  stack already joins — the server itself exports natively, the database
  speaks no OTLP, so the puller complements rather than duplicates.
  Prometheus series carry `exported_job="keycloak-infra"`.
- Dual listeners (ADR 039): `http://keycloak.localhost:8080` (dev browser) and
  `https://keycloak.localhost:8443` (E2E/CI, certs from `nx certgen`). Every
  automated mint — E2E suites, all slice pullers, the apps' OTLP ingest — uses
  `:8443` (DD-202), so the listener a token's `iss` carries is uniform across
  producers; the collector validates both listeners. The
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
    - `import/master.json` declares the dev identities: `aurelius-writer`
      (carries the `aurelius-write` client role on the `aurelius` client — the
      FastAPI example's write gate, `AURELIUS_ATLAS_FASTAPI_AUTH_WRITE_ROLE`) and
      `aurelius-reader` (read-only), so the authorization model is declarative —
      no init sidecar. Passwords are `${DEV_USER_*_PASSWORD}` placeholders
      resolved from the container env (`.env.enc`, `${VAR:?}` guards) by the same
      `replace-placeholders` flag as the client secrets; the apps' `.env` files
      point at `aurelius-writer`. The bootstrap `admin` account
      (`KC_BOOTSTRAP_ADMIN_*`) stays reserved for the admin console. Both dev
      users also carry `realmRoles: ["default-roles-master"]` explicitly —
      Keycloak's import does not auto-grant the realm default role, and the
      Account Console (7.11 SHC-05) needs the `manage-account`/`view-profile`
      roles composited under it. Gotcha (same as secrets): after changing a
      user/role, the boot re-import will not apply it to a running stack — it
      skips an existing realm wholesale ("Import skipped"), and placeholder
      values never re-resolve for existing users. `kcadm delete realms/master`
      refuses ("Can't remove master realm"), so recreate: `docker compose ... \
down -v && up -d` (fresh DB), or `kcadm delete users/<id>` for the
      changed users and restart Keycloak — the boot import then recreates just
      the missing users with fresh placeholder resolution.
- The `aurelius` client (frontend SPA, public) has explicit loopback redirect
  URIs and web origins: `http(s)://localhost|127.0.0.1:4200` (example
  `nx serve`), `http(s)://localhost|127.0.0.1:4300|4301` (webapp `nx serve`,
  en-US/nl-NL), `https://localhost:18443` (example e2e) and
  `https://localhost:18444` (webapp e2e's fixed host ports). Keep them in
  sync when ports change. The client's `defaultClientScopes` include the
  realm's `otel-ingest` scope (DD-193): its audience mapper stamps
  `aud: otel-collector` on user tokens, which is what the OTel collector's
  browser-leg OIDC receiver requires (`azp` stays `aurelius`, so the APIs'
  azp-or-aud token validation is unaffected). Two Keycloak gotchas learned
  the hard way:
  redirect URIs support port wildcards (`http://localhost:*` works), but
  CORS **web origins do not** — `originEquals` compares the port suffix
  literally, so a wildcard or `+` derived from a wildcarded redirect fails
  with "Invalid origin" on every token exchange. List origins exactly.
    - Re-imports do NOT overwrite an existing realm/client: delete it
      (`DELETE /admin/realms/master/clients/<id>` is too blunt — recreate the
      stack or PUT via the admin API) before a changed import takes effect.
      Import strategy is `IGNORE_EXISTING` (`KC-SERVICES0030`): adding the
      `otel-ingest` scope to the `aurelius` client (DD-193) applied only on
      `docker compose down -v && up -d` (fresh DB); tokens minted before that
      carry no `aud`, which the collector's OIDC receiver rejects — the first
      suspect when telemetry 401s on a long-lived dev Keycloak.
- The `otel-*` **ingest clients** (DD-196, per-service telemetry identity):
  `otel-atlas-server`, `otel-elasticsearch`, `otel-keycloak`, `otel-postgres` —
  confidential, service accounts only (every flow off), `defaultClientScopes:
["basic", "otel-ingest", "roles"]` so their tokens carry `aud: otel-collector`
  exactly like the browser leg's user tokens, `secret:
"${OTEL_INGEST_CLIENT_SECRET}"` resolved by the same `replace-placeholders`
  flag as the dev-user passwords. One shared dev client secret (the clients
  differ by id; per-producer secrets are a deployment concern). The collector's
  per-service leg (4317/4319) accepts their client-credentials JWTs and stamps
  `azp` as `otel.ingest.client`. **Rotation**: bump
  `OTEL_INGEST_CLIENT_SECRET` in every consumer `.env` (the three slice pullers,
  the Atlas server — list at DD-196) **and** recreate the Keycloak stack (the
  import applies only on a fresh DB — `docker compose down -v && up -d`, the
  `IGNORE_EXISTING` rule above applies to client secrets too), then restart the
  producers. Adding/renaming an `otel-*` client has the same rule: a running
  stack will not pick up the import.
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

## Helm chart

`helm/` — the `atlas-keycloak` chart (CHT-02): Keycloak 26.7 with the bundled
Postgres (`postgres.*` values; `flavor=external` points at an existing
database). Landed in 10.2 (CHT-16/17): the prod-mode StatefulSet
(`kc.sh start --import-realm` — never `start-dev`) running as the image's uid
(65532, which owns `/opt/keycloak/lib/quarkus` where the start re-augments —
a foreign uid cannot write it, DD-257), the realm ConfigMap (the
`files/master.json` chart asset — a byte-copy of `import/master.json`, the
drift guard is a chart-contract test, DD-256; the `${DEV_USER_*}` /
`${OTEL_INGEST_CLIENT_SECRET}` placeholders resolve inside Keycloak via
`-Dkeycloak.migration.replace-placeholders=true` fed from the generated
Secrets, never by Helm substitution), the RSS headless Service JGroups
discovers through, HTTPS management-port probes (prod mode puts TLS there
too — DD-260), and the bundled Postgres section
(the compose's cert-copy boot: mktemp + `install -m 600`, `ssl=on` flags, the
pg_hba ConfigMap, the `/tmp` tmpfs). The JVM trusts the cluster CA through the
mounted issuer `ca.crt` — the dev truststore workaround is never rendered.
Remember the
issuer pin (runbook): Keycloak fixes its realm issuer at first boot, so the
chart's `global.domain`/issuer URL is immutable for a volume. Conventions:
`helm/AGENTS.md`.

```bash
npx nx run aurelius-atlas-dev-keycloak:helm-template
```

## Removal

Part of the spine. Removing it means replacing auth in the FastAPI example and
dropping the Keycloak config/interceptor wiring from the frontend.
