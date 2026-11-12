# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-523. The engine is a table of fields over the entity index, answered by one search

- **Status:** Proposed
- **Increment:** 14.4
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** Each field of `atlas-dev` is a row of a table: its kind, text or number, and either the index
field it is read from or the constant it holds. A request is checked against the table, and its query,
filters, facets, sort and page become one `_search` of the entity index, filters as a `bool`, facets as
`terms` aggregations. A filter, facet or sort on a constant is decided in the request: a filter matches
every document or none, a facet counts the constant once per match or nothing, and a sort on it is
dropped. The answer reads each result's fields through the same table.

**Reason.** DD-498 stored only what the catalogue derives. The entity's own fields are already indexed, and
the rest are constants until 14.5 fills the scores. One table keeps the engine's field names, the stored
ones and the constants in one place, and 14.5 changes the scores' rows only. One search per request keeps a
search page at one round trip, as App Search took one.

**Alternatives.**

- Storing every field of the engine on each document: 40 fields of constants per entity, which DD-498
  rejected.
- Answering from the in-memory store too: a second implementation of filters, facets and paging that only
  tests would use.

**Consequences.** The engine is answered on Elasticsearch only, and tested on the fake client and the dev
store.

### DD-524. A stale document is answered, a deleted entity never

- **Status:** Proposed
- **Increment:** 14.4
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** The engine holds the active entities with a stored document, stale or not. A deleted entity's
document is not answered, though it stays stored until the indexer's next round. An entity without a document
yet, created since the last round, is not answered until the round gives it one.

**Reason.** A stale document is out of date by one round of the worker, ten seconds by default (DD-521),
and App Search's documents also lagged the catalogue by its pipeline. Hiding a stale document would make a
renamed entity vanish from the search until the round, which is worse than its old name for a moment. A
deleted entity must not be found at all, and its state is on the entity document already.

**Alternatives.**

- Hiding stale documents: a change would take its entity out of every search page and card for a round.

**Consequences.** For up to a round after a change, a search can show an entity's old name or relations.

### DD-525. A query's words match the analysed names and the exact values of the rest

- **Status:** Proposed
- **Increment:** 14.4
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** A non-empty query is a `simple_query_string`, its words joined by OR, over the text sub-fields
of the names, the qualified name and the definition, and over the keywords of the other text fields: the
GUIDs, the types, the email and the source type. `search_fields` narrows the fields, and its `weight`
boosts them. With an empty query, every document scores the same, and the tie goes by `id`.

**Reason.** App Search searched every text field of the engine. The webapp finds a person by an email and a
card by a name's words. Elasticsearch's standard analysis is what the entity index has, so a word matches as
it does in the server's free-text search. The words joined by OR is App Search's high-recall default
(precision 2), with ranking putting the documents that match more words first.

**Alternatives.**

- App Search's analysis, stemming and typo tolerance: a second analysis chain to approximate a closed
  product's ranking, which DV-157 records instead.
- All words required: fewer results than App Search gave for a query of several words.

**Consequences.** For the same query, App Search and Aurelius Atlas can find and rank documents differently
(DV-157). Filters, facets and sorts on field values are exact, and answer alike.

### DD-526. The engine needs `ENTITY_READ`

- **Status:** Proposed
- **Increment:** 14.4
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** A user without `ENTITY_READ` is answered 403 in App Search's error shape. With it, every
document is answered.

**Reason.** The legacy search API needed only a signed-in user, and App Search answered every document.
Here the engine is a view of the entities, and Atlas's own search scrubs the entities of a user without
`ENTITY_READ` (AUZ-12). A document would show that user what a scrubbed header hides. Privileges are the
user's, not the entity's, so the whole engine is allowed or refused.

**Alternatives.**

- Any signed-in user, as the legacy search API: a way around Atlas's authorization.
- Scrubbing each result: App Search's answer has no scrubbed shape, and the webapp would show empty cards.

**Consequences.** A user who could search in the legacy installation but lacks `ENTITY_READ` here sees
the webapp's search fail.

### DD-527. Errors take App Search's shape, in Aurelius's words

- **Status:** Proposed
- **Increment:** 14.4
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** A refused request is answered `{"errors": [...]}` with App Search's status: 400 for a body or
an option, 403 for a missing privilege, 404 for an unknown engine. Each message names the option and the
problem. Keys App Search takes and this engine does not reproduce, such as `group`, `boosts`, `precision`
and `analytics`, are ignored, but a range facet is refused (DV-158).

**Reason.** The webapp reads an answer's status and the `errors` list, never a message's text, and App
Search's texts are not documented. An ignored option changes ranking or grouping only, and the results stay
true to the filters. A range facet would answer a facet the webapp then shows as empty, so refusing it says
what is missing.

**Alternatives.**

- Refusing every key it does not reproduce: a request App Search answered would fail.

**Consequences.** A client that matches App Search's message texts reads other texts here.
