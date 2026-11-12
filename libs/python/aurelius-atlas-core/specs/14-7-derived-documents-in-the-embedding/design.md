# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-538. The document's names follow the classifications in the embedded text

- **Status:** Proposed
- **Increment:** 14.7
- **Date:** 2026-11-12
- **Supersedes:** none; extends VEC-01 of 11.3 (DD-437, Proposed)

**Decision.** The embedded text reads the breadcrumb and relation names from the entity's App Search document,
not from its neighbours. They come after VEC-01's lines: the breadcrumb as one path line (`Finance > Customer`),
then one line per relation field, `m4i_dataset: orders, payments`.

**Reason.** The document already holds each neighbour's current name, derived by the App Search indexer and
derived again when a neighbour changes (DD-519). Reading it costs the embedding indexer no request, and the
two features agree on what an entity relates to. The entity's own text comes first because the embedder keeps
512 tokens (EMB-03): in the sample, the names add 52 characters at the median and 1,161 at most, but a large
domain's relations can outrun the model, and then it is the neighbours that are cut, not the entity's own name.
Labelling a relation line with its type tells the model that `Finance` is a domain the entity sits in, not a
dataset it is.

**Alternatives.**

- The neighbours read by the embedding indexer itself: a second derivation of 14.2's rules, to keep in step.
- The names before the classifications: an entity with many relations would lose its classifications to the
  cut.
- The names unlabelled, one per line: the model cannot tell a domain from a field.

**Consequences.** An entity without an App Search document (LAS-01) embeds as before. The person's email, the
scores and the verdicts stay out of the text.

### DD-539. The hash covers the document's names only when there are any

- **Status:** Proposed
- **Increment:** 14.7
- **Date:** 2026-11-12
- **Supersedes:** none; extends VEC-02 of 11.3 (DD-435, Proposed)

**Decision.** The source hash adds the document's names to VEC-02's parts when the document has any, and stays
VEC-02's hash otherwise. The write's check (VEC-05) is unchanged: it recomputes the hash from the entity being
written, App Search document included.

**Reason.** The write is still the one place every change passes (DD-435): the App Search indexer writes the
entity with its new document, and the check drops an embedding whose names changed. The document's other
fields, its stale flag and the marks of 14.5 and 14.6 are written often and are not in the text, so they stay
out of the hash. Hashing the names only when present leaves the hash of every entity without them as it was, so
the upgrade embeds again only the entities whose text grows.

**Alternatives.**

- The hash of the whole document: every quality round and governance mark would drop the embedding.
- A version number in the hash: every entity embedded again, though most texts are unchanged.

**Consequences.** On upgrade, each entity with a breadcrumb or relations is embedded once more: 684 of the
sample's 930 entities at most.

### DD-540. The embedding indexer waits for an entity's App Search document

- **Status:** Proposed
- **Increment:** 14.7
- **Date:** 2026-11-12
- **Supersedes:** none; amends VEC-06 of 11.3 (DD-436, Proposed)

**Decision.** While the server runs the App Search indexer, the embedding indexer's listing leaves out the
entities that should have a document (LAS-01) and have none, or a stale one. The server says so to the indexer
from `APP_SEARCH_ENABLED`; with it off, the listing is VEC-06's.

**Reason.** An entity created, or one whose neighbours changed, gets its document a round later. Embedded
before, its text lacks the names, or holds the old ones, and the new document drops the vector at once: two
calls to the embedder for one entity, and a backfill of the catalogue would embed every documented entity
twice. Waiting is one more clause of the listing's query. Without the App Search indexer no document ever
comes, so the indexer must not wait.

**Alternatives.**

- Embed at once and again later: double the embedder's work on every change.
- The App Search indexer computing the embedding: one worker tied to the embedder's reachability (VEC-07).

**Consequences.** A new entity is found by meaning a round of the App Search indexer later than before. An
entity whose document cannot be derived waits with it.
