# 4.2a Free text

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-091, DD-092, DV-48, DV-49; ends the `query` part of DV-46; relies on DD-087 to DD-090

The first part of increment 4.2 (DD-091): free text, as Atlas's `FreeTextSearchProcessor` answers basic search's `query` through its Solr `/freetext` handler, weighted by the attributes' `searchWeight`, and `GET v2/search/fulltext`. 4.2b adds quick search with its facets and suggestions.

## Scope

| Endpoint | Takes | Answers |
| --- | --- | --- |
| `POST`/`GET /api/atlas/v2/search/basic` | `query`, with the other parameters of 4.1 | `AtlasSearchResult` |
| `GET /api/atlas/v2/search/fulltext` | `query`, `excludeDeletedEntities`, `limit`, `offset` | `AtlasSearchResult` of `FULL_TEXT` |

In `aurelius-atlas-core`, `free_text` (the searchable text of the registry, Atlas's `SolrIndexHelper` weights, and the text a query asks for), `search_fields` (an entity's classification text), and the search query, processors and discovery service, which take the text. The server's `routes/discovery` answers `fulltext`.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| `GET`/`POST search/quick` with facets, `GET search/suggestions` | 4.2b |
| Business metadata attributes in free text | 5.3 |

## Semantics

| Id | Rule |
| --- | --- |
| FTX-01 | A `query` longer than 4,096 characters fails with `INVALID_QUERY_LENGTH`. Basic search strips `*` from both ends of the query and uses the result when it holds a tokenising character (any but letters, digits and `_`; `.`, `:` and `'` only next to a non-letter; CJK characters), else the query as given |
| FTX-02 | An entity matches a query when one of its words, in any case, matches one of the query's words, a word ending in `*` matching every word it begins (DV-48). Its searchable text is the string attributes of the non-internal entity types, weighted by their `searchWeight` (1 to 10, else 3), its classification text (10), labels (10), custom attributes (3) and type name (1) |
| FTX-03 | An entity's classification text is, for each classification it lists, attached or propagated, the type name and the values of its attributes |
| FTX-04 | With a `query`, basic search finds the entities matching it that also match the types, classifications and filters; without `sortBy`, the best match first, by the weights of FTX-02 |
| FTX-05 | `GET fulltext` answers `queryType` `FULL_TEXT`, `queryText`, and `fullTextResult`: for each entity matching the query, best first, its header and `score`, at most `limit` (normalised as SRC-07), `offset` not used; with `excludeDeletedEntities`, deleted ones left out. `approximateCount` counts every matching entity, deleted ones too (DV-49) |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../discovery/FreeTextSearchProcessor.java`; `EntityDiscoveryService.java`: `searchWithParameters`, `searchUsingFullTextQuery`, `getIndexQueryResults`
- `repository/.../repository/graph/SolrIndexHelper.java` (the search weights), `GraphBackedSearchIndexer.java` (`isStringAttribute`, `isValidSearchWeight`), `FullTextMapperV2.java#getClassificationTextForEntity`
- `graphdb/janus/.../AtlasJanusGraphIndexClient.java#generatePayLoadForFreeText` (the `edismax` handler)
- `intg/.../type/AtlasStructType.java#hastokenizeChar`; `webapp/.../web/rest/DiscoveryREST.java`: `searchUsingFullText`, `searchWithParameters`

## Deviations

DV-48: Atlas parses a query with Solr's `edismax`, which knows `AND`, `OR` and `NOT` in either case and `field:value`; Aurelius Atlas reads it as Elasticsearch's `simple_query_string`, whose operators are `+`, `|`, `-` and quotes. DV-49: with free text enabled, Atlas's default, `fulltext` searches the `__fullText` property, which then is not written, and so finds nothing written since; Aurelius Atlas answers it from the free text.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — FTX-01 to FTX-05 on the in-memory documents and the fake client.
- `libs/python/aurelius-atlas-core/e2e/` — free text on the dev store.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/search/` — FTX-01, FTX-04, FTX-05 over HTTP.
- `uv run aurelius-atlas-trace check`.
