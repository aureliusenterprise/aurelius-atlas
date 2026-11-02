# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-243. DSL traversals and projections are evaluated in steps

- **Status:** Proposed
- **Increment:** 4.4
- **Date:** 2026-10-30

**Decision.** The DSL composer (DD-242) answers a plan: the filter tree of the final entities, the steps
before them, and the `select` and `groupby`. A move to referred entities (a source naming a reference, a
`select` of one) is a step: the entities found so far are read, the GUIDs their attribute refers to taken, and
the next filter holds for those GUIDs. A condition on a referred entity (`db.name`) or a classification
attribute (`Dimension.tagAttr1`) is a criterion whose value the executor resolves to GUIDs before searching:
the referred entities matching, the entities referring to them by reference (`references`, DD-057) or
relationship end (DD-061) and confirmed by reading the attribute; or the classification instances matching, as
the classification search finds them (DD-090). Aggregates, groups and moves read the entities found in one
search of at most 10,000; rows and groups are built from them in memory, as `SelectClauseProjections` builds
them from vertices.

**Reason.** Atlas walks edges; the documents have none. Resolving to GUIDs keeps each step a search of the
entity documents with the filter tree of DD-242, and the in-memory documents answer the same plan. A reference
is read as a read answers it, so plain references and relationship ends, legacy or not, give the same answer.

**Alternatives.** Denormalising referred attributes into the referring document's search fields: one query,
but every write would have to rewrite the entities referring to the one written. Elasticsearch `terms` lookups
across indices: they read one document's field, not a relationship's other end. Aggregating in Elasticsearch:
Java's comparison for `min` and `max` (no value least, kinds equal) and row deduplication are not its.

**Consequences.** A step reads at most 10,000 entities (DV-98); a query reaching past them answers from the
first 10,000. A condition on a referred entity costs a search, a read of the candidates and of their
references.
