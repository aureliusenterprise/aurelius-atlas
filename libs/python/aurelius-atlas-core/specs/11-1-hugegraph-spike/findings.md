# 11.1 Findings: Apache HugeGraph as the store

- **Status:** phase 1, stopped early at HGS-01 (2026-11-09)
- **Spec:** [`spec.md`](./spec.md)
- **Probe:** `spikes/hugegraph/probe_writes.py` and `spikes/hugegraph/docker-compose.yaml` on the branch
  `spike/hugegraph-backend`

HugeGraph 1.7.0 cannot be the only store as Aurelius Atlas writes today: a write conditional on a version is
not atomic, and concurrent writers lost updates in five of six probe runs (HGS-01). The spec stops the spike
there. Two further findings weigh on it: HugeGraph 1.7.0 has no vector index, so HugeGraph-AI needs Faiss,
Qdrant or Milvus beside it (HGS-06), and its text index matches words without a relevance score, with Chinese
analyzers only (HGS-04).

## Setup

- HugeGraph server 1.7.0 (`hugegraph/hugegraph:1.7.0`, core 1.7.0, Gremlin 3.5.1, API 0.71), RocksDB backend,
  the image's own `conf/graphs/hugegraph.properties`, on `127.0.0.1:18080`.
- The probes run on the same machine: 20 CPUs, 31 GB, WSL2 (kernel 6.18), Docker 24.0.6.
- Source read: `apache/hugegraph` at the tag `1.7.0`, and `apache/hugegraph-ai` at `main`, through the GitHub
  API on 2026-11-09.

## Answers

| Id     | Answer                                                                                                     | Outcome    |
| ------ | ---------------------------------------------------------------------------------------------------------- | ---------- |
| HGS-01 | Not atomic: a read-check-write in one Gremlin script lost updates under concurrent writers; no lock option | Fails      |
| HGS-02 | A UNIQUE index held through REST; through Gremlin it once let two writers in; the source has no lock       | Not proven |
| HGS-03 | Property keys, label properties and index labels are added while the server runs; an index builds async    | Passes     |
| HGS-04 | Word segments matched yes or no, no relevance score; the analyzers are Chinese word segmenters             | Fails      |
| HGS-05 | Not reached                                                                                                | —          |
| HGS-06 | No vector index in 1.7.0; it is open work upstream; HugeGraph-AI keeps vectors in Faiss, Qdrant or Milvus  | Two stores |
| HGS-07 | Not reached                                                                                                | —          |
| HGS-08 | Not reached                                                                                                | —          |
| HGS-09 | Not reached; the distributed mode ships as `hstore.properties.template`                                    | —          |
| HGS-10 | No dhi.io image; the upstream image is 729 MB and runs as root                                             | Own image  |
| HGS-11 | Not reached                                                                                                | —          |

### HGS-01: conditional writes

The Elasticsearch store writes an entity only if its version is still the one it read (DD-047). HugeGraph has
no equivalent: its transactions lock schema elements (labels and index labels being deleted), never a vertex
or an edge (`GraphTransaction.lockForUpdateProperty`, `LockUtil`), and its configuration has no isolation or
lock option, only transaction capacities (`CoreOptions`).

The probe emulates the check in one Gremlin script: read the version, wait 20 ms, then write version + 1 only
where the version is still the one read (`g.V(id).has('version', seen).property('version', seen + 1)`). In
each round, every writer runs that script at once on one vertex; two writers that both succeed from the same
version are a lost update.

| Run | Rounds × writers | Successful writes | Lost updates |
| --- | ---------------- | ----------------- | ------------ |
| 1   | 30 × 20          | 37                | 2            |
| 2   | 30 × 20          | 37                | 7            |
| 3   | 30 × 20          | 34                | 2            |
| 4   | 30 × 50          | 208               | 2            |
| 5   | 30 × 50          | 154               | 0            |
| 6   | 30 × 50          | 182               | 2            |

A lost update means two writers each believed they had written on top of the same version: one entity write
silently overwrites another. A multi-entity write cannot be all or nothing on top of that (DD-046). The only
way around it would be one writer process for the whole store, which rules out more than one server replica in
the Helm chart.

### HGS-02: unique values

HugeGraph checks a UNIQUE index by querying the store, then writes, with no lock between
(`GraphIndexTransaction.existUniqueValueInStore`). Under the probe, the REST vertex API held: 50 × 50 and 30 ×
50 concurrent creates of one value each accepted exactly one per round, with no duplicate. Through Gremlin
`addV`, one run of 30 × 50 let two writers create the same value in one round, and another run of 30 × 50
held. The source does not show why REST holds, so neither path is proven safe. A UNIQUE index also answers no
query: it only enforces, and a lookup by the unique value needs a second, SECONDARY index.

### HGS-03: schema at runtime

Property keys, a property appended to an existing vertex label, and an index label all went in while the
server ran. A SECONDARY index over 2,000 vertices written before it built as a server task in 0.5 to 0.6
seconds, and the lookup found the vertex afterwards. Atlas attribute names would still need qualifying by
type, as on JanusGraph (DD-088), since property keys are global to the graph.

### HGS-04: text search

A SEARCH index splits text into word segments with the graph's analyzer and stores them; a text query becomes
`textContainsAny` over the query's segments, and a match is yes or no (`GraphIndexTransaction.segmentWords`,
line 849). Nothing scores the matches, so `search/basic` and `search/quick` could not put the best match first
(FTX-02, FTX-04). The analyzers are Ansj, HanLP, IK, Jcseg, Jieba, MMSeg4J and SmartCN, all Chinese word
segmenters; the image's default is Jieba (`search.text_analyzer=jieba`). None stems English or Dutch.

### HGS-06: vectors

HugeGraph 1.7.0 has no vector, kNN or HNSW code. A vector index is open work upstream: apache/hugegraph#2913
(backend structures, open, updated 2026-10-19) and PR #2922 (a `VectorIndexManager` with ANN search, open),
after PR #2856 was closed in October 2025. HugeGraph-AI's vector index is Faiss (local files, the default),
Qdrant or Milvus (`hugegraph-llm/src/hugegraph_llm/config/index_config.py`). Vector search on HugeGraph
therefore means a second store today.

### HGS-10: the image

dhi.io has no HugeGraph image. The upstream image is 729 MB and runs as root (no `USER`, uid 0 in the
container). A deployment would need an image of its own on a DHI JRE base, or an exception to the dhi.io rule.

## Also found: the REST Gremlin endpoint can answer with another request's result

One Gremlin request with a wrong graph alias puts the server's REST Gremlin endpoint (`POST /gremlin`) out of
step: the failing request gets `refCnt: 0, decrement: 1`, and from then on every request receives the answer
of the request before it, until the server restarts. Reproduced on 1.7.0 from a clean start: requests 201 to
206 got their own answers, also after a script error; after one request with the alias `__g_hugegraph`,
request 207 got the `refCnt` error and 208, 209 and 210 got the answers of 207, 208 and 209. It is
apache/hugegraph#2284, open since August 2023 (on 1.0.0). On a shared server, one bad request from any client
hands every later caller someone else's data. The probe guards each call with a nonce in its result.

On 1.7.0 the graph is bound as `DEFAULT-hugegraph` (graph spaces), so the alias `hugegraph` of older
documentation is exactly the wrong alias that triggers it.

## What was not reached

HGS-05, HGS-07, HGS-08, HGS-09 and HGS-11, and every measurement of phase 2 (HGS-20 to HGS-26), as the spec
stops the spike when HGS-01 fails. If HugeGraph comes back, the first things to check are a released vector
index, element-level locking or compare-and-set, a fix of #2284, and a scored text index.

## Next

ADR 059, Proposed: Elasticsearch stays the system of record, with these findings as the reason, and the
comparison page `docs/architecture/platform/vector-search-and-chat.md` updated with them.
