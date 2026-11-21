# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the Design Log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-820. A tenant's rules are read with the caller's token and cached per tenant

- **Status:** Proposed
- **Increment:** 12.7f
- **Date:** 2026-11-21
- **Supersedes:** DD-499, for a caller acting in a tenant

**Decision.** When the caller's token names one organization, the app reads that tenant's rules with the
caller's token and caches them under the tenant. A caller acting in no tenant keeps DD-499's read as the app's
own identity, under its own cache entry.

**Reason.** Each tenant's rules sit in its own indices (15.2), and the server answers a token in the tenant
it names. The app's service account names none, so every read was refused. DD-499 refused forwarding because
a cache filled under one user's visibility would answer another; per tenant that cannot happen, as every
member of a tenant reads its rules (every role holds `atlas-read`), and no set crosses tenants.

**Alternatives.**

- The service account made a member of every tenant, asking for a token per tenant: a realm membership and a
  token per tenant, kept by the tenant command, for a read the caller may already make.

**Consequences.** The audit trail of a tenant's rule read names the user who was editing, not the app. A user
whose token the server refuses for the search gets the 502 of VEV-06, as any refused read does.
