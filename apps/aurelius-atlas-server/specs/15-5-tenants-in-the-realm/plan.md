# Plan: 15.5b Tenants in the realm

The rules are TRM-01 to TRM-12 of [the spec](./spec.md), the design DD-600 to DD-603.

## Analysis

- **The command:** `provisioning.py`'s `Provisioner` runs `provision`, `trust`, `list` and `remove` on the store
  and the tenants index; the realm becomes a third collaborator, absent when its secret isn't set.
- **Keycloak's admin API, checked on 26.7.4:** organizations by `search` with `exact=true`, then by alias;
  `POST /organizations/{id}/groups`; members by `POST /organizations/{id}/members` with the user id as a JSON
  string, `DELETE …/members/{user}`; groups by `PUT|DELETE …/groups/{group}/members/{user}`. Permissions live
  in the `admin-permissions` client's resource server: `policy/user` and `permission/scope`, read and written
  in their typed form (`policy/user/{id}`, `permission/scope/{id}`).
- **The record:** `StoredTenant` and the strict mapping of `aurelius-atlas-tenants`; an existing index takes
  the new fields through `put_mapping`.
- **The chart:** the server client's secret is the pattern: the umbrella's generated Secret, the Keycloak chart's
  import env, the server chart's env. The provisioning Job has its env from `atlas-server.provisioningEnv`.

## Steps

1. `realm_tenants.py`: `KeycloakAdmin`, `RealmTenants`, `RealmError`.
2. `tenants.py`: `operator_members` and `administrators`; the mapping put on an existing index.
3. `settings.py`: the client id and secret.
4. `provisioning.py`: the realm in `provision`, `trust`, `remove`; `operators` and `admin`.
5. Realms: the client and its account, admin permissions on; `dev/keycloak/.env.enc`'s secret, the dev compose
   env; the Keycloak chart's env; the umbrella's Secret; the server chart's Job env and CronJob; the standalone
   stack's env.
6. Tests: a fake admin API in `tests/fake_keycloak.py`; the realm tests; the chart and realm file tests.
7. A run against Keycloak 26.7.4.
8. Ledger: roadmap status; `AGENTS.md` of the server and `dev/keycloak`.

## Verification

Level 0: `pytest apps/aurelius-atlas-server/tests tests`, ruff, pyright; the hooks at commit. The Keycloak run
is by hand.
