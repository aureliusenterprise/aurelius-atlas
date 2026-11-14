# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-595. The modes ride the one door; a new key names them

- **Status:** Proposed
- **Increment:** 16.4
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `mode` is an optional key of `POST /api/aurelius/v1/search` (AVR-02's known-key rule
extended), with values `keyword`, `semantic` and `hybrid`, defaulting to `keyword`. There is no
`/search/semantic` twin of the door and no second endpoint.

**Reason.** ADR 064 draws the family as one door per job with one shape out, and the semantic modes
change how the door picks and ranks, not what it answers — the `{cards, facets, total}` of AVR-08
holds in every mode (ASV-04). A second endpoint would ask 16.5's results page to switch endpoints
per keystroke of a mode control and to hold two request shapes for one screen, and would grow a
third when a mode is added later. The one-key rule is also what makes ASV-02 testable: the same
body with and without the key must answer the same bytes.

**Alternatives.**

- `POST /api/aurelius/v1/search/semantic` in the door's shape: 11.4's route keeps its own shape and
  its SBM answer, so this is a third search surface, not a mode of the door.
- A path segment (`/search/semantic`) or query parameter: both put a request's meaning outside its
  body, where the door's parse, refusal and log lines all read it.

**Consequences.** One URL to teach, cache and audit; the parse refuses an unknown mode beside every
other refusal (AVR-13). 11.4's endpoint stays untouched for its own callers (ASV-10).

### DD-596. The door's kNN clause is built in the engine's file, on the door's fields

- **Status:** Proposed
- **Increment:** 16.4
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The door's meaning modes add a `knn` clause to the same entity-index request the
keyword mode sends: `field` the embedding's, `k` the page's end (`offset + limit`), `filter` the
door's own holds and parsed filters, and `boost` the mode's weight (1 in `semantic`, as in 11.4,
so the cosine orders the page; the configured weight in `hybrid`). `aurelius-atlas-core` builds it
next to `query_body`, from the engine's `Search` extended with an optional `vector`, and sends it
to the same `search_app_search`.
The clause follows 11.4's shape (DD-441: the filters inside the kNN, so they apply before the
nearest are picked) and reuses `VectorQuery` for the numbers (its `num_candidates` rule, k times
ten clamped to 100..10,000).

**Reason.** The door and 11.4 read one index and one mapping, but their populations differ: the
door holds every active entity (AVR-11) and its filters are parsed through the door's field table
(name paths per type, quality sub-fields), while 11.4's run through `SearchQuery`'s Atlas filters.
Translating the door's parsed filters into a `SearchQuery` to reuse `EntityStore.search` would
re-implement AVR-03's parser as a translator — two shapes to keep equal. Building the clause where
the door's clauses already exist keeps one path: the same bool filter list feeds both the query and
the kNN's inner filter, exactly as DD-441 draws it.

**Alternatives.**

- Call `EntityStore.search` with a `SearchQuery` carrying the door's filters: the translator above,
  plus the door loses its own sort and facet composition (AVR-05..06).
- A rescore pass (text search, then re-rank by stored vectors in Python): exact for the page only,
  wrong for `total` and facets, and it reads every vector into the server.

**Consequences.** Elasticsearch and the fake client both already answer this clause (the fake's
cosine and score-are-added rules are 11.4's tests'). The door's score ties keep AVR-06's `guid`
tie-break, so both modes answer the same entity twice never, and `semantic` scores
`(1 + cosine) / 2` — a display order, not a similarity to quote.

### DD-597. A meaning mode's total is its hits; the facets count over them

- **Status:** Proposed
- **Increment:** 16.4
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** In `semantic`, the answer's `total` counts the hits the kNN search returns — at most
`offset + limit` — and each facet counts over those hits (ASV-04). In `hybrid`, the hits are the
nearest and the text's matches together, and `total` and the facets count over all of them
(ASV-05).

**Reason.** Elasticsearch counts a kNN search's aggregations over its own hits by construction, so
this is what one request answers without a second query. It is also 11.4's rule (SBM-02: the
facets count over the nearest; its e2e pins the facet counts to the answered page) — the door and
the SBM endpoint read the same corpus the same way, which is what lets 16.5's page facet a result
set it cannot enumerate. A door facet that counted the whole filtered population "nearest first"
would name values no page of cards shows, and cost a second, unpageable request.

**Alternatives.**

- Count `total` and the facets over the whole filtered population: one more request per search, and
  its number is unusable for paging because a kNN search cannot enumerate past `k`.
- `total` null in the meaning modes: AVR-08's shape is one shape (ADR 064 R1); a null forces every
  caller to branch per mode.

**Consequences.** A caller sees `total` move with `limit` in `semantic` (it caps at `offset +
limit`), so the webapp's pager treats the meaning modes as "nearest first, windowed", which is the
truth 11.4's results page already shows. ASV-08's window bound keeps every such request inside DD-
441's 1,000.

### DD-598. The semantic door's e2e proof runs in core; the server stack runs no embedder

- **Status:** Proposed
- **Increment:** 16.4
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The door's meaning modes are proven on a real Elasticsearch by a core e2e
(`libs/python/aurelius-atlas-core/e2e/test__view_search_semantic_e2e.py`): entities of their own
per test with hand-made two-dimension vectors, the door's clause checked for nearest-first, the
filters inside the kNN, the paging, the facets over its hits, and the hybrid sum. The server e2e
stack runs no embedder, and this increment does not add one; the server's HTTP loop is proven with
a mock embedder transport (11.4's server-test pattern), and the `semantic`-without-embedding 404
is the server stack's own honest state, tested there.

**Reason.** ADR 062 puts a critical scenario where only a real service can answer the question —
here, whether Elasticsearch runs the door's kNN with the filters inside it, which is the core
question, and the core's dev-store e2e answers it on the same index the server uses. An embedder
in the server's e2e compose would change every suite riding that stack: the indexer would embed
each of their writes through a real model, which is slow, and turns writes into model calls.
11.4 chose the same split for the same reason (its spec names the core e2e for the real kNN and
the server unit tests, with a mock embedder, for the route).

**Alternatives.**

- The embedder image on the server's e2e compose: the embedding worker embeds every write of every
  suite — minutes of GPU-less ONNX inference per run, and failures from the model, not the code.
- No real-index test: DD-441's clause-inside-clause is exactly the Elasticsearch behaviour a fake
  cannot prove (the fake answers its own cosine, not HNSW with filters).

**Consequences.** The e2e gate keeps one critical scenario for the door's real clause (ASV-03,
ASV-05); the server's stack keeps its speed; and the mock-embedder unit tests stay the place where
the route's errors live (ASV-09), because an unreachable embedder is a test double's natural
weather.
