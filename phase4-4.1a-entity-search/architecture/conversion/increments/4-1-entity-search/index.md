# 4.1a Entity search

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-087 to DD-089, DV-43 to DV-46; relies on DD-043, DD-055

The first part of increment 4.1 (DD-087): basic search for entities by type, attribute filters, state, sort and paging, as Atlas's `EntityDiscoveryService.searchWithParameters` answers it with an `EntitySearchProcessor`. Entity attributes are indexed for it in typed search fields named after the type that defines them (DD-088). 4.1b adds classification search.

## Scope

| Endpoint | Takes | Answers |
| --- | --- | --- |
| `POST /api/atlas/v2/search/basic` | `SearchParameters` | `AtlasSearchResult` |
| `GET /api/atlas/v2/search/basic` | `typeName`, `sortBy`, `sortOrder`, `excludeDeletedEntities`, `limit`, `offset`, `marker` | `AtlasSearchResult` |
| `GET /api/atlas/v2/search/attribute` | `attrName`, `attrValuePrefix`, `typeName`, `limit`, `offset` | `AtlasSearchResult` |

In `aurelius-atlas-model`, `discovery` (`SearchParameters`, `FilterCriteria`, `AtlasSearchResult`). In `aurelius-atlas-core`, `search_fields` (the typed search fields of an entity, Atlas's vertex property keys), `search_context` (`SearchContext`), `entity_search_processor` (`EntitySearchProcessor`, the Elasticsearch query) and `discovery_service` (`EntityDiscoveryService.searchWithParameters`). The server's `routes/discovery` (`DiscoveryREST`) answers the endpoints.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| `classification`, `tagFilters`, `__classificationNames` filters (DV-46 until then) | 4.1b |
| `query` (free text), `search/fulltext`, `search/quick`, `search/suggestions` | 4.2 |
| `search/dsl` | 4.4 |
| `search/saved` | 4.5 |
| `termName` | 5.2 |
| `relationshipName`, `relationshipFilters`, `search/relationship`, `search/relations`, search downloads | – |

## Semantics

| Id | Rule |
| --- | --- |
| SRC-01 | `SearchParameters`, `FilterCriteria` and `AtlasSearchResult` read and write Atlas's fields, nulls left out; `includeSubTypes` and `includeSubClassifications` default to true, the other flags to false, `approximateCount` to -1. An operator reads any of its symbols (`=`, `eq`; `startsWith`, `STARTSWITH`, `begins_with`, …) and writes its first; an unknown symbol reads as none. `sortOrder` is `ASCENDING` or `DESCENDING` |
| SRC-02 | `POST basic` fails with `BAD_REQUEST` for a negative `limit` or `offset` (`Limit/offset should be non-negative`), for `entityFilters` without `typeName` (`EntityFilters specified without Type name`), for `tagFilters` without `classification` (`TagFilters specified without tag name`); with `INVALID_SEARCH_PARAMS` when none of `typeName`, `classification`, `query` and `termName` is given; with `INVALID_QUERY_PARAM_LENGTH` for a `typeName`, `classification` or `sortBy` over 4,096 characters |
| SRC-03 | `typeName` is a comma-separated list of entity type names and `_ALL_ENTITY_TYPES`; unknown names are left out, and when none is known the search fails with `UNKNOWN_TYPENAME` naming the whole list. `_ALL_ENTITY_TYPES` stands for every entity; otherwise the types and, with `includeSubTypes`, their sub types |
| SRC-04 | Each attribute an entity filter names, and `sortBy`, must be an attribute (a system attribute such as `__guid` included) of every type given, else the search fails with `UNKNOWN_ATTRIBUTE` naming it and the type (`_ALL_ENTITY_TYPES` for all). Each name in `attributes` must be an attribute or relationship attribute of the first type given, else `UNKNOWN_ATTRIBUTE` |
| SRC-05 | A filter is a criterion with a `condition` (`AND`, `OR`) over its `criterion`, or one on `attributeName` with an `operator` and an `attributeValue`, read as the attribute's type: `LT`, `LTE`, `GT`, `GTE`, `EQ` compare (strings by code point, case-sensitive), `NEQ` matches also entities without a value; `STARTS_WITH`, `ENDS_WITH`, `CONTAINS`, `LIKE` (DV-43) and `NOT_CONTAINS` test strings case-sensitively, and `CONTAINS`/`NOT_CONTAINS` an array's elements; `IS_NULL`, `NOT_NULL` and `NOT_EMPTY` test the value's presence; `IN` matches nothing; `CONTAINS_ANY`, `CONTAINS_ALL` and an unknown operator restrict nothing. A criterion on an attribute several types define matches any of them |
| SRC-06 | `TIME_RANGE` on a date or long takes `<start>,<end>` in epoch milliseconds, both included, or `TODAY`, `YESTERDAY`, `LAST_7_DAYS`, `LAST_30_DAYS`, `THIS_MONTH`, `LAST_MONTH`, `THIS_QUARTER`, `LAST_QUARTER`, `LAST_3_MONTHS`, `LAST_6_MONTHS`, `LAST_12_MONTHS`, `THIS_YEAR`, `LAST_YEAR`, computed as `processDateRange` does in UTC (DV-44). `__isIncomplete` `EQ` 0 or false, and `NEQ` 1, match complete entities; `__labels` and `__customAttributes` `EQ`, `NEQ`, `STARTS_WITH` and `ENDS_WITH` match one element (`key=value` for custom attributes) |
| SRC-07 | With `excludeDeletedEntities` only `ACTIVE` entities match. Matching entities are ordered by `sortBy` of the first type given (`sortOrder` `ASCENDING` by default, entities without a value last), else by creation time and GUID (DD-089); `limit` is 1 to 10,000, else 100, `offset` at least 0, and the answer's `searchParameters` show them so |
| SRC-08 | `marker` pages instead of `offset`: `*` starts, and `nextMarker` is the marker of the next page, `-1` after the last. A marker with an `offset` above 0 fails with `BAD_REQUEST` `Marker can be used only if offset=0.`, a marker that is not one of this search's with `Invalid marker!` (DV-45) |
| SRC-09 | The answer is `queryType` `BASIC`, the `searchParameters`, the entities' headers, their attributes being the header attributes, the requested `attributes` and the attributes the entity filters name, with their classifications when `includeClassificationAttributes`, and `approximateCount`, the number of matching entities. A requested attribute that refers to entities adds their headers to `referredEntities`. No match leaves `entities` out |
| SRC-10 | With `excludeHeaderAttributes`, `attributes` given and none of them a relationship attribute, the answer has, instead of entities, `attributes`: their `name`s and, per entity, the `values` of the first type's attributes, `""` for none |
| SRC-11 | `GET basic` searches with its query parameters, unvalidated; `excludeDeletedEntities` is true only for `true` in any case. `GET attribute` fails with `INVALID_PARAMETERS` `attrName : <name>, attrValue: <value> for attribute search.` without both, and searches for `attrValuePrefix` with `STARTS_WITH` on `attrName`, by default `qualifiedName`, or `name` where the type has no `qualifiedName`, validated as `POST basic`. A `limit`, `offset` or `sortOrder` that is no value of its type fails with `BAD_REQUEST` (DV-39) |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/DiscoveryREST.java`: `searchUsingBasic`, `searchUsingAttribute`, `searchWithParameters`, `validateBasicSearchParameters`
- `repository/.../discovery/EntityDiscoveryService.java`: `searchWithParameters`, `searchWithSearchContext`
- `repository/.../discovery/SearchContext.java` (with `MarkerUtil`), `EntitySearchProcessor.java`, `SearchProcessor.java` (`processDateRange`, `processPipeSeperatedSystemAttribute`, `toInMemoryPredicate`)
- `repository/.../util/SearchPredicateUtil.java`; `repository/.../query/QueryParams.java`
- `intg/.../model/discovery/SearchParameters.java`, `AtlasSearchResult.java`

## Deviations

DV-43: Atlas applies `LIKE` as its in-memory `contains`, and its index or graph query besides as a pattern; Aurelius Atlas applies the `contains` alone. DV-44: named time ranges are computed in UTC, where Atlas uses the server's time zone. DV-45: a marker encodes the search's hash and offset as Atlas's does, but with a hash of Aurelius Atlas's own, so Atlas's markers are not valid here. DV-46: until 4.1b, 4.2 and 5.2, a search with `classification`, `query` or `termName` fails with `BAD_REQUEST` naming the parameter. Atlas answers a `GET basic` without `typeName`, `classification` and `query` with a `NullPointerException`; Aurelius Atlas answers `INVALID_SEARCH_PARAMS`, and a value of a filter that is not one of its attribute's type `BAD_REQUEST` where Atlas fails with a `NumberFormatException` (both DV-46).

## Acceptance

- `libs/python/aurelius-atlas-model/tests/` — SRC-01.
- `libs/python/aurelius-atlas-core/tests/` — SRC-03 to SRC-10 on the in-memory documents and the fake client.
- `libs/python/aurelius-atlas-core/e2e/` — the search fields and the queries on the dev store.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/search/` — SRC-02, SRC-09, SRC-11 over HTTP.
- `uv run aurelius-atlas-trace check`.
