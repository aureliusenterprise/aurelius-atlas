# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-440. The searches by meaning are Aurelius endpoints that answer as quick search

- **Status:** Proposed
- **Increment:** 11.4
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** The endpoints live under `/api/aurelius/v1/`. They take quick search's parameters and answer
`AtlasQuickSearchResult`; their errors are Atlas's `{"errorCode", "errorMessage"}`, with `AURELIUS-` codes
where Atlas has none.

**Reason.** Apache Atlas's API stays exactly as it is (ADR 046, ADR 059 R4), so a search by meaning cannot be
a mode of `search/quick`. Quick search's parameters and answer are what the webapp already sends and shows,
its facet sidebar included (7.4b), so 11.5 reuses them. A version in the path leaves room for the API to
change without breaking its first callers.

**Alternatives.**

- A parameter of Atlas's `search/quick`: Atlas's endpoint would answer what Atlas never does.
- An answer of its own, with scores: the webapp would need a second result list and facet sidebar.

**Consequences.** The answers carry no score; the order is the ranking.

### DD-441. A search by meaning is a kNN clause of the same request as the filters and the facets

- **Status:** Proposed
- **Increment:** 11.4
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** The entity search gets an optional vector clause. On Elasticsearch it is a `knn` search of
`embedding.vector` with `k = offset + limit` and the search's filters inside it, so the filters apply before
the nearest are picked; the facets are aggregations of the same request. `offset + limit` is at most 1,000;
`num_candidates` is ten times `k`, at least 100 and at most 10,000.

**Reason.** One entity document per entity (ADR 047, DD-434) lets kNN, the type, state and attribute filters
and the facets run in one request. Measured on 9.5.5: a `knn` with `k = 20` answers a total of 20, `from` and
`size` page within them, and the aggregations count over those 20, the answer quick search's shape needs.
Filtering inside the kNN search keeps a narrow filter from emptying the result after the nearest were picked.

**Alternatives.**

- A kNN search, then a filtered search of its hits: two requests, and the facets of a different set.
- Post-filtering the nearest: a page with fewer hits than asked whenever the filter is narrow.

**Consequences.** The facets of a search by meaning count the `offset + limit` nearest, not the whole store;
paging deeper than 1,000 is refused.

### DD-442. Hybrid ranking is a weighted sum, not reciprocal rank fusion

- **Status:** Proposed
- **Increment:** 11.4
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** A hybrid search sends quick search's text query and the `knn` clause in one request; an entity's
score is its text score plus its vector score times a weight, `AURELIUS_ATLAS_SERVER_HYBRID_VECTOR_WEIGHT`,
10 by default.

**Reason.** Elasticsearch's RRF and linear retrievers need a paid licence: on the Basic licence the stack
runs, 9.5.5 refuses RRF ("current license is non-compliant for [Reciprocal Rank Fusion (RRF)]"). The sum of a
`query` and a `knn` in one request is free. Text scores are of a few units (about 4 for the top hits of a
sample query), vector scores between 0.5 and 1 and close together, so without a weight the text alone would
rank.

**Alternatives.**

- RRF: a paid licence.
- Fusing two requests' rankings in the server: the facets of neither set, and two requests.

**Consequences.** The weight is a setting to tune on real queries; a catalogue whose names are its users'
words may want it lower.

### DD-443. The query is embedded through the embedder at request time; its failures answer 503

- **Status:** Proposed
- **Increment:** 11.4
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** The server embeds the search's query as a `query` through the same client the indexer uses. An
embedder that cannot be reached, refuses, or answers vectors of other dimensions answers the search with 503
`AURELIUS-503-00-001`. The similar-entities search embeds nothing: it uses the entity's stored vector.

**Reason.** The query's vector has to come from the model that computed the stored ones, with the model's
query prefix (DD-430). A search that cannot embed cannot answer by meaning; 503 tells the caller to retry
later or fall back to quick search, without hiding the failure as an empty result.

**Alternatives.**

- Falling back to quick search inside the endpoint: an answer to another question than the one asked.

**Consequences.** Each search costs one embedding of its query, a few milliseconds on the CPU.
