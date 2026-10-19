# 1.6 Types REST

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-034, DD-035, DV-09, DV-10; relies on DD-028, DD-029, DD-024, DV-04, DV-06, DV-07

## Scope

The 26 endpoints of `TypesREST` under `/api/atlas/v2/types`, on the typedef store of 1.4 and the models of 1.5:

| Endpoint | Store operation |
| --- | --- |
| `GET typedef/name/{name}`, `GET typedef/guid/{guid}` | `getByName`, `getByGuid` |
| `GET {kind}def/name/{name}`, `GET {kind}def/guid/{guid}` for `enum`, `struct`, `classification`, `entity`, `relationship`, `businessmetadata` | `get{Kind}DefByName`, `get{Kind}DefByGuid` |
| `GET typedefs`, `GET typedefs/headers` | `searchTypesDef` |
| `POST typedefs`, `PUT typedefs`, `DELETE typedefs` | `createTypesDef`, `updateTypesDef`, `deleteTypesDef` |
| `DELETE typedef/name/{typeName}` | `deleteTypeByName` |

The checks of the writes are 1.4's (TDS-01 to TDS-11); this increment adds the reads, the search filter and the HTTP side.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| `TYPE_READ`, `TYPE_CREATE`, `TYPE_UPDATE` and `TYPE_DELETE` checks and filtering of reads | 6.2 |
| `createdBy` and `updatedBy` of the logged-in user | 6.1 |
| Refusing to delete a type that entities use | 2.2 (DD-030) |
| The legacy `TypesResource` (`/api/atlas/types`) | not ported |

## Semantics

| Id | Rule |
| --- | --- |
| TYR-01 | `GET typedef/name/{name}` answers the registered definition of that name, of any kind, as the registry holds it: with the `subTypes`, `relationshipAttributeDefs` and `businessAttributeDefs` resolution adds. A blank name fails with `TYPE_NAME_INVALID` (400), an unknown one with `TYPE_NAME_NOT_FOUND` (404), and a built-in, array or map type with `SYSTEM_TYPE` (400) naming its category (`PRIMITIVE`, `OBJECT_ID_TYPE`, `ARRAY`, `MAP`) |
| TYR-02 | `GET typedef/guid/{guid}` answers the definition with that GUID; a blank or unknown GUID fails with `TYPE_GUID_NOT_FOUND` (404) |
| TYR-03 | `GET {kind}def/name/{name}` and `GET {kind}def/guid/{guid}` answer the definition of that kind; a name or GUID that no definition of that kind has, including one of another kind, fails with `TYPE_NAME_NOT_FOUND` or `TYPE_GUID_NOT_FOUND` (404) |
| TYR-04 | On every `GET` by name or GUID, a name or GUID longer than 4096 characters fails with `INVALID_QUERY_PARAM_LENGTH` (400), naming `name` or `guid`, before the lookup |
| TYR-05 | `GET typedefs` answers every registered definition the filter keeps, as the registry holds them, in an `AtlasTypesDef`: enums, structs, classifications, entities, relationships, business metadata, each list sorted by name (DD-034, DV-09) |
| TYR-06 | The filter is the request's query parameters, each with its first value, with case-sensitive names: `type` keeps one kind (`CLASS` or `ENTITY`, `TRAIT` or `CLASSIFICATION`, `STRUCT`, `ENUM`, `RELATIONSHIP`, `BUSINESS_METADATA`, ignoring case; any other value keeps nothing); `name` the definition of that name; `servicetype` those of that service type; `supertype` the entity and classification types with it among all their super types; `notsupertype`, `notservicetype` and `notname` the others. A blank value filters nothing; other parameters are ignored |
| TYR-07 | `excludeInternalTypesAndReferences=true`, name and value ignoring case, adds `notname=__internal` and `notsupertype=__internal`. A `notname` given as well also applies; of two `notsupertype` values, the one first in the request applies (DV-09) |
| TYR-08 | `GET typedefs/headers` answers the header (`guid`, `name`, `category`, `serviceType`) of each definition `GET typedefs` would answer with the same filter, in its order |
| TYR-09 | `POST typedefs` creates (TDS-01 to TDS-06, TDS-10) and `PUT typedefs` updates (TDS-07, TDS-08, TDS-10) the definitions of the body; both answer 200 with the definitions as stored |
| TYR-10 | `DELETE typedefs` deletes the definitions of the body (TDS-09) and `DELETE typedef/name/{typeName}` the named one (TDS-09: blank `TYPE_NAME_INVALID`, unknown `TYPE_NAME_NOT_FOUND`, built-in `SYSTEM_TYPE`); both answer 204 with no body |
| TYR-11 | A write body that is not JSON, or not an `AtlasTypesDef`, fails with `BAD_REQUEST` (400) and Atlas's error body; unknown fields are ignored (DV-10) |
| TYR-12 | Every endpoint answers from a registry no older than `AURELIUS_ATLAS_SERVER_TYPEDEF_REFRESH_SECONDS` (TDS-13); responses are Atlas JSON (TDM-02) as `application/json; charset=UTF-8`, and errors Atlas's error body (SRV-04) |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/src/main/java/org/apache/atlas/web/rest/TypesREST.java`: every endpoint, `getSearchFilter`
- `webapp/.../web/util/Servlets.java`: `validateQueryParamLength`; `intg/.../AtlasConfiguration.java`: `QUERY_PARAM_MAX_LENGTH` (4096)
- `repository/.../store/graph/AtlasTypeDefGraphStore.java`: `getByName`, `getByGuid`, `get*DefByName`, `get*DefByGuid`, `getTypeDefFromTypeWithNoAuthz`, `searchTypesDef`
- `repository/.../repository/util/FilterUtil.java`: `getPredicateFromSearchFilter`, `addParamsToHideInternalType`
- `intg/.../model/SearchFilter.java`: the parameter names; `intg/.../type/AtlasTypeUtil.java`: `toTypeDefHeader`
- tests: `webapp/src/test/java/org/apache/atlas/web/integration/TypedefsJerseyResourceIT.java`, `webapp/src/test/java/org/apache/atlas/web/adapters/TypeDefsRESTTest.java`

## Deviations

DV-09: Atlas lists definitions in the iteration order of its registry's hash maps, and applies the `notsupertype` value that comes first in its request parameters' hash order; Aurelius Atlas sorts each list by name and takes the request's order. DV-10: Atlas leaves a body it cannot read to Jersey's JSON provider, whose answer its source and tests do not state; Aurelius Atlas answers `BAD_REQUEST`. Authorization is not checked until 6.2, as DV-04 says for every endpoint.

## Acceptance

- `apps/aurelius-atlas-server/scenarios/types/` — one or more parity scenarios per endpoint, each citing `TypesREST`, the store and Atlas's tests; each creates the types it needs, named `scenario_…`, and deletes them at its end (DD-035). They run in process (`tests/`) and against the image on the dev store (`e2e/`).
- `libs/python/aurelius-atlas-core/tests/` — the reads and the filter (TYR-01 to TYR-08) on the in-memory document.
- `apps/aurelius-atlas-server/tests/` — the HTTP side (TYR-04, TYR-09 to TYR-12).
- `uv run aurelius-atlas-trace check`.
