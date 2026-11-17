# Add a Tenant to the Standalone Server

This page adds a tenant, a customer or department with its own catalogue and its own people, to a running [Standalone Server](<https://aureliusenterprise.github.io/feat-account-page-language/user-guide/standalone-server/index.md>) with tenancy on. The stack's Keycloak keeps no data of its own and imports `keycloak/atlas.json` at every start, so a tenant that should last is added to the stack's files, not only in Keycloak's console. The example tenant is `acme`; replace it with yours throughout.

> [!NOTE]
>
> **Before you start**
>
> - The stack runs with tenancy, as the [Tenants](<https://aureliusenterprise.github.io/feat-account-page-language/user-guide/standalone-server/#tenants>) section starts it: `ATLAS_TENANCY_ENABLED=true` and `--profile tenancy`.
> - Your SOPS key is registered, so you can re-encrypt `dev/keycloak/.env.enc` ([Development Environment](<https://aureliusenterprise.github.io/feat-account-page-language/contributor-guide/development-environment/index.md>)).
> - All commands run from the repository root. The stack's files are in `apps/aurelius-atlas-server/standalone/`.

## What a tenant consists of

A tenant is a Keycloak organization with its own indices in the store (ADR 063). Adding one touches five places:

| Where | What you add |
| --- | --- |
| `standalone/keycloak/atlas.json`, `organizations` | the organization, its four role groups and its members |
| `standalone/keycloak/atlas.json`, `users` | the tenant's own users, each with a password of its own |
| `dev/keycloak/.env.enc` | those passwords, encrypted |
| `standalone/docker-compose.yaml`, service `keycloak` | the passwords passed to Keycloak's import |
| `standalone/tenants.py` | the provisioning of the tenant's indices, at every start |

The tenant's users belong to it alone, so they sign in to it without choosing a tenant. The user `operator` reads every tenant and joins the new one as a member.

## Choose the alias

The alias names the tenant everywhere: the organization, its users, its indices and its password variables.

- Lowercase letters, digits and `-`, starting with a letter or digit, at most 63 characters.
- Not `operators`, which is the platform's own organization.
- The users are `<alias>_atlas`, `<alias>_steward` and `<alias>_scientist`.
- The password variables are `<ALIAS>_USER_<ROLE>_PASSWORD`, the alias in capitals with `-` as `_`: for `acme`, `ACME_USER_ATLAS_PASSWORD`, `ACME_USER_STEWARD_PASSWORD` and `ACME_USER_SCIENTIST_PASSWORD`.

## Give the users passwords of their own

Each tenant's users get passwords no other tenant knows. Add them to the dev Keycloak's `.env`, then encrypt it into `.env.enc`, which is the file the repository keeps:

```
for role in ATLAS STEWARD SCIENTIST; do
    echo "ACME_USER_${role}_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')" \
        >> dev/keycloak/.env
done
npx nx encrypt aurelius-atlas-dev-keycloak
```

> [!WARNING]
>
> **Start from the current `.env`**
>
> `nx encrypt` writes `.env.enc` from your local `.env`. If your `.env` is older than `.env.enc`, run `npx nx decrypt aurelius-atlas-dev-keycloak` first, or the encryption drops the keys your copy lacks.

## Add the organization and its users to the realm

Add the tenant to `standalone/keycloak/atlas.json`. Every person, organization and group has a fixed id, so the tenant's record still names them after Keycloak imports the realm again. Generate eight ids, one for the organization, four for its groups and three for its users:

```
python3 -c 'import uuid; [print(uuid.uuid4()) for _ in range(8)]'
```

Add the organization to `organizations`. The members are the tenant's three users and `operator`, each listing the ids of its groups:

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
    "members": [
        {
            "groups": ["<read group id>", "<write group id>", "<types group id>", "<admin group id>"],
            "username": "acme_atlas"
        },
        { "groups": ["<read group id>", "<write group id>"], "username": "acme_steward" },
        { "groups": ["<read group id>"], "username": "acme_scientist" },
        { "groups": ["<read group id>"], "username": "operator" }
    ],
    "name": "acme"
}
```

Add the three users to `users`. The steward and the scientist differ from the administrator only in their username, id, email, names, roles and password variable:

```
{
    "clientRoles": { "aurelius-atlas-server": ["atlas-read", "atlas-write", "atlas-types", "atlas-admin"] },
    "credentials": [{ "type": "password", "value": "${ACME_USER_ATLAS_PASSWORD}" }],
    "email": "acme.atlas@example.com",
    "enabled": true,
    "firstName": "Atlas",
    "id": "<user id>",
    "lastName": "Administrator",
    "username": "acme_atlas"
}
```

| User | `clientRoles` of `aurelius-atlas-server` | Password variable |
| --- | --- | --- |
| `acme_atlas` | `atlas-read`, `atlas-write`, `atlas-types`, `atlas-admin` | `ACME_USER_ATLAS_PASSWORD` |
| `acme_steward` | `atlas-read`, `atlas-write` | `ACME_USER_STEWARD_PASSWORD` |
| `acme_scientist` | `atlas-read` | `ACME_USER_SCIENTIST_PASSWORD` |

> [!WARNING]
>
> **Keycloak's profile rules**
>
> Every email must be unique in the realm, and names may not contain characters such as `(` or `)`. A user that breaks either rule imports, but Keycloak refuses to sign them in: "Account is not fully set up".

## Pass the passwords to Keycloak

Keycloak's import replaces each `${…}` placeholder with the variable of that name in its environment. Add the three variables to the service `keycloak` in `standalone/docker-compose.yaml`, beside meyn's:

```
ACME_USER_ATLAS_PASSWORD: ${ACME_USER_ATLAS_PASSWORD:?}
ACME_USER_STEWARD_PASSWORD: ${ACME_USER_STEWARD_PASSWORD:?}
ACME_USER_SCIENTIST_PASSWORD: ${ACME_USER_SCIENTIST_PASSWORD:?}
```

## Provision the tenant at every start

The one shot `tenants` provisions each tenant it lists when the stack starts, and leaves a tenant already there as it is. Add `acme` to the list in `standalone/tenants.py`. `--admin` makes `acme_atlas` the tenant's administrator in Keycloak; `--sample <path>` would import an Apache Atlas export ZIP into it, once:

```
for argv in (
    ["provision", "demo", "--existing-ok", "--sample", str(sample), "--admin", "demo_atlas"],
    ["provision", "meyn", "--existing-ok", "--admin", "meyn_atlas"],
    ["provision", "acme", "--existing-ok", "--admin", "acme_atlas"],  # the new tenant
    ["list"],
):
    if main(argv) != 0:
        sys.exit(1)
```

## Start the stack and check

Start the stack as before. Keycloak's environment changed, so it is recreated and imports the realm with the new tenant; then `tenants` provisions it:

```
ATLAS_TENANCY_ENABLED=true docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file dev/keycloak/.env --profile tenancy up -d
docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml logs tenants
```

The log ends with the list of tenants; `acme` is `active`. Sign in to `https://localhost:9000/` as `acme_atlas` with `ACME_USER_ATLAS_PASSWORD`: the webapp opens acme's catalogue, empty, without asking for a tenant.

> [!NOTE]
>
> **A sign-in refused right after the start**
>
> A new Keycloak signs with new keys. The server reads them again within a minute of seeing a token it can't verify, so a sign-in in that minute can fail; try again. A server image from before that fix (\#378) keeps the old keys for an hour: restart it with `docker restart aurelius-atlas-standalone-aurelius-atlas-server-1`.

## Check the tests

The repository's tests pin the realm file. Two of them follow a new tenant without changes: every person has an id and a password variable of their own. Others list the tenants by name and need `acme` added:

```
uv run pytest tests/test__standalone_demo_realm.py tests/test__realm_organizations.py tests/test__tenancy_chart.py
```

## Try a tenant without changing files

To try a tenant briefly, provision it with the server's command and add its people in Keycloak's admin console. Keycloak forgets them when its container is recreated; the tenant's indices stay.

```
ATLAS_TENANCY_ENABLED=true docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file dev/keycloak/.env \
    run --rm --no-deps --entrypoint python aurelius-atlas-server \
    -m aurelius_atlas_server.provisioning provision acme
```

The command makes the organization and its four groups and adds `operator` to it. Add people at `https://localhost:9000/auth/admin/`, signed in as `KC_BOOTSTRAP_ADMIN_USERNAME` of `dev/keycloak/.env`: realm `atlas`, Users to create them, then Organizations, `acme`, Members to add them and give them groups.

## Remove a tenant

`remove` deletes the tenant's indices, about a minute after the server stops serving it, then its organization and its record:

```
ATLAS_TENANCY_ENABLED=true docker compose -f apps/aurelius-atlas-server/standalone/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file dev/keycloak/.env \
    run --rm --no-deps --entrypoint python aurelius-atlas-server \
    -m aurelius_atlas_server.provisioning remove acme
```

Then take `acme` out of the five places above, or the next start provisions it again, empty.
