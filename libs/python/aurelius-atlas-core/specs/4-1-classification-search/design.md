# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-090. A classification search finds instances first, then the entities listing them

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** The entity documents gain what Atlas keeps on an entity vertex of its classifications, computed
when an entity is written from the instances it lists: `__traitNames` and `__propagatedTraitNames`, the type
names of those attached and propagated, `__classificationNames` and `__propagatedClassificationNames` as
`|a|b|`, and the GUIDs of the instances. A search naming classifications without tag filters tests the type
names, as Atlas's `buildTraitPredict` does; with tag filters it reads the instances of the types named from
the classification index, keeps those that match, evaluated with the search query's predicates over their
attribute values, and adds to the entity query that the entity lists one of them.

**Reason.** An entity already lists every classification it carries, propagated ones included (DD-070,
DD-075), and tag filters are what classification instances are searched by; no mapping of classification
attributes is needed, and the filter semantics are the ones entity filters have.

**Alternatives.** Search fields on classification documents: the same answers, with a second set of mappings.
Classification type names on the entity only: tag filters could not be answered.

**Consequences.** A search reads every instance of the types it names; an entity query names at most 65,536
instances, Elasticsearch's `terms` limit, beyond which the search fails.
