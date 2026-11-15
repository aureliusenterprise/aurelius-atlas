# 15.5b Tenants in the realm

- **Status:** in progress
- **Pull request:** to follow
- **Records:** ADR 063 (Proposed); DD-600 to DD-603 (here); relies on 15.3 (TPR-01 to TPR-06, DD-573) and 15.5a
  (RLM-01, RLM-04, DD-580, DD-581)

15.5a set up the realms with the operator organization. A tenant's organization was still made by hand. This
increment makes the provisioning command keep the realm in step with the tenants it records: it creates a
tenant's organization and its four groups, makes the operators read members of each tenant that trusts them and
keeps that membership current, grants each tenant's administrators the right to manage its role groups, and
removes it all with the tenant.

## Scope

- `aurelius-atlas-server`:
    - the realm's side of the tenants (`realm_tenants.py`), through Keycloak's admin API;
    - `provision`, `trust` and `remove` keeping the realm in step; the new commands `operators` and `admin`
      (`provisioning.py`);
    - the tenants' records keep the operators that trust added and the tenant's administrators (`tenants.py`);
    - the settings `tenancy_admin_client_id` and `tenancy_admin_client_secret` (`settings.py`);
    - the chart: the provisioning client's secret for the Job, and a CronJob that runs `operators`;
    - the standalone stack: the secret for the command.
- `dev/keycloak`: the client `aurelius-atlas-provisioning` and its service account in the dev and chart realms,
  and fine-grained admin permissions on; the chart's secret for it.
- the umbrella chart: the generated `<release>-provisioning-client` Secret.

Not delivered, with the increment that will:

| Not delivered                                                                       | Lands with                   |
| ----------------------------------------------------------------------------------- | ---------------------------- |
| A tenant administrator listing or adding the tenant's members in Keycloak's console | Keycloak scoping user rights |
| The webapp asking for the organization scope, showing the tenant, and switching     | 15.6                         |

## Semantics

"The command", "a tenant" and "the operator organization" are as in 15.3. "The realm" is the realm the server's
settings name (`auth_realm`). "The four groups" and "the group mapper" are as in 15.5a. "An operator" is a member
of the operator organization who holds the operator realm role (`tenancy_operator_role`). "The tenant's
organization" is the realm's organization whose alias is the tenant's.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                             |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TRM-01 | The command reaches the realm as the client `tenancy_admin_client_id` (`aurelius-atlas-provisioning` by default) with `tenancy_admin_client_secret`. Without the secret it leaves the realm as it is and says so once; the store's side runs as in 15.3 (DD-603)                                                                                 |
| TRM-02 | `provision` makes the tenant's organization, named and aliased as the tenant, when it doesn't exist, and each of the four groups it lacks, before it records the tenant `active`. Run again, it changes nothing that is already there; with `--existing-ok`, an `active` tenant's realm is brought in step too                                   |
| TRM-03 | A tenant that trusts the operators has each operator as a member of its organization in `atlas-read` alone. The record lists the operators trust added; an operator who was a member before is neither changed nor listed (DD-601)                                                                                                               |
| TRM-04 | `trust <alias> off` removes from the organization every operator the record lists, and `trust <alias> on` adds the operators. Neither touches another member                                                                                                                                                                                     |
| TRM-05 | `operators` brings every `active` tenant in step: an operator who is not yet a member of a trusting tenant is added, and one the record lists who is no longer an operator, or whose tenant no longer trusts them, is removed. It prints what it changed per tenant. The chart runs it on a schedule (DD-601)                                    |
| TRM-06 | `admin <alias> add <username>` and `admin <alias> remove <username>` change the tenant's administrators, kept in its record (DD-602)                                                                                                                                                                                                             |
| TRM-07 | A tenant's administrators may view and manage the tenant's organization and its four groups, and change the groups of the tenant's members other than the operators trust added. They may not read any other organization, any other user, or the realm's users. With no administrator, the realm grants nothing for the tenant (DD-602)         |
| TRM-08 | The administrators' right over the tenant's members follows the members: `provision`, `trust`, `admin` and `operators` bring it in step. It never names no member, which Keycloak would read as every user                                                                                                                                       |
| TRM-09 | `remove` deletes the tenant's organization, with its groups and memberships, and the administrators' rights, after its indices and before its record                                                                                                                                                                                             |
| TRM-10 | A call the realm refuses fails the command with Keycloak's status and the call, exit 1. The record keeps the operators already added or removed, so that running the command again carries on, and a `provision` interrupted there leaves the tenant `provisioning` (TPR-04)                                                                     |
| TRM-11 | The dev and chart realms have the client `aurelius-atlas-provisioning`, confidential with a service account and no sign-in flow, whose account holds the realm-management roles the command needs, and fine-grained admin permissions on (DD-600). The chart's provisioning Job and CronJob, and the standalone stack's command, have its secret |
| TRM-12 | With the tenancy setting off, the realm is not called, and no answer of Apache Atlas's API changes                                                                                                                                                                                                                                               |

## Java origin

None: Apache Atlas has no tenants (ADR 063).

## Deviations

None beyond DV-163: no Atlas endpoint changes.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_realm_tenants.py`: TRM-02 to TRM-10 against a
  fake of Keycloak's admin API that answers as Keycloak 26.7.4 did (DD-600 to DD-602).
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_provisioning.py`: TRM-01, the command without
  the secret.
- `tests/test__realm_organizations.py` and `tests/test__tenancy_chart.py`: TRM-11 on the realm files and the
  charts' renders.
- A run of the command's realm side against Keycloak 26.7.4, recorded in the PR.
- `uv run pytest apps/aurelius-atlas-server/tests tests` (level 0).
