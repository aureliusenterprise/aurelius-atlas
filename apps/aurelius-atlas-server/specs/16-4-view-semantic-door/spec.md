# 16.4 The view family: the semantic door

- **Status:** in progress
- **Pull request:** #360
- **Records:** ADR 064, ADR 059; DD-595 to DD-598 (here); relies on 16.2 (AVR-01..13), 16.1 (AVS),
  11.3 (VEC, the entity vectors), 11.4 (SBM-01..08, DD-440..443, the meaning machinery)

## Scope

The search door's two extra modes, on the same endpoint and in the same answer:

- `mode` in `POST /api/aurelius/v1/search`: `keyword` (the door of 16.2, the default), `semantic`
  and `hybrid`, answered with 16.1 cards, facet counts and a total (AVR-08's shape unchanged);
- in `aurelius-atlas-core`: a `vector` on the door's search, composed as a `knn` clause that holds
  the door's own filters inside it, reusing 11.4's `VectorQuery` and its hybrid score (DD-441,
  DD-442);
- in `aurelius-atlas-server`: the query's embedding through the embedder the 11.4 route uses, the
  mode check, and SBM-06's errors.

Not in scope, with the increment that will:

| Not delivered                                                              | Lands with |
| -------------------------------------------------------------------------- | ---------- |
| The webapp switched to the doors, and to a mode switch on the results page | 16.5       |
| A nearest-neighbours door for one entity (`similar` stays 11.4's, SBM-05)  | –          |
| The App Search wire retired                                                | 16.6       |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                         |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASV-01 | `mode` is an optional key of the search door's body (AVR-02's rule extended): `keyword` (default), `semantic` or `hybrid`. Any other value, or any other kind, is refused with one message per problem (AVR-13's shape)                                                                                                                                                                      |
| ASV-02 | The `keyword` mode answers exactly as AVR says. A body that names `keyword` answers what the same body without the key answers: the modes change nothing that is already there (AVR-12 holds for the door too)                                                                                                                                                                               |
| ASV-03 | `semantic`: the query is embedded as a query through the embedder (11.4's client), and the door answers the `offset + limit` entities nearest to it among those the filters allow, nearest first, paged by `offset` and `limit`. The kNN search carries the same filters inside it, so the state and the request's filters apply before the nearest are picked (DD-441, SBM-02)              |
| ASV-04 | The `semantic` answer is `{cards, facets, total}` as AVR-08 shapes it. `total` counts the answer's hits — at most `offset + limit` of them — and the facets count over those hits, not over the whole population (SBM-02's count)                                                                                                                                                            |
| ASV-05 | `hybrid`: the query is embedded and also matched as the keyword mode matches it, and an entity's score is its text score plus the configured weight (`AURELIUS_ATLAS_SERVER_HYBRID_VECTOR_WEIGHT`, 10, as SBM-03) times its vector similarity. The answer holds the nearest and the text's matches together, best first; `total` and the facets count over all of them (SBM-03)              |
| ASV-06 | The two meaning modes need a query: a request whose `query` is empty or absent is refused with a message. The query's length bound stays AVR-02's (4,096 characters) (SBM-04's rules, in the door's words)                                                                                                                                                                                   |
| ASV-07 | The two meaning modes answer in score order only: `sort` is absent or `_score` with `desc`, and any other sort is refused naming the mode (SBM-04's ban on `sortBy`)                                                                                                                                                                                                                         |
| ASV-08 | The two meaning modes keep 11.4's window: `offset + limit` is at most 1,000 (DD-441), or the request is refused with a message. AVR-07's `limit` and `offset` bounds hold as they do for the keyword mode                                                                                                                                                                                    |
| ASV-09 | Without an embedding service configured, the two meaning modes answer 404 `AURELIUS-404-00-001`, and an embedder that cannot be reached or answers otherwise answers 503 `AURELIUS-503-00-001` (both SBM-06's codes). The keyword mode needs no embedding. The door's gate stays the same in every mode: `ENTITY_READ` (AVR-01), and the mode never changes which entities a request answers |
| ASV-10 | No answer of Apache Atlas's API, no App Search answer, and no answer of 11.4's `POST /api/aurelius/v1/search/semantic` changes (AVR-12, SBM-08)                                                                                                                                                                                                                                              |

## Aurelius origin

- ADR 064's door family (the modes were named there as the search door's, delivered by this
  increment) and ADR 059's searches by meaning (11.4): the embedding, the kNN-with-filters clause
  (DD-441), the hybrid score sum and its weight (DD-442), and the errors (SBM-06) are 11.4's,
  reused unchanged.
- `apps/aurelius-atlas-webapp` 7.4a: the results page's search box is where a mode switch appears;
  16.5 places it.

## Deviations

None against Apache Atlas (AVR-12, SBM-08: the endpoints are Aurelius's own). Against the door's
own 16.2 rules, recorded here rather than in [Deviations](../../../../docs/architecture/conversion/deviations.md)
because they narrow a new mode of a door that entry does not describe: the meaning modes refuse an
empty query (ASV-06), a named sort (ASV-07) and a window over 1,000 (ASV-08), where the keyword
mode allows an empty query, any card-field sort, and 10,100.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__view_search_semantic.py` on the fake client: the
  mode key and its refusals (ASV-01, ASV-06, ASV-07, ASV-08), the kNN clause carrying the filters
  with nearest-first and paging (ASV-03), `total` and facets over the nearest (ASV-04), the hybrid
  sum and its weight (ASV-05), the keyword answer unchanged with and without the key (ASV-02).
- `apps/aurelius-atlas-server/tests/test__view_semantic.py` with a mock embedder (11.4's server-test
  pattern): the two modes answered through the door (ASV-03, ASV-05), embedding off and embedder
  down (ASV-09), the read gate across modes (ASV-09), the keyword mode answering with embedding off
  (ASV-02).
- `libs/python/aurelius-atlas-core/e2e/test__view_search_semantic_e2e.py` on the dev Elasticsearch:
  the real kNN with the filters inside it, the facets over its hits, the paging, and the hybrid
  score sum — the door's answer on a real index, with hand-made two-dimension vectors as 11.4's
  e2e draws them. One `@pytest.mark.critical` scenario (ADR 062).
- No server e2e scenario is added: the server's e2e stack runs no embedder, and standing one up
  would embed every write of every suite riding it (DD-598's record). The real-index proof is the
  core e2e's, and the HTTP loop is the server unit tests' with a mock transport.
