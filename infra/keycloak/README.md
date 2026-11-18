# aurelius-atlas-infra-keycloak

Local development Keycloak (identity provider) with a pre-imported realm matching
what the Atlas server, the auxiliary APIs, and the webapp expect.

Part of the template **spine**.

## Services

| Service           | Image                           | Host port  | Notes                      |
| ----------------- | ------------------------------- | ---------- | -------------------------- |
| Keycloak          | `dhi.io/keycloak:26.7-debian13` | 8080, 8443 | `start-dev --import-realm` |
| postgres-keycloak | Postgres (internal, TLS-only)   | —          | Keycloak's own database    |

- Two listeners (ADR 039): plaintext `http://keycloak.localhost:8080` for the dev
  browser, and TLS `https://keycloak.localhost:8443` used by E2E/CI — and by every
  automated token mint (E2E suites, the slice metrics-pullers, the apps' OTLP
  ingest: DD-202 keeps all producers on one issuer). Both issuers
  are what Keycloak advertises (`KC_HOSTNAME=keycloak.localhost`).
- Its database connects with `sslmode=verify-full` against the local CA (`nx certgen`).
- Realm/client definitions are imported from `import/master.json` on startup —
  edit those files to change realms, clients, or test users:
    - `import/master.json` — the `master` realm: admin console plus the
      application clients and test users
- Telemetry is exported via OTLP over TLS to the observability stack
  (`https://otel-collector:4317`, trusted via this project's `certs/truststore.p12`)

## Dev users

`import/master.json` declares two realm users so RBAC works out of the box —
no post-import scripting:

- `aurelius-writer` — has the `aurelius-write` client role (the write gate in
  `aurelius_atlas_auth` requires it on services that enable it; the mutating
  e2e scenarios log in as this user)
- `aurelius-reader` — authenticates but holds no roles (denied on writes)

Their passwords are `${DEV_USER_WRITER_PASSWORD}` / `${DEV_USER_READER_PASSWORD}`
placeholders resolved from the container environment at import time
(`-Dkeycloak.migration.replace-placeholders=true`); the values live in this
project's `.env.enc` like every other dev credential.

The standalone stack's realm `aurelius-atlas`
(`docker/keycloak/aurelius-atlas.json`, DD-673) holds no users, so this project's
`.env` holds no user passwords for it — only the client secrets its import
fills, and `DEMO_USER_OPERATOR_PASSWORD`, which is the store's `operator`
user (the tenants one shot, not this Keycloak). This Keycloak doesn't import
that realm.

> [!NOTE]
> `--import-realm` uses `IGNORE_EXISTING`: changing users/roles requires
> recreating the stack (`docker compose down -v && docker compose up -d`).

## Running

```bash
nx up aurelius-atlas-infra-keycloak
```

The `up` target first runs `decrypt` (SOPS) and the project's `docker-build`,
and starts its dependencies (`aurelius-atlas-infra-observability`). It waits until
every service is healthy, then leaves the stack running. Keycloak can take a
couple of minutes to become healthy on first start.

> [!NOTE]
> `keycloak.localhost` resolves to 127.0.0.1 on most systems. Log in with the
> bootstrap admin credentials (`KC_BOOTSTRAP_ADMIN_USERNAME` /
> `KC_BOOTSTRAP_ADMIN_PASSWORD` in this project's `.env`) for the admin console;
> application users are the `aurelius-*` dev users above.
