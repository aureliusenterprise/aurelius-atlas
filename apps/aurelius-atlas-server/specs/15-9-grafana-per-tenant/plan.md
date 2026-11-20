# 15.9 Plan

The steps, in order, each with the rules it delivers and its tests. The spec is [`spec.md`](./spec.md). One pull
request; it reworks the unmerged commit 303fcf80d, whose dashboards it keeps.

1. **The realm and the secrets** (TGF-01): the client `grafana` in `docker/keycloak/aurelius-atlas.json`, modelled
   on the chart's realm's, with the stack's redirect and the organization claim; `GRAFANA_CLIENT_SECRET` and
   `GRAFANA_ADMIN_PASSWORD` in `infra/keycloak/.env.enc`, the first passed to Keycloak's import.
2. **Grafana behind the proxy** (TGF-02, TGF-03): in `docker/observability/compose.yaml`, Grafana in the
   proxy's network with `root_url` `https://localhost:9000/grafana/` and `serve_from_sub_path`, its port
   unpublished, anonymous access and the login form off, generic OAuth on `grafana`, no role or organization
   taken from the token, new users joining the main organization with the role `None`, the local
   administrator's password from `GRAFANA_ADMIN_PASSWORD`; in `docker/gateway/nginx.conf`, the route
   `/grafana/` to it. The files of 303fcf80d's data sources and dashboards leave its mounts.
3. **Grafana's API in the server** (TGF-04 to TGF-09, TGF-11, TGF-12): `grafana_tenants.py`, a client of the
   organizations, users, members, data sources, dashboards and folders the spec names; the settings
   `grafana_url`, `grafana_admin_user` and `grafana_admin_password`; the dashboards as package data,
   `aurelius_atlas_server/grafana/*.json`, moved from 303fcf80d with their data sources named by uid.
4. **The command** (TGF-04 to TGF-11): `add`, `user add`, `user remove`, `remove` and `operators` call it after
   their realm steps; the subcommand `grafana sync`. The tenant's reader in the store, with its generated
   password (DD-734).
5. **Tests**: `test__aurelius_atlas_server_grafana_tenants.py` against a stand-in Grafana API, recording its calls
   and answering as Grafana does; the command's tests extended; the workspace test of the realm, the compose
   pieces and the proxy route.
6. **The stack's seeding** (TGF-13): the one shot `tenants` names the Grafana settings and seeds demo and meyn;
   `grafana_demo_reader`, its role and `GRAFANA_ES_READER_PASSWORD` retired.
7. **Docs**: the stack's README and the tenant guide: Grafana's address, signing in, what each person sees, and
   `grafana sync` for people added in the console.
8. **Verify**: the server and workspace suites and the hooks; by hand the spec's acceptance on a fresh stack.
