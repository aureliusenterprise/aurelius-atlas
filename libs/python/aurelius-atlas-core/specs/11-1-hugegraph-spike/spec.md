# 11.1 Spike: Apache HugeGraph as the store

- **Status:** planned
- **Pull request:** [#301](https://github.com/aureliusenterprise/aurelius-atlas/pull/301), the spec;
  the spike's code stays on the branch `spike/hugegraph-backend` and is not merged
- **Records:** relies on ADR 046, ADR 047, ADR 052, DD-043, DD-045 to DD-047, DD-061, DD-070, DD-088, DD-092,
  DD-093; ends with ADR 059, Proposed

The spike finds out, with measurements, whether Apache HugeGraph can replace Elasticsearch as the one store of
Aurelius Atlas, with HugeGraph-AI for the vector search and the chat. It ends in a decision record, not in
production code. Elasticsearch stays the store until a person accepts that record.

## Why

A graph store walks relationships and lineage in one traversal, where the Elasticsearch store makes one call
per hop (`EntityLineageService`), and HugeGraph-AI brings GraphRAG and text-to-Gremlin for a chat on the
catalogue. Apache HugeGraph and HugeGraph-AI are both Apache 2.0, active, and released together (1.7.0,
November 2025).

The facets that HugeGraph has no aggregations for are derivable from the graph: `__typeName` and `__state`
from each vertex, `Asset.owner` from an attribute or an edge, `ServiceType` from the type hierarchy. One
`groupCount()` per facet over the matching vertices counts them. What the spike measures is how fast: the
facets count every match of a search, unpaged, on every search.

## Scope

**What a backend means here.** The Elasticsearch store sits behind three protocols of `aurelius-atlas-core`,
about 1,400 lines specific to Elasticsearch, plus the connection, health and snapshots of
`aurelius-atlas-store-es`:

| Protocol                | What it holds                                                                                                                                                   |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EntityDocuments`       | Entities, relationships, classifications and tasks; the write journal; unique value reservations; search with facets; type counts; prefix terms for suggestions |
| `TypedefDocument`       | The type definitions and the record of their patches, as one document                                                                                           |
| `EntityAuditRepository` | The audit events, read by entity and by time range                                                                                                              |

A HugeGraph backend is a second implementation of these three. The services above them, and the REST API, stay
as they are, so the parity scenarios (ADR 052) check a port without change.

**HugeGraph-AI keeps its vectors outside HugeGraph.** Its vector index is Faiss (local files, the default),
Qdrant or Milvus (`hugegraph-llm`, `config/index_config.py`). Unless HugeGraph's own vector support is enough,
the backend is HugeGraph plus a vector store, two stores to keep in step; the spike settles which.

**In scope:** the questions and measurements below, a throwaway compose file for HugeGraph (and Qdrant if
needed), a loader from the current store, a partial `EntityDocuments` on HugeGraph, the findings, and ADR 059.

**Not in scope:** a merged backend, the webapp, the Helm chart, a migration tool, the embedding model and the
chat endpoint. They follow in a port series if ADR 059 is accepted.

## Questions

Phase 1 answers each question from HugeGraph 1.7's documentation and source, and checks it on a running server
where the answer decides the outcome. Each answer goes into `findings.md` beside this spec, with its source.

| Id     | Question                                                                                                                                                                                                                                                                  |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HGS-01 | Can a vertex or edge write be made conditional on its version, atomically, as the store's conditional writes are (DD-047)? Does a HugeGraph transaction make a multi-entity write all or nothing, so the write journal (DD-046) is no longer needed?                      |
| HGS-02 | Can a create-only reservation of a unique attribute value hold under concurrent writers, natively or emulated (DD-045)?                                                                                                                                                   |
| HGS-03 | Can property keys and index labels be added while the server runs, as Atlas types are created at runtime, and what does building an index on existing data cost? Atlas attributes of one name and different types need names qualified by type, as on JanusGraph (DD-088) |
| HGS-04 | What does HugeGraph's text ("search") index offer for `search/basic` and `search/quick`: which analyzers, a relevance score, sorting by it (DD-092)?                                                                                                                      |
| HGS-05 | Can a traversal sort on an indexed property with a tie-break and page by offset, and answer prefix terms for suggestions?                                                                                                                                                 |
| HGS-06 | Does HugeGraph 1.7 have a vector index of its own, and can a kNN search apply filters before the top-k cut? If not, which of Faiss, Qdrant or Milvus, and how is it kept in step?                                                                                         |
| HGS-07 | Where do the write journal (if HGS-01 still needs it), the audit events with their time-range reads, and the typedefs document live: vertices with range indexes, or something beside the graph?                                                                          |
| HGS-08 | What do backup, restore and retention look like, against the snapshots of increment 6.4?                                                                                                                                                                                  |
| HGS-09 | What runs where: a single server on RocksDB for the dev and standalone stacks, the distributed mode (HStore with PD) for the Helm chart (ADR 057)?                                                                                                                        |
| HGS-10 | Which image: there is no HugeGraph image on dhi.io, so one built on a DHI JRE, or an exception to the rule that infrastructure images come from dhi.io                                                                                                                    |
| HGS-11 | How does HugeGraph-AI fit behind the server: its RAG API is unauthenticated by default, so it may only be reached through the Atlas server, under the server's access rules                                                                                               |

## Measurements

Phase 2 loads the same data into HugeGraph and into Elasticsearch, on the same machine, and measures both. The
data is the sample dataset (`data/atlas-sample/`), then synthetic sets of 10,000, 100,000 and 1,000,000
entities with the m4i types (ADR 058), their relationships and classifications.

| Id     | Measurement                                                                                           | Passes at 100,000 entities                |
| ------ | ----------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| HGS-20 | `search/quick` with the four facets: p50 and p95 latency                                              | p95 of 300 ms or less                     |
| HGS-21 | Free-text ranking: the first ten hits of a fixed set of queries, compared by hand                     | No worse than Elasticsearch's             |
| HGS-22 | Lineage at 3, 5 and 10 hops: one traversal against the store's call per hop                           | Faster than Elasticsearch                 |
| HGS-23 | Filtered kNN: hits lost after the top-k cut, and latency                                              | No hit lost                               |
| HGS-24 | Conditional writes with several concurrent writers, run against the ENS rules of the entity store     | No lost update, no duplicate unique value |
| HGS-25 | Backup and restore of the 100,000 entities: duration, and the data back as it was                     | The restore works                         |
| HGS-26 | The partial `EntityDocuments` (`get`, `write`, `search`, `type_counts`) against the core's unit tests | The tests that touch those methods pass   |

HGS-26 also yields the port's estimate: the three protocols, the store library, the dev and standalone
services, the Helm chart and a migration tool, cut into increments of at most about 1,500 lines (ADR 051).

## Outcome

- `findings.md` beside this spec: each question's answer with its source, each measurement with its numbers
  and the machine, and what passed.
- ADR 059, Proposed: HugeGraph replaces Elasticsearch as the system of record, superseding ADR 047, or
  Elasticsearch stays, with the findings as the reason either way. Only a person marks it Accepted.
- The comparison page `docs/architecture/platform/vector-search-and-chat.md` updated with the findings; its
  HugeGraph row now reads "limited vector search".

The spike stops early when HGS-01, HGS-02 or HGS-20 fails, as each alone rules HugeGraph out as the only
store.

## Java origin

None ported. Java Atlas keeps its graph in JanusGraph and its search in Solr or Elasticsearch beside it
(`org.apache.atlas.repository.graphdb.janus`); the spike asks whether one graph store can do both.

## Deviations

None: the spike changes no behaviour.

## Acceptance

The spike is done when `findings.md` answers HGS-01 to HGS-11 and reports HGS-20 to HGS-26 (or the one that
stopped it), and ADR 059 is written as Proposed. Its ids are answered in `findings.md`, not by tests; the
spike's scripts stay on its branch.
