# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-580. The realms carry the operator organization; tenants' organizations come with provisioning

- **Status:** Proposed
- **Increment:** 15.5a
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** Each realm file turns organizations on and carries the organization `operators` with its four
groups, at fixed group ids, and the realm role `atlas-operator`. A member's groups in an organization are listed
under the member, by group id, as Keycloak's own export writes them. A tenant's organization is made when the
tenant is provisioned (15.5b), so the dev and chart realms carry no tenant. The standalone demo realm carries
the sample tenant `acme`, which its README provisions.

**Reason.** The operator organization exists in every deployment from its start (DD-567), so it belongs to the
realm, as the server's client does. A tenant exists only once provisioned, and the command that provisions it
is the one place that knows its alias. A check on Keycloak 26.7.4 showed the following:

- A realm import makes organizations with their members and their own groups. A group can't list its members;
  a member lists its groups by id.
- A token asked for with `organization:acme` and the group mapper carries
  `{"acme": {"groups": ["/atlas-read"]}}`, and nothing of the person's other organizations.

**Alternatives.**

- The operator organization made by the provisioning command: a fresh deployment would refuse its own
  operators until someone ran it.
- Example tenants in every realm: the chart's production realm would carry an organization no deployment
  asked for.

**Consequences.** A realm that exists already doesn't take the change: Keycloak skips the import of an existing
realm, so its administrator adds the organization by hand.

### DD-581. A service account acts in its organization through membership and a default scope

- **Status:** Proposed
- **Increment:** 15.5a
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** A service client carries the group mapper and has `organization` among its default scopes. Its
service account is a member of the organization it acts in, in the groups of its roles. In the dev realm that
is `operators`.

**Reason.** A client-credentials token has no sign-in to choose an organization. A service account in one
organization gets that organization in its token by the default scope, which a check on Keycloak 26.7.4
confirmed. Membership is what binds people to a tenant too, so the server reads one claim for both, and a
tenant's delegated administrator can see who acts in it.

**Alternatives.**

- A hardcoded claim per client that names the tenant: a second way to state membership, which the realm's
  administrators would keep in step with the first by hand, and which a tenant's administrator can't see.
- The scanner asking for `organization:<alias>`: every scanner gains a setting, and a client could ask for an
  organization it is no member of and get an empty claim.

**Consequences.** A scanner deployed for a tenant needs its service account to be a member of that tenant only.
A service account in two organizations gets an empty claim and is refused (TEN-03).

### DD-582. The server's sign-in asks for the organization scope while tenancy is on

- **Status:** Proposed
- **Increment:** 15.5a
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** With tenancy on, the server's authorization request asks for `openid organization`. With it off,
it asks for `openid`, as before.

**Reason.** With the bare `organization` scope, Keycloak 26.7.4 asks a person who belongs to several
organizations to choose one at sign-in, and the token names that one. That is ADR 063's R3: the identity
provider decides the tenant, through a choice the person makes there. Without tenancy, the scope would add a
claim nobody reads, and a page that asks a person to choose for nothing.

**Alternatives.**

- `organization:*`: every organization in the token, which TEN-03 refuses.
- A tenant chosen in the server and asked for as `organization:<alias>`: the server would offer a choice the
  identity provider makes better, and a sign-in for an organization the person isn't in yields an empty claim.

**Consequences.** Switching tenant means signing in again (15.6). The webapp asks for the scope itself (15.6).

### DD-583. The operators' store access is a role of the store, held as the deployment decides

- **Status:** Proposed
- **Increment:** 15.5a
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The store's roles file defines `aurelius_atlas_operator`: `read`, `view_index_metadata` and
`monitor` on `aurelius-atlas-*`, and the cluster privilege `monitor`. The dev stack and the chart mount it. No
user holds it by default.

**Reason.** ADR 063 gives operators direct read access to every tenant's indices for operations and support,
outside the catalogue's API. A role of the store is how the store grants that. Who holds it depends on how a
deployment signs operators in to the store, which is its own, not the repository's.

**Alternatives.**

- A store user per operator in the chart: the chart would seed people, as the production realm doesn't (CHT-75).
- No role: each deployment writes its own, and the access ADR 063 describes differs between deployments.

**Consequences.** The role reaches every tenant's indices, trusted or not, as ADR 063's sharp edge says.
