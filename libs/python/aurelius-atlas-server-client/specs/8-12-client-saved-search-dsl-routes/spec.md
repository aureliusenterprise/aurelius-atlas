# 8.12 Client route coverage — saved searches and the DSL search

- **Status:** planned
- **Pull request:** —
- **Records:** DD-307 (the per-module live-check spec), DD-309 (bodies reused from
  `aurelius-atlas-model`); cites 8.4 (CL-13, the seven shipped search routes), 8.8
  (CL-60..CL-65), and the server's rules SVS, DSE.

`SearchApi` covers seven of the fifteen routes of `routes/discovery.py` (8.4,
CL-13). The eight left are the saved searches of the acting user and the DSL
search. This increment completes `AtlasClient.search` and its matrix.

## Scope

In scope: `GET /dsl` and the seven saved-search routes of `routes/discovery.py`.

Out of scope: the seven search routes of 8.4 (unchanged); the user-profile routes
behind saved searches (`__AtlasUserProfile` internals, server 4.5); server
behaviour (SVS and DSE rules stay in the server's specs, cited not restated).

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CSD-01 | `search.search_using_dsl(query=None, type_name=None, classification=None, limit=0, offset=0)` answers `GET /dsl` with those query parameters, each sent only when set (the CL-13 default-absence rule), and returns an `AtlasSearchResult` (DSE-01, DSE-02). The client validates no length locally — the server answers `INVALID_QUERY_LENGTH` / `INVALID_QUERY_PARAM_LENGTH` (CL-12 of 8.4). |
| CSD-02 | `search.add_saved_search(saved_search)` and `update_saved_search(saved_search)` post and put an `AtlasUserSavedSearch` body and return the server's saved answer (SVS-02, SVS-03). Neither pre-checks the body; the server answers `BAD_REQUEST` for a missing one (DV-110).                                                                                                                   |
| CSD-03 | `search.saved_searches(user=None)` answers `GET /saved`. A `None` answer means the server said 204 — no profile for that user — and the client returns `None` rather than an empty list (SVS-04). A `user` value travels as the `user` query parameter, and the acting user is the server's default.                                                                                           |
| CSD-04 | `search.saved_search(name, user=None)` answers `GET /saved/{name}` and returns an `AtlasUserSavedSearch` (SVS-04). `search.delete_saved_search(guid)` answers `DELETE /saved/{guid}` and returns `None` (SVS-05). The name and guid paths are separate methods because the server's verbs are asymmetric on purpose: read by name, delete by guid.                                             |
| CSD-05 | `search.execute_saved_search_by_name(name, user=None)` and `execute_saved_search_by_guid(guid)` answer the two `GET /saved/execute/...` routes and return an `AtlasSearchResult` — the saved search run, not the saved search read (SVS-06).                                                                                                                                                   |
| CSD-06 | `AtlasClient.search` keeps its seven 8.4 methods unchanged; the eight new methods join the same class (CL-13 is not edited — extended, per CLW-07's relation to CL-11).                                                                                                                                                                                                                        |

### The coverage matrix (`routes/discovery.py`, 15 routes)

| Method and path                  | Server function            | Client method                  | Rule         |
| -------------------------------- | -------------------------- | ------------------------------ | ------------ |
| `POST /basic`                    | `searchWithParameters`     | `search_with_parameters`       | CL-13 (done) |
| `GET /basic`                     | `searchUsingBasic`         | `search_using_basic`           | CL-13 (done) |
| `GET /fulltext`                  | `searchUsingFullText`      | `search_using_full_text`       | CL-13 (done) |
| `GET /quick`                     | `quickSearch` (query)      | `quick_search_using_query`     | CL-13 (done) |
| `POST /quick`                    | `quickSearch` (body)       | `quick_search`                 | CL-13 (done) |
| `GET /suggestions`               | `getSuggestions`           | `get_suggestions`              | CL-13 (done) |
| `GET /attribute`                 | `searchUsingAttribute`     | `search_using_attribute`       | CL-13 (done) |
| `GET /dsl`                       | `searchUsingDSL`           | `search_using_dsl`             | CSD-01       |
| `POST /saved`                    | `addSavedSearch`           | `add_saved_search`             | CSD-02       |
| `PUT /saved`                     | `updateSavedSearch`        | `update_saved_search`          | CSD-02       |
| `GET /saved`                     | `getSavedSearches`         | `saved_searches`               | CSD-03       |
| `GET /saved/{name}`              | `getSavedSearch`           | `saved_search`                 | CSD-04       |
| `DELETE /saved/{guid}`           | `deleteSavedSearch`        | `delete_saved_search`          | CSD-04       |
| `GET /saved/execute/{name}`      | `executeSavedSearchByName` | `execute_saved_search_by_name` | CSD-05       |
| `GET /saved/execute/guid/{guid}` | `executeSavedSearchByGuid` | `execute_saved_search_by_guid` | CSD-05       |

After this increment, `routes/discovery.py` is fully covered.

Bodies, reused whole (DD-309): `AtlasUserSavedSearch`, `AtlasSearchResult`,
`SavedSearchType`. The client imports them from `aurelius-atlas-model`'s `profile`
and `discovery` modules and defines none.

## Aurelius origin

- Apache Atlas 2.4.0 `DiscoveryREST` (the DSL search and the saved searches) and
  the Angular `DiscoveryClient` / `AtlasSearchService` in `libs/atlas/api`.
- This workspace: `routes/discovery.py` (paths, the `user` parameter, the 204
  with no profile) and the server's specs `4-3-dsl-parser` / the DSL search rules
  (DSE) and `4-5-saved-searches` (SVS-01..SVS-07) — cited, not restated.
- `aurelius-atlas-model`'s `profile` module — `AtlasUserSavedSearch` (DD-309).

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-307 and DD-309 in [8.8's
`design.md`](../8-8-client-route-coverage/design.md).

## Acceptance

- Unit: `tests/test__aurelius_atlas_server_client_saved_search.py` (new). One
  test per row naming its method and rules, on the `MockTransport` recorder.
- Unit: CSD-03's 204-to-`None` (not `[]`) gets its own test — the distinction a
  caller can get wrong silently.
- Trace: `uv run aurelius-atlas-trace check` names CSD-01..CSD-06.
- Gates: `nx test aurelius-atlas-server-client -c ci`, `ruff check`, `zensical
build --strict`.
