# aurelius-atlas-auth

Keycloak bearer-token authentication shared by the Aurelius Atlas services
(8.0, DD-197). This file covers wiring specific to this lib; workspace-wide
rules live in the root `AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_auth/auth.py` — `AuthConfig` (what an app maps its settings
  into), `KeycloakAuth` (the verifier: `require_bearer` / `require_auth` /
  `require_write` route dependencies, the circuit-broken JWKS cache), and the
  shared `bearer_scheme`

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`).
- The app owns the lifecycle: build `KeycloakAuth(config)` in `create_app`,
  call `auth.close()` in the lifespan's shutdown.
- The rules it keeps (AUX-01..AUX-05) are specified by the 8.0 spec
  (`docs/architecture/conversion/increments/8-0-auxiliary-api-foundation.md`).
- A service that gates writes needs its write role assigned through Keycloak:
  a realm role, or a client role on the service's own client —
  `dev/keycloak/import/master.json` carries the dev users (see the
  `aurelius-write` pattern of the `aurelius` client).

## Conventions

- Libraries read no env vars: apps pass an `AuthConfig` built from their own
  pydantic-settings (issuer URL, realm, audience, write role, CA file).
- `write_role=''` disables the write gate — the development-only posture;
  apps enforce non-empty roles outside development in their settings.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-auth/tests
```

## Removal

The auxiliary API apps (8.1-8.3) depend on it; removing it means removing them.
