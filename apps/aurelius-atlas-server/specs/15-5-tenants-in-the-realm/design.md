# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-600. The command keeps the realm in step through a service account of its own

- **Status:** Proposed
- **Increment:** 15.5b
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** The realm has the confidential client `aurelius-atlas-provisioning`, with a service account and
no sign-in flow. Its account holds nine roles of `realm-management`:

- `manage-organizations`, `view-organizations` and `query-organizations`;
- `manage-users`, `view-users`, `query-users` and `query-groups`;
- `view-clients`, to find the `admin-permissions` client;
- `manage-realm`, to write the administrators' permissions.

Fine-grained admin permissions are on in the realm. The command gets a client-credentials token and calls
Keycloak's admin API.

**Reason.** The tenant's organization, its groups and its members belong to the realm, and only its admin API
changes them. A check on Keycloak 26.7.4 found that no smaller set of roles works:

- With the user roles alone, every organization call was refused. The organization roles admit them.
- Writing a policy or a permission of `admin-permissions` was refused with `manage-clients` and
  `manage-authorization`, and admitted with `manage-realm`.
- `view-clients` is needed to find the `admin-permissions` client.
- An operator is found from the operator organization's members and each member's realm roles. That needs
  `view-users`, not `view-realm`.

**Alternatives.**

- The server's own client with these roles: every server process would hold them, and the server never needs
  them.
- `realm-admin`: every role of the realm, for calls that need nine.

**Consequences.** `manage-realm` lets the account change the realm's settings, which the command never does. The
client's secret is a credential of the platform's operators, kept as the server client's is.

### DD-601. The operators' membership follows trust, and the record lists what trust added

- **Status:** Proposed
- **Increment:** 15.5b
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** An operator is a member of the operator organization who holds `atlas-operator`. A tenant that
trusts the operators has each of them as a member in `atlas-read`. The tenant's record lists the operators that
trust made members, by user id. The command `operators` adds an operator missing from a trusting tenant and
removes one the record lists who no longer should be there. The chart runs it every 15 minutes.

**Reason.** Keycloak has no membership that follows another organization's, so the command keeps it. The list
tells apart a member that trust added, which trust removes, from a person who is a member of the tenant in their
own right and holds an operator role too, whom trust leaves alone. The operator role, not membership alone,
marks an operator: the operator organization also holds service accounts (DD-581), which must not join other
tenants, because a service account in two organizations acts in none (TEN-03).

**Alternatives.**

- Trust as the organizations' shared membership, read at sign-in: Keycloak has no such feature.
- Removing every operator from a tenant that withdraws trust: a tenant's own member who also runs the platform
  would lose their membership.

**Consequences.** An operator who joins or leaves is in step with every tenant within the schedule. The tenants
index mapping gains `operatorMembers` and `administrators`, added to an existing index.

### DD-602. A tenant's administrator manages its role groups for its own members, and sees no one else

- **Status:** Proposed
- **Increment:** 15.5b
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** For a tenant with administrators, the realm holds a user policy that names them, and three scope
permissions:

- `view` and `manage` on the tenant's organization;
- `view`, `view-members`, `manage-members` and `manage-membership` on its four groups;
- `view` and `manage-group-membership` on each of its members, the operators that trust added excepted.

A tenant without administrators has none of these. The command keeps the members' permission in step with the
members, and deletes it when no member is left.

**Reason.** ADR 063 gives each tenant administrators who manage its members' roles and nothing outside it (R10).
A check on Keycloak 26.7.4 showed the following:

- With these permissions, an administrator set and removed the groups of the tenant's members. They were
  refused on another organization, its groups, a user who isn't a member, and the realm's users.
- Listing the organization's members, or a group's members, needs `view` on every user of the realm. Granted,
  every tenant administrator could read every user's profile, other tenants' people included. The user chose
  not to grant it.
- A permission on users that names no user applies to every user, so the command never leaves it empty.
- Deleting an organization drops the permissions on it and its groups. It leaves the policy and the members'
  permission, which the command deletes.

**Alternatives.**

- `view` on every user: the administrator can list members in Keycloak's console, and reads every other tenant's
  people.
- No delegated administration until Keycloak scopes user rights to an organization: R10 waits for Keycloak.

**Consequences.** An administrator manages roles but can't list members in Keycloak's console, nor add or
remove members. Members join by invitation or through a platform administrator, as ADR 063 foresees. The
administrator can also change the organization's own settings, as ADR 063 notes.

### DD-603. Without the client's secret, the command leaves the realm alone

- **Status:** Proposed
- **Increment:** 15.5b
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** `tenancy_admin_client_secret` is unset by default. Without it, the command's realm steps are
skipped, and it says so once. With it, a refused or failed call fails the command (TRM-10).

**Reason.** A deployment may keep its realm by hand, or run Keycloak that its operators don't administer. The
store's side of a tenant doesn't need the realm. Once the secret is given, a half-done realm is a fault the
operator must see.

**Alternatives.**

- The realm steps always on: a deployment without the client couldn't provision at all.

**Consequences.** The chart and the standalone stack pass the secret, so their tenants' realms are kept by the
command.
