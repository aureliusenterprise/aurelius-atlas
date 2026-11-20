# 15.10 Plan

The steps, in order, each with the rules it delivers and its tests. The spec is [`spec.md`](./spec.md). One pull
request.

1. **Who is a Viewer** (TDL-01 to TDL-03): the realm's members of a tenant's group `atlas-write`
   (`realm_tenants.py`); the command keeps those and the record's operator members as the Viewers, and
   `grafana sync` keeps those people alone in Grafana (`provisioning.py`). Tests in
   `test__aurelius_atlas_server_grafana_tenants.py`, the stand-in realm answering a group's members.
2. **The organization id in the record** (TDL-04): `StoredTenant.grafana_org` and its mapping, written by the
   command after it keeps the tenant's Grafana organization.
3. **The answer** (TDL-05 to TDL-07): the setting `grafana_public_url`; `GET /api/aurelius/v1/tenancy/dashboards`
   in `routes/tenancy.py`, reading the user's tenant roles and the operator role from the request's user and the
   record from the tenants index. Tests in `test__aurelius_atlas_server_tenancy_dashboards.py`.
4. **The menu item** (TDL-08 to TDL-10): the webapp asks the answer once after sign-in with tenancy on and shows
   "Dashboards" under "Switch tenant" on 200; the Dutch translation. Header unit tests.
5. **The stack** (TDL-11): the standalone server's public Grafana address; the workspace test.
6. **Docs**: the tenant guide's dashboards section (who sees them, the menu item).
7. **Verify**: the server, webapp and workspace suites and the hooks; by hand the spec's acceptance on the
   standalone stack.
