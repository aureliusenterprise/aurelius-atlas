# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-248. An entity's meanings are read from its listed relationships

- **Status:** Proposed
- **Increment:** 5.2c
- **Date:** 2026-10-31

**Decision.** An entity header's `meanings` (GTA-05) are read from the relationships the entity lists
(DD-061): those of type `AtlasGlossarySemanticAssignment` whose second end is the entity, in the order listed,
with their terms read in one request. The relationships are read once per response, as the header's
relationship attributes already read them. Basic search's `termName` and the DSL's `hasTerm` read the terms'
listed relationships the same way and search the entities by GUID, as a DSL condition on referred entities
does (DD-243).

**Reason.** Atlas reads the entity's incoming edges with the assignment's label. The listing is the one place
an entity's relationships are known by real-time `get`s, so a header read right after an assignment shows it,
as every other relationship attribute does.

**Alternatives.** A search of the relationship index by type and end: one request per page of headers, but it
sees an assignment only after a refresh. A field of meanings on the entity document: every assignment would
write the entity too.

**Consequences.** A header costs a read of all the entity's relationships, also for an entity with many and no
meanings; a header that reads relationship attributes pays it once. A term assigned to more entities than one
search window holds is not searched beyond it.
