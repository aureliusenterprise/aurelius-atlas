# Vector search and chat: store options

> [!NOTE]
>
> **Proposal**
>
> A comparison written on 2026-11-07, ahead of any increment. It records no decision: a change of store would supersede [ADR 047](<https://aureliusenterprise.github.io/ci-criticality-tiers/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>), and the vector search and chat endpoints need an ADR and a spec of their own.

Keep Elasticsearch 9.5 as the one store and add the vectors to it; no second database is needed. Each entity document gets a `dense_vector` field. One query then mixes BM25 text matching, kNN on that vector and the filters already in use: type, state, owner and the user's access rights. The chat is a retrieval-augmented service in the Atlas server, not a database feature. It retrieves entities, follows their relationships and breadcrumb chain in the same indices, and passes that context to an LLM.

This keeps [ADR 047](<https://aureliusenterprise.github.io/ci-criticality-tiers/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>): one search store is the system of record, with no graph database beside it.

- **Fallback:** OpenSearch, Apache 2.0, if the Elastic License 2.0 is ruled out, for example because customers are to reach Elasticsearch itself. It has the closest query DSL, but moving to it migrates the store and the client.
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
| Licence | Free commercial use, and hosting allowed while customers don't reach the database |

A worker re-embeds an entity whenever it changes.

## The licence filter

A database passes when its licence allows free commercial use and hosting Aurelius Atlas on it, as long as customers reach Aurelius Atlas and not the database itself: the terms Elasticsearch has under the Elastic License 2.0. Open-source licences pass, the permissive ones and the copyleft ones alike; source-available licences pass when their limit is on offering the database itself.

| Licence | Free commercial use | Hosting Aurelius Atlas on it | Passes |
| --- | --- | --- | --- |
| Apache 2.0, MIT, BSD-3-Clause, PostgreSQL | Yes | Yes, keeping the notices | Yes |
| Elastic License 2.0 | Yes | Yes, while customers have no access to "any substantial set of the features or functionality" of the database | Yes |
| AGPLv3 | Yes | Yes. Changes to the database's own code go to its users as source; run unmodified, nothing is owed | Yes |
| GPLv3 | Yes | Yes. Shipping the database, in the Helm chart for example, comes with an offer of its source; Aurelius Atlas's own code is not affected | Yes |
| Redis Source Available License 2.0 | Yes | Its limit has no "substantial set" qualifier: no making "the functionality of the Software" available as a service. Redis 8 can be taken under AGPLv3 | Unclear |
| Server Side Public License v1 | Yes | Its section 13 includes "enabling third parties to interact with the functionality of the Program remotely", and asks then for the whole service's source | Unclear |
| Business Source Licence 1.1 (Memgraph) | Only internal use | No: the grant is for "internal business purposes", without distribution to third parties or database-as-a-service; each version turns Apache 2.0 after four years | No |

The licences were read from each project's repository licence file on GitHub, on 2026-11-07 and again on 2026-11-09 for the ones this filter now lets through. This is a reading of the licence texts, not legal advice.

| Database | Licence | Passes |
| --- | --- | --- |
| [Elasticsearch](<https://github.com/elastic/elasticsearch>) | AGPLv3, SSPL or Elastic License 2.0 (choice) | Yes, under ELv2 or AGPLv3 |
| [OpenSearch](<https://github.com/opensearch-project/OpenSearch>) and its [k-NN plugin](<https://github.com/opensearch-project/k-NN>) | Apache 2.0 | Yes |
| [Qdrant](<https://github.com/qdrant/qdrant>) | Apache 2.0 | Yes |
| [Milvus](<https://github.com/milvus-io/milvus>) | Apache 2.0 | Yes |
| [Vespa](<https://github.com/vespa-engine/vespa>) | Apache 2.0 | Yes |
| [Apache Solr](<https://github.com/apache/solr>) | Apache 2.0 | Yes |
| [Apache Cassandra](<https://github.com/apache/cassandra>) 5 | Apache 2.0 | Yes |
| [Chroma](<https://github.com/chroma-core/chroma>) | Apache 2.0 | Yes |
| [LanceDB](<https://github.com/lancedb/lancedb>) | Apache 2.0 | Yes |
| [pgvector](<https://github.com/pgvector/pgvector>) and PostgreSQL | PostgreSQL Licence | Yes |
| [Weaviate](<https://github.com/weaviate/weaviate>) | BSD-3-Clause; its enterprise features under their own licence | Yes, without those features |
| [Redis](<https://github.com/redis/redis>) 8 | RSALv2, SSPL or AGPLv3 (choice) | Yes, under AGPLv3 |
| [Valkey Search](<https://github.com/valkey-io/valkey-search>) | BSD-3-Clause | Yes |
| [ArcadeDB](<https://github.com/ArcadeData/arcadedb>) (graph) | Apache 2.0 | Yes |
| [Neo4j](<https://github.com/neo4j/neo4j>) Community (graph) | GPLv3 | Yes |
| [NebulaGraph](<https://github.com/vesoft-inc/nebula>) (graph) | Apache 2.0 | Yes, but no vector search known |
| [Apache HugeGraph](<https://github.com/apache/hugegraph>) (graph) | Apache 2.0 | Yes, but limited vector search |
| [JanusGraph](<https://github.com/JanusGraph/janusgraph>) (graph) | Apache 2.0 (code), CC-BY-4.0 (docs) | Yes, but no vector search |
| [Apache AGE](<https://github.com/apache/age>) (graph) | Apache 2.0, an extension of PostgreSQL | Yes, with PostgreSQL |
| [FalkorDB](<https://github.com/FalkorDB/FalkorDB>) (graph) | Server Side Public License v1 | Unclear |
| [Memgraph](<https://github.com/memgraph/memgraph>) (graph) | Business Source Licence 1.1 | No |
| [Kùzu](<https://github.com/kuzudb/kuzu>) (graph) | MIT | Licence yes; archived |

Some Elasticsearch code is licensed solely under the Elastic License 2.0. That licence is source-available, not OSI open source. It allows free use, also commercially, with three limits: no providing Elasticsearch to third parties "as a hosted or managed service, where the service provides users with access to any substantial set of the features or functionality of the software", no working around its licence-key checks, and no removing its notices.

Aurelius Atlas offered as a hosted service, with Elasticsearch hosted behind it, stays within that limit. Customers reach the Atlas REST API and the webapp, and the server builds its own queries from their calls: no route passes Elasticsearch's API or query DSL through. Elastic's licence FAQ names this case, Elasticsearch as the backend of one's own SaaS product, as allowed. Exposing Elasticsearch to customers, or passing its query DSL through nearly unchanged, would not be. The vector search and chat endpoints keep to Aurelius's own requests for that reason, and so would any other database in the table.

FalkorDB stays unclear because the Server Side Public License words its limit more broadly than the Elastic License. A hosted Aurelius Atlas whose chat runs on FalkorDB's graph queries could count as "enabling third parties to interact with the functionality" of FalkorDB. The price of being wrong is high: the source of every program used to run the service, under the same licence. MongoDB reads its own SSPL as not covering an application built on the database, but that reading is not part of the licence. It needs a legal review, or a commercial FalkorDB licence, before it is used.

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
| PostgreSQL + pgvector | Replaces the store | `tsvector` full-text, no BM25, plus HNSW vectors | `GROUP BY` counts only | New store; re-port every query; AGE adds Cypher | One PostgreSQL |
| Weaviate | Second store, vectors only | BM25 and vectors, fused | Aggregate queries by property | Same as Qdrant | One extra service |
| Redis 8 | Second store, vectors only | Full-text and vector in one query | `FT.AGGREGATE` group-by | Same as Qdrant | In memory |
| Valkey Search | Second store, vectors only | Vector search with tag filters | No | Same as Qdrant | Valkey module, in memory |
| Neo4j Community | Replaces the store | Lucene full-text plus vector index | Cypher `count` grouping only | New store; re-port every query | One Java server, no clustering |

FalkorDB's licence is unclear for a hosted Aurelius Atlas, see above. All of them can filter during the vector search. Built-in LLM support differs:

- Elasticsearch has the `semantic_text` field and inference endpoints that call an embedding model.
- OpenSearch has ML Commons connectors, RAG and conversational search pipelines, and agents.
- Vespa has embedders and LLM components in the engine.
- FalkorDB has a GraphRAG SDK.
- The others leave embedding and LLM calls to the application.

## The candidates in short

- **Elasticsearch 9.5: recommended.** Entities, relationships, facets and audits already live there. A vector field on the entities index keeps one document per entity, one write path and one place where access filters apply. Its licence allows running Aurelius Atlas yourself, at a customer or as a hosted service, as long as Elasticsearch stays behind the server. Some ranking and ML features may need a paid tier.
- **OpenSearch 3: the fallback under Apache 2.0.** The same capabilities, plus ready-made RAG pipelines. It means porting `aurelius-atlas-store-es` to `opensearch-py`, re-indexing, and giving up Elasticsearch 9 features such as retrievers.
- **Qdrant: the best dedicated vector database.** Fast, memory-efficient filtered vector search. The vectors would sit apart from the entities, so every write and access rule must reach it too, while facets and graph context still come from Elasticsearch. Worth it only at tens of millions of vectors.
- **Milvus: built for billions of vectors.** The same split-store cost as Qdrant, with a heavier deployment.
- **Vespa: the best ranking, the hardest to adopt.** A rewrite of the store and every search on a new query language and operating model.
- **Apache Solr 9: Apache Atlas's own index.** It has kNN and strong facets, but switching would undo the move to Elasticsearch and gain nothing over it.
- **ArcadeDB: the strongest graph candidate.** Graph, document, full-text and vector indexes in one server, under Apache 2.0. Its facets are `GROUP BY` queries, not search aggregations.
- **Neo4j Community: the best-known graph database.** Full-text and vector indexes beside the graph, under GPLv3, which asks nothing of Aurelius Atlas's own code. Community has no clustering. Like ArcadeDB, its facets are `count` queries, and it brings the costs below.
- **PostgreSQL with pgvector and Apache AGE: one well-known server.** Vectors, full-text and a Cypher graph in PostgreSQL, but no BM25 ranking and no search facets.
- **FalkorDB: built for GraphRAG, licence unclear.** Its Server Side Public License v1 needs a legal review for a hosted Aurelius Atlas. As a graph database it also brings the costs below.
- **Weaviate, Redis 8 and Valkey Search: second stores.** The same sync cost as Qdrant, with no gain over it here.
- **Cassandra, Chroma and LanceDB: not a fit.** Cassandra lacks full-text ranking and facets, Chroma suits prototypes, and LanceDB is a library with no open-source server.

## A graph database instead of Elasticsearch

A graph database as the only store would lose search and facets, or bring back a second store. Java Atlas keeps its graph in JanusGraph but still needs Solr or Elasticsearch beside it for full-text search and facets. Graph databases walk relationships well, but rank text and aggregate counts poorly. That leaves two options:

- **A graph database only:** `search/basic`, `search/quick` and the facet counts are lost, or rebuilt on a weaker engine.
- **A graph database plus a search index:** two stores to keep in sync, which ADR 047 ended.

Either way, the store library and every increment built on it would be ported again.

### FalkorDB as the only store

FalkorDB as the only store, in place of Elasticsearch, costs more than it gives:

- **Search and facets get weaker.** `search/basic`, `search/quick` and the facet counts (`aggregationMetrics`) are built on Elasticsearch's ranking and aggregations. FalkorDB has a full-text index and Cypher `count` grouping, but nothing like Elasticsearch's aggregations. The facet sidebar and DSL search would be rebuilt on a weaker engine.
- **The whole store library is rewritten.** `aurelius-atlas-store-es` and every increment built on it assume Elasticsearch indices: entities, relationships, classifications, audits, the journal, unique values and typedefs. Moving means porting all of it again and checking parity again. It would also supersede [ADR 047](<https://aureliusenterprise.github.io/ci-criticality-tiers/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>).
- **The graph lives in memory.** FalkorDB is a Redis module, so the whole graph has to fit in one node's RAM. A single graph is not sharded across nodes, which caps its size and sets its cost per node. Elasticsearch keeps its data on disk.
- **Filtering during vector search may be weaker.** FalkorDB's vector query returns the top k nodes first, and Cypher filters them afterwards. With access rights and type filters, hits are lost after the top-k cut instead of being filtered before it. Elasticsearch filters inside the kNN search.
- **It is younger.** FalkorDB grew out of RedisGraph in 2023, so it has a shorter track record and a smaller ecosystem than Elasticsearch.

The points on sharding and on vector filtering are from memory of FalkorDB's documentation, not checked for this page.

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

- Should customers ever reach Elasticsearch itself, for example its query DSL or Kibana? Then the Elastic License 2.0 rules out Elasticsearch, and OpenSearch is the choice. A hosted Aurelius Atlas with Elasticsearch behind the server is allowed.
- Which hybrid ranking and inference features are in Elastic's free Basic tier at 9.5, especially the RRF and linear retrievers and `semantic_text` with an external model? Without them, the server combines a kNN and a BM25 clause in one query itself.
- Which embedding model and LLM, and where do they run? A local model keeps catalogue metadata on site; a hosted API is simpler.
- Which text makes up an entity's embedding: name, description, type, classifications, breadcrumb path, owner?
- Should the breadcrumb path be stored on the entity document at write time? It would feed both the embedding and the empty trail of DD-317.
- The vector search and chat endpoints go beyond the Apache Atlas REST API. They need an ADR, and a spec of their own as an Aurelius extension.
