# 2.4 Entity write REST

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-052 to DD-055, DV-20 to DV-22; relies on DD-026, DD-039, DD-043 to DD-051, DV-15, DV-16, DV-18

## Scope

The create and update endpoints of `EntityREST` under `/api/atlas/v2/entity`, on the entity store of 2.2 and
in the stored form 2.3 reads (DD-049): Atlas's `createOrUpdate`, `updateByUniqueAttributes` and
`updateEntityAttributeByGuid` of `AtlasEntityStoreV2`, with the discovery of the entities a request names
(`AtlasEntityGraphDiscoveryV2`, `IDBasedEntityResolver`, `UniqAttrBasedEntityResolver`), the comparison that
skips unchanged entities (`AtlasEntityComparator`) and the mapping of values to what is stored
(`EntityGraphMapper`).

| Endpoint                                                  | Takes                      | Answers                  |
| --------------------------------------------------------- | -------------------------- | ------------------------ |
| `POST /`                                                  | `AtlasEntityWithExtInfo`   | `EntityMutationResponse` |
| `POST bulk`                                               | `AtlasEntitiesWithExtInfo` | `EntityMutationResponse` |
| `PUT uniqueAttribute/type/{typeName}?attr:<name>=<value>` | `AtlasEntityWithExtInfo`   | `EntityMutationResponse` |
| `PUT guid/{guid}?name=<attribute>`                        | a JSON value               | `EntityMutationResponse` |

In `aurelius-atlas-core`, one module per Java class: `entity_discovery` (`EntityDiscovery`: the walk, the
references and their resolution), `entity_mapper` (`EntityMapper`: values to the stored form),
`entity_comparator` (`EntityComparator`) and `entity_writer` (`EntityWriter`: the store's write methods and
their mutation context). In `aurelius-atlas-typesystem`, the entity type's dynamic attributes (DD-026). The
server's `routes/entity` answers the endpoints. The parity harness gains `{run}`, a value unique to each run
of a scenario (DD-055).

Not in scope:

| Not delivered here                                                                                                     | Delivered by |
| ---------------------------------------------------------------------------------------------------------------------- | ------------ |
| Deleting entities; a reference an update removes is dropped, where Atlas keeps it as a deleted edge (soft delete)      | 2.5          |
| Relationships: relationship attribute values, inverse references (`inverseRef`), relationship GUIDs (DD-053)           | 3.1          |
| Deleting an owned entity whose reference an update removes; reviving a deleted owned entity                            | 3.2          |
| Classifications given with an entity (`classifications`), which are ignored                                            | 3.3          |
| Business attributes given with an entity (`businessAttributes`), which are ignored; the label endpoints                | 5.3          |
| Import (`createOrUpdateForImport`), shell entities for missing references (`create.shell.entity.for.non-existing.ref`) | 6.3          |
| Access checks (`ENTITY_CREATE`, `ENTITY_UPDATE`)                                                                       | 6.2          |

## Semantics

"Assigned" GUIDs are non-empty and do not start with `-`; "unassigned" ones start with `-`; either is valid
(`AtlasTypeUtil`). An entity read from JSON without a `guid` has a new unassigned one, `-` and a number
(`nextInternalId`). Errors name values as Java's `toString` writes them.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| EWR-01 | `guid`, `name` and `typeName` longer than 4096 characters fail with `INVALID_QUERY_PARAM_LENGTH` before anything else (`Servlets.validateQueryParamLength`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| EWR-02 | `POST /` and `POST bulk` create or update their entities (`createOrUpdate`, not partial). A request without entities fails with `INVALID_PARAMETERS` (`no entities to create/update.`), a null entity in it with `INVALID_PARAMETERS` (`found null entity`), an entity whose type is no entity type with `TYPE_NAME_INVALID` (`ENTITY`, the name)                                                                                                                                                                                                                                                                                                                                                                                                                  |
| EWR-03 | Before an entity is walked, each dynamic attribute of its type (a string attribute named by an entity type option `dynAttribute:<name>`, others ignored) is set to its template evaluated on the entity, a dynamic attribute another one's template names first: text outside braces as it is, `{attribute}` the entity's value of that attribute as Java's text, `{a.b}` the text `TEMP`. When an attribute named is null, the dynamic attribute keeps its value                                                                                                                                                                                                                                                                                                  |
| EWR-04 | The request's entities are walked, then each entity of `referredEntities` whose GUID a walked entity names, until none is left; others are ignored. Walking an entity records its GUID and visits each of its relationship attributes (from `relationshipAttributes`, else `attributes`) and its other attributes that are given: references in object id values, arrays, maps (keys and values) and structs, at any depth. A reference records its GUID when it has a valid one, else its type and unique attributes. A reference that is no object id or map, or whose map has neither a valid GUID nor a type and unique attributes, fails with `INVALID_OBJECT_ID` (the value); a struct value that is no struct or map fails with `INVALID_STRUCT_VALUE`      |
| EWR-05 | Each recorded GUID resolves to the stored entity with that GUID when it is assigned; else, when the request has an entity with that GUID, to the `ACTIVE` entity holding that entity's unique values (ENS-06); else an unassigned GUID with no entity in the request fails with `REFERENCED_ENTITY_NOT_FOUND` (the GUID), and an assigned GUID that resolves to nothing fails likewise. An unassigned GUID that resolves to nothing names an entity to create. Each reference by unique attributes resolves to the `ACTIVE` entity of its type or a sub type holding them, created in this request or stored, or fails with `REFERENCED_ENTITY_NOT_FOUND` (the object id)                                                                                          |
| EWR-06 | Each entity of the request among the recorded GUIDs, in their order, is updated when its GUID or its unique values resolved, else created; an entity named twice is handled once. A relationship attribute given in `attributes` moves to `relationshipAttributes` unless that holds it already (`compactAttributes`). An updated entity takes the stored GUID; a created one a new GUID (ENS-02). Each GUID that changes is a `guidAssignments` entry, from the request's GUID to the stored one. A full update of an incomplete entity makes it complete                                                                                                                                                                                                         |
| EWR-07 | A created or fully updated entity is checked and normalised by its type (EVL-01 to EVL-09); a partially updated one for update (EVL-03). Before that: a GUID that is not valid fails with `INVALID_OBJECT_ID` (`invalid guid <guid>`); a custom attribute key longer than 50 characters with `INVALID_CUSTOM_ATTRIBUTE_KEY_LENGTH`, one with characters other than letters, digits, `_`, `-` and CJK ideographs with `INVALID_CUSTOM_ATTRIBUTE_KEY_CHARACTERS`, a value longer than 500 with `INVALID_CUSTOM_ATTRIBUTE_VALUE`; a label longer than 50 with `INVALID_LABEL_LENGTH`, one with other characters with `INVALID_LABEL_CHARACTERS`. The type's messages, when there are any, fail the request with `INSTANCE_CRUD_INVALID_PARAMS` (the list of messages) |
| EWR-08 | An updated entity is skipped, neither written nor reported, when each attribute it gives that its type has, each relationship attribute it gives and, when given, its custom attributes equal the stored ones (`areEqualValues`, through `guidAssignments`). Labels, classifications and business attributes are not compared                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| EWR-09 | A created entity is stored `ACTIVE`, with the request's time as both times, its type's super types, `version` its own or 0, its custom attributes and its labels; `isProxy`, `provenanceType`, `homeId` and `isIncomplete` are not taken from the request. When it gives any attribute, every attribute of its type is mapped: a primitive one without a value takes its definition's `defaultValue` when there is one, else, when optional, its type's optional default (null for a string, `0`, `false` or the epoch otherwise), else its type's default                                                                                                                                                                                                         |
| EWR-10 | An updated entity maps the attributes it gives that its type has, with the defaults of EWR-09 for a null primitive one, and its custom attributes when given; its labels, `version` and other system properties stay. When it gives any attribute or relationship attribute, its `updateTime` becomes the request's time. A struct value updates the stored struct of its attribute, attribute by attribute; a null struct leaves it. An array or map of structs updates the stored struct at each index or key, and drops the others                                                                                                                                                                                                                              |
| EWR-11 | Values are stored as DD-049 holds them: a reference as the GUID it resolved to, a soft reference as `typeName:guid` from the object id given (a GUID assigned in this request for an unassigned one). Null elements of an array of primitives or structs are dropped; a null reference in an array or map fails with `INVALID_OBJECT_ID` (`null`). A `SET` array keeps its first of equal elements. A partial update of an array or map whose attribute has `isAppendOnPartialUpdate` appends to the stored elements, a map's entries replacing those of the same key. References keep the request's order (DV-21)                                                                                                                                                 |
| EWR-12 | A single reference that is set where the stored entity had none, not soft, in an entity attribute or a struct's, makes the referenced entity updated: its `updateTime` becomes the request's time, and it is reported with the operation of the request, once, unless it is created in this request or skipped (EWR-08)                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| EWR-13 | The response's `mutatedEntities` has, under `CREATE`, the header of each created entity and, under `UPDATE` (`PARTIAL_UPDATE` for a partial update), of each updated one, as written, with `classifications` (ERD-07); then each entity EWR-12 made updated, with its header without `classifications`. An entity created in the request is reported only under `CREATE`; an operation with no entity is absent, and with no entity at all `mutatedEntities` is. `guidAssignments` is always there                                                                                                                                                                                                                                                                 |
| EWR-14 | `PUT uniqueAttribute/type/{typeName}` checks the type and the `attr:` values as ERD-08 does; a body without an entity fails with `INVALID_PARAMETERS` (`no entity to update.`); no `ACTIVE` entity holding the values fails with `INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND` (the type and the values as `{name=value}`). The entity takes the found GUID and is partially updated                                                                                                                                                                                                                                                                                                                                                                                    |
| EWR-15 | `PUT guid/{guid}?name=` sets one attribute of the entity with the GUID (`INSTANCE_GUID_NOT_FOUND` when none) to the body: an attribute of its type, else its relationship attribute of that name, else `UNKNOWN_ATTRIBUTE` (the name, the type). A primitive attribute takes the body as it is; an object id attribute takes a string body as the GUID of an object id of the attribute's type, any other body as an object id; an attribute of another kind fails with `ATTRIBUTE_UPDATE_NOT_SUPPORTED` (the name, its type name). The entity is then partially updated                                                                                                                                                                                           |
| EWR-16 | A request's entities are written together, all or nothing (ENS-07). A write that loses a race with another (ENS-08) runs the whole request again, once; a second loss, or a unique value another entity holds (ENS-05), fails with `INTERNAL_ERROR` naming the cause (DV-20)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| EWR-17 | Until 3.1, a relationship attribute's value is checked, normalised and its references resolved as Atlas does, and is stored as the value of the entity's attribute of the same name when its type has one (a legacy relationship end); any other is not stored (DD-053)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/EntityREST.java`: `createOrUpdate` (both), `partialUpdateEntityByUniqueAttrs`,
  `partialUpdateEntityAttrByGuid`
- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `createOrUpdate`, `preCreateOrUpdate`,
  `updateByUniqueAttributes`, `updateEntityAttributeByGuid`, `compactAttributes`, `getResolvedEntityVertex`
- `repository/.../store/graph/v2/AtlasEntityGraphDiscoveryV2.java`, `IDBasedEntityResolver.java`,
  `UniqAttrBasedEntityResolver.java`, `repository/.../store/graph/EntityGraphDiscoveryContext.java`,
  `AtlasEntityStream.java`, `EntityMutationContext.java`
- `repository/.../store/graph/v2/AtlasEntityComparator.java`
- `repository/.../store/graph/v2/EntityGraphMapper.java`: `createVertexWithGuid`, `createStructVertex`,
  `mapAttributesAndClassifications`, `mapAttributes`, `mapRelationshipAttributes`, `mapAttribute`,
  `mapToVertexByTypeCategory`, `mapSoftRefValue`, `mapStructValue`, `mapObjectIdValue`, `mapMapValue`,
  `mapArrayValue`, `recordEntityUpdate`, `constructHeader`, `validateCustomAttributes`, `validateLabels`;
  `graph/GraphHelper.java#updateModificationMetadata`; `AtlasGraphUtilsV2.java#setProperty`,
  `getGuidByUniqueAttributes`
- `intg/.../type/AtlasEntityType.java`: `parseDynAttributeTemplates`, `templateSplit`, `reorderDynAttributes`;
  `AttributeToken`, `ConstantToken`, `DependentToken`; `intg/.../model/instance/EntityMutationResponse.java`;
  `server-api/.../RequestContext.java#recordEntityUpdate`; `intg/.../AtlasConfiguration.java` (custom
  attribute and label limits)

## Deviations

DV-20: Atlas fails a write that needs a unique value another entity holds with JanusGraph's
`SchemaViolationException`, an internal error answered with a plain-text logged id; Aurelius Atlas answers
`INTERNAL_ERROR` with Atlas's error body naming the value and its holder, and the same for a write that loses
two races (DD-052). DV-21: Atlas orders the references of an array by the hash order of their edges
(`CollectionUtils.union`); Aurelius Atlas keeps the request's order. Entities EWR-12 makes updated are
reported in the order they were reached, where Atlas uses a `HashMap`'s. DV-22: until 3.1, a relationship
attribute that is not also an attribute of the type is not stored (DD-053).

## Acceptance

- `libs/python/aurelius-atlas-typesystem/tests/` — EWR-03's templates and their order.
- `libs/python/aurelius-atlas-core/tests/` — EWR-02 to EWR-17 on the in-memory documents: discovery and
  resolution, the stored form of every kind of value on create and update, skipped entities, responses.
- `libs/python/aurelius-atlas-core/e2e/` — a create, an update and a race against the dev store.
- `apps/aurelius-atlas-server/tests/` — EWR-01 to EWR-16 over HTTP.
- `apps/aurelius-atlas-server/scenarios/entity/` — creating, reading back and updating entities, each
  endpoint's errors (DD-051, DD-055).
- `uv run aurelius-atlas-trace check`.
