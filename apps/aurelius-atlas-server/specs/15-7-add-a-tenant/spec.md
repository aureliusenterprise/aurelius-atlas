# 15.7 Adding a tenant by command

- **Status:** planned
- **Pull request:** to follow
- **Records:** ADR 063 (Proposed); DD-701 and DD-702 (here); relies on 15.3 (TPR-01 to TPR-06), 15.5b
  (TRM-01 to TRM-12, DD-600, DD-602) and 17.1 (DD-700)

Adding a tenant to the standalone stack took edits: the tenant in `tenants.py`, its users' passwords in
`infra/keycloak/.env` and the compose file, then a restart. The server's command `provision` made the tenant
but none of its people. This increment adds one command that makes a tenant with its people, with or without
sample data, and a script that runs it against the standalone stack. Nothing is edited: the tenant lives in
the store and the realm, which the stack keeps across restarts until `down -v`.

## Scope

- `aurelius-atlas-server`:
    - the command's subcommands `add`, `user` and `samples` (`provisioning.py`);
    - making a tenant's people in the realm: a user, their membership and groups, a temporary password
      (`realm_tenants.py`);
    - the stack's one shot `tenants` seeding demo and meyn through the same code (`docker/tenants.py`);
    - the script `docker/bin/tenant.sh` running the command against the standalone stack.
- `docs/user-guide/standalone-tenants.md` rewritten around the command.

Not delivered, with the increment that will:

| Not delivered                                                             | Lands with            |
| ------------------------------------------------------------------------- | --------------------- |
| The command against a Kubernetes deployment, and its guide                | a later increment     |
| A tenant administrator managing their tenant's people through the command | not planned (ADR 063) |

## Semantics

"The command" is `python -m aurelius_atlas_server.provisioning`, run with the server's settings and the
provisioning client's secret in its environment (15.3, TRM-11). "The sample folder" is the folder `SAMPLE_DIR`
names; "a sample" is an Apache Atlas export ZIP in it, named by its file name without `.zip`. "A tenant's role
groups" are its organization's `atlas-read`, `atlas-write`, `atlas-types` and `atlas-admin` (TRM-02). The roles
of a tenant's people and their groups:

| Role        | The tenant's groups                                       |
| ----------- | --------------------------------------------------------- |
| `atlas`     | `atlas-read`, `atlas-write`, `atlas-types`, `atlas-admin` |
| `steward`   | `atlas-read`, `atlas-write`                               |
| `scientist` | `atlas-read`                                              |

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TAD-01 | `add <tenant>` provisions the tenant as `provision <tenant> --existing-ok` does (TPR-02, TRM-02, TRM-03), makes its standard users (TAD-03 to TAD-06), makes `<tenant>_atlas` its administrator (TRM-06), then prints a summary (TAD-08). A tenant already `active` is left as it is; only its missing users are made. An alias `provision` refuses is refused before anything is done                                                             |
| TAD-02 | `add <tenant> --sample <name>` imports the sample `<name>` into a tenant it makes (TPR-02). A name no sample in the sample folder has is refused before anything is done, the error listing the samples there. A tenant already `active` gets no sample, and the summary says so. Without `--sample`, the tenant starts empty                                                                                                                      |
| TAD-03 | `add <tenant> --users atlas`, the default, makes `<tenant>_atlas`; `--users all` makes `<tenant>_steward` and `<tenant>_scientist` too. Each has the role its name says                                                                                                                                                                                                                                                                            |
| TAD-04 | A user `add` makes has the username `<tenant>_<role>`, the email `<tenant>.<role>@example.com`, verified, and a first and last name from its role (`Atlas Administrator`, `Data Steward`, `Data Scientist`). It becomes a member of the tenant, in the tenant's groups of its role, and of no other organization                                                                                                                                   |
| TAD-05 | A user the command makes gets a generated password that meets the realm's password policy, temporary, with the required action to change it at the first sign-in (DD-701). The summary prints it once. The command writes it nowhere else: no file, no record, no log line                                                                                                                                                                         |
| TAD-06 | A user the realm has already is not made again: its password is kept and not printed, and the summary says it existed. It becomes a member of the tenant and gets the groups of its role, as a new user does                                                                                                                                                                                                                                       |
| TAD-07 | `user <tenant> add <username> --role <role> [--email <address>]` adds one person to a tenant that is `active`: made as TAD-05 if the realm has no such user, with the email given or `<username>@example.com`, or the existing user as TAD-06; then a member of the tenant in the groups of its role. The role `atlas` grants the groups, not the tenant's administration, which `admin` grants (TRM-06). A tenant that is not `active` is refused |
| TAD-08 | The summary of `add` and of `user add` names the tenant, the sample imported or why none was, and each of its users: made, with its temporary password, or existing, with none                                                                                                                                                                                                                                                                     |
| TAD-09 | `user <tenant> remove <username>` takes the user out of the tenant: its membership, its groups there and its administration of the tenant (TRM-07). The user stays in the realm, with any other tenant's membership                                                                                                                                                                                                                                |
| TAD-10 | `samples` lists the samples in the sample folder, one name per line                                                                                                                                                                                                                                                                                                                                                                                |
| TAD-11 | When a step fails, the command says which, makes nothing more and exits non-zero. Each step leaves what it made, so running the same command again finishes the rest (TAD-01, TAD-06)                                                                                                                                                                                                                                                              |
| TAD-12 | `docker/bin/tenant.sh <arguments>` runs the command with those arguments in the standalone stack's one shot `tenants`: the server's image, its settings, tenancy on, the stack's env files and the sample folder (DD-702). It answers the command's output and exit code, and needs the stack running. It edits no file                                                                                                                            |
| TAD-13 | The stack's one shot `tenants` seeds demo with the sample `sample_data` and meyn without one, each with all three users, through the code of TAD-01 to TAD-06. Their passwords come from `<TENANT>_USER_<ROLE>_PASSWORD` and are permanent (DD-700); a role without one gets no user                                                                                                                                                               |

## Java origin

None: Apache Atlas has no tenants. The command follows the server's own provisioning (15.3, 15.5b) and the
runbook's admin accounts, which make people with a temporary password through Keycloak's admin API.

## Deviations

None against Apache Atlas.

## Acceptance

- `tests/test__aurelius_atlas_server_tenant_people.py`: TAD-01 to TAD-11 against the fake store and the fake
  Keycloak, which answers 409 for a member already in a group as Keycloak 26.7 does.
- `tests/test__standalone_tenant_users.py`: TAD-13, the one shot's seeding through the same code.
- `tests/test__standalone_tenant_script.py` (workspace): TAD-12, the script's compose invocation read as
  written.
- By hand, on the standalone stack:
    - `docker/bin/tenant.sh samples` lists `only_gov_quality`, `sample_data` and `small`;
    - `docker/bin/tenant.sh add acme` makes acme and `acme_atlas` with a temporary password, and nothing else;
    - `docker/bin/tenant.sh add globex --sample small --users all` makes globex with the small sample and three
      users;
    - signing in as `acme_atlas` asks for a new password, then opens acme's catalogue, empty;
    - running `docker/bin/tenant.sh add acme` again changes nothing and prints no password;
    - `docker/bin/tenant.sh user acme add jane --role steward` adds jane to acme, and
      `docker/bin/tenant.sh user acme remove jane` takes her out again.
