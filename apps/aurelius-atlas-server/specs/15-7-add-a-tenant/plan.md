# 15.7 Plan

The steps, in order, each with the rules it delivers and its tests. The spec is [`spec.md`](./spec.md).

1. **The realm's people** (`realm_tenants.py`): `create_user`, a user made with its representation, its id
   from the `Location`; `add_to_groups`, a member put in organization groups, a group it has already counted
   as done (`present=True`). The fake Keycloak learns `POST /users`, 409 for a taken username.
2. **A tenant's people** (`tenant_people.py`, new): the three roles and their groups; a generated temporary
   password that meets the realm's policy; `ensure_person`, a user found or made, then made a member of the
   tenant with the groups of its role. TAD-03 to TAD-06.
3. **The command** (`provisioning.py`): the subcommands `add`, `user` and `samples`, the sample folder as the
   setting `sample_dir`, and the summary. `add` reuses `provision --existing-ok` and `admin`. TAD-01, TAD-02,
   TAD-07 to TAD-11. Tests in `tests/test__aurelius_atlas_server_tenant_people.py`.
4. **The stack** : the one shot `tenants` seeds demo and meyn through `ensure_person` with their permanent
   passwords (TAD-13), and gets `AURELIUS_ATLAS_SERVER_SAMPLE_DIR`; `docker/bin/tenant.sh` runs the command in
   it (TAD-12). The bundle's README names the script, and the workspace tests list it.
5. **The guide**: `docs/user-guide/standalone-tenants.md` rewritten around `docker/bin/tenant.sh`.
6. **Verify**: the server, core and workspace suites, the hooks, then by hand on the standalone stack as the
   spec's acceptance lists.
