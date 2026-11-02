# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-246. Glossary objects are entities written through the entity and relationship stores

- **Status:** Proposed
- **Increment:** 5.2
- **Date:** 2026-10-30

**Decision.** Glossaries and categories (and from 5.2b terms) are entities of Atlas's glossary model
(`0011-glossary_model`), as `DataAccess` and the glossary DTOs keep them: an object is saved by creating or
updating its entity with `EntityWriter`, which also writes a category's mandatory `anchor`, and loaded back
from the entity and its relationship attributes with `EntityRetriever`; the relationships between glossary
objects (anchors, the category hierarchy, term categorizations) are written with the `RelationshipStore` as
`GlossaryCategoryUtils` writes them, `getOrCreate` taking an existing relationship of the type and ends, and a
removed one deleted for good. 5.2 is split by the user into 5.2a (glossaries and categories), 5.2b (terms) and
5.2c (term assignment); glossary import is a later increment.

**Reason.** Atlas's glossary is entities and relationships of internal types, read and written through its
stores; the stores here already keep entities, relationships, unique qualified names and internal types' hard
deletes as Atlas does, so the glossary's behaviour follows from them without a store of its own.

**Alternatives.** Glossary documents of their own index: simpler reads, but the glossary would no longer be
entities the entity API, search and lineage see, as they are in Atlas.

**Consequences.** A glossary write is several entity and relationship writes, each all or nothing on its own,
as in Atlas within its graph transaction only when the graph commits; a failure part way leaves what was
written. The server's models carry `0011-glossary_model`, as they do with every model loaded.
