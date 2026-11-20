# 15.9 Grafana per tenant

- **Status:** planned
- **Pull request:** to follow
- **Records:** ADR 063 (Proposed); DD-735 to DD-738 (here); relies on 15.7 (TAD-01 to TAD-13), 15.5b (TRM-02,
  TRM-03, TRM-05), 17.1 (IRT-06, DD-700) and 10.15 (DD-661, the chart's Grafana sign-in)

The standalone stack's Grafana shows the demo tenant's dashboards to anyone on the machine: anonymous access,
one read-only store user for the demo tenant, data sources and dashboards from files. This increment puts Grafana
behind Keycloak and gives each tenant a Grafana organization of its own, with data sources that read that
tenant's indices alone and the same dashboards. A tenant's members see their tenant's organization; the
operators see the platform's own dashboards too. The tenant command of 15.7 keeps Grafana in step: adding a
tenant or a person adds them in Grafana, removing them removes them.

## Scope

- The stack's realm (`docker/keycloak/aurelius-atlas.json`): the confidential client `grafana`.
- The stack's Grafana (`docker/observability/`, `docker/gateway/`): served behind the proxy at
  `https://localhost:9000/grafana/`, signing in through Keycloak alone; the demo tenant's data sources and
  dashboards no longer from files.
- `aurelius-atlas-server`:
    - a tenant's Grafana organization, data sources, dashboards and members through Grafana's API
      (`grafana_tenants.py`, new), with the dashboards shipped in the package;
    - the command's `add`, `user add`, `user remove`, `remove` and `operators` keeping Grafana in step, and the
      new subcommand `grafana sync` (`provisioning.py`);
    - the settings of the Grafana API (`settings.py`).
- The secrets `GRAFANA_CLIENT_SECRET` and `GRAFANA_ADMIN_PASSWORD` in `infra/keycloak/.env.enc`.

Not delivered, with the increment that will:

| Not delivered                                                                                | Lands with        |
| -------------------------------------------------------------------------------------------- | ----------------- |
| Grafana per tenant on Kubernetes: the chart's Grafana, the Job of 15.8 keeping it in step    | a later increment |
| Charts of the indices with no time field: governance quality, relationships, classifications | a later increment |
| A tenant member editing or adding dashboards                                                 | not planned       |

## Semantics

"The command" and "the tenant script" are as in 15.7: `python -m aurelius_atlas_server.provisioning` and
`docker/bin/tenant.sh`. "Grafana's API" is the stack's Grafana's HTTP API, called as its local administrator.
"A tenant's Grafana organization" is the Grafana organization named after the tenant's alias. "The platform's
organization" is Grafana's main organization, which holds the infra slice's dashboards. "A tenant's reader" is
the store user `grafana_<tenant>_reader`.

### Signing in

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TGF-01 | The stack's realm holds the confidential client `grafana`, its secret the placeholder `${GRAFANA_CLIENT_SECRET}`, its only redirect `https://localhost:9000/grafana/login/generic_oauth`, and the organization claim in its tokens as the client `aurelius` has it                                                                                           |
| TGF-02 | The stack's Grafana answers at `https://localhost:9000/grafana/` behind the proxy and publishes no port of its own. A browser signs in through Keycloak alone: no anonymous access and no login form. The local administrator remains for Grafana's API, reached on the stack's network alone (DD-735)                                                       |
| TGF-03 | Grafana takes a person's login, name and email from the token and gives no one a role from it. Every person is a member of Grafana's main organization, the platform's, with no role, which shows them nothing there; the command makes them a Viewer where they may read (TGF-07, TGF-09) and their own tenant's organization the one they land in (DD-736) |

### A tenant in Grafana

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TGF-04 | `add <tenant>` makes, after the tenant's people (TAD-01), the tenant's Grafana organization if it is missing, and in it the data sources and dashboards of TGF-05 and TGF-06. A tenant whose Grafana organization exists keeps it as it is, and gets what is missing                                                                                                                                                            |
| TGF-05 | A tenant's Grafana organization has two Elasticsearch data sources, the tenant's entities by `createTime` and its audit events by `timestamp`, read as the tenant's reader over TLS against the store's CA. The tenant's reader has a role that reads `aurelius-atlas-tenant-<tenant>-*` and the cluster's status, and nothing else. Its password is generated by the command and held by Grafana's data sources alone (DD-737) |
| TGF-06 | A tenant's Grafana organization holds the dashboards _catalogue_ and _activity_, shipped with the server's package and pointed at its own data sources. They are read-only (DD-738)                                                                                                                                                                                                                                             |
| TGF-07 | Each member of a tenant is a Viewer of the tenant's Grafana organization: those `add` and `user add` make or find, added when the command adds them to the tenant (TAD-04, TAD-07). A person who has never signed in to Grafana is made in it, with their username and email and no password, so that their first sign-in finds the membership. A person of one tenant lands in that tenant's organization                      |
| TGF-08 | `user <tenant> remove <username>` takes the person out of the tenant's Grafana organization too (TAD-09). `remove <tenant>` deletes the tenant's Grafana organization, with its data sources and dashboards, and the tenant's reader (TPR-05)                                                                                                                                                                                   |

### The platform

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                    |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TGF-09 | The members of the realm's `operators` organization are Viewers of the platform's organization; everyone else is a member of it with no role. A tenant's operators, the members trust gives it in the realm (TRM-03), are Viewers of its Grafana organization as its other members are                                                                                                  |
| TGF-10 | `grafana sync` brings every `active` tenant's Grafana organization, data sources, dashboards and members in step with the realm, and the platform's organization with the operators: missing ones are made and added, people no longer in a tenant are taken out. `operators` (TRM-05) ends with it, so the CronJob-free stack keeps Grafana in step whenever the tenant script runs it |
| TGF-11 | Without the Grafana settings (TGF-12), the command leaves Grafana alone and says so once, as it does without the realm (TRM-01). A failed Grafana call stops the command and says which; the store and the realm keep what they have, and running the command again finishes Grafana (TAD-11)                                                                                           |
| TGF-14 | `grafana sync` deletes from Grafana each person the realm no longer has, and each person who is a member of no `active` tenant and no operator. Grafana's local administrator is never deleted. A deleted person who later joins a tenant is made again by the command (TGF-07)                                                                                                         |
| TGF-15 | If Grafana refuses to delete the tenant's Grafana organization, `remove <tenant>` empties it instead (its members other than Grafana's administrator, its data sources and its dashboards), says so, and finishes the removal. Adding the tenant back finds that organization by name and fills it again (DD-765)                                                                       |

### Settings and the stack

| Id     | Rule                                                                                                                                                                                                                                                                                                                                  |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TGF-12 | The command reaches Grafana's API at `AURELIUS_ATLAS_SERVER_GRAFANA_URL` as `AURELIUS_ATLAS_SERVER_GRAFANA_ADMIN_USER` with `AURELIUS_ATLAS_SERVER_GRAFANA_ADMIN_PASSWORD`; the stack's one shot `tenants` names them, the password `GRAFANA_ADMIN_PASSWORD`, which also sets Grafana's local administrator                           |
| TGF-13 | The stack's one shot `tenants` seeds demo's and meyn's Grafana organizations through the same code as `add` (TAD-13), so a fresh stack shows the demo tenant's dashboards as 303fcf80d did. The files of that commit's data sources and dashboards, its store user `grafana_demo_reader` and `GRAFANA_ES_READER_PASSWORD` are retired |

## Java origin

None: Apache Atlas has no tenants and no Grafana.

## Deviations

None against Apache Atlas.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_grafana_tenants.py`: TGF-04 to TGF-11 and
  TGF-14 against a stand-in Grafana API and the fake store and realm.
- `tests/test__standalone_grafana.py` (workspace): TGF-01, TGF-02, TGF-12 and TGF-13 read from the realm file,
  the compose pieces and the proxy's configuration.
- By hand, on the standalone stack:
    - a fresh stack with tenancy: signing in at `https://localhost:9000/grafana/` as `demo_atlas` shows the
      organization `demo` with the two dashboards and the demo tenant's data, and no other organization;
    - as `meyn_scientist`, the organization `meyn` alone, its dashboards empty of demo's data;
    - as `operator`, the platform's organization with the infra slice's dashboards, and `demo` and `meyn`;
    - `docker/bin/tenant.sh add acme --sample small`, then `acme_atlas`'s first sign-in to Grafana shows the
      organization `acme` with the small sample's data;
    - `docker/bin/tenant.sh user acme remove acme_atlas` takes `acme` from that person's Grafana;
    - a person made in Keycloak's console and added to `demo` there sees nothing in Grafana until
      `docker/bin/tenant.sh grafana sync`, then sees `demo`;
    - after `docker/bin/tenant.sh remove acme` and `grafana sync`, `acme_atlas` is no longer a Grafana user.
