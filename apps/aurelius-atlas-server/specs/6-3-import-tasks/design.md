# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-361. An import holds the tasks it records until it ends

- **Status:** Proposed
- **Increment:** 6.3d
- **Date:** 2026-11-05

**Decision.** An import with tasks enabled starts a hold: an id and a time an hour ahead. Every task its
entity writes record carries the hold, and no process claims a task while its hold lasts. When the import
ends, in success or failure, it releases its tasks and wakes the workers. TSK-03 passes over the tasks the
deleting import holds.

**Reason.** Our entity writes are conditional on the version read (DD-052), so a task's write between an
import's read and write of an entity makes the import lose. One retry is enough against another request but
not against a worker running hundreds of tasks the import itself just recorded: the import's writes and its
tasks touch the same entities. Atlas never meets this, because it locks the GUIDs a transaction changes, so
they wait for each other. Holding the tasks removes the import's own tasks from its way. A hold stored on each
task works across replicas, which all run workers (DV-38). Its time limit means a crashed import only delays
propagation.

**Alternatives.**

- More retries, with a backoff: makes the failure rarer, but still a matter of chance with a busy worker, and
  every request would pay for it.
- Pausing the worker of the importing process: no other replica would know.
- Locks on GUIDs, as Atlas has them: a lock service across replicas, for every write.

**Consequences.** Propagation from an import starts when the import ends (DV-138); in the meantime, entities show
their own classifications but not those propagated to them. A re-import shortly after an import can meet the first
import's tasks still running and is refused as TSK-03 says, as Atlas would be. An import running longer than an
hour releases its tasks to the workers early, and the race comes back for what remains.
