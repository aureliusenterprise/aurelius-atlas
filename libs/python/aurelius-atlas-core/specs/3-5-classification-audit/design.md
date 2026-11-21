# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-085. Classification events are collected in the request and recorded after its write

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** The classification operations, the entity writer, the relationship store and the propagation
tasks take the change notifier, as the entity writer does (DD-084), and tell it, once their write has
committed, what Atlas's would have told it during the request, in Atlas's order: the notifier's classification
methods, then `notifyPropagatedEntities` where Atlas calls it.

**Reason.** The events are recorded after the change, as entity events are (DD-082); keeping Atlas's order
keeps the events' keys, and so the order in which `{guid}/audit` lists them.

**Alternatives.** Events derived from the stored differences after the write: Atlas's quirks, such as one
update event per updated classification on each entity notified, would be lost.

**Consequences.** Every propagating operation answers what it propagated, to whom; 3.5b adds that to
`TagPropagation`'s results (DD-086).

### DD-086. Tag propagation records the propagations a request added and removed

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** `TagPropagation` keeps, per entity, the classification instances it newly listed and those it
stopped listing, in the order it changed them, as `RequestContext` keeps added and removed propagations. The
callers give them to the notifier after their write (CAU-05).

**Reason.** The propagation is computed in one place (DD-075); recording there covers every caller, including
the delete handlers and the tasks.

**Alternatives.** Comparing the entities' classification lists before and after the write: a classification
added and removed again within a request would be missed, and the order lost.

**Consequences.** `propagate` answers the entities it propagated to, which the add events need (CAU-02).

### DD-818. Propagation tells skip an entity that is not ACTIVE

- **Status:** Proposed
- **Increment:** 3.5 (a fix, 2026-11-21)
- **Date:** 2026-11-21

**Decision.** `notifyPropagatedEntities` tells an entity only while it still exists and is `ACTIVE`, beside
the entities the request deleted. A propagation task tells through that one method, from the `added` and
`removed` maps its propagation recorded, instead of calling the notifier's classification methods for the
entities its own write touched (CAU-05, CAU-06).

**Reason.** A propagation task runs after the request that queued it (TSK-02), so an entity can be deleted
while the task waits. A soft delete leaves the entity in the store as a `DELETED` tombstone that still lists
its classifications, so the task's write still counts it as changed and told it a propagated delete after
its `ENTITY_DELETE` event. The History tab then shows a removed tag on a deleted entity, and a server restart
replays a queued task (TSK-01), so the same pair can repeat. Atlas ends every propagation path in the same
filtered tell, so every tell shares one rule; it reads each entity and skips those it cannot (its comment:
"if entity is deleted, don't send propagated classifications add/remove notifications"). Aurelius's read
answers a tombstone with its values kept (EDL-06), so the filter is applied on the state instead of on a
failed read.

**Alternatives.** Filter inside the task, on the entities it changed: every propagation path would repeat the
check, and the notifier's own path would keep telling tombstones. Have the delete handler remove the entity
from queued tasks: the task's write is still correct — the propagation must be removed — only its tell is
not, and Atlas leaves the queue alone.

**Consequences.** Aurelius records less than Java Atlas, which reads the tombstone and records the event
(DV-191); a deleted entity's history stays closed. The task's write does not change.
