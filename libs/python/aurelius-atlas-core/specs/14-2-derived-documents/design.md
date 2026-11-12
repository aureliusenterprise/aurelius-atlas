# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-498. The derived fields live on the entity's document, written whole by an indexer

- **Status:** Proposed
- **Increment:** 14.2
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** A stored entity has an `appSearch`: the fields of its `atlas-dev` document that are derived from
the catalogue, under the engine's names, with the hash they were derived with. The engine's other fields are not
stored. Some are the entity's own (`id`, `guid`, `typename`, `supertypenames`); the others are constants
(LAS-07) or come from the scores (LAS-12). An indexer derives the missing documents in rounds and writes each
entity whole, on the version it read, as the embedding indexer does.

**Reason.** ADR 060 keeps what App Search held on the one store. On the entity's document, a search of 14.4 is
one query, with the entity's own filters (state, type, classifications) beside the derived ones. The engine's
names make 14.4's field mapping a prefix. A partial update would rewrite the stored source and lose its numbers'
digits (DD-039, DD-434), so the indexer writes whole documents. A conditional write means two servers
deriving at once only lose work. The same listing backfills an index stored before 14.2.

**Alternatives.**

- An index of the documents beside the entity index: a second copy of the catalogue to keep in step, and two
  queries for a search that filters on both (ADR 047).
- Deriving the documents inside each write of the store: a write would read its neighbours' neighbours, and an
  import would rewrite every document many times over.
- Storing the whole engine document, constants included: 40 fields more per entity that say nothing.

**Consequences.** A new entity lacks its document until the indexer's next round. Until 14.3 adds the worker,
nothing runs the indexer in the server.

### DD-499. A hash of the entity's own inputs decides whether its document is still current

- **Status:** Proposed; superseded in part by DD-518 (14.3)
- **Increment:** 14.2
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** A document records the SHA-256 of what it was derived from on the entity itself: its type, its
state, its `name`, `qualifiedName`, `definition` and `email`, and the relationships it lists. Each write
recomputes the hash and drops a document whose hash differs. The indexer then derives it again.

**Reason.** The write is the one place every change of the entity passes through, as for embeddings (DD-435).
A rename, a delete and a new relationship each change the hash; a new relationship is listed at both its ends,
so both documents go. Changes of other entities, such as a renamed parent, a deleted end or a relationship
deleted while its ends keep listing it, would need reads of the neighbours during the write. They are 14.3's,
which finds the documents a change affects (DD-486).

**Alternatives.**

- Dropping the document at every write: every unrelated change would re-derive it.
- No check: a renamed entity would keep its old name on its own document until 14.3.

**Consequences.** Until 14.3, a document can name a neighbour by an old name or list a relationship that was
deleted while its ends kept listing it.

### DD-500. Quality scores get no document

- **Status:** Proposed
- **Increment:** 14.2
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** The m4i types without a document are `m4i_source`, as in the legacy pipeline, and `m4i_dq_score`,
12.2's quality results (DQS-06, DD-455). LAS-01 reads so from 14.2.

**Reason.** The legacy pipeline had no score entities: its scores were documents of `atlas-dev-quality`, never
entities, so `atlas-dev` never held them. Here they are entities, one per dataset and rule. A document for
each would fill the original webapp's search with results it never showed. 14.5 reads them for
`atlas-dev-quality` and the roll-up.

**Alternatives.**

- Documents for the scores, filtered out by 14.4: every search would pay for a filter on a type that never
  belongs in the answer.

**Consequences.** A new m4i type gets a document unless it is added to this list.

### DD-501. Derived relations keep the order the entity lists its relationships in

- **Status:** Proposed
- **Increment:** 14.2
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** A relation field lists the other ends of the entity's active relationships in the order the
entity lists those relationships, then the ends a field joins (LAS-06), each once. The comparison with
`atlas-dev` compares sets.

**Reason.** The legacy order is the order in which events reached the pipeline, which no catalogue state
records. The entity's own listing is the order its relationships were created in, and stays stable across
re-derivations.

**Alternatives.**

- Sorted by name: stable too, but it reorders a list whenever an end is renamed.

**Consequences.** Two installations holding the same catalogue order a relation field alike only if they
created its relationships in the same order.
