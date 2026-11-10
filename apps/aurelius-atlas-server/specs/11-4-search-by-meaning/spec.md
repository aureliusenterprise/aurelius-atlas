# 11.4 Search by meaning

- **Status:** in progress
- **Pull request:** [#305](https://github.com/aureliusenterprise/aurelius-atlas/pull/305)
- **Records:** ADR 059 (Proposed); DD-440 to DD-443; relies on 11.3 (entity vectors, DD-434 to DD-439), 11.2
  (the embedder), DD-089, DD-093

Users find entities by what their names and descriptions mean: a search by meaning, a hybrid of meaning and
words, and the entities nearest to one entity. The answers have the shape of quick search's, the facets
included, so the webapp can show them as it shows quick search's (11.5).

## Scope

- `POST /api/aurelius/v1/search/semantic`, in the modes `semantic` and `hybrid`;
- `GET /api/aurelius/v1/entity/guid/{guid}/similar`;
- in `aurelius-atlas-core`: a vector clause of the entity search, run with the search's filters and facets in
  one request, on Elasticsearch and on the in-memory store;
- in `aurelius-atlas-server`: the query's embedding through the embedder, the routes and their errors.

Not in scope: the webapp (11.5), a chat on the catalogue, the dev stack and the Helm chart.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                             |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SBM-01 | `POST /api/aurelius/v1/search/semantic` takes quick search's `query`, `typeName`, `excludeDeletedEntities`, `entityFilters`, `limit` and `offset`, and `mode`: `semantic`, the default, or `hybrid`. It answers 200 with quick search's `{"searchResults", "aggregationMetrics"}`                                                |
| SBM-02 | `semantic`: the query is embedded as a query, and the answer is the `offset + limit` entities nearest to it among those the type, the state and the filters allow, nearest first, paged by `offset` and `limit`; `approximateCount` counts them, and the facets count over them                                                  |
| SBM-03 | `hybrid`: the query is also matched as quick search matches its text, and an entity's score is its text score plus its vector score times the configured weight (`AURELIUS_ATLAS_SERVER_HYBRID_VECTOR_WEIGHT`, 10); the answer holds the nearest entities and the text's matches, best first, and the facets count over them all |
| SBM-04 | A request without a query, with a query of more than 4,096 characters, with filters but no type, with a negative `offset` or `limit`, with `offset + limit` over 1,000, with a `sortBy`, or with another `mode`, answers 400 in Atlas's error shape                                                                              |
| SBM-05 | `GET /api/aurelius/v1/entity/guid/{guid}/similar` takes `limit`, `offset`, `typeName` and `excludeDeletedEntities`, and answers as SBM-02 with the entity's own embedding as the query, the entity itself left out; an unknown GUID answers 404 `ATLAS-404-00-005`, an entity without an embedding yet 409 `AURELIUS-409-00-001` |
| SBM-06 | Without embedding configured both answer 404 `AURELIUS-404-00-001`; an embedder that cannot be reached or answers otherwise, 503 `AURELIUS-503-00-001`                                                                                                                                                                           |
| SBM-07 | As quick search, both need a signed-in user, and leave out the entities the user may not read                                                                                                                                                                                                                                    |
| SBM-08 | Apache Atlas's own search endpoints answer as before                                                                                                                                                                                                                                                                             |

## Java origin

None: Apache Atlas has no search by meaning (ADR 059). The parameters, the answer and the errors' shape are those
of `DiscoveryREST.quickSearch` (`AtlasQuickSearchResult`, `AtlasBaseException`).

## Deviations

None against Apache Atlas: the endpoints are Aurelius's own, under `/api/aurelius/` (DD-440).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__search_by_meaning.py`: SBM-02, SBM-03 and SBM-05's exclusion on
  the in-memory store.
- `libs/python/aurelius-atlas-core/e2e/test__search_by_meaning_e2e.py`: SBM-02, SBM-03 on the dev Elasticsearch:
  the kNN clause with the filters, the facets, the paging and the hybrid score.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_search_by_meaning.py`: SBM-01 to SBM-08 on the
  fake store with a mock embedder.
