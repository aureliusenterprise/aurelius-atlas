# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-245. Lineage walks the relationships of the process edges

- **Status:** Proposed
- **Increment:** 5.1
- **Date:** 2026-10-30

**Decision.** `EntityLineageService` ports Atlas's default traversal (`getLineageInfoV2`) and lineage on
demand over the relationship documents (DD-061): an edge `__Process.inputs` or `__Process.outputs` is a
relationship of that label, going out of end 1 (the process) into end 2 (the data set), read through the
relationships an entity lists, as `graph_helper.edges_for_label` reads them for the other edge lookups. Each
entity's relationships are read once per lineage. The Gremlin lineage (`atlas.lineage.query.use.gremlin`) is
not ported. Atlas's lineage settings are server settings with Atlas's defaults: on demand off, 3 relations
each way, at most 9,000 relations.

**Reason.** The relationships are the edges Atlas walks: one document per edge, listed by both ends, in any
state as Atlas's `getEdges` returns them. Walking them keeps Atlas's order of visits, its visited sets and its
cap, which decide what a deep or wide lineage answers.

**Alternatives.** A search per step for the relationships of a label whose end is the entity: an index on ends
the relationship documents do not have, and a refresh before each read. Denormalising each entity's process
edges into its document: a second copy every relationship write would keep equal.

**Consequences.** A lineage costs two reads per entity it reaches (the entity and its relationships); the
9,000 relation cap bounds it. Lineage on demand, off by default as in Atlas, is answered once the setting is
on.
