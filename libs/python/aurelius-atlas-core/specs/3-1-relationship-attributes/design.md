# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-064. Relationship attribute values are relationships

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** From 3.1b an entity write maps the values of relationship attributes, legacy ends included, to
relationship instances (DD-061) as `EntityGraphMapper` maps them to edges, and stores none of them as an
attribute value. Reads answer `relationshipAttributes`, and the legacy ends in `attributes`, from the entity's
relationships. It supersedes DD-050 and DD-053. Entity documents written before 3.1b keep the legacy ends
2.4 stored as attribute values; they are not migrated, since no deployment holds entities yet.

**Reason.** Atlas keeps a relationship attribute's value only as the edge; one place for it keeps a value
written through an entity and one written through `RelationshipREST` the same.

**Alternatives.** Keeping legacy ends as attribute values as well: two copies of every such reference, which
every relationship write would have to keep equal.

**Consequences.** DV-18 and DV-22 end. Plain references, those of attributes that are no relationship end, stay
attribute values (DD-049).

### DD-065. A relationship keeps one array index, the last writer's

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** A relationship document holds `index`, Atlas's `__index` edge property: the position the last
write of an array relationship attribute gave it, at either end. An array of relationships reads in the order
of their indices when the first has one, else in the order the entity lists them.

**Reason.** Atlas stores the position on the edge, so both ends of a `LIST`-to-`LIST` relationship share it; one
field reproduces what Atlas reads, its quirks included.

**Alternatives.** A position per end: an order Atlas does not keep.

**Consequences.** An array whose elements are also in an array at the other end may read in another order after
the other end is written, as in Atlas.

### DD-066. Relationship attributes are mapped in memory and written with the entities

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** `RelationshipMapper` maps a request's relationship attributes in memory, after its entities are
discovered: it reads the relationships the entities list as it needs them, keeps the ones it creates, changes
and removes, and the changes to the ends' lists, and the writer writes them with the entities in the one write
of DD-052 and DD-062. A relationship between two entities is looked for among the relationships both list.

**Reason.** A request is all or nothing (DD-052), and the lists on both ends (DD-061) make the relationships of
an entity, and those between two, readable by id without a search.

**Alternatives.** Writing each relationship as it is mapped: a failing request would leave some behind.

**Consequences.** A write reads every relationship of the entities whose relationship attributes it maps; an
entity at the centre of many is costly to update through them, as Atlas iterating its edges is.

### DD-067. Delete cascades follow owned relationships from 3.1b

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** The owned-reference cascade of a delete (DD-060) also follows the relationships of owned
relationship attributes, from 3.1b rather than 3.2. 3.2 keeps the owned entities an update replaces or drops.

**Reason.** From 3.1b a legacy end such as `hive_table.columns` is no longer stored as an attribute value
(DD-064), so a cascade that read only attribute values would stop at it until 3.2.

**Alternatives.** Leaving it to 3.2: deletes between 3.1b and 3.2 would leave owned entities behind that 2.5
deleted.

**Consequences.** 3.2's roadmap row narrows to the owned entities an update drops (DV-31).
