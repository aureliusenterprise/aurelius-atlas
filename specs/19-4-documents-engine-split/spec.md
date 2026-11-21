# 19.4 One document module set and one narrow engine seam

- **Status:** in review
- **Pull request:** TBD
- **Records:** DD-788 to DD-792, plan in [plan.md](./plan.md), design in [design.md](./design.md)

## Scope

This increment replaces the 1,343-line `entity_documents.py` with three modules by job, and splits the
779-line `app_search_engine.py` into a schema part, a query part, and an answer part. It then narrows each
contract to the methods its callers actually call. The query translation this needs moved to `es_clauses` in
[19.1](../19-1-query-semantics/spec.md), and the engine's word pattern moved to `free_text` there, so this
increment moves what is left.

This increment changes no answer that leaves the server. No endpoint changes its body, its status, or its
headers. The parity scenarios and the frozen 14.6 corpus must answer byte-identical, and that is an acceptance
rule below.

This increment does not deliver:

| Not delivered                                  | It lands in |
| ---------------------------------------------- | ----------- |
| The `es_clauses` builder and the word export   | 19.1        |
| The store contract the write path is typed on  | 19.2        |
| The route providers and the store-lookup error | 19.5        |

## Semantics

The two large modules each mix three jobs: how an index is built, how a document is stored and read, and how a
query is translated or rendered. The rules below give each job a module and give each module only the methods
its
callers use.

| Id     | Rule                                                                                                                                                                                       |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| EDS-01 | One module owns index setup: the index names, the mappings, and the create-once logic that today sit in `entity_documents` beside the client. No other module names an index or a mapping. |
| EDS-02 | One module owns the Elasticsearch document client: the class today called `ElasticsearchEntityDocuments`. It calls the index module for names and the `es_clauses` module for translation. |
| EDS-03 | The `EntityDocuments` contract lists only the methods the indexers and the doors call. It does not list methods no caller calls, so a fake need not carry them.                            |
| EDS-04 | The App Search engine is three modules: the engine schema (fields and kinds), the engine query (build the request), and the engine answer (render hits and highlight).                     |
| EDS-05 | No wire answer changes. The parity scenarios and the 14.6 governance corpus answer identical to the base commit, and each moved function keeps the test that already named it.             |

## Java origin

This ports nothing. Apache Atlas 2.4.0 builds its index through `GraphBackedSearchIndexer` and `IndexUtil`,
and
its App Search analogue is a Solr request handler. Aurelius Atlas replaced all of it with the Elasticsearch
document client and the App Search engine, and both files this increment splits are Aurelius code. This
increment reorganises that code, so it adds no row to [Java
map](../../docs/architecture/conversion/java-map.md).

## Deviations

None from Apache Atlas. The increment moves code and narrows contracts without changing observable behaviour,
so
it adds no row to [Deviations](../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                                     | Command                                                                                          | Level |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ----- |
| Every EDS rule has a test that names it                   | `uv run aurelius-atlas-trace check` scoped to this increment                                     | 0     |
| The move changed no line the tests do not see             | `git diff -w --stat` shows the move, and `git diff -w` of the pure-move commit shows only moves  | 0     |
| The core, store, and server suites pass                   | `nx test aurelius-atlas-core aurelius-atlas-store-es aurelius-atlas-server -c ci`                | 1     |
| No wire answer moved                                      | The parity scenarios and `test__app_search_governance.py` answer identical                       | 1     |
| The contracts are no wider than their callers             | Each indexer and each door types on a contract whose methods it calls, checked by `nx typecheck` | 0     |
| Lint and types                                            | `nx lint aurelius-atlas-core aurelius-atlas-store-es` and `nx typecheck aurelius-atlas-core`     | 0     |
| One live proof that the search and index path still works | `nx e2e aurelius-atlas-server -c ci`                                                             | 2     |

## Design decisions

The reasoning for each rule above lives in [design.md](./design.md) as DD-788 to DD-792. The one worth reading
before the rest is DD-788, which records the pure-move commit rule that keeps a 1,300-line split reviewable.
