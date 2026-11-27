# Add a Tenant to the Standalone Server

This page adds a tenant, a customer or department with its own catalogue and its own people, to a running [Standalone Server](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/user-guide/standalone-server/index.md>) with tenancy on. One command does it: `docker/bin/tenant.sh` makes the tenant, its people and, if you name one, its sample catalogue. You edit no file. The tenant and its people live in the store and in Keycloak, which the stack keeps across restarts until `down -v` (15.7). The example tenant is `acme`; replace it with yours throughout.

> [!NOTE]
>
> **Before you start**
>
> - The stack runs with tenancy, as the [Tenants](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/user-guide/standalone-server/#tenants>) section starts it: `ATLAS_TENANCY_ENABLED=true`.
> - All commands run from the repository root, or from the root of a release bundle.

## Choose the alias

The alias names the tenant everywhere: its Keycloak organization, its indices and its standard users.

- Lowercase letters, digits and `-`, starting with a letter or digit, at most 63 characters.
- Not `operators`, which is the platform's own organization.

The command refuses an alias that breaks either rule, before it does anything.

## Add the tenant

```
bash docker/bin/tenant.sh add acme
```

This makes the tenant `acme`: its indices and models, its organization with the four role groups, and the operators as read members. It makes the user `acme_atlas`, with every role in acme and acme's administrator. The command ends with a summary:

```
Tenant acme: no sample
  acme_atlas (atlas): made, temporary password 7f?Kq2…
```

Each password is temporary and printed once: the person sets their own at the first sign-in. Pass it on and keep no copy.

Two options choose what the tenant starts with:

| Option | What it adds |
| --- | --- |
| `--users all` | `acme_steward`, who reads and writes, and `acme_scientist`, who reads |
| `--sample <name>` | that sample's catalogue, imported into the new tenant |

```
bash docker/bin/tenant.sh samples                               # the samples you can name
bash docker/bin/tenant.sh add acme --users all --sample small   # three users and the small sample
```

`samples` lists the export ZIPs in the stack's sample folder, `SAMPLE_DIR`, by name without `.zip`, such as `sample_data`, `small` and `only_gov_quality`. A name it doesn't list is refused before anything is done.

Running `add` again is safe. A tenant that exists is left as it is and gets no sample; the command makes only the users it is missing, and a user that exists keeps their password, so none is printed for them.

## Add more people

Add a person to a tenant with their role:

```
bash docker/bin/tenant.sh user acme add jane --role steward --email jane@acme.example
```

| Role | What the person may do in the tenant |
| --- | --- |
| `atlas` | everything, the four role groups |
| `steward` | read and write the catalogue |
| `scientist` | read the catalogue, the default |

A new person gets a temporary password in the summary, as above; the email is `<username>@example.com` unless you give one. A person the realm has already, such as a member of another tenant, joins this tenant too and keeps their password. The role `atlas` grants the groups, not the tenant's administration: to make someone a tenant administrator, run `bash docker/bin/tenant.sh admin acme add jane`.

To take a person out of a tenant, with their groups and administration there:

```
bash docker/bin/tenant.sh user acme remove jane
```

The person stays in Keycloak, with any other tenant they belong to.

## Check the tenant

```
bash docker/bin/tenant.sh list
```

`acme` is listed `active`. Sign in to `https://localhost:9000/` as `acme_atlas` with the printed password: Keycloak asks for a new one, then the webapp opens acme's catalogue without asking for a tenant.

> [!NOTE]
>
> **A sign-in refused right after the start**
>
> A new Keycloak signs with new keys. The server reads them again within a minute of seeing a token it can't verify, so a sign-in in that minute can fail; try again.

## The tenant's dashboards

`add`, `user add` and `user remove` keep the tenant's Grafana organization in step: its data sources, which read the tenant's indices alone, and its dashboards *catalogue* and *activity*. Its Viewers are the tenant's people with the role `atlas` or `steward`, and the operators the tenant trusts; a `scientist` doesn't see them. Those people find "Dashboards" in the webapp's account menu, under "Switch tenant": it opens the tenant's catalogue in Grafana in a new tab. Grafana is also at `https://localhost:9000/grafana/`. A person in more than one tenant switches between them with Grafana's organization menu; operators also see the main organization, with the stack's own telemetry.

People added or removed in Keycloak's console, not with the command, reach Grafana with:

```
bash docker/bin/tenant.sh grafana sync
```

It also deletes the Grafana users who are no tenant's Viewer any more and aren't operators. A role changed in Keycloak's console reaches Grafana the same way, and the webapp's menu at the person's next sign-in.

## Remove a tenant

```
bash docker/bin/tenant.sh remove acme
```

`remove` deletes the tenant's indices, about a minute after the server stops serving it, then its organization, its Grafana organization and its record. Its people stay in Keycloak, members of no tenant; delete them in Keycloak's admin console at `https://localhost:9000/auth/admin/` if they should go too, and run `bash docker/bin/tenant.sh grafana sync` to delete them from Grafana.

## The seeded tenants demo and meyn

`bash docker/bin/provision-tenants.sh` seeds the tenants demo, with the sample `sample_data`, and meyn, each with its three users. Unlike the tenants the command adds, their users have fixed passwords, `<TENANT>_USER_<ROLE>_PASSWORD` in `infra/keycloak/.env`, because a demo is signed in to again and again (DD-700). To make another tenant part of that seed, add it to the list in `apps/aurelius-atlas-server/docker/tenants.py`, its passwords to `infra/keycloak/.env.enc`, and those to the one shot `tenants` in `apps/aurelius-atlas-server/docker/compose.yaml`. For any other tenant, use the command.
