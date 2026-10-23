# aurelius-atlas-auth

Keycloak bearer-token authentication for the Aurelius Atlas services (8.0,
DD-108): OIDC discovery, JWKS verification (RS256, kid, issuer, azp/aud
audience) and the write-role gate. Ported from the template's FastAPI
example, reshaped as a per-service object so each application owns one
`KeycloakAuth` built from its own settings. This file covers wiring specific
to this lib; workspace-wide rules live in the root `AGENTS.md` and
`libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_auth/auth.py` — `AuthConfig` (what an app maps its settings
  into), `KeycloakAuth` (the verifier: `require_bearer` / `require_auth` /
  `require_write` route dependencies, circuit-broken JWKS cache)

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`).
- The app owns the lifecycle: build `KeycloakAuth(config)` in `create_app`,
  call `auth.close()` in the lifespan's shutdown.
- The rules it keeps (AUX-01..AUX-05) are specified by the 8.0 spec
  (`docs/architecture/conversion/increments/8-0-auxiliary-api-foundation.md`).
- A service that verifies user tokens needs an `aux-write`-style client role
  on its Keycloak client (dev realm: `dev/keycloak/import/master.json`),
  mirroring the webapp client's `aurelius-write` pattern.

## Conventions

- Libraries read no env vars: apps pass an `AuthConfig` built from their own
  pydantic-settings (`auth_server_url`, `auth_realm`, `auth_audience`,
  `auth_write_role`, `auth_ca_file`).
- `write_role=''` disables the write gate — the development-only posture;
  apps enforce non-empty roles outside development in their settings.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-auth/tests
```

## Removal

The auxiliary API apps (8.1-8.3) depend on it; removing it means removing them.
