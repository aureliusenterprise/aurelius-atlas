# 3.1a Relationship instances

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-061 to DD-063, DV-28 to DV-30; relies on DD-043 to DD-048, DD-056 to DD-059

The first part of increment 3.1 (3.1b brings relationship attributes to entity reads, writes and deletes):
relationship instances themselves, through `RelationshipREST`.

## Scope

| Endpoint                                                   | Takes               | Answers                        |
| ---------------------------------------------------------- | ------------------- | ------------------------------ |
| `POST /api/atlas/v2/relationship`                          | `AtlasRelationship` | `AtlasRelationship`            |
| `PUT /api/atlas/v2/relationship`                           | `AtlasRelationship` | `AtlasRelationship`            |
| `GET /api/atlas/v2/relationship/guid/{guid}?extendedInfo=` | –                   | `AtlasRelationshipWithExtInfo` |
| `DELETE /api/atlas/v2/relationship/guid/{guid}`            | –                   | nothing (`204`)                |

In `aurelius-atlas-model`, `AtlasRelationship` and `AtlasRelationshipWithExtInfo`; in `aurelius-atlas-typesystem`,
the relationship type's value side, which 2.1c left out. In `aurelius-atlas-core`, `stored_relationship`
(`StoredRelationship`) and `relationship_store` (`RelationshipStore`, `AtlasRelationshipStoreV2`); relationships
are documents of their own index, and both end entities list their GUIDs (DD-061). The entity store writes
relationships with entities, all or nothing; deleting an entity deletes its relationships (DD-062); a type with
relationship instances is in use. The server's `routes/relationship` answers the endpoints.

Not in scope:

| Not delivered here                                                                                              | Delivered by |
| --------------------------------------------------------------------------------------------------------------- | ------------ |
| Relationship attributes of entities: `relationshipAttributes` in reads and writes, legacy ends as relationships | 3.1b         |
| Composition cascades through relationships                                                                      | 3.2          |
| Classifications propagated over relationships; `propagatedClassifications`, blocked ones                        | 3.4          |
| Access checks (`RELATIONSHIP_ADD`, `RELATIONSHIP_UPDATE`, `RELATIONSHIP_REMOVE`)                                | 6.2          |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REL-01 | `AtlasRelationship` reads and writes Atlas's JSON: `guid`, `homeId`, `provenanceType`, `end1`, `end2`, `label`, `propagateTags`, `status`, `createdBy`, `updatedBy`, `createTime`, `updateTime`, `version`, `propagatedClassifications`, `blockedPropagatedClassifications`, `typeName`, `attributes`. Read without them, `guid` is a new temporary GUID, `provenanceType` and `version` are 0, `propagateTags` and `status` null (`init()`). `AtlasRelationshipWithExtInfo` holds `relationship` and `referredEntities`, headers by GUID                                                                                                                                                                                                                              |
| REL-02 | A relationship type takes an `AtlasRelationship`, or null; anything else is invalid. With both ends, a relationship is valid when both ends name a type, each the end type's or a sub type's, and its attributes are valid for the struct side; else when both ends have a GUID; without both ends it is invalid. The same holds for update. Two relationships are equal when both are null, or their attributes, GUIDs, ends, labels, `propagateTags` and statuses are                                                                                                                                                                                                                                                                                                |
| REL-03 | `guid` longer than 4096 characters fails with `INVALID_QUERY_PARAM_LENGTH`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| REL-04 | `POST` finds each end by its GUID, in any state, else by its type and unique attributes (ENS-06). It fails with `INVALID_VALUE` (`unknown relationship type'<name>'`) for an unknown type; `RELATIONSHIP_END_IS_NULL` (the type's end 1, then end 2 type) for an end not found (DV-28); `INVALID_RELATIONSHIP_END_TYPE` (the type, its end 2 type, end 1's type) unless end 1 and end 2 are of the type's ends' types in either order; `INVALID_PROPAGATION_TYPE` (given, type name, type's) for a `propagateTags` other than `NONE` the type's does not allow; `RELATIONSHIP_CRUD_INVALID_PARAMS` with the struct side's messages; `RELATIONSHIP_ALREADY_EXISTS` (type, end 1 GUID, end 2 GUID) when one with the same label exists from end 1 to end 2, in any state |
| REL-05 | A created relationship has the given GUID when it is assigned, else a new one (ENS-02); status `ACTIVE`; both times the request's; `version` the given or 0; the given `homeId` and `provenanceType`; the label of end 1's relationship attribute, else the type's; the type's `propagateTags`, swapped `ONE_TO_TWO`/`TWO_TO_ONE` when end 1 is of the type's end 2 type; each attribute of the type with its given value. The end entities are not changed but for listing it (DD-061)                                                                                                                                                                                                                                                                                |
| REL-06 | A relationship is answered as `mapEdgeToAtlasRelationship` maps an edge: its system fields, `end1` and `end2` as object ids with each end's GUID, type and unique attribute values, `label`, `propagateTags`, `propagatedClassifications` and `blockedPropagatedClassifications` empty until 3.4, and every attribute of its type, null when it has none. `GET` without `extendedInfo=true` answers it alone, with it also each end's header in `referredEntities`. An unknown GUID fails with `RELATIONSHIP_GUID_NOT_FOUND`                                                                                                                                                                                                                                           |
| REL-07 | `PUT` fails with `RELATIONSHIP_GUID_NOT_FOUND` for no or an unknown GUID; `RELATIONSHIP_UPDATE_TYPE_CHANGE_NOT_ALLOWED` (GUID, stored type, given) for another type name ignoring case; `RELATIONSHIP_UPDATE_END_CHANGE_NOT_ALLOWED` (type, GUID, stored end GUID, given end GUID) for an end whose GUID, or the entity its unique attributes find, is another; an end given by unique attributes alone thus always fails, as Atlas compares the given GUID. It then checks as REL-04 does, sets the given `propagateTags` when it differs (DV-29), and each attribute of the type to its given value, or, when not given, to its non-empty default. Times, users and version stay                                                                                     |
| REL-08 | `DELETE` fails with `RELATIONSHIP_GUID_NOT_FOUND` for an unknown GUID and `RELATIONSHIP_ALREADY_DELETED` for a `DELETED` one. A soft delete sets status `DELETED` and its `updateTime` and `updatedBy`; a hard delete removes it (EDL-04). It answers `204`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| REL-09 | Deleting an entity softly also soft-deletes its `ACTIVE` relationships in which it is end 2 (Atlas's incoming edges); a hard delete or a purge removes every relationship it is an end of, and drops them from the other end's list (DD-062). The other end is not otherwise changed                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| REL-10 | A relationship type is in use while a relationship of it exists, in any state: the typedef store refuses to delete it (`TYPE_HAS_REFERENCES`, `relationshipTypeHasInstanceEdges`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/RelationshipREST.java`
- `repository/.../store/graph/v2/AtlasRelationshipStoreV2.java`: `create`, `update`, `getById`,
  `getExtInfoById`, `deleteById`, `createRelationship`, `updateRelationship`, `validateRelationship`,
  `getVertexFromEndPoint`, `getRelationshipTagPropagation`, `getRelationshipEdgeLabel`
- `repository/.../store/graph/v2/EntityGraphRetriever.java#mapEdgeToAtlasRelationship`,
  `repository/.../graph/GraphHelper.java#addEdge`
- `repository/.../store/graph/v1/DeleteHandlerV1.java`: `deleteRelationships`, `deleteVertex`,
  `updateTagPropagations`; `AtlasRelationshipDefStoreV2#deleteByName`
- `intg/.../model/instance/AtlasRelationship.java`, `intg/.../type/AtlasRelationshipType.java` (value side)

## Deviations

DV-28: a relationship without `end1` or `end2` fails in Atlas with a `NullPointerException`; Aurelius Atlas
answers `RELATIONSHIP_END_IS_NULL`. DV-29: an update without `propagateTags` fails in Atlas with a
`NullPointerException` (`updateTagPropagations` writes the null's name); Aurelius Atlas keeps the stored one.
DV-30: Atlas's request to create relationships with one entity serialises on nothing but the graph; Aurelius
Atlas rewrites both ends, so writers relating many entities to one popular entity retry more often (DD-061,
DD-052).

## Acceptance

- `libs/python/aurelius-atlas-model/tests/instance/`, `libs/python/aurelius-atlas-typesystem/tests/values/` —
  REL-01, REL-02.
- `libs/python/aurelius-atlas-core/tests/` — REL-04 to REL-10 on the in-memory documents.
- `libs/python/aurelius-atlas-core/e2e/` — relationships written, read and deleted with entities on the dev store.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/relationship/` — REL-03 to REL-08.
- `uv run aurelius-atlas-trace check`.
