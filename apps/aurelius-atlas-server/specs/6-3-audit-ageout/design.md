# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-309. One task finds an aging's entities and ages out their audits

- **Status:** Proposed
- **Increment:** 6.3c4
- **Date:** 2026-11-04

**Decision.** An aging is one `AUDIT_REDUCTION_ENTITY_RETRIEVAL` task. When it runs it finds the entities
of the aging, ages out each one's audits in batches of 100, and is removed. There is no
`ATLAS_AUDIT_REDUCTION` task and no stored list of the entities still to age out.

**Reason.** Atlas's retrieval task writes the GUIDs it found onto an `__auditReductionInfo` vertex, then queues
an `ATLAS_AUDIT_REDUCTION` task that works through them and shortens the list after each batch, so a stopped
run carries on where it was. Our tasks are claimed with a lease and run again when their process stops (DD-080),
and aging is idempotent: a run again finds the same entities and removes only what is still past the count or
the TTL. One task gives the same result without a second store of GUIDs and with one task to show in
`admin/tasks`.

**Alternatives.** Both tasks, the GUIDs kept in the second task's parameters: faithful, but `admin/tasks` would
answer every eligible GUID. Both tasks with a document of GUIDs: faithful, but a new document kind for no
observable difference.

**Consequences.** A task without parameters or a creator fails like any other task, after its attempts, where
Atlas marks it failed at once. A large catalogue's aging that stops is redone from its start.
