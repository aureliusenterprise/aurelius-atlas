# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-901. The cut-off is one fixed cosine threshold, a server setting, 0.82 by default

- **Status:** Proposed
- **Increment:** 11.6
- **Date:** 2026-11-27
- **Supersedes:** none

**Decision.** The cut-off is one number, `AURELIUS_ATLAS_SERVER_SEMANTIC_MIN_SIMILARITY`. It is a
raw cosine similarity between the query's embedding and an entity's (SCT-02), and it is the same
for every query and every user. Its default is 0.82, chosen for the model the embedder image ships,
`intfloat/multilingual-e5-small` (DD-429). 0 turns the cut-off off (SCT-06).

**Reason.** The default comes from a measurement, not a guess. The embedder image (revision
`614241f6`) embedded 24 catalogue entries written the way `embedding_text` writes them (type, name,
description, classification, breadcrumb, relation lines), across sales, finance, HR, assets,
governance, logistics, and one Dutch table. It also embedded 8 queries, each with a hand-marked set
of relevant entries (21 relevant pairs, 171 unrelated pairs), including one Dutch query and
paraphrases with no shared words ("how much money did we make", "where are parcels").

| Threshold | Relevant kept | Unrelated kept |
| --------- | ------------- | -------------- |
| 0.80      | 19 / 21       | 57 / 171       |
| 0.82      | 17 / 21       | 13 / 171       |
| 0.84      | 11 / 21       | 1 / 171        |
| 0.85      | 10 / 21       | 0 / 171        |

e5 models squeeze every cosine into a narrow band: here 0.78 to 0.90. Relevant and unrelated
pairs overlap, since the weakest relevant pair scored 0.789 and the strongest unrelated one 0.845.
No threshold is clean. 0.82 keeps four in five relevant entities and lets through one unrelated in
thirteen, which suits a facet sidebar that should narrow rather than hide. A deployment with
another model, or a catalogue in other words, tunes the setting; the probe is small (24 entries),
so the default is a starting point, not a property of every catalogue.

**Alternatives.**

- A cut-off relative to the best hit ("within 0.03 of the best"). On the same pairs it did no better
  (0.03 kept 16 relevant and 9 unrelated; 0.04 kept 18 and 18) and it needs a first request to learn
  the best score, so every search costs two requests.
- A threshold on Elasticsearch's `_score`. For cosine, `_score` is `(1 + cosine) / 2`, so it carries
  the same information on a different scale, and the hybrid weight (DD-442) changes it. The raw
  cosine is the number the measurement and Elasticsearch's `similarity` share.
- A per-request threshold (a body key). It gives callers a knob before anyone knows they need one,
  and it adds rules to two endpoints. It stays open (the spec's not-in-scope table).
- Default off. Nobody would get facets that mean something without first tuning a number, which is
  the problem this increment exists to solve.

**Consequences.** A query in words the catalogue lacks can answer nothing (SCT-04) where today it
answers its 20 nearest, however far. The webapp already shows an empty result for that. Changing
the embedding model means measuring again: DD-429's model id and this default go together.

### DD-902. With a cut-off, `k` is the meaning window, so the counts cover every match

- **Status:** Proposed
- **Increment:** 11.6
- **Date:** 2026-11-27
- **Supersedes:** none (amends DD-441's `k` and DD-597's count while a cut-off is set)

**Decision.** With a cut-off, the kNN clause asks for `k` = 1,000 (the meaning window, DD-441) with
`similarity` = the cut-off. `from` and `size` page within those hits. The total and the facets
count all of them (SCT-03), as Elasticsearch counts a kNN search's aggregations over its `k` hits.
`num_candidates` keeps its rule: 10 per entity asked, at most 10,000. Without a cut-off, `k` stays
`offset + limit` (SCT-06).

**Reason.** `similarity` alone only trims: with `k` = `offset + limit`, a cut-off would remove
weak hits from the page, but the facets would still count at most one page's worth and would still
grow as the user pages. That is today's problem, so trimming alone does not fix it. With `k` at the
window, the set of hits depends only on the query and the filters, so every page of one search
reports the same counts. The window keeps its bound of 1,000, so `offset + limit` still cannot
reach past what was counted.

**Alternatives.**

- A second request that counts the matches over the whole population: no kNN search counts past
  its `k`, so it would need a brute-force `script_score` over every entity, which is the cost DD-441
  chose a kNN search to avoid.
- `k` = 10,000. The counts would reach further, but the window and the webapp's `MAX_NEAREST`
  (SBW-04) are 1,000, and the candidates' cap would then be equal to `k`, which leaves HNSW no
  room to search wider.

**Consequences.** Every meaning search with a cut-off asks HNSW for 10,000 candidates per shard,
where a first page of ten asked for 100. On the catalogues the dev stores hold, that costs milliseconds,
next to the embedder call each query already makes. A catalogue where it shows can lower
`num_candidates` in a later increment. With more than 1,000 matches, the total reads 1,000.

### DD-903. `similar` and the App Search wire keep no cut-off

- **Status:** Proposed
- **Increment:** 11.6
- **Date:** 2026-11-27
- **Supersedes:** none

**Decision.** `GET /api/aurelius/v1/entity/guid/{guid}/similar` (SBM-05) and the App Search wire's
meaning search take no cut-off (SCT-07).

**Reason.** `similar` compares an entity's passage embedding with other passages, and e5 embeds a
query and a passage with different prefixes (`input_type`, DD-430). Passage-to-passage cosines sit on a different
band from query-to-passage ones, so DD-901's 0.82 does not carry over, and `similar` has no facets
whose counts need a set of matches. The App Search wire retires in 16.6, and the webapp no longer
searches through it (16.5).

**Alternatives.**

- One setting for every vector search: it would apply a threshold measured for queries to passages.
- A second setting for `similar`: no one has asked for it, and it would need its own measurement.

**Consequences.** `similar` keeps answering its nearest, however far, as 11.4 says.
