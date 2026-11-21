# 19.1 One query semantics for the store and its fakes

- **Status:** in review
- **Pull request:** #427
- **Records:** DD-767 to DD-772, plan in [plan.md](./plan.md), design in [design.md](./design.md)

## Scope

This increment gives the store one place that builds Elasticsearch query clauses, and one place that defines how
a free-text word works. Both the store documents and the App Search engine then call that place, and the test
fake reads the word rules from it instead of carrying its own copy. It puts the App Search search on a narrow
store contract, so a spec can drive an engine with a small fake instead of the whole store.

This increment changes no answer that leaves the server. No endpoint changes its body, its status, or its
headers. The parity scenarios and the frozen 14.6 corpus must answer byte-identical, and that is an acceptance
rule below.

This increment does not deliver:

| Not delivered                                | It lands in |
| -------------------------------------------- | ----------- |
| The `entity_documents.py` module split       | 19.4        |
| The engine's schema, query, and answer split | 19.4        |
| The write-path store contract                | 19.2        |
| The owner for the shared classification rule | 19.3        |

## Semantics

One reading of a query is the meaning it has for one document. Today core holds that meaning in two places on
purpose, and the store fake holds a third, which reads Elasticsearch's own query JSON. This increment keeps all
three readings and removes the duplication between them.

| Id     | Rule                                                                                                                                                                                                                                                                                                               |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| QRY-01 | One module builds every Elasticsearch query clause core emits: filters, ranges, free text, kNN, and facet aggregations. No other core module writes a `bool`, `should`, `must`, or `knn` clause by hand.                                                                                                           |
| QRY-02 | One module defines the free-text word rules. The store fake imports them, so a pattern and a query word mean the same thing in the fake and in the text index.                                                                                                                                                     |
| QRY-03 | The fake honours `minimum_should_match` with the value the clause carries, not a fixed one. A `should` group with a value of `2` needs two matching clauses.                                                                                                                                                       |
| QRY-04 | A saved matrix of queries answers the same hit GUIDs and the same facet counts from the in-memory store and from the fake store. The matrix covers each predicate in `Test`, both sort tie-breaks, present-before-absent ordering, and a vector query.                                                             |
| QRY-05 | The App Search search sits on a narrow store contract, so an engine takes that instead of the concrete store, a spec drives one with a purpose-built fake, and no test writes a type-ignore to build the store it drives it with. The in-memory store keeps its two searches and stays off that contract (DD-770). |
| QRY-06 | No wire answer changes. The parity scenarios and the 14.6 governance corpus answer identical to the base commit.                                                                                                                                                                                                   |

## Java origin

This ports nothing. Apache Atlas 2.4.0 spreads query translation over `SolrIndexHelper`, `SearchPredicateUtil`,
and its graph queries, and Aurelius Atlas already replaced all of it with the `SearchQuery` filter tree and the
`Test` predicate vocabulary in `search_query.py`. This increment reorganises that port.

## Deviations

None from Apache Atlas. The increment changes no observable behaviour, so it adds no row to
[Deviations](../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                              | Command                                                                                                                                                                                      | Level |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| Every QRY rule has a test that names it            | `uv run aurelius-atlas-trace check` scoped to this increment                                                                                                                                 | 0     |
| The store packages and the core search suites pass | `uv run pytest libs/python/aurelius-atlas-store-es/tests libs/python/aurelius-atlas-core/tests`                                                                                              | 0     |
| The server unit suites pass                        | `nx test aurelius-atlas-server -c ci`                                                                                                                                                        | 1     |
| No wire answer moved                               | The parity scenarios and `test__app_search_governance.py` answer identical                                                                                                                   | 1     |
| The doors and engines run on a narrow contract     | `nx test aurelius-atlas-core -c ci`: `test__search_documents.py` drives both on a purpose-built fake, and no spec writes a `# type: ignore[arg-type]` to build the store it drives them with | 0     |
| Lint and types                                     | `nx run-many -t lint -p aurelius-atlas-core aurelius-atlas-store-es` and the same for `-t typecheck`                                                                                         | 0     |
| One live proof that the search path still works    | `nx e2e aurelius-atlas-server -c ci`                                                                                                                                                         | 2     |

## Design decisions

The reasoning for each rule above lives in [design.md](./design.md) as DD-767 to DD-772. The two worth reading
before the rest are DD-768, which records why the fake keeps its own reading of Elasticsearch query JSON, and
DD-770, which records why the App Search search joins a narrow contract instead of widening the existing one.
