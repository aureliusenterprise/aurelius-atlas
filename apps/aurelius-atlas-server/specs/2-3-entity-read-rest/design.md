# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-049. Attribute values are stored normalised; a struct inline, a reference as a GUID

- **Status:** Proposed
- **Increment:** 2.3
- **Date:** 2026-10-22

**Decision.** An entity document holds each attribute value as its attribute's type normalises it
(`getNormalizedValue`), in the codec's JSON (DD-039): a date as epoch milliseconds, an enum as its value's
name, numbers with their digits. A struct value is held inline as `{"typeName": …, "attributes": {…}}`, its
attributes by name and normalised the same way. A reference to an entity, whether an `objectid` attribute, an
element of an array or a value of a map, is held as the referenced entity's GUID; a soft reference
(`isSoftReference`) is held as Atlas holds it, `typeName:guid`. Reading an entity gets the entities its
attributes refer to by GUID, in one request, to build their object ids and owned entities; a GUID that finds
no entity reads as nothing, as an edge to a removed vertex does.

**Reason.** Atlas keeps a struct in a vertex of its own and a reference as an edge; Elasticsearch has
neither, and one document per entity is what DD-043 decided. A struct belongs to its entity alone, so it
stays inside it. A reference's GUID never changes, where the referenced entity's unique attributes and
type may, so the GUID is the only stable thing to store; everything else the object id shows is read from
the referenced entity, as `toAtlasObjectId` reads it from the vertex.

**Alternatives.** Storing the object id with its unique attributes: stale once the referenced entity
changes. Structs as documents of their own: a second read per struct, and nothing ever refers to one.

**Consequences.** 2.4 writes values in this form, resolving every object id it is given, by GUID or by
unique attributes, to a GUID first. A reference read needs a second `mget` per nesting level of owned
entities. 3.1 decides how relationship attributes are stored; references that are also relationship ends
(legacy attributes) move there then.

### DD-050. Relationship attributes read empty until relationships are stored

- **Status:** Superseded by DD-064
- **Increment:** 2.3
- **Date:** 2026-10-22

**Decision.** Until 3.1 stores relationships, an entity reads as Atlas reads one without relationship
edges: `relationshipAttributes` names every relationship attribute of its type, null for a `SINGLE` end and
`[]` for a `LIST` or `SET` end, the end chosen as Atlas chooses it without edges (the attribute's first
relationship type). `ignoreRelationships=true` leaves `relationshipAttributes` out.

**Reason.** The keys and the empty values are what Atlas answers for an entity no relationship has reached
yet; answering them now keeps the response's shape, and 3.1 only fills values in.

**Alternatives.** Leaving `relationshipAttributes` out until 3.1: a different shape for every entity, which
clients that read the keys would notice.

**Consequences.** Until 3.1, a reference given as a legacy relationship attribute (DD-049) reads in
`attributes` but not in `relationshipAttributes` (DV-18).

### DD-051. Entity reads are tested on entities written through the store until 2.4

- **Status:** Proposed
- **Increment:** 2.3
- **Date:** 2026-10-22

**Decision.** 2.3's HTTP tests write the entities they read through `EntityStore` (2.2), in the stored form
of DD-049, and check every read rule on them. Its parity scenarios cover what needs no entity: unknown GUIDs
and types, invalid and missing unique attributes, values that find nothing. 2.4 adds scenarios that create
entities over REST and read them back.

**Reason.** A parity scenario only reaches the server over REST, and entities can be created over REST from
2.4 on. Seeding through the store tests the read path now without porting the write path early.

**Alternatives.** Merging 2.3 into 2.4: one pull request far above the size limit. Moving 2.4 before 2.3:
a write increment whose responses could not be read back.

**Consequences.** Until 2.4, the stored form the tests write is checked against Atlas's responses only by
the expectations read from the Java source; 2.4's scenarios check both directions.
