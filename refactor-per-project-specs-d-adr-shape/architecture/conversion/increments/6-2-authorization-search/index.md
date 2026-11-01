# 6.2c Authorization: search, lineage and type listings

- **Status:** in progress
- **Pull request:** to follow
- **Records:** accepts ADR 038; amends AUZ-04 (6.2a); relies on DD-300, DD-301

6.2a and 6.2b check each request where Atlas's stores check it. This last part covers the answers that list many entities or types at once. Atlas does not refuse these: it scrubs the search results of the entities the user may not read, and leaves out of a type listing the definitions the user may not read. It also checks that the user may read an entity before answering its lineage. With this part, the authorizer answers every endpoint the server serves, so ADR 038 is accepted. The production realm gets the four roles too, so a cluster checks the same way as the dev stack.

## Scope

| Endpoint | Needs |
| --- | --- |
| `GET`, `POST /api/atlas/v2/search/basic`, `/search/attribute`, `/search/quick` | `ENTITY_READ` of each entity found, or it is scrubbed |
| `GET /api/atlas/v2/search/fulltext`, `/search/dsl`, `/search/saved/execute/...` | as above |
| `GET /api/atlas/v2/lineage/{guid}`, `POST .../{guid}`, `.../uniqueAttribute/type/{type}` | `ENTITY_READ` of the entity |
| `GET /api/atlas/v2/types/typedefs`, `/types/typedefs/headers` | `TYPE_READ` of each definition, or it is left out |

In `aurelius-atlas-core`, `authorization` gains `is_access_allowed` on the `Authorizer`, the scrubbing (`scrub_entity_header`, `scrub_search_results`) and the type filter (`filter_types_def`). `EntityDiscoveryService` scrubs its answers and `EntityLineageService` checks the entity. In `aurelius-atlas-server`, the search and lineage routes hand their services the request's authorizer, and the type listings are filtered. In `dev/keycloak`, the production realm asset gets the roles.

## Semantics

| Id | Rule |
| --- | --- |
| AUZ-12 | A basic, attribute, quick, full-text, DSL or saved search scrubs each entity the user may not read (`ENTITY_READ`): the result's entities, the entity of each full-text hit and the referred entities. A scrubbed header's GUID is `-1`, and its attributes, classifications, classification names, meanings and meaning names are emptied where present. Its type name, status, display text and labels stay. So do the count, the next marker, a quick search's facets and the attribute table of a search that excludes header attributes. Suggestions are not scrubbed |
| AUZ-13 | Lineage needs `ENTITY_READ` of the entity: `read entity lineage: guid=<guid>`, checked once the entity is found and before its type is checked. The entities on the lineage are not checked |
| AUZ-14 | Listing type definitions and their headers leaves out each definition the user may not read (`TYPE_READ`); a user without it gets an empty listing. This amends AUZ-04, which had the listings unchecked |
| AUZ-15 | The production realm asset carries the four roles of the server's client and their mapping into the webapp client's scope, as the dev realm does; no user holds them until an operator grants them |

## Java origin

Apache Atlas `release-2.4.0`:

- `authorization/.../authorize/AtlasAuthorizationUtils.java`: `scrubSearchResults`, `filterTypesDef`
- `authorization/.../authorize/AtlasAuthorizer.java`: `scrubEntityHeader`
- `authorization/.../authorize/simple/AtlasSimpleAuthorizer.java`: `scrubSearchResults`, `checkAccessAndScrub`, `filterTypesDef`, `filterTypes`
- `repository/.../discovery/EntityDiscoveryService.java`: `searchUsingDslQuery`, `searchUsingFullTextQuery`, `searchWithSearchContext` (basic and quick search)
- `repository/.../discovery/EntityLineageService.java`: `validateEntityTypeAndCheckIfDataSet`
- `repository/.../store/graph/AtlasTypeDefGraphStore.java`: `searchTypesDef`

## Deviations

None. Under DD-300 `ENTITY_READ` and `TYPE_READ` hold for all entities and types or none, so a search answers all its headers scrubbed or none, and a type listing is complete or empty. Atlas's per-entity and per-type checks are kept, so a finer grant would scrub entity by entity.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — AUZ-12 on each search, on a header of every field and on full-text hits and referred entities; AUZ-13 on lineage and lineage on demand; AUZ-14 on the filter.
- `apps/aurelius-atlas-server/tests/` — AUZ-12 to AUZ-14 with tokens of no role and of `atlas-read`.
- `tests/` (chart contract) — AUZ-15: the production asset's roles and scope mapping equal the dev asset's. The trace check does not read this suite, as for the CHT rules.
- `apps/aurelius-atlas-server/e2e/` — the parity scenarios as the dev realm's writer, who holds every role.
- `uv run aurelius-atlas-trace check`.
