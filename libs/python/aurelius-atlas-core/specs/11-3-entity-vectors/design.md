# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-434. The vector lives on the entity's document, in an index that keeps sources as written

- **Status:** Proposed
- **Increment:** 11.3
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** A stored entity has an `embedding`: its vector, the model and the source hash. With embedding
on, the entity index is created with `index.mapping.exclude_source_vectors: false`. The embedder's vectors are
written by the store's own whole-document writes, never by partial updates.

**Reason.** One document per entity keeps kNN, the filters and the facets in one query (ADR 047). Measured on
Elasticsearch 9.5.5, with the default setting an index that maps a vector rewrites the source of every
document it holds, vector or not: `1.10` is stored as `1.1`, and `12345678901234567890.10` as
`1.2345678901234567E19`. The store sends its documents as the bytes of Atlas's codec so that values keep their
digits (DD-039); the default would break that for every entity. No read option undoes it, as the source is
rewritten when stored. With the setting off, sources stay byte for byte, and every read returns the vector, so
a write that replaces the whole document carries it. A partial update rewrites the source too, so the indexer
writes whole documents.

**Alternatives.**

- The default setting, naming the vectors in the reads that writes start from: every source rewritten when
  stored, digits lost.
- The vectors in an index of their own: kNN there and the filters and facets on the entities, two queries and
  two stores to keep in step.
- Partial updates of the embedding: each one rewrites the entity's source.

**Consequences.** Every read of an entity, searches included, fetches its vector, about 8 KB of JSON at 384
dimensions. The setting is static: an index created without it is moved (DD-439).

### DD-435. A source hash, checked at every write, decides whether an embedding is still the entity's

- **Status:** Proposed
- **Increment:** 11.3
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** An embedding records the SHA-256 of what its text was made of. Each write recomputes it from the
entity being written and drops an embedding whose hash differs. The hash covers the classifications' GUIDs,
not their names.

**Reason.** The write is the one place every change passes through, so no stale vector survives a change of
name, description or classifications, whichever service made it. The entity holds its classifications' GUIDs,
not their names; a GUID changes whenever a classification is added or removed, so hashing the GUIDs needs no
read of the classifications during a write.

**Alternatives.**

- The indexer comparing hashes of every entity: a scan of the whole store each round.
- Dropping the embedding on every write: an entity without a vector after each unrelated change.

**Consequences.** A classification's type renamed in place, with its GUID kept, leaves the old name in the
embedding until the entity changes otherwise.

### DD-436. The indexer polls the store for entities without a current embedding

- **Status:** Proposed
- **Increment:** 11.3
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** Each round queries the entity index for entities without an embedding of the configured model,
embeds a page of them and writes each embedding on the version it read, until none is left. The server runs a
round at start and every poll interval.

**Reason.** The store already says which entities need an embedding, so there is no queue to keep in step and
nothing to lose when a server stops. The same query backfills the entities stored before embedding was on, and
re-embeds everything when the model changes. A conditional write means two servers embedding at once only lose
work, never data.

**Alternatives.**

- A queue of changed entities, written beside each entity write: a second record of every change.
- Embedding inside the write: a write that waits for the embedder, and fails when it is down.

**Consequences.** A search by meaning sees a change up to a poll interval after a keyword search does.

### DD-437. The text is taken from the attributes by their short name; internal types are not embedded

- **Status:** Proposed
- **Increment:** 11.3
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** The text takes the attributes whose name after the defining type is `name`, `displayName`,
`qualifiedName`, `description` or `definition`. Entities of types whose names start with `__`, such as Atlas's
audit entries, get no embedding.

**Reason.** Attributes are stored under qualified names, and the m4i types define their own `name` and
`definition` (`m4i_data_entity.definition`) beside `Asset.name` and `Asset.description`; the short name finds
them all. The internal types are records of the system, which nobody searches for: in the standalone sample
they are 209 of 930 entities.

**Alternatives.**

- Every string attribute: identifiers and paths would dilute the meaning.
- A list of qualified names per type: every new type would need an entry.

**Consequences.** A type that names its descriptive attribute otherwise is embedded by its type and name only.

### DD-438. The dimensions are the mapping's: another number needs a new index

- **Status:** Proposed
- **Increment:** 11.3
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** The vector's dimensions come from the settings and are mapped once. A start whose dimensions
differ from the mapped ones fails, naming both.

**Reason.** Elasticsearch cannot change a mapped vector's dimensions. Failing the start names the conflict
before the indexer writes vectors the mapping refuses.

**Alternatives.**

- A field per model: the searches of 11.4 would have to know which field holds which model.

**Consequences.** Moving to a model of other dimensions takes a re-index into a new entity index; one of the
same dimensions only re-embeds.

### DD-439. An entity index created before embedding moves to a new generation at start

- **Status:** Proposed
- **Increment:** 11.3
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** When embedding is on and the entity index was created without
`index.mapping.exclude_source_vectors: false`, the server, while it starts, creates the next index behind the
alias (`…-entities-000002`) with the setting and the full mapping, copies every document into it with
`_reindex`, checks that the counts agree, moves the alias in one change and deletes the old index.

**Reason.** The setting cannot change on an existing index (DD-434), and every installation stored before 11.3
has one. `_reindex` copies each source as written, measured on 9.5.5 with the same decimals. The aliases exist
for such a move (DD-043): readers and writers name the alias, never the index. Doing it at start, before the
server writes, needs no step by an operator.

**Alternatives.**

- Refusing to start with embedding on an old index: every existing installation would need a manual reindex.
- A migration command run by an operator: the same steps, and one more thing to remember.
- Mapping the vector on the old index in place: every source rewritten, digits lost (DD-434).

**Consequences.** The move takes as long as a reindex of the store, once. A server process that writes during
another's move loses its write: with several servers, the first start with embedding on must be the only one
running. The document versions start again in the new index, which nothing outside a request keeps. Recorded
as a storage change in the sense of ADR 023 (Proposed).
