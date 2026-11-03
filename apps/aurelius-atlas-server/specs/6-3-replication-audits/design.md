# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-307. The replication bookkeeping is written unchecked and read as entities

- **Status:** Proposed
- **Increment:** 6.3c2
- **Date:** 2026-11-02

**Decision.** The audit entry and the servers an export or import saves, and the marks on its entities, are
written without a privilege check. The two endpoints that read them read through the request's authorizer, as
entity reads.

**Reason.** Atlas writes them through `DataAccess` and the entity store, which check the acting user's entity
privileges. Under Atlas's default policy the administrator holds every privilege, so the check never refuses.
Under our fixed roles (DD-300) `atlas-admin` grants only the admin privileges, so the check would fail an export
after its ZIP is built. The operation was already allowed by `ADMIN_EXPORT` or `ADMIN_IMPORT`; its bookkeeping
is part of it. Reading stays checked, as Atlas's store and search check it.

**Alternatives.** Checking the writes: faithful, but a user with only `atlas-admin` could not export. Checking
the reads against an admin privilege: Atlas asks none.

**Consequences.** A reader without `atlas-read` is refused a server and sees no audit entries (DV-130). The core
services take the authorizer they read with; the audits writer is built with none.
