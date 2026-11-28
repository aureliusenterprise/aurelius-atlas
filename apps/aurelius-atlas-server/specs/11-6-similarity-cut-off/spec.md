# 11.6 The similarity cut-off

- **Status:** planned
- **Pull request:** [#495](https://github.com/aureliusenterprise/aurelius-atlas/pull/495)
- **Records:** DD-901 to DD-903 (in [design.md](./design.md)); amends 16.4's ASV-03 to ASV-05 (DD-597)
  and 11.4's SBM-02 and SBM-03 (DD-441) while a cut-off is set; relies on 11.2 (the embedder's model,
  DD-429), 11.3 (VEC, the cosine vector field)

A search by meaning ranks every entity by how close it is to the query, so it has no set of
matches. Today its facet counts cover only the nearest entities fetched for the page (`offset +
limit`): 20 on the first page, more with each page. A cut-off gives a search by meaning a set of
matches, the entities at least as similar to the query as a configured threshold. Its total and its
facets then count that whole set, and are the same on every page.

## Scope

- In `aurelius-atlas-core`: a minimum similarity on `VectorQuery`, carried into the kNN clause as
  Elasticsearch's `similarity`, and `k` widened to the meaning window when it is set (DD-902).
- In `aurelius-atlas-server`: the setting `AURELIUS_ATLAS_SERVER_SEMANTIC_MIN_SIMILARITY` (DD-901),
  passed to the search door's meaning modes (16.4) and to `POST /api/aurelius/v1/search/semantic`
  (11.4).
- The dev `.env`, the standalone stack and the Helm chart's values carry the setting with its
  default, so each deployment can tune it.

Not in scope, with the increment that will:

| Not delivered                                                                | Lands with |
| ---------------------------------------------------------------------------- | ---------- |
| A cut-off on `GET …/entity/guid/{guid}/similar` (SBM-05)                     | – (DD-903) |
| A cut-off on the App Search wire's meaning search                            | – (16.6)   |
| A per-request threshold, or a "strictness" control in the webapp             | –          |
| The webapp showing the meaning modes' total ("42 matches") instead of paging | –          |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SCT-01 | `AURELIUS_ATLAS_SERVER_SEMANTIC_MIN_SIMILARITY` is the cut-off: a number from 0 to 1, default 0.82 (DD-901). The server refuses to start with a value outside that range. 0 turns the cut-off off                                                                                                                                                   |
| SCT-02 | With a cut-off, a `semantic` search answers the entities whose cosine similarity to the query's embedding is at least the cut-off, among those the type, the state and the filters allow, nearest first, at most 1,000 of them, paged by `offset` and `limit`. The similarity is the raw cosine of the two vectors, not the search's score (DD-902) |
| SCT-03 | With a cut-off, a `semantic` answer's total (the door's `total`, 11.4's `approximateCount`) and its facets count every entity SCT-02 answers, up to 1,000. They are the same for every `offset` and `limit` of one query and one set of filters                                                                                                     |
| SCT-04 | With a cut-off, a page past the last match answers no entities, with SCT-03's total and facets. A query nothing is similar enough to answers no entities, a total of 0 and empty facets, with status 200                                                                                                                                            |
| SCT-05 | With a cut-off, a `hybrid` search adds the vector score only to entities at least as similar as the cut-off. Its answer holds those entities and the text's matches together, best first, and its total and facets count all of them. A text match below the cut-off is still answered, with its text score alone                                   |
| SCT-06 | With the cut-off at 0, both meaning modes answer exactly as ASV-03 to ASV-05 and SBM-02 and SBM-03 say today: the `offset + limit` nearest, counted over themselves                                                                                                                                                                                 |
| SCT-07 | The cut-off changes no other answer. The `keyword` mode, `similar` (SBM-05), the App Search wire and Apache Atlas's endpoints answer as before. The meaning modes' refusals (ASV-06 to ASV-09, SBM-04, SBM-06) and their read gate (ASV-09, SBM-07) stay the same, and the 1,000 window (ASV-08, SBM-04) still bounds `offset + limit`              |

## Aurelius origin

None in Apache Atlas: it has no search by meaning (ADR 059). This refines 11.4's kNN clause
(DD-441) and 16.4's meaning modes (DD-597). Elasticsearch's own `knn.similarity` parameter applies
the threshold inside the same request, with the filters and the facets.

## Deviations

None against Apache Atlas: the endpoints are Aurelius's own (SBM-08, ASV-10). Against Aurelius's own
rules: with a cut-off set, the count part of ASV-04 and SBM-02 ("counts the `offset + limit`
nearest") gives way to SCT-03. Neither spec is rewritten. SCT-06 keeps them true at 0.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__view_search_semantic.py` on the fake client: the kNN
  clause carries `similarity` and `k` = 1,000 with a cut-off, and today's `k` without one (SCT-02,
  SCT-06), and the hybrid clause does the same (SCT-05).
- `libs/python/aurelius-atlas-core/tests/test__search_by_meaning.py`: 11.4's route builds the same
  clause (SCT-02, SCT-06).
- `apps/aurelius-atlas-server/tests/`: the setting's default, its bounds and its refusal at start
  (SCT-01), and the value reaching both endpoints through a mock embedder (SCT-02, SCT-07).
- `libs/python/aurelius-atlas-core/e2e/test__view_search_semantic_e2e.py` on the dev Elasticsearch,
  with hand-made vectors at known cosines (16.4's pattern): only entities above the cut-off answer;
  total and facets are the same on page 1 and page 2; a page past the matches is empty with the same
  total; a query nothing is close to answers 0; a hybrid text match below the cut-off is still
  answered (SCT-02 to SCT-05). One `@pytest.mark.critical` scenario (ADR 062): the counts are the
  same across pages.
- The default 0.82 is not a test assertion. It is DD-901's measurement, repeatable with the probe the
  design entry describes.
