# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-061. Relationships are documents of their own index, listed by both ends

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** A relationship instance is one document of the index behind `aurelius-atlas-relationships`, keyed
by its GUID: type name, label, end 1 and end 2 GUIDs, status, times, users, version, provenance type, home id,
tag propagation and attribute values (as DD-049 stores values). Each end entity's document lists the GUIDs of
the relationships it is an end of (`relationshipGuids`), written with the relationship. Reading an entity's
relationships is a get of its document and of the listed relationships, in real time.

**Reason.** Atlas keeps a relationship as an edge both vertices reach. Listing the GUIDs on both ends keeps
entity reads to gets by id, never a search that waits for a refresh, at the cost of writing the ends with the
relationship.

**Alternatives.** Relationship documents found by searching their end GUIDs: writes touch only the relationship,
but every entity read with relationships pays a refresh and a search, and may miss one just written.

**Consequences.** An entity at the centre of many relationships (a database with thousands of tables) has a long
list in its document, and writers relating entities to it conflict on it and retry (DD-052, DV-30). Ten thousand
GUIDs are about 400 KB, well inside Elasticsearch's document size.

### DD-062. An entity write also writes relationships, all or nothing

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** `EntityStore.write` takes relationship changes next to entity changes: new, changed and removed
relationships, conditional on the version read, in the same bulk request and the same journal entry as the
entities (DD-046, DD-056). Recovery restores relationships as it restores entities.

**Reason.** Creating a relationship changes three documents, deleting an entity may change many; a partial write
would leave a relationship its ends do not list, or a list naming a relationship that does not exist.

**Alternatives.** A separate relationship store with its own journal: two writes per request, with a window in
which one is done and the other not.

**Consequences.** The journal entry holds the relationships' states before the write too.

### DD-063. 3.1 is split into relationship instances and relationship attributes

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** 3.1a ports relationship instances: models, the relationship type's value side, storage and
`RelationshipREST`, and the deletion of an entity's relationships. 3.1b ports relationship attributes of entities:
`relationshipAttributes` in reads, relationships created, changed and deleted by entity writes, legacy ends read
through relationships, and inverse references; it replaces DD-053.

**Reason.** Together they are two to three times the size an increment may have (ADR 051).

**Alternatives.** One increment: one pull request far above the limit.

**Consequences.** Until 3.1b, entities read with empty relationship attributes (DD-050) even when relationships
created over `RelationshipREST` name them.
