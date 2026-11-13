# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-563. A request's tenant is the one organization its token names

- **Status:** Proposed
- **Increment:** 15.1
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** With tenancy on, the tenant is read from the token's organization claim, which Keycloak's
`organization` client scope adds. The claim must name exactly one organization. A client that acts for a person
in several organizations asks for the scope `organization:<alias>` at sign-in, which puts that one alone in the
token. A token naming none or several is refused with 403.

**Reason.** The identity provider already knows who belongs to which organization and lets the person choose one
at sign-in (ADR 063, R3). The server checks the token's signature, so it doesn't need to look anything up. A
header or a path naming the tenant would need a second check of the caller's right to it. Refusing a token with
several organizations, rather than taking the first, keeps a request from acting in a tenant that nobody chose.
Keycloak writes the claim as a list of aliases, or as an object keyed by alias when its mapper adds the id or
attributes, so both forms are read.

**Alternatives.**

- A header `X-Tenant` checked against the token's organizations: the client chooses per request. It leaves two
  sources to keep in step, and the dashboards can't send it.
- The first organization of several: deterministic only as long as Keycloak's order is.
- A realm per tenant: see ADR 063.

**Consequences.** A person in two organizations signs in again to switch tenant (15.6). So does an operator
reading a tenant that trusts the operators: trust makes them a member (DD-567). Service clients, which
can't be members of an organization, get the claim from a hardcoded mapper on their client (15.5).

### DD-564. The roles in a tenant are the organization's own groups, from the organization claim

- **Status:** Proposed
- **Increment:** 15.1
- **Date:** 2026-11-13
- **Supersedes:** none; with tenancy on, replaces how AUZ-01 (DD-300, Accepted) reads the roles

**Decision.** With tenancy on, a user's roles in the tenant are those of the four Atlas roles held as top-level
groups of the tenant's organization: `/atlas-read`, `/atlas-write`, `/atlas-types` and `/atlas-admin`. Keycloak's
Organization Group Membership mapper writes them into the organization claim, under the tenant's alias:
`"organization": {"acme": {"groups": ["/atlas-write"]}}`. Realm groups and the server client's roles count for
nothing while tenancy is on.

**Reason.** Keycloak's organizations have their own groups since 26.6, in a hierarchy apart from the realm's
groups, and a delegated administrator of one organization can assign them (ADR 063, R10). Client roles and
realm groups are realm-wide: they would grant the same right in every organization a person belongs to (R2),
and only a realm administrator can assign them. A check on Keycloak 26.7.4 showed the following:

- The mapper writes only the groups of the organizations the token names. With `organization:acme`, globex's
  groups aren't in the token at all.
- The organization's groups don't appear in the user's realm groups.
- An administrator granted `manage` on acme alone could add and remove members of acme's groups, and was
  refused on globex's groups.

**Alternatives.**

- Realm groups `/<alias>/<role>` in the groups claim: one realm hierarchy per tenant, which only a realm
  administrator, or one granted rights on those groups, can manage. The token would carry the groups of every
  organization, so a parsing fault could grant in the wrong tenant.
- Client roles named `<alias>:atlas-write`: a client role per organization and role, and realm-wide.
- Client roles and organization groups together: a realm-wide role would grant in every tenant.

**Consequences.** Each client the server accepts tokens from needs the Organization Group Membership
mapper, and provisioning a tenant creates its organization and its four groups (15.5). Nested groups grant
nothing, so a tenant can organize its own groups under its role groups without widening them.

### DD-565. A tenant alias is an index-safe slug from a provisioned list

- **Status:** Proposed
- **Increment:** 15.1
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** A tenant's alias must be a lowercase letter or digit, followed by up to 62 lowercase letters,
digits or `-`, and must be among the provisioned tenants. Until 15.3 adds the tenants index, the provisioned
tenants are the setting `tenancy_tenants`. Any other alias answers 403 `Tenant <alias> is not provisioned`.

**Reason.** The alias becomes part of the tenant's index names in 15.2: `aurelius-atlas-tenant-<alias>-entities`
and its siblings. The `tenant-` segment keeps them apart from the operator organization's indices, which are
a single-tenant deployment's `aurelius-atlas-*` (DD-567). Without it, a tenant `entity` would get
`aurelius-atlas-entity-journal`, the operator organization's journal. Elasticsearch forbids uppercase letters
and some punctuation in index names, and a 255-byte name leaves room for the prefix and suffixes. Checking the
alias before any store is built keeps a token from naming an index of its choosing. Requiring the tenant to be
provisioned means an organization created in Keycloak gets no storage until an operator provisions it
(ADR 063). The setting is a stand-in with the same check, so 15.3 changes only where the list comes from.

**Alternatives.**

- Map any alias to a safe index name, by hashing it: the indices can no longer be told apart by an operator.
- Create a tenant's indices the first time a token names it: any organization in the realm would get storage.

**Consequences.** A Keycloak organization alias with uppercase letters or other characters can't be a tenant.
The operator gives organizations a lowercase alias. One store role on `aurelius-atlas-*` reaches the operator
organization's and every tenant's indices.

### DD-566. Tenancy is off by default and not offered before its stores are separate

- **Status:** Proposed
- **Increment:** 15.1
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** `tenancy_enabled` defaults to false. While it is off, the server reads no tenant and answers as
before. No Helm value, compose file or user guide offers the setting until 15.4, when each tenant has its own
stores and workers.

**Reason.** Single-tenant deployments and the parity scenarios must stay as they are (ADR 063, R5). Splitting
the series keeps each pull request reviewable. But with only 15.1 delivered, tenants that are refused or
admitted would still share the default indices, and a deployment that turned the setting on would believe it
was isolated when it was not.

**Alternatives.**

- Deliver 15.1 to 15.4 as one pull request: well over the ~1,500 lines an increment may change (ADR 051).
- Refuse to start with the setting on until 15.4: a guard that every increment edits, and the tests of 15.1
  to 15.3 couldn't turn it on.

**Consequences.** The setting exists in the code from 15.1 on, documented only in the server's settings and this
spec, and is used by the tests alone. 15.4's spec lists offering it among its deliverables.

### DD-567. The operator organization keeps the default indices, and operators only read elsewhere

- **Status:** Proposed
- **Increment:** 15.1
- **Date:** 2026-11-13
- **Supersedes:** none

**Decision.** The setting `tenancy_operator_organization` (`operators` by default) names the default
organization, whose members run the platform. It is always provisioned, and in 15.2 it keeps a single-tenant
deployment's index set, `aurelius-atlas-*`. A user holding the realm role `tenancy_operator_role`
(`atlas-operator` by default) holds at most `atlas-read` in any other tenant, whatever groups of that tenant
they have.

A tenant trusts the operators unless it is provisioned without that trust or withdraws it (15.3). While it
does, the operators are members of its organization, in its `atlas-read` group (15.5), so they read it by
signing in to it like its own users. The server knows no trust of its own.

**Reason.** Keycloak puts an organization in a token only for its members. Making trust a membership keeps one
answer to who may act where: the identity provider's (DD-563, ADR 038). The cap in the server is the second
lock ADR 063 asks for (R7): a tenant administrator can put an operator into the tenant's `atlas-write` group,
but can't change a realm role, which only a realm administrator assigns. The marker is a realm role, not the
operator organization's groups, because a token for acme carries acme's groups alone (DD-564). Keeping today's
indices for the operator organization means a single-tenant deployment turns tenancy on without moving its
catalogue (R5).

**Alternatives.**

- A header naming the tenant an operator reads, checked by the server against a trust flag: a second source of
  who may read where, and the dashboards can't send it.
- Operators read every tenant without trust: a tenant could not close its catalogue to them (R8).
- The operator organization's groups as the marker: absent from a token for any other tenant.

**Consequences.** Operators need the realm role as well as membership of the operator organization. 15.5 assigns
both, and keeps them in step. An operator who is also a genuine member of a tenant, with write access there,
only reads it while they hold the role. The operator organization's alias must not be among `tenancy_tenants`.
