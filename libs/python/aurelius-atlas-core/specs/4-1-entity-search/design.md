# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-087. Basic search is split into entity and classification search

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** Increment 4.1 is split: 4.1a searches entities by type, entity filters, state, sort and paging,
with the search fields it needs (DD-088); 4.1b adds the classification search of
`ClassificationSearchProcessor`. The free-text `query` of basic search goes with quick search to 4.2.

**Reason.** Atlas's two processors are separate, and each is as large as one increment.

**Alternatives.** One increment of about twice the size; the free text with 4.1, where it would need the full
text index 4.2 builds anyway.

**Consequences.** Until 4.1b a search naming a classification is refused (DV-46).

### DD-088. Entity attributes are searched in typed search fields named after their defining type

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** An entity document carries `search`, a flat object (`subobjects: false`) of its searchable
values: each primitive, enum or array-of-primitive attribute under `<kind>.<qualified name>`, the qualified
name being Atlas's vertex property key (`hive_table.name`, `Referenceable.qualifiedName`, `__guid`), and
`<kind>` the Elasticsearch type its Atlas type maps to: `keyword` for strings and enums, `long` for the
integer types and dates, `double` for `float`, `double` and the big number types, `boolean`. Dynamic templates
on the kind map each new field. The system attributes of the entity root are filled from the document's own
fields. The entity store computes `search` with the registry when it writes an entity.

**Reason.** Atlas's index keys a property by its defining type, so one attribute is one field across sub
types, and its type decides how it compares. A kind in the field's name lets Elasticsearch map a field the
first time it is written, in any process, without a mapping kept in step with the type definitions.

**Alternatives.** Mapping each field from the type definitions when they change: the same fields, but every
process and every type change would update the mapping. One `flattened` field: no range or numeric sort.
Filtering in memory: every search reads every entity of its types.

**Consequences.** Entities written before 4.1a have no `search` until written again. The field limit of the
entity index is raised to 100,000. The big number types compare as doubles.

### DD-089. A search is a query of the entity documents, ordered by creation when no sort is given

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** `EntitySearchProcessor` builds a search query of its own: the types, the state, the filter tree
over search fields with Atlas's operators, the sort, offset and size. The entity documents answer it with the
matching entities and their total, which is `approximateCount`; Elasticsearch as a `bool` query, the in-memory
documents by evaluating it. Without `sortBy` entities come by creation time, then GUID.

**Reason.** One query instead of Atlas's index query, graph query and in-memory predicates, whose combination
the rules of SRC-05 state; Atlas's order without a sort is the index's and has nothing to keep.

**Alternatives.** Elasticsearch's query language in the core: the in-memory documents could not answer it.

**Consequences.** `approximateCount` is exact.
