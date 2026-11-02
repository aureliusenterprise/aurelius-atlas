# 4.5 Saved searches and user profile

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-252, DV-110; relies on DD-244, DD-246, DD-250

A user saves basic and DSL searches under a name, reads, renames, deletes and runs them, as Atlas's
`DiscoveryREST` and `UserProfileService` answer them. Each search belongs to the user who saves it (6.1a): it
is an `__AtlasUserSavedSearch` entity owned by the user's `__AtlasUserProfile` entity, both internal types of
Atlas's base model, written and read through the generic `DataAccess` (DD-252), as the glossary's objects are.

## Scope

| Endpoint                                                        | Answers                                    |
| --------------------------------------------------------------- | ------------------------------------------ |
| `POST`, `PUT /api/atlas/v2/search/saved`                        | `AtlasUserSavedSearch`                     |
| `GET /api/atlas/v2/search/saved`                                | `AtlasUserSavedSearch[]`, or nothing (204) |
| `GET /api/atlas/v2/search/saved/{name}`                         | `AtlasUserSavedSearch`                     |
| `DELETE /api/atlas/v2/search/saved/{guid}`                      | nothing (204)                              |
| `GET /api/atlas/v2/search/saved/execute/{name}`, `/guid/{guid}` | `AtlasSearchResult`                        |

In `aurelius-atlas-model`, `profile` (`AtlasUserSavedSearch`, `AtlasUserProfile`); in `aurelius-atlas-core`,
`data_access` (`DataAccess`, its DTO registry), `user_profile_dto` (`AtlasUserProfileDTO`,
`AtlasSavedSearchDTO`), `user_profile_service` (`UserProfileService`) and the saved-search methods of
`EntityDiscoveryService`. The glossary's DTOs register with the generic `DataAccess`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                        |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SVS-01 | A saved search is its `guid`, `ownerName`, `name`, `searchType` (`BASIC`, `ADVANCED` or `BASIC_RELATIONSHIP`; `BASIC` unless named), `searchParameters` and `uiParameters`, written without nulls; it is an `__AtlasUserSavedSearch` whose `uniqueName` is `<owner>:<name>`, its parameters as JSON text    |
| SVS-02 | Saving a search makes its owner the acting user when it names none; another owner fails with `BAD_REQUEST` `invalid data`. The owner's profile, `__AtlasUserProfile` of the user's name, is created when there is none; a search of the name the owner has already fails with `SAVED_SEARCH_ALREADY_EXISTS` |
| SVS-03 | Updating a search needs its GUID (`INVALID_OBJECT_ID`); it may not change owner (`SAVED_SEARCH_CHANGE_USER`) nor take the name of another of the owner's searches (`SAVED_SEARCH_ALREADY_EXISTS`)                                                                                                           |
| SVS-04 | The acting user's searches are listed in their profile's order, nothing (204) without a profile; a search is read by name or by GUID. Naming another user (`user`), or a search of another owner, fails with `BAD_REQUEST` `invalid data`                                                                   |
| SVS-05 | Deleting a search by GUID removes it from its owner's profile; another owner's fails as SVS-04                                                                                                                                                                                                              |
| SVS-06 | Running a saved search answers as the search it saved: an `ADVANCED` one as the DSL query of its query, type and classification with its limit and offset, any other as the basic search of its parameters                                                                                                  |
| SVS-07 | Names, owners and GUIDs in a request are at most the query-parameter length, as are the parameters' type, classification and sort; a query longer than the full-text limit fails with `INVALID_QUERY_LENGTH`                                                                                                |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/DiscoveryREST.java`: the `saved` endpoints, `executeSavedSearch`, `validateUserSavedSearch`
- `repository/.../discovery/EntityDiscoveryService.java`: the saved-search methods, `checkSavedSearchOwnership`
- `repository/.../repository/userprofile/UserProfileService.java`
- `repository/.../repository/ogm/DataAccess.java`, `ogm/profiles/AtlasUserProfileDTO.java`,
  `ogm/profiles/AtlasSavedSearchDTO.java`
- `intg/.../model/profile/AtlasUserSavedSearch.java`, `AtlasUserProfile.java`
- Tests: `repository/.../userprofile/UserProfileServiceTest.java`

## Deviations

- **DV-110:** a request without a saved search, or running a search without parameters, answers `BAD_REQUEST`,
  where Atlas fails on a null.

## Acceptance

- `libs/python/aurelius-atlas-model/tests/`, `libs/python/aurelius-atlas-core/tests/` — SVS-01 to SVS-06.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/search/` — the endpoints over HTTP.
- `uv run aurelius-atlas-trace check`.
