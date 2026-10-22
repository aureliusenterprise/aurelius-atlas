# 2.3 Entity read REST

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-049 to DD-051, DV-17 to DV-19; relies on DD-039, DD-040, DD-043 to DD-047, DV-15

## Scope

The read endpoints of `EntityREST` under `/api/atlas/v2/entity`, on the entity store of 2.2: Atlas's
`EntityGraphRetriever` and the read methods of `AtlasEntityStoreV2`.

| Endpoint                                                           | Answers                    |
| ------------------------------------------------------------------ | -------------------------- |
| `GET guid/{guid}`                                                  | `AtlasEntityWithExtInfo`   |
| `GET guid/{guid}/header`                                           | `AtlasEntityHeader`        |
| `GET uniqueAttribute/type/{typeName}?attr:<name>=<value>`          | `AtlasEntityWithExtInfo`   |
| `GET uniqueAttribute/type/{typeName}/header?attr:<name>=<value>`   | `AtlasEntityHeader`        |
| `GET bulk/uniqueAttribute/type/{typeName}?attr_<n>:<name>=<value>` | `AtlasEntitiesWithExtInfo` |
| `GET bulk?guid=<guid>&guid=…`                                      | `AtlasEntitiesWithExtInfo` |

In `aurelius-atlas-core`, `entity_retriever` (`EntityRetriever`) builds entities and headers from stored ones;
the server's `routes/entity` answers the endpoints. `StoredEntity` gains `isProxy`, which Atlas stores and
reads back.

Not in scope:

| Not delivered here                                                                                     | Delivered by |
| ------------------------------------------------------------------------------------------------------ | ------------ |
| Creating and updating entities over REST, and scenarios that create what they read (DD-051)            | 2.4          |
| Relationship attribute values (`relationshipAttributes` hold none until relationships are stored)      | 3.1          |
| Classifications of an entity (`classifications`, `classificationNames`), `guid/{guid}/classifications` | 3.3          |
| `bulk/headers` (headers by classification update time)                                                 | 3.4          |
| Audit events (`{guid}/audit`)                                                                          | 3.5          |
| Meanings (glossary terms) and business attributes of an entity                                         | 5.2, 5.3     |
| Access checks (`ENTITY_READ`)                                                                          | 6.2          |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ERD-01 | A GUID or type name in the path, and each `guid` of `bulk`, longer than 4096 characters fails with `INVALID_QUERY_PARAM_LENGTH` (400) before anything is read (`Servlets.validateQueryParamLength`)                                                                                                                                                                                                                                                                                                                                                                                                             |
| ERD-02 | `guid/{guid}` answers the entity with that GUID, in any state, with its extended info; an unknown GUID fails with `INSTANCE_GUID_NOT_FOUND` (404). `bulk` answers the entities of every `guid` given, in order, sharing one `referredEntities`; one unknown GUID fails the request, and no `guid` fails with `INSTANCE_GUID_NOT_FOUND` naming `[]`                                                                                                                                                                                                                                                              |
| ERD-03 | An entity has its system properties as stored: `guid`, `typeName`, `status`, `version`, `createTime`, `updateTime`, `proxy`, `isIncomplete`, `provenanceType`, and `homeId`, `createdBy`, `updatedBy` and `customAttributes` when it has them; `labels` always, empty or not. `classifications`, `meanings`, `businessAttributes` and `pendingTasks` are left out (3.3, 5.2, 5.3)                                                                                                                                                                                                                               |
| ERD-04 | `attributes` holds every attribute of the entity's type, inherited ones included, null when the entity has no value (`mapAttributes`). A date reads as epoch milliseconds, an enum as its value, a struct as an `AtlasStruct` with every attribute of its type, arrays and maps as their elements read so (DD-049)                                                                                                                                                                                                                                                                                              |
| ERD-05 | An attribute that refers to entities reads each as an object id: GUID, type name and the referenced entity's unique attribute values that are not null. An owned reference (`ownedRef`) reads as GUID and type name only and adds the referenced entity to `referredEntities`: in full, or with `minExtInfo=true` with its system properties and those of its type's minimal-info attributes that have a value. An entity is built once per response, the first way it is reached. A reference to an entity that does not exist, and a null element of an array or map of references, reads as nothing (DD-049) |
| ERD-06 | Unless `ignoreRelationships=true`, `relationshipAttributes` names every relationship attribute of the type: null for a `SINGLE` end and `[]` for a `LIST` or `SET` end, as an entity without relationships reads (DD-050). `referredEntities` never holds the entities the response answers with (`compact`)                                                                                                                                                                                                                                                                                                    |
| ERD-07 | `guid/{guid}/header` answers the entity's header: `typeName`, `guid`, `status`, `isIncomplete`, `labels`, `classificationNames` and `classifications` empty, `meanings` and `meaningNames` empty, each header attribute (the unique ones, `name`, `description`, `owner`, `createTime`) with its value or `""`, and `displayText`: the type's display text attribute, else `name`, `displayName`, `qualifiedName`, when one has a value (`mapVertexToAtlasEntityHeader`). The header by unique attributes is the same without `classifications`                                                                 |
| ERD-08 | The unique attributes of `uniqueAttribute` reads are the query parameters `attr:<name>`, each with its first value; of `bulk/uniqueAttribute`, the parameters `attr_<n>:<name>`, one set per `<n>`, each with its first value; an `attr_` parameter without `:` is ignored. An unknown entity type fails with `TYPE_NAME_INVALID` (400, `ENTITY`), no attribute or one that is not a unique attribute of the type, system attributes included, with `ATTRIBUTE_UNIQUE_INVALID` (400); the bulk read checks every set before reading any, and answers `{}` for none                                              |
| ERD-09 | A read by unique attributes finds the `ACTIVE` entity of the type or of its first sub type holding the values, each normalised by its attribute's type (ENS-06); none fails with `INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND` (404) naming the type and the attributes as `{name=value}`. A unique system attribute (`__guid`) finds nothing (DV-17). The bulk read answers the sets in the order their indices first appear (DV-19) and leaves out those that find none                                                                                                                                            |
| ERD-10 | Every endpoint reads from a registry no older than the refresh interval (TDS-13) and answers Atlas JSON (SRV-04, SRV-05)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/EntityREST.java`: `getById`, `getHeaderById`, `getByUniqueAttributes`,
  `getEntityHeaderByUniqueAttributes`, `getEntitiesByUniqueAttributes`, `getByGuids`, `getAttributes`,
  `getAttributesList`, `validateUniqueAttribute`, `ensureEntityType`
- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `getById`, `getHeaderById`, `getByIds`,
  `getByUniqueAttributes`, `getEntityHeaderByUniqueAttributes`, `getEntitiesByUniqueAttributes`
- `repository/.../store/graph/v2/EntityGraphRetriever.java`: `mapVertexToAtlasEntity`, `mapVertexToAtlasEntityMin`,
  `mapSystemAttributes`, `mapAttributes`, `mapVertexToAttribute`, `mapVertexToPrimitive`, `mapVertexToObjectId`,
  `toAtlasObjectId`, `mapRelationshipAttributes`, `mapVertexToAtlasEntityHeader`, `getDisplayText`
- `repository/.../graph/GraphHelper.java`: `getLabels`, `getCustomAttributes`, `getRelationshipTypeName`;
  `AtlasGraphUtilsV2.getVertexByUniqueAttributes`

## Deviations

- DV-17: a read by a unique system attribute alone finds nothing; Atlas answers an arbitrary entity of the type.
- DV-18: until 3.1, a reference that is also a relationship end is not in `relationshipAttributes` (DD-050).
- DV-19: `bulk/uniqueAttribute` answers in query order, not Java's hash order.

DV-15 and DV-16 hold for every entity.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — ERD-03 to ERD-07 and ERD-09 on entities seeded through the store.
- `apps/aurelius-atlas-server/tests/` — every endpoint on entities seeded through the store (DD-051).
- `apps/aurelius-atlas-server/scenarios/entity/` — what needs no entity: unknown GUIDs and types, invalid and
  missing unique attributes, values found by nothing. 2.4 adds scenarios that create the entities they read.
- `uv run aurelius-atlas-trace check`.
