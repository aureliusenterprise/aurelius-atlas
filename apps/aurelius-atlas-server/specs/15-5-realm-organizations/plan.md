# Plan: 15.5a Organizations in the realm

The rules are RLM-01 to RLM-09 of [the spec](./spec.md), the design DD-580 to DD-583.

## Analysis

- **The realms:** `dev/keycloak/import/master.json` is the dev realm, copied byte for byte into the chart as
  `helm/files/master.json` (CHT-75's test). `helm/files/aurelius-atlas.json` is the production realm, which seeds
  no person. `standalone/keycloak/demo.json` is the demo realm, with three people.
- **Keycloak's shapes:** checked on 26.7.4. `organizationsEnabled`, `organizations[]` with `alias`, `groups[]`
  (fixed ids) and `members[]` (`username`, `groups` by id); the mapper `oidc-organization-group-membership-mapper`;
  `organization` is a scope Keycloak makes in every realm, so a client can name it without the realm declaring
  it.
- **The sign-in:** `OidcClient.authorization_url` sends `scope=openid`; the client knows whether tenancy is on
  through its `tenancy` callable (TPR-07).
- **The store:** the dev stack mounts `config/elasticsearch.yml` alone; the chart's ConfigMap carries
  `elasticsearch.yml` mounted by `subPath`, over a seeded config directory.

## Steps

1. A script in the scratchpad edits the three realm files the same way: organizations on, the role, the
   organization and its groups, the mapper and scopes, the members. The dev realm is copied to the chart.
2. `oidc_client.py`: the scope with tenancy on.
3. The store's `roles.yml`: dev mount, chart ConfigMap and mount.
4. Tests: `tests/test__realm_organizations.py`; the production realm's surface test; the sign-in scope.
5. A run of the three realms on Keycloak 26.7.4: import, tokens, the sign-in's choice.
6. Ledger: the roadmap's 15.5 split into 15.5a and 15.5b; `AGENTS.md` of `dev/keycloak`.

## Verification

Level 0: `pytest apps/aurelius-atlas-server/tests tests`, ruff, pyright; the hooks at commit. The Keycloak run
is by hand, its result in DD-580 and DD-582.
