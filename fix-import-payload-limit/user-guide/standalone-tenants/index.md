# Add a Tenant to the Standalone Server

This page adds a tenant, a customer or department with its own catalogue and its own people, to a running [Standalone Server](<https://aureliusenterprise.github.io/fix-import-payload-limit/user-guide/standalone-server/index.md>) with tenancy on. The stack's Keycloak imports `keycloak/aurelius-atlas.json` at every start, so a tenant's organization that should last is added to the stack's files, not only in Keycloak's console. A tenant's three users are made by the one shot `tenants` when it provisions the tenant (DD-700), each with a password of its own; further people are made in Keycloak's console. The example tenant is `acme`; replace it with yours throughout.

> [!NOTE]
>
> **Before you start**
>
> - The stack runs with tenancy, as the [Tenants](<https://aureliusenterprise.github.io/fix-import-payload-limit/user-guide/standalone-server/#tenants>) section starts it: `ATLAS_TENANCY_ENABLED=true`. The script `docker/bin/provision-tenants.sh` runs the provisioning one shot when you ask for it (SPC-07).
> - All commands run from the repository root. The stack's files are in `docker/`.

## What a tenant consists of

A tenant is a Keycloak organization with its own indices in the store (ADR 063). Adding one touches four places:

| Where | What you add |
| --- | --- |
| `docker/keycloak/aurelius-atlas.json` | the organization and its four role groups |
| `apps/aurelius-atlas-server/docker/tenants.py` | the provisioning of the tenant's indices, when the script runs it |
| `infra/keycloak/.env.enc` | the passwords of the tenant's three users |
| `apps/aurelius-atlas-server/docker/compose.yaml` | those passwords passed to the one shot `tenants` |
| Keycloak's admin console | further members, created and added there |

The tenant's members belong to it alone, so they sign in to it without choosing a tenant. The realm's `operators` organization reads every tenant, and the provisioning command adds each of its members to the new one.

## Choose the alias

The alias names the tenant everywhere: the organization and its indices.

- Lowercase letters, digits and `-`, starting with a letter or digit, at most 63 characters.
- Not `operators`, which is the platform's own organization.

## Add the organization to the realm

Add the tenant to `docker/keycloak/aurelius-atlas.json`. Every organization and group has a fixed id, so the tenant's record still names them after Keycloak imports the realm again. Generate five ids, one for the organization and four for its groups:

```
python3 -c 'import uuid; [print(uuid.uuid4()) for _ in range(5)]'
```

Add the organization to `organizations`, with no members yet:

```
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

## Provision the tenant

The one shot `tenants` provisions each tenant it lists, and leaves a tenant already there as it is. The script runs it on demand. Add `acme` to the list in `apps/aurelius-atlas-server/docker/tenants.py`. The command makes the realm's side too, as the client `aurelius-atlas-provisioning`: the organization already imported by the realm file stays as it is, and its indices and record are made here. `--sample <path>` imports an Apache Atlas export ZIP into the tenant, once:

```
for alias, extra in (("demo", ["--sample", str(sample)]), ("meyn", []), ("acme", [])):  # acme: the new tenant
```

After provisioning each tenant, the one shot makes its users `acme_atlas`, `acme_steward` and `acme_scientist`, puts them in acme's role groups, and makes `acme_atlas` acme's administrator (DD-700).

## Give the tenant's users their passwords

Each tenant's users get passwords no other tenant knows. Add them to `infra/keycloak/.env`, then encrypt it into `infra/keycloak/.env.enc`, which is the file the repository keeps:

```
for role in ATLAS STEWARD SCIENTIST; do
    echo "ACME_USER_${role}_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(15))')-7Kq" \
        >> infra/keycloak/.env
done
npx nx encrypt aurelius-atlas-infra-keycloak
```

Then pass them to the one shot `tenants`, in its `environment` in `apps/aurelius-atlas-server/docker/compose.yaml`, beside meyn's:

```
ACME_USER_ATLAS_PASSWORD: ${ACME_USER_ATLAS_PASSWORD:-}
ACME_USER_STEWARD_PASSWORD: ${ACME_USER_STEWARD_PASSWORD:-}
ACME_USER_SCIENTIST_PASSWORD: ${ACME_USER_SCIENTIST_PASSWORD:-}
```

The realm's password policy asks for 12 characters with an upper- and a lower-case letter, a digit and a special character; the suffix above makes sure of the last three. A role without a password, or with one the policy refuses, gets no user and the log says why; the tenant itself is provisioned all the same.

## Start the stack and check

Start the stack as before. The realm file changed, so recreate Keycloak (`docker compose up -d --force-recreate keycloak`): it imports the realm again, with acme's organization. Then `tenants` provisions the tenant:

```
ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env up -d
docker/bin/provision-tenants.sh
docker compose -f docker/docker-compose.yaml logs tenants
```

The log names acme's users as made and ends with the list of tenants; `acme` is `active`. Sign in to `https://localhost:9000/` as `acme_atlas` with `ACME_USER_ATLAS_PASSWORD`: the webapp opens acme's catalogue, empty, without asking for a tenant. Further people are made in the console at `https://localhost:9000/auth/admin/` (realm `aurelius-atlas`): create a user under Users with a password, then add it under Organizations, `acme`, Members, with acme's role groups.

> [!NOTE]
>
> **A sign-in refused right after the start**
>
> A new Keycloak signs with new keys. The server reads them again within a minute of seeing a token it can't verify, so a sign-in in that minute can fail; try again. A server image from before that fix (\#378) keeps the old keys for an hour: restart it with `docker restart aurelius-atlas-standalone-aurelius-atlas-server-1`.

## Check the tests

The repository's tests pin the realm file. The id-uniqueness test follows a new tenant without changes, as long as the new organization and its groups carry their own ids. Others list the tenants by name and need `acme` added:

```
uv run pytest tests/test__standalone_demo_realm.py tests/test__realm_organizations.py tests/test__tenancy_chart.py
```

## Try a tenant without changing files

To try a tenant briefly, provision it with the server's command and add its people in Keycloak's admin console. Keycloak forgets them when its container is recreated; the tenant's indices stay.

```
ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    run --rm --no-deps --entrypoint python aurelius-atlas-server \
    -m aurelius_atlas_server.provisioning provision acme
```

The command makes the organization and its four groups and adds the members of `operators` to it. Add people at `https://localhost:9000/auth/admin/`, signed in as `KC_BOOTSTRAP_ADMIN_USERNAME` of `infra/keycloak/.env`: realm `aurelius-atlas`, Users to create them, then Organizations, `acme`, Members to add them and give them groups.

## Remove a tenant

`remove` deletes the tenant's indices, about a minute after the server stops serving it, then its organization and its record:

```
ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    run --rm --no-deps --entrypoint python aurelius-atlas-server \
    -m aurelius_atlas_server.provisioning remove acme
```

Then take `acme` out of the places above, or the next start provisions it again, empty.
