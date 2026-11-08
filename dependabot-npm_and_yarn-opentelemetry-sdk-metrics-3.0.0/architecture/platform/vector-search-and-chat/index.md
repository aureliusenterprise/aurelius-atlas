# Vector search and chat: store options

> [!NOTE]
>
> **Proposal**
>
> A comparison written on 2026-11-07, ahead of any increment. It records no decision: a change of store would supersede [ADR 047](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-opentelemetry-sdk-metrics-3.0.0/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>), and the vector search and chat endpoints need an ADR and a spec of their own.

Keep Elasticsearch 9.5 as the one store and add the vectors to it; no second database is needed. Each entity document gets a `dense_vector` field. One query then mixes BM25 text matching, kNN on that vector and the filters already in use: type, state, owner and the user's access rights. The chat is a retrieval-augmented service in the Atlas server, not a database feature. It retrieves entities, follows their relationships and breadcrumb chain in the same indices, and passes that context to an LLM.

This keeps [ADR 047](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-opentelemetry-sdk-metrics-3.0.0/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>): one search store is the system of record, with no graph database beside it.

- **Fallback:** OpenSearch, Apache 2.0, if the Elastic License 2.0 is ruled out, for example because Aurelius Atlas is offered as a hosted service to third parties. It has the closest query DSL, but moving to it migrates the store and the client.
- **A dedicated vector database:** Qdrant is the strongest Apache 2.0 candidate, but it pays off only at many millions of vectors. Below that it adds a second store to keep in sync and a second copy of the access rules.
- **A graph database instead of Elasticsearch,** FalkorDB or ArcadeDB, would lose search and facets or bring back a second store. The chat's graph context comes from the relationships index.

## What the feature needs

The store holds Atlas's model in the indices `aurelius-atlas-entities`, `-relationships`, `-classifications`, `-entity-audits`, `-entity-journal`, `-unique-values` and `aurelius-atlas-typedefs`. Search and facets (`search/basic`, and `search/quick` with `aggregationMetrics`) are Elasticsearch queries on the entities index. The webapp's breadcrumb trail is empty today (DD-317, increment 7.20). The legacy stack derived it from the parent chain into `breadcrumbguid`, `breadcrumbname` and `breadcrumbtype` arrays; the relationships index can supply it again.

| Need | What it means here |
| --- | --- |
| Embeddings per entity | A vector per entity from its name, description, type, classifications, breadcrumbs |
| Hybrid retrieval | kNN combined with BM25, so exact names such as `customer_id` still win |
| Filters inside the kNN query | Type, state, owner and access rights applied before the neighbours are picked |
| Facets on the hits | The `aggregationMetrics` counts from the same query |
| Graph context for the chat | A hit's relationships, lineage and breadcrumb chain |
| One source of truth | No second copy of entities and access rights |
| Operations | Fits the dev stack, the standalone stack and the Helm chart (ADR 057) |
| Licence | Apache 2.0 or Elastic License 2.0 only |

A worker re-embeds an entity whenever it changes.

## The licence filter

Ten databases with vector search pass the filter, ArcadeDB the only graph database among them. Eight well-known options fail it, FalkorDB among them. The licences were read from each project's repository licence file on GitHub on 2026-11-07.

| Database | Licence | Passes |
| --- | --- | --- |
| [Elasticsearch](<https://github.com/elastic/elasticsearch>) | AGPLv3, SSPL or Elastic License 2.0 (choice) | Yes, under Elastic License 2.0 |
| [OpenSearch](<https://github.com/opensearch-project/OpenSearch>) and its [k-NN plugin](<https://github.com/opensearch-project/k-NN>) | Apache 2.0 | Yes |
| [Qdrant](<https://github.com/qdrant/qdrant>) | Apache 2.0 | Yes |
| [Milvus](<https://github.com/milvus-io/milvus>) | Apache 2.0 | Yes |
| [Vespa](<https://github.com/vespa-engine/vespa>) | Apache 2.0 | Yes |
| [Apache Solr](<https://github.com/apache/solr>) | Apache 2.0 | Yes |
| [Apache Cassandra](<https://github.com/apache/cassandra>) 5 | Apache 2.0 | Yes |
| [Chroma](<https://github.com/chroma-core/chroma>) | Apache 2.0 | Yes |
| [LanceDB](<https://github.com/lancedb/lancedb>) | Apache 2.0 | Yes |
| [ArcadeDB](<https://github.com/ArcadeData/arcadedb>) (graph) | Apache 2.0 | Yes |
| [NebulaGraph](<https://github.com/vesoft-inc/nebula>) (graph) | Apache 2.0 | Yes, but no vector search known |
| [Apache HugeGraph](<https://github.com/apache/hugegraph>) (graph) | Apache 2.0 | Yes, but limited vector search |
| [JanusGraph](<https://github.com/JanusGraph/janusgraph>) (graph) | Apache 2.0 (code), CC-BY-4.0 (docs) | Yes, but no vector search |
| [Apache AGE](<https://github.com/apache/age>) (graph) | Apache 2.0, an extension of PostgreSQL | Only with PostgreSQL |
| [FalkorDB](<https://github.com/FalkorDB/FalkorDB>) (graph) | Server Side Public License v1 | No |
| [pgvector](<https://github.com/pgvector/pgvector>) and PostgreSQL | PostgreSQL Licence | No: permissive, but not Apache 2.0 |
| [Weaviate](<https://github.com/weaviate/weaviate>) | BSD-3-Clause and the Weaviate Licence | No |
| [Neo4j](<https://github.com/neo4j/neo4j>) Community (graph) | GPLv3 | No |
| [Memgraph](<https://github.com/memgraph/memgraph>) (graph) | Business Source Licence 1.1 | No |
| [Redis](<https://github.com/redis/redis>) 8 | RSALv2, SSPL or AGPLv3 | No |
| [Valkey Search](<https://github.com/valkey-io/valkey-search>) | BSD-3-Clause | No |
| [Kùzu](<https://github.com/kuzudb/kuzu>) (graph) | MIT, and the repository is archived | No |

Some Elasticsearch code is licensed solely under the Elastic License 2.0. That licence is source-available, not OSI open source. It allows free use, also commercially, but forbids offering Elasticsearch to third parties as a hosted or managed service, and working around its licence-key checks.

## Comparison

Only Elasticsearch and OpenSearch cover hybrid search, filters, facets and the Atlas store in one database. The feature descriptions are from memory of each product's documentation, not checked for this page; check a feature before relying on it.

| Database | Role for Aurelius | Text + vector hybrid | Facets on the hits | Change to Aurelius Atlas | Footprint |
| --- | --- | --- | --- | --- | --- |
| Elasticsearch 9.5 | Stays the one store | BM25 and kNN in one query | Full aggregations, as today | Mapping fields, embedding step, chat route | Already running |
| OpenSearch 3 | Replaces the store | Hybrid query, score normalisation | Full aggregations | Port store and client; re-index | Same as Elasticsearch |
| Qdrant | Second store, vectors only | Dense plus sparse vectors, fused | Facet counts on keyword fields | Sync every write and access rule | One extra service, light |
| Milvus | Second store, vectors only | Dense plus BM25 sparse, fused | No | Same as Qdrant | Heavy: etcd and object storage |
| Vespa | Replaces the store | Strongest: multi-phase ranking | Grouping | New store and query language | Config server plus content nodes |
| Apache Solr 9 | Replaces the store | kNN plus BM25, boolean or rerank | Facets, strong | New store; re-port search and facets | Solr plus ZooKeeper in cloud mode |
| ArcadeDB (graph) | Replaces the store | Lucene full-text plus HNSW vectors | `GROUP BY` counts only | New store; re-port every query | One Java server, multi-model |
| FalkorDB (graph) | Replaces the store | Full-text and vector indexes | Cypher `count` grouping only | New store; re-port search and lineage | Redis module, graph in memory |
| Apache Cassandra 5 | Replaces the store | No BM25 ranking | No | New store without full-text search | Cluster of nodes, heavy |
| Chroma | Second store, prototype | Vector plus document text match | No | Same as Qdrant | Light, single node |
| LanceDB | Embedded library | Vector plus full-text index | No | No server in the open-source version | A library inside the server |

FalkorDB fails the licence filter and is listed for comparison only. All of them can filter during the vector search. Built-in LLM support differs:

- Elasticsearch has the `semantic_text` field and inference endpoints that call an embedding model.
- OpenSearch has ML Commons connectors, RAG and conversational search pipelines, and agents.
- Vespa has embedders and LLM components in the engine.
- FalkorDB has a GraphRAG SDK.
- The others leave embedding and LLM calls to the application.

## The candidates in short

- **Elasticsearch 9.5: recommended.** Entities, relationships, facets and audits already live there. A vector field on the entities index keeps one document per entity, one write path and one place where access filters apply. Its weak spot is the licence: fine for running Aurelius Atlas yourself or at a customer, not for a hosted service. Some ranking and ML features may need a paid tier.
- **OpenSearch 3: the fallback under Apache 2.0.** The same capabilities, plus ready-made RAG pipelines. It means porting `aurelius-atlas-store-es` to `opensearch-py`, re-indexing, and giving up Elasticsearch 9 features such as retrievers.
- **Qdrant: the best dedicated vector database.** Fast, memory-efficient filtered vector search. The vectors would sit apart from the entities, so every write and access rule must reach it too, while facets and graph context still come from Elasticsearch. Worth it only at tens of millions of vectors.
- **Milvus: built for billions of vectors.** The same split-store cost as Qdrant, with a heavier deployment.
- **Vespa: the best ranking, the hardest to adopt.** A rewrite of the store and every search on a new query language and operating model.
- **Apache Solr 9: Apache Atlas's own index.** It has kNN and strong facets, but switching would undo the move to Elasticsearch and gain nothing over it.
- **ArcadeDB: the graph candidate that passes.** Graph, document, full-text and vector indexes in one server; the only graph database that could be one store. Its facets are `GROUP BY` queries, not search aggregations.
- **FalkorDB: built for GraphRAG, but fails the licence filter.** Its Server Side Public License v1 is neither Apache 2.0 nor the Elastic License. As a graph database it also brings the costs below.
- **Cassandra, Chroma and LanceDB: not a fit.** Cassandra lacks full-text ranking and facets, Chroma suits prototypes, and LanceDB is a library with no open-source server.

## A graph database instead of Elasticsearch

A graph database as the only store would lose search and facets, or bring back a second store. Java Atlas keeps its graph in JanusGraph but still needs Solr or Elasticsearch beside it for full-text search and facets. Graph databases walk relationships well, but rank text and aggregate counts poorly. That leaves two options:

- **A graph database only:** `search/basic`, `search/quick` and the facet counts are lost, or rebuilt on a weaker engine.
- **A graph database plus a search index:** two stores to keep in sync, which ADR 047 ended.

Either way, the store library and every increment built on it would be ported again.

The chat does not need a graph database. A GraphRAG-style answer needs one or two hops around each hit, and the relationships index holds those edges. A graph database is clearly better only for deep traversals, such as lineage across many hops, which Elasticsearch answers with one round trip per hop. If those turn out too slow, the next step is a graph database as a read-only copy built from the relationships index, not a new store.

## Elasticsearch's own graph features

Elasticsearch has graph-like features, but none walks a stored property graph; the traversal stays in the Atlas server. The licence tiers are from memory and must be checked.

| Feature | What it does | Use for Aurelius Atlas | Licence tier |
| --- | --- | --- | --- |
| Graph explore API, Kibana Graph | Finds terms that often occur together | Related-entity hints, not lineage | Paid (Platinum) |
| `join` field (parent and child) | One parent-child relation per index | Too narrow: relationships are many-to-many | Free |
| ES\|QL `LOOKUP JOIN` | Joins a lookup-mode index, one step | One hop per query, no recursion | Free |
| `terms` lookup query, `enrich` processor | Ids from another document, fields copied | One hop per query, or breadcrumbs copied over | Free |

The server already walks the graph itself: `EntityLineageService` in `aurelius-atlas-core` fetches each entity's in- and out-edges from the relationships index, within Atlas's depth and on-demand limits. For the chat that is enough:

- **One or two hops around the hits:** one query for the edges of all hits, a second for the entities at their other ends.
- **Breadcrumbs:** the parent chain stored on each entity document when it is written, so neither the chat nor the embedding needs a walk. It also fills the empty trail of DD-317.
- **Lineage summaries:** the lineage service at a small depth, its result passed to the LLM.

## The chat on Elasticsearch

The chat is a new endpoint in the Atlas server; Elasticsearch stays the only store.

```
flowchart LR
    webapp["Webapp chat panel"] <-->|ask| chat["Chat endpoint<br/>in the Atlas server"]
    chat -->|prompt| llm["LLM"]
    chat -->|embed question| model["Embedding model"]
    chat -->|hybrid query, graph walk| es[("Elasticsearch 9.5<br/>entities: text, facets, vector<br/>relationships: lineage, parents")]
    write["Atlas entity write"] -->|change| worker["Embedding worker"]
    worker -->|entity text| model
    worker -->|writes vector| es
```

A question is embedded, then one hybrid query on the entities index finds the hits, with facets and access filters. The server walks one or two hops in the relationships index. The LLM answers from that context and cites the entity GUIDs, so the webapp can link each one. On the write side, a worker re-embeds every changed entity into its vector field.

As a rough size: 100,000 entities with 1,024-dimension float vectors take about 0.4 GB before quantisation, and a quarter of that or less with int8 or BBQ quantisation.

## Open questions

- Will Aurelius Atlas be offered as a hosted service to third parties? Then the Elastic License 2.0 rules out Elasticsearch, and OpenSearch is the choice.
- Which hybrid ranking and inference features are in Elastic's free Basic tier at 9.5, especially the RRF and linear retrievers and `semantic_text` with an external model? Without them, the server combines a kNN and a BM25 clause in one query itself.
- Which embedding model and LLM, and where do they run? A local model keeps catalogue metadata on site; a hosted API is simpler.
- Which text makes up an entity's embedding: name, description, type, classifications, breadcrumb path, owner?
- Should the breadcrumb path be stored on the entity document at write time? It would feed both the embedding and the empty trail of DD-317.
- The vector search and chat endpoints go beyond the Apache Atlas REST API. They need an ADR, and a spec of their own as an Aurelius extension.
