# Plan: 15.6 The webapp's tenant

The rules are TNW-01 to TNW-10 of [the spec](./spec.md), the design DD-634 to DD-636.

## Analysis

- **The server:** `ServerSettings.tenancy()` answers the tenancy or None; `authentication.OPEN_PATHS` lists the
  paths that need no user; the Aurelius routes sit under `/api/aurelius/v1`.
- **The start:** `initialize()` in `app.config.ts` loads `/config.json`, then builds the providers;
  `keycloakInitOptions()` gives `check-sso` with the silent redirect. keycloak-js takes a `scope` in its init
  options and in each `login()`.
- **The sign-in:** `rootAuthGuard` in `routes.ts` calls `keycloak.login({ redirectUri })`.
- **The menu:** `ShellHeader` and its template; `Session` reads the parsed token.
- **The gate:** `canWriteEntities()` reads `hasResourceRole("atlas-write", atlasClientId)`.
- **Strings:** the shell fixtures feed `tools/generate-legacy-catalogue.mjs`.

## Steps

1. Server: `routes/tenancy.py`, the path open, the router mounted; its test.
2. `tenancy.ts`: the answer's shape and read, the tenant of a token, the memory, the scopes.
3. `app.config.ts`: the answer read in `initialize()`, the `TENANCY` token, the init scope; `routes.ts`: the
   guard's scope.
4. `Session`: the tenant, remembered; the header's tenant and "Switch tenant".
5. `can-write-entities.ts`: the tenant's groups and the operator cap.
6. The shell fixtures, the catalogue regenerated.
7. Tests; ledger: roadmap status, the webapp's `AGENTS.md`.

## Verification

Level 0: `nx test aurelius-atlas-webapp -c ci`, `nx lint aurelius-atlas-webapp`, the purity check,
`uv run pytest apps/aurelius-atlas-server/tests`; the hooks at commit.
