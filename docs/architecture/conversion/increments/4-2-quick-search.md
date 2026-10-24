# 4.2b Quick search and suggestions

- **Status:** in progress
- **Pull request:** [#146](https://github.com/aureliusenterprise/aurelius-atlas/pull/146)
- **Records:** DD-093, DD-094, DV-50, DV-51; relies on DD-087 to DD-092

The second part of increment 4.2 (DD-091): quick search, as Atlas's `EntityDiscoveryService.quickSearch`
answers it with the facets of `SearchAggregatorImpl`, and suggestions, as `SuggestionsProviderImpl` reads them
from Solr's terms of the fields weighted 8 or more.

## Scope

| Endpoint                               | Takes                                                                                                       | Answers                  |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------ |
| `GET /api/atlas/v2/search/quick`       | `query`, `typeName`, `excludeDeletedEntities`, `offset`, `limit`, `sortBy`, `sortOrder`                     | `AtlasQuickSearchResult` |
| `POST /api/atlas/v2/search/quick`      | `QuickSearchParameters`: those, `entityFilters`, `includeSubTypes`, `attributes`, `excludeHeaderAttributes` | `AtlasQuickSearchResult` |
| `GET /api/atlas/v2/search/suggestions` | `prefixString`, `fieldName`                                                                                 | `AtlasSuggestionsResult` |

In `aurelius-atlas-core`, `search_aggregator` (`SearchAggregatorImpl` with its `ServiceTypeAggregator`) and
`suggestions_provider` (`SuggestionsProviderImpl`); the discovery service answers quick search, the entity
documents count facets and read terms. The server's `routes/discovery` answers both endpoints.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| QSR-01 | `POST quick` fails, in this order, with `BAD_REQUEST` for a negative limit or offset (`Limit/offset should be non-negative`) and for entity filters without `typeName` (`EntityFilters specified without Type name`), with `INVALID_SEARCH_PARAMS` with neither `typeName` nor `query`, with `BAD_REQUEST` for `sortBy` without `typeName` (`SortBy specified without Type name`), then on lengths as SRC-02 and FTX-01 check them. `GET quick` checks the query's length only |
| QSR-02 | A query without a tokenising character (FTX-01) gets a `*` appended; the search is then a basic search of the parameters (FTX-04, SRC-03 to SRC-10), sub types only with `includeSubTypes` (never by `GET`), answered as `searchResults`                                                                                                                                                                                                                                       |
| QSR-03 | `aggregationMetrics` counts the entities matching the query, types, filters and `excludeDeletedEntities`, unpaged: by `__typeName`, `__state` and `Asset.owner`, each value with its count, most first, then by value; values counted none are left out                                                                                                                                                                                                                        |
| QSR-04 | `ServiceType` adds up the `__typeName` counts by each entity type's `serviceType`, for the service types the registry's types name; types without one and service types counted none are left out, and without any `ServiceType` is absent                                                                                                                                                                                                                                     |
| SUG-01 | `GET suggestions` answers `prefixString`, `fieldName` and `suggestions`: up to 5 terms that begin with the prefix, case-sensitively, of every entity's text in the fields weighted 8 or more (FTX-02), each field's 5 most frequent first, then all by their summed frequency, most first, then by term (DV-50)                                                                                                                                                                |
| SUG-02 | A `fieldName` that is a system attribute, or `<type>.<attribute>` of a primitive attribute the type defines, reads that field alone; any other is ignored. A field that is not a string has no suggestions (DV-51)                                                                                                                                                                                                                                                             |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/DiscoveryREST.java`: `quickSearch` (both), `getSuggestions`, `validateSearchParameters`
- `repository/.../discovery/EntityDiscoveryService.java`: `quickSearch`, `createSearchParameters`,
  `getAggregationFields`, `getAggregationAtlasAttributes`
- `repository/.../discovery/SearchAggregatorImpl.java` (`ServiceTypeAggregator`),
  `SuggestionsProviderImpl.java`
- `graphdb/janus/.../AtlasJanusGraphIndexClient.java`: `getAggregatedMetrics`, `getSuggestions`, `getTopTerms`
- `repository/.../repository/graph/SolrIndexHelper.java#getIndexFieldNamesForSuggestions`
- `intg/.../model/discovery/`: `QuickSearchParameters`, `AtlasQuickSearchResult`, `AtlasAggregationEntry`,
  `AtlasSuggestionsResult`

## Deviations

DV-50: Solr's terms of a field are as its schema indexes them: words for text, but whole values for an
attribute of `indexType` `STRING`; Aurelius Atlas suggests the analysed words of the text sub-field
throughout, and ranks terms of equal frequency by term where Atlas's priority queue leaves their order open.
DV-51: for a field that is not a string, Solr answers its encoded terms; Aurelius Atlas answers none.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — QSR-02 to QSR-04, SUG-01, SUG-02 on the in-memory documents and
  the fake client.
- `libs/python/aurelius-atlas-core/e2e/` — facets and suggestions on the dev store.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/search/` — QSR-01 to QSR-04,
  SUG-01 over HTTP.
- `uv run aurelius-atlas-trace check`.
