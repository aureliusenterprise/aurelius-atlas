# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-043. Entities are documents of one index, their attributes under qualified names

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** Every entity, of every type, is one document of the index behind the alias
`aurelius-atlas-entities`, with its GUID as the document id. The document holds the system properties Atlas
keeps on a vertex (GUID, type name, super type names, state, times, users, version, labels, custom attributes)
as top-level fields, mapped for exact lookup, and the attribute values in an `attributes` object keyed by each
attribute's qualified name (`Referenceable.qualifiedName`, `hive_table.createTime`), as the vertex properties
are named. The `attributes` object is stored but not indexed (`dynamic: false`) until 4.1 designs the search
mapping.

**Reason.** A GUID is how Atlas reads, writes and refers to an entity, and a get by id is Elasticsearch's only
real-time read. One index serves every type, as one graph holds every vertex; per-type indices would multiply
shards with the number of types. A qualified name is defined by one attribute definition, whose type may not
change (TDS-08), so one field never holds two value types, which Elasticsearch could not map. Leaving
attributes unindexed until search needs them keeps 2.2 from deciding analysis and field types it cannot yet
test.

**Alternatives.** Attributes keyed by their plain names: the same name with different types in two entity
types cannot share one mapping. An index per entity type: thousands of small indices for Atlas's models alone,
and queries across a super type touch them all.

**Consequences.** The store's client reads floats as decimals and is given documents as the codec's bytes
(DD-039), so values keep their digits through Elasticsearch. 4.1 adds attribute mappings and indexes the existing
documents again (an `update_by_query`),
the first change ADR 023 records as a migration if data exists by then. Reading an entity back maps qualified
names to attribute names through the type registry (2.3).

### DD-044. A GUID is a random UUID

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** The store gives a new entity a random (version 4) UUID in canonical lower-case text, as Atlas's
`UUID.randomUUID().toString()`.

**Reason.** Atlas's clients see and keep GUIDs of this form; any process can make one without coordination,
and the chance of two equal ones is negligible.

**Alternatives.** Time-ordered UUIDs (version 7): better index locality, but a GUID would reveal its creation
time and differ in form from Atlas's.

**Consequences.** None beyond Atlas's.

### DD-045. Unique values are reserved by create-only documents

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** For each unique attribute value an `ACTIVE` entity has, the store keeps a reservation document
in `aurelius-atlas-unique-values`, whose id is a SHA-256 of the entity type name, the attribute's qualified
name and the value as the codec writes it, and which names the GUID holding it. A reservation is made with
`op_type=create`, so of two processes reserving the same value one fails, and is deleted when the entity
changes the value or leaves `ACTIVE`. A lookup by unique attributes reads the reservations by id, in real
time.

**Reason.** Atlas enforces unique attributes with a JanusGraph unique index on a shadow property
(`__u_Referenceable.qualifiedName`), composite with the type name (`PER_TYPE_UNIQUE`), removed when an entity
is deleted. Elasticsearch has no unique constraint except the document id, and a search would see neither a
value written a moment ago nor one being written concurrently. A create-only document with a deterministic id
is atomic across processes.

**Alternatives.** Search the entity index before writing: races between processes, and misses unrefreshed
writes. The value itself as the document id: limited to 512 bytes, while a `qualifiedName` may be longer.

**Consequences.** Every write of an entity with unique attributes writes one more document per changed value.
Reservations belong to the write that made them until it ends (DD-046), so recovery can release those of a
write that never finished.

### DD-046. A multi-entity write is all or nothing, through a journal

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** A write of several entities runs in steps:

1. a journal entry in `aurelius-atlas-entity-journal` records the write's id, a lease time and the state of
   every entity before it (or that it is new);
2. every unique value the write needs is reserved; a value held by another entity ends the write, before any
   entity is written, with an error 2.4 turns into an answer;
3. all entities are written in one bulk request, each conditionally (DD-047) and marked with the write's id;
4. if any entity fails, every entity written is restored to its state before, and the write's reservations are
   released;
5. the journal entry is marked committed; values no longer held are released and the entry is deleted.

Recovery, at start-up, finds journal entries whose lease has passed. A committed entry only has its releases
finished; any other is undone as in step 4: it restores an entity only while it still carries that write's id,
and releases only reservations made by that write.

**Reason.** Atlas commits all entities of a request in one graph transaction (`GraphTransactionInterceptor`).
Elasticsearch writes one document atomically but no more (ADR 047). The user chose an all-or-nothing outcome,
also after a crash, over per-entity writes or full isolation (2026-10-22): the journal makes the outcome
recoverable at the cost of one document per write, while isolation would make every read look up write states.

**Alternatives.** Per-entity atomicity: a failed batch leaves part of it written. Isolation through pending
versions and a committed flag: no reader sees a partial write, but every read pays for it.

**Consequences.** Between steps 3 and 4 another reader may see part of a write (DV-16). A write must finish
within its lease (60 seconds) or recovery may undo it; a write that finds its lease passed before step 3 gives
up. Recovery runs at start-up, so a crash's leftovers stay until a process starts.

### DD-047. Entities are written conditionally on their Elasticsearch version

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** A changed entity is written with the `if_seq_no` and `if_primary_term` it was read with, and a
new one with `op_type=create`. A conflict fails the write (DD-046 restores the rest) with a version conflict
the caller handles by reading again. Atlas's `version` field is stored as the entity has it and plays no part.

**Reason.** Atlas serialises writes inside one JanusGraph transaction per request; several server processes
writing to one Elasticsearch need optimistic concurrency, as the type definitions do (DD-029). Atlas never
increments an entity's `version` itself (`getEntityVersion` takes the entity's or 0), so it cannot serve as a
concurrency token without changing what clients see.

**Alternatives.** A lock document per entity: needs expiry when its holder dies. Incrementing `version`:
changes Atlas's responses.

**Consequences.** 2.4 decides how a write request retries after a conflict and what it answers when it gives
up.

### DD-048. A type is in use while the entity index holds one of it

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** The typedef store's usage check (DD-030) refreshes the entity index and counts the documents
whose type name is the type, in any state, as Atlas's `typeHasInstanceVertex` counts vertices of the type.
Classification and relationship types join the check when their instances are stored (3.1, 3.3).

**Reason.** A count is near real time; the refresh makes an entity written a moment ago count. Deleting a type
is rare, so the refresh's cost does not matter.

**Alternatives.** Keeping a counter per type: one more document to update atomically with every write.

**Consequences.** Until 3.1 and 3.3, a classification or relationship type is never in use.
