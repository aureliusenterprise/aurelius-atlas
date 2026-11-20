# 15.10 The tenant's dashboards in the webapp

- **Status:** planned
- **Pull request:** to follow
- **Records:** DD-767 to DD-769 (here); relies on 15.9 (TGF-04 to TGF-10, TGF-14), 15.6 (TNW-01, TNW-06),
  15.5b (TRM-03) and 15.1 (TEN-05, TEN-06)

15.9 gave each tenant a Grafana organization with the catalogue and activity dashboards, but nothing in the
webapp leads there. This increment adds a menu item "Dashboards" under "Switch tenant" in the account menu. It
opens the tenant's catalogue dashboard in Grafana, and only people who may see it are shown it. Who may is
narrowed at the same time: the tenant's stewards and administrators, and the operators the tenant trusts. A
data scientist no longer sees the tenant's dashboards in Grafana either, so the menu never offers a link Grafana
would refuse.

## Scope

- `aurelius-atlas-server`:
    - the Grafana Viewers of a tenant's organization narrowed to its members with the role `atlas-write`
      and its trusted operators (`grafana_tenants.py`, `provisioning.py`, `realm_tenants.py`);
    - the tenant's Grafana organization id kept in its tenant record (`tenants.py`, `provisioning.py`);
    - the setting of Grafana's address for the browser (`settings.py`);
    - the answer `GET /api/aurelius/v1/tenancy/dashboards` (`routes/tenancy.py`).
- `aurelius-atlas-webapp`: the menu item "Dashboards" in the account menu (`shell/`), in English and Dutch.
- The standalone stack: the server's Grafana address for the browser (`apps/aurelius-atlas-server/docker/`).

Not delivered, with the increment that will:

- The chart's Grafana per tenant and its address in the chart's server values: none planned; the chart has no
  Grafana per tenant yet (15.9 delivered the standalone stack only).
- A link to the platform's organization for operators signed in to the operator organization: none planned.

## Semantics

### Who sees a tenant's dashboards

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDL-01 | The Viewers of a tenant's Grafana organization are the members of its organization in the realm who are in its group `atlas-write` (the roles `atlas` and `steward`, TAD-04), and the operators the tenant's trust made members of it (TRM-03, the record's `operatorMembers`). No one else is a member, Grafana's administrator aside. This replaces the half of TGF-07 that made every member a Viewer (DD-767) |
| TDL-02 | `add`, `user add`, `user remove`, `operators` and `grafana sync` keep TDL-01; a role changed in Keycloak's console reaches Grafana at the next `grafana sync` (TGF-10). A person made in Grafana by the command lands in the tenant's organization (TGF-07)                                                                                                                                                       |
| TDL-03 | `grafana sync` keeps in Grafana the people TDL-01 makes a Viewer of an `active` tenant's organization and the operators; it deletes every other Grafana user but the local administrator. This replaces TGF-14's "a member of an active tenant" (DD-767)                                                                                                                                                          |

### What the server answers

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDL-04 | The command writes the tenant's Grafana organization id into its tenant record (`grafanaOrg`) whenever it keeps the tenant's Grafana organization (TGF-04): on `add`, `user add`, `user remove` and `grafana sync`. A tenant without one has none in its record (DD-768)                                                                                                                                                                                                                                         |
| TDL-05 | The setting `AURELIUS_ATLAS_SERVER_GRAFANA_PUBLIC_URL` is Grafana's address as the browser reaches it, distinct from the command's API address (TGF-12). The server never calls Grafana and holds none of its credentials (DD-768)                                                                                                                                                                                                                                                                               |
| TDL-06 | `GET /api/aurelius/v1/tenancy/dashboards`, for a signed-in user, answers 200 with `{"url": "<public URL>/d/tenant-catalogue?orgId=<grafanaOrg>"}` when tenancy is on, the public URL is set, the token's tenant has a `grafanaOrg` in its record, and the user holds `atlas-write` in the tenant (TEN-05) or is one of the operators its trust made members: the token's subject is in the record's `operatorMembers` (TDL-01). The webapp's tokens carry no realm roles, so the operator role itself can't tell |
| TDL-07 | The same call answers 403 when the user may not see the dashboards (TDL-06's role condition fails), and 404 when there are none to see: tenancy off, no public URL, or no `grafanaOrg` for the tenant. Without a user it answers 401, as every Aurelius path does                                                                                                                                                                                                                                                |

### The menu item

| Id     | Rule                                                                                                                                                                                                                               |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDL-08 | With tenancy on, the webapp asks `GET /api/aurelius/v1/tenancy/dashboards` once after sign-in. On 200 the account menu shows "Dashboards" right under "Switch tenant", a link to the answer's URL that opens in a new tab (DD-769) |
| TDL-09 | On any other answer, or no answer, the menu shows no "Dashboards" item and the webapp shows no error                                                                                                                               |
| TDL-10 | The item reads "Dashboards" in English and "Dashboards" in Dutch (`shell.header.dashboards`)                                                                                                                                       |

### The stack

| Id     | Rule                                                                                                   |
| ------ | ------------------------------------------------------------------------------------------------------ |
| TDL-11 | The standalone server's `AURELIUS_ATLAS_SERVER_GRAFANA_PUBLIC_URL` is `https://localhost:9000/grafana` |

## Java origin

None: Apache Atlas has no tenants and no Grafana.

## Deviations

None from Atlas. TDL-01 and TDL-03 narrow 15.9's TGF-07 and TGF-14 (DD-767).

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_grafana_tenants.py`: TDL-01 to TDL-04 against
  the stand-in Grafana API and the fake store and realm.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_tenancy_dashboards.py`: TDL-05 to TDL-07.
- The webapp's header unit tests: TDL-08 to TDL-10.
- `tests/test__standalone_grafana.py`: TDL-11.
- By hand on the standalone stack: `demo_atlas` and `demo_steward` see "Dashboards" and it opens demo's
  catalogue; `demo_scientist` sees no item and Grafana shows them no tenant organization; the operator signed
  in to demo sees the item.
