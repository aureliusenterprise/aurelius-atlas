# Plan: 15.1 Tenant claims

The rules are TEN-01 to TEN-09 of [the spec](./spec.md), the design DD-563 to DD-567.

## Analysis

- **Where a user is made:** `authentication.user_of` turns verified claims into a `User` (name, groups, the
  server client's roles). Two callers: `AuthenticationMiddleware._bearer` for a bearer token and
  `OidcClient._apply` for a session's sign-in and each refresh. The tenant is read at the same point, so both
  paths get it from one function.
- **Where a refusal can answer:** `_bearer` runs in a `BaseHTTPMiddleware`, where FastAPI's exception handlers
  don't reach. It answers through `atlas_error_handler` itself, which keeps Atlas's error shape (TEN-07). The
  sign-in's `login` route catches the refusal, removes the session and answers the same way. A refresh whose
  new token is refused signs the session out, as a refused refresh does today (AUT-06). The next page then
  goes through sign-in again, which answers 403.
- **The roles:** `authorization.ROLE_PRIVILEGES` is keyed by the four roles. `authorization` imports
  `authentication`, so the four role names live in the new `tenancy` module, and a test pins them to the
  privilege table's keys.
- **The context:** `RequestContextMiddleware` binds the core's `RequestContext` inside the authentication.
  `RequestContext` gains `tenant: str | None = None`, so 15.2's stores can read it. `request.state.tenant`
  serves the routes.
- **The codes:** Aurelius's own codes sit at the end of `AtlasErrorCode` (`AURELIUS-404-00-001` …). The three
  refusals are `AURELIUS-403-00-001` to `-003`.

## Chosen scope

The settings, the `tenancy` module, the user's tenant on both authentication paths, the refusals, the tenant on
the request state and the core's context, and the tests. No chart, compose or realm change (DD-566).

## Steps

1. `aurelius-atlas-model` `errors.py`: `NO_TENANT`, `SEVERAL_TENANTS` and `TENANT_NOT_PROVISIONED` (TEN-03,
   TEN-04).
2. `aurelius-atlas-core` `request_context.py`: `RequestContext.tenant` (TEN-08).
3. `settings.py`: `tenancy_enabled`, `tenancy_operator_organization`, `tenancy_operator_role`,
   `tenancy_tenants` and `auth_organization_claim`. A validator refuses the operator organization among the
   tenants (DD-567), and `tenancy()` builds the `Tenancy` the authentication reads, or `None` while the setting
   is off (TEN-01).
4. `tenancy.py`: `Tenancy`, `TENANT_ROLES`, `ALIAS`; `organizations(claims, claim)` (TEN-02); `tenant_of`
   (TEN-03, TEN-04); `tenant_roles` (TEN-05) and the operator cap (TEN-06).
5. `authentication.py`: `User.tenant`; `user_of(..., tenancy=None)` reads the tenant and its roles, or raises
   the refusal; `_bearer` answers the refusal in Atlas's shape and sets `request.state.tenant` (TEN-07,
   TEN-08).
6. `oidc_client.py`: the `tenancy` it names users with; `fresh` signs out a session whose refreshed token is
   refused. `routes/login.py`: a refused sign-in removes the session and its cookie and answers 403 (TEN-07).
   `app.py`: `build_oidc` passes `settings.tenancy()`, and `app.state.tenancy` holds it.
7. `request_context.py`: the tenant bound (TEN-08).
8. Tests: `test__aurelius_atlas_server_authentication.py` (TEN-01, TEN-02, TEN-05, TEN-06 over `user_of`);
   `test__aurelius_atlas_server_tenancy.py` (TEN-03, TEN-04, TEN-06 to TEN-08 over HTTP, by bearer and
   session); the settings test for the new settings; the existing suite for TEN-09.
9. Ledger: `java-map.md` has no Java class to add (none is ported); `deviations.md` DV-163 is in. The server's
   `AGENTS.md` names `tenancy.py`.

## Verification

Level 0: `uv run pytest apps/aurelius-atlas-server/tests libs/python/aurelius-atlas-model/tests
libs/python/aurelius-atlas-core/tests`, `nx lint`/`nx typecheck` on the three projects. Level 1 at commit through
the toolbox.
