# aurelius-atlas-dev-keycloak

Local development Keycloak (identity provider) with a pre-imported realm matching
what the FastAPI backend and Angular frontend expect.

Part of the template **spine**.

## Services

| Service           | Image                           | Host port  | Notes                      |
| ----------------- | ------------------------------- | ---------- | -------------------------- |
| Keycloak          | `dhi.io/keycloak:26.7-debian13` | 8080, 8443 | `start-dev --import-realm` |
| postgres-keycloak | Postgres (internal, TLS-only)   | —          | Keycloak's own database    |

- Two listeners (ADR 039): plaintext `http://keycloak.localhost:8080` for the dev
  browser, and TLS `https://keycloak.localhost:8443` used by E2E/CI. Both issuers
  are what Keycloak advertises (`KC_HOSTNAME=keycloak.localhost`).
- Its database connects with `sslmode=verify-full` against the local CA (`nx certgen`).
- Realm/client definitions are imported from `import/master.json` on startup —
  edit those files to change realms, clients, or test users:
    - `import/master.json` — the `master` realm: admin console plus the
      FastAPI/Angular clients and test users
- Telemetry is exported via OTLP over TLS to the observability stack
  (`https://otel-collector:4317`, trusted via this project's `certs/truststore.p12`)

## Running

```bash
nx serve aurelius-atlas-dev-keycloak
```

The `serve` target first runs `decrypt` (SOPS) and the project's `docker-build`,
and starts its dependencies (`aurelius-atlas-dev-observability`). Keycloak can take a
couple of minutes to become healthy on first start.

> [!NOTE]
> `keycloak.localhost` resolves to 127.0.0.1 on most systems. Log in with the
> credentials defined in `import/master.json` for the admin console.
