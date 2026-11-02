# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-305. An import replaces an entity's classifications through the classification store, after its write

- **Status:** Proposed
- **Increment:** 6.3b1
- **Date:** 2026-11-02

**Decision.** When an import updates an entity, the entity's own write comes first. Then its own
classifications are removed and the given ones added through `EntityClassifications`, each as that store writes
it, with its propagation and its audit events.

**Reason.** Atlas removes and adds them inside the entity's mapping, through `deleteClassification` and
`addClassifications`, so every propagation rule applies. Our classification store already holds those rules,
and the entity writer does not remove classifications. Calling the store keeps one implementation of them.

**Alternatives.** Removing and adding the classification instances inside the entity's write: one write, but a
second copy of the removal and propagation rules in the writer.

**Consequences.** An import's update is several writes, not one: a failure between them leaves the entity
updated with its old classifications. The classification events follow the entity's event (DV-123).
