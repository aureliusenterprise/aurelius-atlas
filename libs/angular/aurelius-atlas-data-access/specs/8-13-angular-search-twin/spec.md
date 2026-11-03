# 8.13 Angular search twin — saved searches and the DSL search

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-314; cites DD-217 (the search client lands on both sides of
  the wire), 7.3 (APC-01..APC-11), 8.12 (CSD-01..CSD-06, the Python twin), and
  the server's rules SVS and DSE.

`SearchService` answers seven of the fifteen routes of `routes/discovery.py`
(APC-11, 4.1/4.2). The lib's own rule is one typed method per endpoint the
server implements, and its AGENTS.md keeps the search wire contract in step
with its Python twin (`AtlasClient.search`, CL-13). 8.12 completed that twin
with `GET /dsl` and the seven saved-search routes; this increment lands the
same eight routes on the Angular side and closes the pair.

## Scope

In scope: `GET /dsl` and the seven saved-search routes of `routes/discovery.py`
in `SearchService`, the saved-search DTOs in `atlas-profile.ts`, and their
Vitest specs.

Out of scope: the seven search routes of APC-11 (unchanged); the user-profile
routes behind saved searches (`AtlasUserProfile`, server 4.5 — the Python twin
skips them too); any screen that calls the new methods (7.4a/7.4b remain the
search UI); entity, relationship, and glossary Angular clients (their Python
twins' series grew the server surface; this increment is the search pair only).

## Semantics

Each rule's id is named in its Vitest `it()` title, the APC family's convention
(the trace check reads pytest files only; the eleven APC rules are already in
its gap list).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ACS-01 | `searchUsingDsl(query)` answers `GET /dsl` with the parameters `query`, `typeName`, `classification`, `limit`, `offset`, each sent only when set — the GET default-absence rule of APC-11 — and answers an `AtlasSearchResult` (DSE-01, DSE-02). The client checks no length; the server answers `INVALID_QUERY_LENGTH` and `INVALID_QUERY_PARAM_LENGTH` through the typed Atlas error (APC-04).  |
| ACS-02 | `addSavedSearch(savedSearch)` and `updateSavedSearch(savedSearch)` post and put an `AtlasUserSavedSearch` body (SVS-02, SVS-03) and answer the server's saved search. Neither pre-checks the body; the server answers `BAD_REQUEST` for a missing one (DV-110).                                                                                                                                   |
| ACS-03 | `getSavedSearches(user?)` answers `GET /saved` and is typed `Observable<AtlasUserSavedSearch[] \| null>`: the server's 204 (no profile for that user) is observable in the body as `null`, folded by no map (SVS-04, DD-314). A `user` value travels as the `user` query parameter; the acting user is the server's default.                                                                      |
| ACS-04 | `getSavedSearch(name, user?)` answers `GET /saved/{name}` and answers an `AtlasUserSavedSearch` (SVS-04). `deleteSavedSearch(guid)` answers `DELETE /saved/{guid}` and answers `void` (SVS-05). The name rides the path percent-encoded, as every path segment in this lib (APC-01). Read by name, delete by guid: the server's verbs are asymmetric on purpose, and the methods keep that shape. |
| ACS-05 | `executeSavedSearchByName(name, user?)` and `executeSavedSearchByGuid(guid)` answer the two `GET /saved/execute/...` routes and answer an `AtlasSearchResult` — the saved search run, not the saved search read (SVS-06). `executeSavedSearchByGuid` takes no `user`: the server's route takes none.                                                                                              |
| ACS-06 | The seven methods of APC-11 keep their names, paths, and behaviour. The eight new methods join the same class; APC-11 is extended, not edited (the relation 8.11's CLW-07 set for CL-11).                                                                                                                                                                                                         |

### The coverage matrix (`routes/discovery.py`, 15 routes)

Open means no client method yet. All 15 are covered as of this increment.

| Method and path                  | Server function            | Client method                        | Rule        |
| -------------------------------- | -------------------------- | ------------------------------------ | ----------- |
| `POST /basic`                    | `searchWithParameters`     | `searchWithParameters`               | APC-11 done |
| `GET /basic`                     | `searchUsingBasic`         | `searchUsingBasic`                   | APC-11 done |
| `GET /fulltext`                  | `searchUsingFullText`      | `searchUsingFullText`                | APC-11 done |
| `GET /quick`                     | `quickSearch` (query)      | `quickSearchUsingQuery`              | APC-11 done |
| `POST /quick`                    | `quickSearch` (body)       | `quickSearch`                        | APC-11 done |
| `GET /suggestions`               | `getSuggestions`           | `getSuggestions`                     | APC-11 done |
| `GET /attribute`                 | `searchUsingAttribute`     | `searchUsingAttribute`               | APC-11 done |
| `GET /dsl`                       | `searchUsingDSL`           | `searchUsingDsl` (covered)           | ACS-01      |
| `POST /saved`                    | `addSavedSearch`           | `addSavedSearch` (covered)           | ACS-02      |
| `PUT /saved`                     | `updateSavedSearch`        | `updateSavedSearch` (covered)        | ACS-02      |
| `GET /saved`                     | `getSavedSearches`         | `getSavedSearches` (covered)         | ACS-03      |
| `GET /saved/{name}`              | `getSavedSearch`           | `getSavedSearch` (covered)           | ACS-04      |
| `DELETE /saved/{guid}`           | `deleteSavedSearch`        | `deleteSavedSearch` (covered)        | ACS-04      |
| `GET /saved/execute/{name}`      | `executeSavedSearchByName` | `executeSavedSearchByName` (covered) | ACS-05      |
| `GET /saved/execute/guid/{guid}` | `executeSavedSearchByGuid` | `executeSavedSearchByGuid` (covered) | ACS-05      |

After this increment, `routes/discovery.py` is fully covered on both sides of
the wire.

Bodies, hand-mirrored (APC-03): `AtlasUserSavedSearch` and `SavedSearchType` in
`atlas-profile.ts`, from `aurelius_atlas_model/profile.py` (SVS-01); the
`searchParameters` field reuses the `SearchParameters` DTO of `atlas-search.ts`
unchanged.

## Aurelius origin

- Apache Atlas 2.4.0 `DiscoveryREST` (the DSL search and the saved searches) and
  the `DiscoveryClient` / saved-search services in `libs/atlas/api` of the
  Aurelius product.
- This workspace: `routes/discovery.py` (paths, the `user` parameter, the 204
  with no profile) and the server's specs — `libs/python/aurelius-atlas-core/specs/4-4-dsl-entities/`
  (DSE) and `libs/python/aurelius-atlas-core/specs/4-5-saved-searches/`
  (SVS-01..SVS-07) — cited, not restated. `AtlasClient.search` (CL-13, CSD-01..CSD-06 in
  `libs/python/aurelius-atlas-server-client/specs/8-12-client-saved-search-dsl-routes/`)
  is the twin this mirrors; the method names are its snake_case names in
  camelCase.

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-217 (both-sides landing) and
DD-314 (the 204 stays observable) in [`design.md`](./design.md). Against the
Python twin, one shape differs on purpose: CSD-03 returns `None` for the 204 of
a missing profile, while ACS-03 types the body `AtlasUserSavedSearch[] | null`
because an `Observable` has no separate no-answer channel (DD-314).

## Acceptance

- Unit: `src/lib/atlas/search.service.spec.ts` grows one `it()` per row naming
  its method, its URL, its body or parameters, and the rule ids (APC-10's
  pattern, extended; Vitest `HttpTestingController`).
- Unit: ACS-03's null-vs-`[]` gets its own `it()` — the distinction a caller can
  get wrong silently, the twin of CSD-03's dedicated test.
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`.
