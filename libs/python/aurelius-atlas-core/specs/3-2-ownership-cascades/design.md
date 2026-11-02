# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-068. Owned entities an update drops are deleted through a view of the request

- **Status:** Proposed
- **Increment:** 3.2
- **Date:** 2026-10-22

**Decision.** After a write request is mapped (DD-052, DD-066), the owned entities it dropped are deleted by the
delete handlers of 2.5, reading through `TransactionView`: the entity store as the request has changed it, its
changed entities and relationships read as changed, the relationships it removed gone, and the entities referring
to a deleted one found by the search of DD-057 and checked against their changed references. The deletes' changes
replace the request's own for the same documents, and everything is written in the request's one write.

**Reason.** Atlas deletes them inside the update's transaction, after the update's own edge changes; the view
gives the handlers that state without a second write, so the request stays all or nothing.

**Alternatives.** Deleting them in a second write after the update: simpler, but an update could then succeed
while the deletes fail, which Atlas never shows.

**Consequences.** The delete handlers read the store through a protocol (`EntityView`) that both `EntityStore`
and `TransactionView` answer.

### DD-069. A reference to a deleted entity stands for a deleted edge when reviving

- **Status:** Proposed
- **Increment:** 3.2
- **Date:** 2026-10-22

**Decision.** `updateInConsistentOwnedMapVertices` revives an owned map entry whose edge and entity are both
`DELETED`; a stored plain reference has no state (DD-058), so an entry that keeps naming a `DELETED` entity is
taken as one with a deleted edge, and the entity becomes `ACTIVE` again.

**Reason.** Atlas soft-deletes the edges to an entity with it, so a `DELETED` entity is the case in which its
edge is deleted too.

**Alternatives.** A state per stored reference: rejected with DD-058.

**Consequences.** An entity deleted without its owner, its owner's entry kept by the soft delete, is revived by
the owner's next update that keeps the entry, as in Atlas.
