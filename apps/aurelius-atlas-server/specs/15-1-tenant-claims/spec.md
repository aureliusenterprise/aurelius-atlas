# 15.1 Tenant claims

- **Status:** in progress
- **Pull request:** to follow
- **Records:** ADR 063 (Proposed); DD-563 to DD-567 (here); relies on 6.1 (AUT-02, AUT-03, DD-250) and 6.2
  (AUZ-01 to AUZ-03, DD-300)

Series 15 lets one deployment serve several tenants (ADR 063). A tenant is a Keycloak organization, and it has
its own indices. A person can belong to several organizations, with different Atlas roles in each. This first
increment teaches the server to read a request's tenant and its roles in that tenant from the token. It also
refuses the requests that name no tenant, several tenants, or one that isn't provisioned. And it caps the
operators, the members of the default organization that runs the platform, at read access in every other
tenant. The later increments hang the tenant's stores, provisioning, workers, realm and webapp on that.

## Scope

- `aurelius-atlas-server`:
    - the settings `tenancy_enabled`, `tenancy_operator_organization`, `tenancy_operator_role`,
      `tenancy_tenants` and `auth_organization_claim` (`settings.py`);
    - a request's tenant and its roles in that tenant, read from the token's claims (`authentication.py`), for
      a bearer token and a browser session alike (`oidc_client.py`);
    - the refusals, in Atlas's error shape;
    - the tenant on the request's context, for the stores of 15.2.

Not delivered, with the increment that will:

| Not delivered                                                                                                                                                                                      | Lands with |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Each tenant's own indices and type registry, the operator organization's being today's; the routes reading the tenant's stores                                                                     | 15.2       |
| The `aurelius-atlas-tenants` index and the CLI that provisions and removes a tenant, with or without the sample data, and records its trust of the operators                                       | 15.3       |
| The task, App Search, embedding, audit-aging and metrics workers per tenant                                                                                                                        | 15.4       |
| The realms' organizations and groups, the operators' membership of each trusting tenant kept in step, the operators' role in the store, the server login's organization scope, the service clients | 15.5       |
| The webapp's organization scope, its current tenant and switching                                                                                                                                  | 15.6       |

Until 15.2, every tenant reads and writes the default index set, so tenancy must not be turned on in a
deployment yet. No chart or compose file sets it (DD-566).

## Semantics

"The tenancy setting" is `AURELIUS_ATLAS_SERVER_TENANCY_ENABLED`. "The four roles" are AUZ-02's `atlas-read`,
`atlas-write`, `atlas-types` and `atlas-admin`. "A token" is one AUT-02 accepted, whether sent as a bearer token
or held by the browser session it signed in.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TEN-01 | With the tenancy setting off (the default), a request has no tenant, and its user's roles are the server client's roles (AUZ-01). Every answer is as before                                                                                                                                                                                                                                            |
| TEN-02 | With it on, the organizations a token names are those of its organization claim (`auth_organization_claim`, `organization` by default): the strings of a list (Keycloak's Organization Membership mapper), or the keys of an object (the same mapper with the id or attributes, or the Organization Group Membership mapper). A missing claim, or one of another shape, names none                     |
| TEN-03 | With it on, a token that names exactly one organization acts in that tenant. A token naming none answers 403 `AURELIUS-403-00-001`, `<user> acts in no tenant: the token names no organization`, and one naming several answers 403 `AURELIUS-403-00-002`, `<user> acts in no tenant: the token names <n> organizations` (DD-563)                                                                      |
| TEN-04 | With it on, a tenant whose alias is not a lowercase letter or digit, followed by up to 62 lowercase letters, digits or `-`, or that is neither the operator organization (`tenancy_operator_organization`, `operators` by default) nor among `tenancy_tenants`, answers 403 `AURELIUS-403-00-003`, `Tenant <alias> is not provisioned` (DD-565, DD-567)                                                |
| TEN-05 | With it on, the user's roles in the tenant are the four roles whose group `/<role>` is among the tenant's own groups: the `groups` list under the tenant's alias in the organization claim, as Keycloak's Organization Group Membership mapper writes it. A group of another organization, a nested group, a role outside the four, a realm group and the server client's roles grant nothing (DD-564) |
| TEN-06 | With it on, in a tenant other than the operator organization, a user holding the operator realm role (`tenancy_operator_role`, `atlas-operator` by default) holds at most `atlas-read` there, whatever TEN-05 grants (DD-567)                                                                                                                                                                          |
| TEN-07 | The refusals of TEN-03 and TEN-04 come after the token is accepted and before the request reaches its route. They answer in Atlas's error shape, `{"errorCode", "errorMessage"}`, to an API path and a dashboard page alike, and a browser session that signs in with such a token is not kept                                                                                                         |
| TEN-08 | With it on, the request's context carries its tenant: the request's state for the routes, and the core's `RequestContext` for the stores                                                                                                                                                                                                                                                               |
| TEN-09 | No answer of Apache Atlas's API changes while the tenancy setting is off                                                                                                                                                                                                                                                                                                                               |

## Java origin

None: Apache Atlas has no tenants (ADR 063). TEN-05 replaces, while tenancy is on, how AUZ-01 reads the roles
from Keycloak's client roles. That reading ports `AtlasKeycloakAuthenticationProvider` (6.2).

## Deviations

[DV-163](../../../../docs/architecture/conversion/deviations.md): with tenancy on, a request without one
provisioned organization in its token is refused, roles are read per organization, and an operator holds at most
read access outside the operator organization. While the setting is
off, nothing deviates.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_authentication.py`:
    - TEN-01 and TEN-02: `user_of` over claim sets, with tenancy off and on, with the organization claim as a
      list, an object, missing, and malformed;
    - TEN-05: the roles from the tenant's own groups in the organization claim only, not another
      organization's, a realm group or the client roles;
    - TEN-06: an operator's roles in another tenant capped at `atlas-read`, and kept whole in the operator
      organization.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_tenancy.py`:
    - TEN-03, TEN-04 and TEN-07: requests with tokens naming no, one, two, the operator, and an unprovisioned
      or malformed organization, on an API path and a dashboard path, by bearer token and by session sign-in;
    - TEN-06: an operator's write refused in a trusting tenant, and allowed in the operator organization;
    - TEN-08: the tenant on the request state and the bound context;
    - TEN-07: a session whose refreshed token names no tenant is signed out;
    - TEN-09: the existing server suite, with tenancy off, unchanged.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_settings.py`: TEN-01 and TEN-04, the settings
  off by default, read when on, and the operator organization refused among the tenants.
- `uv run pytest apps/aurelius-atlas-server/tests` (level 0) and `nx test aurelius-atlas-server -c ci`
  (level 1).
