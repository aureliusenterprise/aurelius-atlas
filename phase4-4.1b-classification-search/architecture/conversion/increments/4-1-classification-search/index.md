# 4.1b Classification search

- **Status:** in progress
- **Pull request:** [\#142](<https://github.com/aureliusenterprise/aurelius-atlas/pull/142>)
- **Records:** DD-090, DV-47; ends the classification part of DV-46; relies on DD-070, DD-087 to DD-089

The second part of increment 4.1 (DD-087): basic search by `classification` and `tagFilters`, as Atlas's `ClassificationSearchProcessor` and the classification filter of `EntitySearchProcessor` answer it, and entity filters on `__classificationNames` and `__propagatedClassificationNames`.

## Scope

`POST` and `GET /api/atlas/v2/search/basic` take `classification`, and `POST` also `tagFilters` and `includeSubClassifications`. In `aurelius-atlas-core`, `classification_search_processor` (`ClassificationSearchProcessor`) finds the classification instances a search names (DD-090); `search_context`, `entity_search_processor` and `discovery_service` take them; `search_fields` adds the classification names of an entity. The free-text `query` and `termName` stay refused until 4.2 and 5.2 (DV-46).

## Semantics

| Id | Rule |
| --- | --- |
| CSR-01 | `classification` is a comma-separated list of classification type names, names with `*`, `*`, `_CLASSIFIED`, `_NOT_CLASSIFIED` and `_ALL_CLASSIFICATION_TYPES`; other unknown names are left out, and when none is left the search fails with `UNKNOWN_CLASSIFICATION` naming the whole list. `_NOT_CLASSIFIED` among them stands for entities without classifications; else `*`, `_CLASSIFIED` or `_ALL_CLASSIFICATION_TYPES` for entities with any |
| CSR-02 | An entity matches the classification types when it lists, attached or propagated, an instance of one of them or, with `includeSubClassifications` (the default), of a sub type. With a name containing `*`, an entity matches when one of its classifications' type names matches one of the names, `*` standing for any characters, ignoring case (DV-47) |
| CSR-03 | `tagFilters` are filters as SRC-05 and SRC-06 state them, on the attributes (system attributes such as `__entityStatus` included) of every classification type given, else the search fails with `UNKNOWN_ATTRIBUTE` naming the type (`_ALL_CLASSIFICATION_TYPES` for any); with a name containing `*` other than `*` itself they fail with `BAD_REQUEST` `TagFilters specified with wildcard tag name`. An entity matches when one of the instances it lists matches them |
| CSR-04 | With `typeName` too, an entity must match both, and the entity filters; without, entities of every type match. `excludeDeletedEntities` applies as in SRC-07. With `tagFilters`, `approximateCount` is -1, as Atlas's classification processor answers it; `sortBy` orders only with `typeName` |
| CSR-05 | An entity's `__classificationNames` are the type names of the classifications attached to it, `__propagatedClassificationNames` those propagated to it, each as `\\|a\\|b\\|`, and entity filters match them as SRC-06 states |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../discovery/ClassificationSearchProcessor.java`
- `repository/.../discovery/SearchContext.java`: `getClassificationNames`, `getClassificationTypes`, `filterStructTypes`, `needClassificationProcessor`, `isWildCardSearch`
- `repository/.../discovery/SearchProcessor.java#buildTraitPredict`, `getRegexString`
- `repository/.../discovery/EntitySearchProcessor.java` (the classification filter without `tagFilters`)

## Deviations

DV-47: Atlas matches a wildcard name with a regular expression over the entity's pipe-separated names, where `*` can also span `|` and so match across two names; Aurelius Atlas matches each name on its own.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — CSR-01 to CSR-05 on the in-memory documents.
- `libs/python/aurelius-atlas-core/e2e/` — a classification search on the dev store.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/search/` — CSR-01, CSR-02, CSR-04 over HTTP.
- `uv run aurelius-atlas-trace check`.
