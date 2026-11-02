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
