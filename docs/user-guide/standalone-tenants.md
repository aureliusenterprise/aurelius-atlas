# Add a Tenant to the Standalone Server

This page adds a tenant, a customer or department with its own catalogue and its own people, to a running
[Standalone Server](./standalone-server.md) with tenancy on. The stack's Keycloak imports
`keycloak/aurelius-atlas.json` at every start, so a tenant's organization that should last is added to the
stack's files, not only in Keycloak's console. The realm holds no users (DD-673), so a tenant's people are
always made in Keycloak's console. The example tenant is `acme`; replace it with yours throughout.

!!! NOTE "Before you start"

    - The stack runs with tenancy, as the [Tenants](./standalone-server.md#tenants) section starts it:
      `ATLAS_TENANCY_ENABLED=true` and `--profile tenancy`.
    - All commands run from the repository root. The stack's files are in `docker/`.

## What a tenant consists of

A tenant is a Keycloak organization with its own indices in the store (ADR 063). Adding one touches three
places:

| Where                                          | What you add                                             |
| ---------------------------------------------- | -------------------------------------------------------- |
| `docker/keycloak/aurelius-atlas.json`          | the organization and its four role groups                |
| `apps/aurelius-atlas-server/docker/tenants.py` | the provisioning of the tenant's indices, at every start |
| Keycloak's admin console                       | the tenant's members, created and added there            |

The tenant's members belong to it alone, so they sign in to it without choosing a tenant. The realm's
`operators` organization reads every tenant, and the provisioning command adds each of its members to the
new one.

## Choose the alias

The alias names the tenant everywhere: the organization and its indices.

- Lowercase letters, digits and `-`, starting with a letter or digit, at most 63 characters.
- Not `operators`, which is the platform's own organization.

## Add the organization to the realm

Add the tenant to `docker/keycloak/aurelius-atlas.json`. Every organization and group has a fixed id, so the
tenant's record still names them after Keycloak imports the realm again. Generate five ids, one for the
organization and four for its groups:

```bash
python3 -c 'import uuid; [print(uuid.uuid4()) for _ in range(5)]'
```

Add the organization to `organizations`, with no members yet:

```json
{
    "alias": "acme",
    "description": "The tenant acme",
    "enabled": true,
    "groups": [
        { "id": "<read group id>", "name": "atlas-read" },
        { "id": "<write group id>", "name": "atlas-write" },
        { "id": "<types group id>", "name": "atlas-types" },
        { "id": "<admin group id>", "name": "atlas-admin" }
    ],
    "id": "<organization id>",
    "members": [],
    "name": "acme"
}
```

## Provision the tenant at every start

The one shot `tenants` provisions each tenant it lists when the stack starts, and leaves a tenant already there
as it is. Add `acme` to the list in `apps/aurelius-atlas-server/docker/tenants.py`. The command makes the
realm's side too, as the client `aurelius-atlas-provisioning`: the organization already imported by the realm
file stays as it is, and its indices and record are made here. `--sample <path>` imports an Apache Atlas
export ZIP into the tenant, once:

```python
for argv in (
    ["provision", "demo", "--existing-ok", "--sample", str(sample)],
    ["provision", "meyn", "--existing-ok"],
    ["provision", "acme", "--existing-ok"],  # the new tenant
    ["list"],
):
    if main(argv) != 0:
        sys.exit(1)
```

## Start the stack and check

Start the stack as before. The realm file changed, so recreate Keycloak (`docker compose up -d --force-recreate
keycloak`): it imports the realm again, with acme's organization. Then `tenants` provisions the tenant:

```bash
ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env --profile tenancy up -d
docker compose -f docker/docker-compose.yaml logs tenants
```

The log ends with the list of tenants; `acme` is `active`. Now make a person and give it acme: in the console
at `https://localhost:9000/auth/admin/` (realm `aurelius-atlas`), create a user under Users with a password,
then add it under Organizations, `acme`, Members, with acme's role groups. Sign in to
`https://localhost:9000/` as that person: the webapp opens acme's catalogue, empty, without asking for a
tenant.

!!! NOTE "A sign-in refused right after the start"

    A new Keycloak signs with new keys. The server reads them again within a minute of seeing a token it can't
    verify, so a sign-in in that minute can fail; try again. A server image from before that fix (#378) keeps
    the old keys for an hour: restart it with
    `docker restart aurelius-atlas-standalone-aurelius-atlas-server-1`.

## Check the tests

The repository's tests pin the realm file. The id-uniqueness test follows a new tenant without changes, as
long as the new organization and its groups carry their own ids. Others list the tenants by name and need
`acme` added:

```bash
uv run pytest tests/test__standalone_demo_realm.py tests/test__realm_organizations.py tests/test__tenancy_chart.py
```

## Try a tenant without changing files

To try a tenant briefly, provision it with the server's command and add its people in Keycloak's admin console.
Keycloak forgets them when its container is recreated; the tenant's indices stay.

```bash
ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    run --rm --no-deps --entrypoint python aurelius-atlas-server \
    -m aurelius_atlas_server.provisioning provision acme
```

The command makes the organization and its four groups and adds the members of `operators` to it. Add people
at `https://localhost:9000/auth/admin/`, signed in as `KC_BOOTSTRAP_ADMIN_USERNAME` of
`infra/keycloak/.env`: realm `aurelius-atlas`, Users to create them, then Organizations, `acme`, Members to
add them and give them groups.

## Remove a tenant

`remove` deletes the tenant's indices, about a minute after the server stops serving it, then its organization
and its record:

```bash
ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    run --rm --no-deps --entrypoint python aurelius-atlas-server \
    -m aurelius_atlas_server.provisioning remove acme
```

Then take `acme` out of the places above, or the next start provisions it again, empty.
