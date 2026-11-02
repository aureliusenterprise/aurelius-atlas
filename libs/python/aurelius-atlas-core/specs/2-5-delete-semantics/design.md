# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-056. An entity write also removes documents, journaled like the others

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** An `EntityChange` may remove its entity instead of writing a new state. The removal is a
`delete` action of the same bulk request, conditional on the version read (DD-047); the journal entry records
the entity's state before and lists the removed GUIDs. A failed write restores a removed entity; recovery
restores a removed entity of an unfinished write when no document has its GUID. A removed entity holds no
unique value: its reservations are released as for one that left `ACTIVE`.

**Reason.** A hard delete or a purge removes entities and changes those referring to them in one request; the
all-or-nothing write of DD-046 already covers the changes, and removals need the same guarantee.

**Alternatives.** Marking removed entities and deleting them in a second step: a reader would see them in
between, and a crash would leave them. Removing them after the write commits: a crash in between leaves
entities the response called purged.

**Consequences.** Recovery cannot tell a removal undone by it from a later write's removal of the same GUID;
a GUID is removed once, so this does not arise.

### DD-057. Entities referring to one are found through an indexed field of GUIDs

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** Every entity document holds `references`, a keyword field of the GUIDs its references name (its
own object id attributes and the elements and values of its arrays and maps of object ids; not soft references,
not references in structs), set by `EntityStore` on every write. Deleting an entity refreshes the entity index,
then searches `references` for its GUID, in pages. Preparing the store adds the field's mapping to an existing
entity index; documents written before it have no `references` until they are written again.

**Reason.** Atlas follows an entity's incoming edges; documents have none. Of the alternatives offered, the
indexed field keeps writes to the entities written (DD-052), and the refresh makes every write finished before
the delete visible.

**Alternatives.** A reverse list on each referenced entity, kept by the same write: exact, but every write that
adds or drops a reference rewrites the entities it names, and popular entities become write hot spots.

**Consequences.** A referrer written while the delete runs may be missed (DV-27). Lineage (5.1) and
relationships (3.1) can use the same field.

### DD-058. A stored reference stands for an edge: active for a delete, deleted for a purge

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** A stored reference has no state of its own. A delete treats the references to the entities it
deletes, and those of an `ACTIVE` owner to its owned entities, as active edges; a purge treats them as deleted
edges, which a soft delete left behind.

**Reason.** Atlas soft-deletes an entity's edges with it: the edges a purge finds deleted are those of entities
a delete made `DELETED`, which is what this rule reads from the entities' states.

**Alternatives.** A state per reference in the stored form (DD-049): an exact copy of the edges' states, at the
cost of a second representation of every reference until 3.1 stores relationships.

**Consequences.** A reference written to an entity after it was deleted counts as deleted for a purge, where
Atlas would hold an active edge and leave it.

### DD-060. The owned-reference cascade moves from 3.2 to 2.5

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** Deleting an entity deletes the entities its owned reference attributes name (`ownedRef`), as
`DeleteHandlerV1.getOwnedVertices` does, from 2.5. Composition through `relationshipDefs` and deleting an owned
entity whose reference an update drops stay with 3.2.

**Reason.** Owned references are stored as GUIDs (DD-049); following them needs no relationships, and without
them a delete would leave owned entities `ACTIVE`, unlike Atlas.

**Alternatives.** All cascades in 3.2, as the roadmap first had it: deletes would differ from Atlas until then.

**Consequences.** The roadmap's 2.5 and 3.2 rows change accordingly.
