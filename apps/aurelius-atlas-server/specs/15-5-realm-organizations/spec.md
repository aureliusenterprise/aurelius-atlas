# 15.5a Organizations in the realm

- **Status:** in progress
- **Pull request:** to follow
- **Records:** ADR 063 (Proposed); DD-580 to DD-583 (here); relies on 15.1 (TEN-02 to TEN-06, DD-564, DD-567)

15.1 taught the server to read a request's tenant and its roles from the token's organization claim. No realm
issued that claim yet. This increment sets up the realms the repository ships, dev, standalone and chart, so that
a token names one organization with its groups: organizations on, the operator organization with its four role
groups, the operator realm role, the mapper that writes an organization's groups into the token, and the
organization scope on the clients. The server's sign-in asks for that scope while tenancy is on. The store gains
the operators' read role. 15.5b makes and removes a tenant's organization as the tenant is provisioned and
removed, and keeps the operators' membership in step with the tenant's trust.

## Scope

- `dev/keycloak`: the dev realm (`import/master.json`, carried by the chart as `helm/files/master.json`) and the
  chart's production realm (`helm/files/aurelius-atlas.json`);
- `apps/aurelius-atlas-server`: the standalone stack's demo realm (`standalone/keycloak/demo.json`); the sign-in's
  scope (`oidc_client.py`, `app.py`);
- `dev/elasticsearch`: the store's operator role, in dev and the chart (`config/roles.yml`, `helm/`).

Not delivered, with the increment that will:

| Not delivered                                                                                                         | Lands with |
| --------------------------------------------------------------------------------------------------------------------- | ---------- |
| A tenant's organization and its four groups made and removed by `provision` and `remove`                              | 15.5b      |
| The operators made members of each trusting tenant with `/atlas-read`, kept in step with trust and with the operators | 15.5b      |
| Each tenant's delegated administrator                                                                                 | 15.5b      |
| The webapp asking for the organization scope, showing the tenant, and switching                                       | 15.6       |

## Semantics

"The realms" are the dev realm (`master`), the chart's production realm (`aurelius-atlas`) and the standalone
stack's demo realm (`demo`). "The four groups" are an organization's top-level groups `atlas-read`,
`atlas-write`, `atlas-types` and `atlas-admin` (DD-564). "The group mapper" is Keycloak's Organization Group
Membership mapper (`oidc-organization-group-membership-mapper`), which writes the organizations a token names
with their groups: `"organization": {"operators": {"groups": ["/atlas-read"]}}`.

| Id     | Rule                                                                                                                                                                                                                                                                                                  |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RLM-01 | Each realm has organizations enabled, the realm role `atlas-operator` (TEN-06), and the organization `operators`, alias `operators`, with the four groups (DD-580)                                                                                                                                    |
| RLM-02 | In each realm, the server's client `aurelius-atlas-server` and the webapp's client `aurelius` carry the group mapper and offer `organization` as an optional scope. A token asked for without that scope is as before                                                                                 |
| RLM-03 | With the tenancy setting on, the server's browser sign-in asks for the scopes `openid organization`, so Keycloak lets a person in several organizations choose the one to act in, and the token names it. With the setting off, it asks for `openid` alone, as before (DD-582)                        |
| RLM-04 | In the dev realm, each service client (`aurelius-atlas-db-scanner`, `-kafka-scanner`, `-quality-scanner`, `-validate-entity`) carries the group mapper and `organization` as a default scope, and its service account is a member of `operators` in the groups of its client roles (DD-581)           |
| RLM-05 | In the dev realm, `aurelius-writer` and `aurelius-reader` are members of `operators` in the groups of their client roles, and `aurelius-writer` holds `atlas-operator`                                                                                                                                |
| RLM-06 | In the demo realm, `atlas` holds `atlas-operator` and is a member of `operators` in the four groups. The sample tenant `acme` has the four groups, `steward` in `atlas-read` and `atlas-write`, `scientist` in `atlas-read`, and `atlas` in `atlas-read`, as the operators' trust makes them (DD-580) |
| RLM-07 | Every user keeps the server client's roles they held, so with the tenancy setting off a user's roles are as before (AUZ-01). The production realm still seeds no person                                                                                                                               |
| RLM-08 | The store defines the role `aurelius_atlas_operator`: `read`, `view_index_metadata` and `monitor` on `aurelius-atlas-*`, and the cluster's `monitor`, in dev and the chart. The deployment decides who holds it (DD-583)                                                                              |
| RLM-09 | With the tenancy setting off, no answer of Apache Atlas's API changes                                                                                                                                                                                                                                 |

Keycloak imports a realm only when it doesn't exist yet. A deployment whose realm exists keeps it as it was;
its administrator adds the organizations, groups, role, mappers and scopes by hand, as for any change of the
realm files.

## Java origin

None: Apache Atlas has no tenants (ADR 063). Its Keycloak authentication reads the client's roles, which every
realm keeps.

## Deviations

None beyond DV-163: no Atlas endpoint changes, and with tenancy off the tokens' roles are as before.

## Acceptance

- `tests/test__realm_organizations.py`: RLM-01, RLM-02, RLM-04 to RLM-07 on the three realm files, the dev
  realm byte-equal in the chart (CHT-75's existing test); RLM-08 on the dev store's role file and the chart's
  render.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_authentication.py` and `…_tenants.py`: RLM-03,
  the authorization URL's scope with tenancy off and on.
- A run against Keycloak 26.7.4 (recorded in DD-580 and DD-582): the realms import, a token of each kind names
  one organization with its groups, and the sign-in shows the organization choice.
- `uv run pytest apps/aurelius-atlas-server/tests tests` (level 0).
