# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-584. The search door reuses the engine's query machinery, not its wire

- **Status:** Proposed
- **Increment:** 16.2
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The door's query, filters, facets, sort and paging compose the same Elasticsearch
query the 14.4 engine composes (DD-523's field table, DD-525's matching), pointed at the view's
field names. The request and answer models are new: flat values, `limit`/`offset`, the facet
answer of AVR-08. The engine's own request models are not reused and its wire does not change.

**Reason.** ADR 064 wants the facets without the wire. The facet machinery lives behind the wire
already (the bucketing over the stored fields), so reuse it and redesign the contract in front.
`{raw}` wrappers, engine names and `page.current` exist only because the original webapp speaks
them (ADR 060 R1); nothing asks the new doors to.

**Alternatives.**

- `POST /api/as/v1/...` for the new webapp: the sixth shape enters the client, and 16.6's
  retirement would break it. ADR 064 rejects this as an alternative.
- A second query builder for the door: two implementations of one Elasticsearch composition to
  keep in step, the drift pattern of the hand-mirrored clients.

**Consequences.** A field the engine table gains must join the door's table; both cite the same
stored field. 16.6 deletes the wire and its request models, not the machinery.

### DD-585. The read door derives live, from one read

- **Status:** Proposed
- **Increment:** 16.2
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `GET /entity/guid/{guid}` reads the entity document once and answers the view that
one read carries (DD-581's function). It does not wait for the indexer, and it does not compute
the breadcrumb or relations from the graph. A freshly created entity's view has empty derived
fields until a worker round fills the document, marked `stale: true` in that case (DD-524's rule
inverted for a never-derived document).

**Reason.** The Atlas entity GET is the freshest read available at one round trip, and the
derived fields are a worker round behind whatever the door did. Deriving from one read keeps the
door at exactly one call (ADR 064 R1); recomputing relations live re-creates the join 14.2 moved
to the workers, and a details page pays it per open.

**Alternatives.**

- Answering from the derived document only (stale hidden): a new entity's page shows nothing for
  a round, and 16.3's answer (AVW-07) could not be fresher than what was just saved.
- Recomputing the derived fields live: the rejected "join on the fly" of ADR 060, per open.

**Consequences.** A details page can show a stale relation name for a round; AVS-06 marks it.
The write door's fresh answer (16.3) is what hides the window for the person who caused it.

### DD-586. One door types over everything, documents or not

- **Status:** Proposed
- **Increment:** 16.2
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The search door answers every active entity, not the 14.1 mapped types only. An
entity without a stored document (a non-m4i type, or a new one mid-round) is in the door and
matches on its own fields with empty derived fields. `filters.typeName` narrows as ASE-03's
population did.

**Reason.** The webapp's browse affordances and pickers search every type (7.4a's browse, 7.7c's
pickers over `searchUsingAttribute`); a door limited to m4i types leaves Atlas-classified glossary
or generic entities unfindable and forces the client to keep an Atlas search call alive, which
ADR 064's "no Atlas read on webapp screens" rule forbids. The engine keeps its narrow population
because legacy parity (R2 of ADR 060) fixed it there, not here.

**Alternatives.**

- Mirroring ASE-03's population: a client split across two search doors, the inconsistency ADR
  064 names as the problem.
- Backfilling documents for all types: grows every entity document by 40 derived fields to serve
  a search that needs none of them (DD-498's rejected cost again).

**Consequences.** The door's ES query is `bool`-shaped around the stored-document existence; the
dev-store e2e proves the unindexed case. Recorded as a deviation from the engine's population in
16.2's spec.

### DD-587. Facets are a named-field list, counts on the matching set

- **Status:** Proposed
- **Increment:** 16.2
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** A facet request names card fields (a quality score sub-field is one name:
`quality.accuracy.score`), with a size. The answer is the matching documents' value counts per
name. Facets count what the query and filters match, before the facet's own field filters, as
today's quick search and 14.4's engine both do.

**Reason.** 7.4b already renders quick-search facets and App Search facets; both want name plus
`{value, count}` entries. Keeping the count-before-own-filter rule is what lets a facet list show
"23 more under this type" beside the active filter, which both clients already behave as (SDX
rules). Range facets are absent because 14.4 refused them (DV-158) and no screen asks.

**Alternatives.**

- Facets as filters and counts in two calls: DD-093's one-call rule re-broken.
- Range facets for the quality scores: no asking screen; ponytail keeps the door thin.

**Consequences.** The facet fields are the card's fields, so 16.1's model names them and a card
field that should facet must be stored, not computed.

### DD-588. The doors live on the Aurelius prefix, under the Aurelius error shape

- **Status:** Proposed
- **Increment:** 16.2
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `/api/aurelius/v1/search` and `/api/aurelius/v1/entity/guid/{guid}` join 11.4's
search-by-meaning and 12.5's quality routes on the native prefix, with SBM-08's error shape
(Aurelius codes in the Atlas body). The Atlas `/api/atlas/v2/search` and entity paths keep
answering third parties untouched (AVR-12).

**Reason.** The prefix is the established home for Aurelius-native endpoints (ADR 059, ADR 061's
banner rides the same shape), it is inside ADR 054's one data host, and it cannot collide with a
path ADR 046 froze. The error shape continues SBM-08 rather than inventing a third convention.

**Alternatives.**

- `/api/atlas/v2/...`-adjacent paths: Atlas's namespace, which 046 reserves for what Java Atlas
  answers there — a new shape under an Atlas path reads as a parity violation.
- A new prefix per family: every family its own CSP and config conversation, paid again.

**Consequences.** The webapp's bearer-token pattern list already covers `/api`; nothing joins
the CSP. The parity harness never reads these paths, so ADR 052's scenarios stay Atlas-only.
