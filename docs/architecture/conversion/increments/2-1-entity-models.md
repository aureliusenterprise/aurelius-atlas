# 2.1a Entity models

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-037, DD-038; relies on DD-002, DD-020, DD-021, DD-022, DD-025

Increment 2.1 of the roadmap is split in two, each within the size limit of ADR 051: 2.1a, this
specification, ports the entity models; 2.1b (`2-1-value-types.md`) and 2.1c (`2-1-entity-validation.md`) port
the value side of the types that validates and normalises them (DD-025).

## Scope

The data shapes of Atlas entities and their parts, in `aurelius-atlas-model` (package
`aurelius_atlas_model.instance`, one module per Java class, DD-037):

| Module                     | Java class (`org.apache.atlas.model`)           |
| -------------------------- | ----------------------------------------------- |
| `struct`                   | `instance.AtlasStruct`                          |
| `entity`                   | `instance.AtlasEntity`                          |
| `entity_status`            | `instance.AtlasEntity.Status`                   |
| `entity_ext_info`          | `instance.AtlasEntity.AtlasEntityExtInfo`       |
| `entity_with_ext_info`     | `instance.AtlasEntity.AtlasEntityWithExtInfo`   |
| `entities_with_ext_info`   | `instance.AtlasEntity.AtlasEntitiesWithExtInfo` |
| `object_id`                | `instance.AtlasObjectId`                        |
| `related_object_id`        | `instance.AtlasRelatedObjectId`                 |
| `relationship_status`      | `instance.AtlasRelationship.Status`             |
| `classification`           | `instance.AtlasClassification`                  |
| `time_boundary`            | `TimeBoundary`                                  |
| `entity_header`            | `instance.AtlasEntityHeader`                    |
| `entity_headers`           | `instance.AtlasEntityHeaders`                   |
| `entity_operation`         | `instance.EntityMutations.EntityOperation`      |
| `entity_mutation_response` | `instance.EntityMutationResponse`               |
| `term_assignment_header`   | `glossary.relations.AtlasTermAssignmentHeader`  |
| `term_assignment_status`   | `glossary.enums.AtlasTermAssignmentStatus`      |

The JSON conventions the typedef models already follow (`AtlasModel`, the timestamp, Java boolean and set
types) move from `typedef` to a shared `aurelius_atlas_model.base`, which both packages import.

No endpoint changes; nothing uses the models yet.

Not in scope:

| Not delivered here                                                                            | Delivered by |
| --------------------------------------------------------------------------------------------- | ------------ |
| Validating and normalising attribute values against their types; default values; equal values | 2.1b         |
| Exact decimals in attribute values (`USE_BIG_DECIMAL_FOR_FLOATS`, DD-038)                     | 2.1b         |
| The paged lists built on `PList` (`AtlasEntities`, `AtlasClassifications`, …)                 | where used   |
| `AtlasRelationship` and `AtlasRelationshipHeader`                                             | 3.1          |
| `ClassificationAssociateRequest`                                                              | 3.3          |
| `EntityMutations` and `EntityMutation`: no getter, so never on the REST API                   | not ported   |
| `AtlasCheckStateRequest`, `AtlasCheckStateResult`, `GuidMapping`                              | not planned  |

## Semantics

As in 1.1, "reading" is what Atlas's Jackson 2.12.7 mapper does with a REST request body, and "writing" is
what it puts in a response. Jackson builds each model with its no-argument constructor, then calls the
setter of each property in the order of the JSON; it writes each public getter, including a `Boolean`
`isXxx()` getter, as property `xxx`.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ENT-01 | Every model reads and writes as the typedef models do: Java getter names (TDM-01), null fields left out and empty collections kept (TDM-02), unknown fields ignored (TDM-03), scalars coerced as Jackson coerces them (TDM-15); except the term assignment header (ENT-15)                                                                                                                                                                                                                                                |
| ENT-02 | A struct has `typeName` and `attributes`. Attribute values are JSON values, kept as read: a null value stays in the map and is written. `attributes` that is missing stays null and is not written                                                                                                                                                                                                                                                                                                                        |
| ENT-03 | A struct tells whether it has an attribute, gets, sets and removes one by exact name; setting one on a struct without attributes creates the map                                                                                                                                                                                                                                                                                                                                                                          |
| ENT-04 | An entity read without them has a new temporary GUID, `-` followed by digits, never the same twice in a process; `isProxy` and `isIncomplete` false; `provenanceType` and `version` 0; `status` null (`init()` clears the field's `ACTIVE`). A field given as null stays null                                                                                                                                                                                                                                             |
| ENT-05 | An entity reads and writes `guid`, `homeId`, `isIncomplete`, `provenanceType`, `status`, `createdBy`, `updatedBy`, `createTime`, `updateTime`, `version`, `relationshipAttributes`, `classifications`, `meanings`, `customAttributes`, `businessAttributes`, `labels` and `pendingTasks`. It reads `isProxy` and writes it as `proxy`, as Jackson names the `Boolean isProxy()` getter                                                                                                                                    |
| ENT-06 | `createTime` and `updateTime` are written as milliseconds since the epoch and read from such a number or an ISO-8601 date-time string, as TDM-05                                                                                                                                                                                                                                                                                                                                                                          |
| ENT-07 | `labels` and `pendingTasks` hold each value once, in first-seen order (DD-021), and may be null                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ENT-08 | An entity gets, sets and tells whether it has a relationship attribute; gets and sets a business attribute by business metadata and attribute name, creating the maps it needs; appends classifications and meanings, creating the list                                                                                                                                                                                                                                                                                   |
| ENT-09 | Entity statuses (`ACTIVE`, `DELETED`, `PURGED`), relationship statuses (`ACTIVE`, `DELETED`), entity operations (`CREATE`, `UPDATE`, `PARTIAL_UPDATE`, `DELETE`, `PURGE`) and term assignment statuses (`DISCOVERED` to `OTHER`) are read and written by their Java names, with case; any other value is rejected                                                                                                                                                                                                         |
| ENT-10 | Extended info maps GUIDs to `referredEntities`; it adds (an entity without a GUID is not added), gets, removes and finds a referred entity, and moves one to a new GUID. With one entity (`entity`) or a list (`entities`), finding by GUID also finds those, and compacting removes them from the referred entities                                                                                                                                                                                                      |
| ENT-11 | An object id has `guid`, `typeName` and `uniqueAttributes`. Two object ids are equal by GUID when either has a non-empty one, otherwise by type name and unique attributes                                                                                                                                                                                                                                                                                                                                                |
| ENT-12 | A related object id adds `entityStatus`, `displayText`, `relationshipType`, `relationshipGuid`, `relationshipStatus`, `relationshipAttributes` (a struct) and `qualifiedName`. Setting relationship attributes with a type name sets `relationshipType` to it; in a body, of the two the one that comes later wins                                                                                                                                                                                                        |
| ENT-13 | A classification adds `entityGuid`, `entityStatus` (`ACTIVE` when not given), `propagate`, `validityPeriods` and `removePropagationsOnEntityDelete`, and appends a validity period. A time boundary has `startTime`, `endTime` and `timeZone`, as strings                                                                                                                                                                                                                                                                 |
| ENT-14 | An entity header adds `guid`, `status` (`ACTIVE` when not given), `displayText`, `classificationNames`, `classifications`, `meaningNames`, `meanings`, `isIncomplete` (false when not given) and `labels` (as ENT-07). Made from an entity it takes the type name, attributes, GUID, status, classifications and `isIncomplete`, the classification names when it has any, and the labels when it has any; not the meanings                                                                                               |
| ENT-15 | A term assignment header has `termGuid`, `relationGuid`, `description`, `displayText`, `expression`, `createdBy`, `steward`, `source`, `confidence`, `status` and `qualifiedName`; it leaves out null and empty strings (`@AtlasJSON`, `NON_EMPTY`) but always writes `confidence`, an `int` that is 0 when not given or null                                                                                                                                                                                             |
| ENT-16 | The entity headers of `bulk/headers` map GUIDs to headers in `guidHeaderMap`                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ENT-17 | A mutation response has `mutatedEntities`, headers by operation name, and `guidAssignments`. It also writes `partialUpdatedEntities`, the `PARTIAL_UPDATE` headers, when that operation is present (a getter without `@JsonIgnore`), and ignores it on reading. Adding an updated entity created in the same response records it as created; an entity is added once per operation, by GUID. It lists the headers of an operation, of an operation and type name, and finds the first, or one by type and attribute value |
| ENT-18 | Writing a model and reading the result gives an equal model; the entities of Atlas's hive hook test messages read without error and write back the same JSON                                                                                                                                                                                                                                                                                                                                                              |

## Java origin

Apache Atlas `release-2.4.0`, `intg/src/main/java/org/apache/atlas/model/`:

- `instance/AtlasStruct`, `AtlasEntity` (with `Status`, `AtlasEntityExtInfo`, `AtlasEntityWithExtInfo`,
  `AtlasEntitiesWithExtInfo`), `AtlasObjectId`, `AtlasRelatedObjectId`, `AtlasClassification`,
  `AtlasEntityHeader`, `AtlasEntityHeaders`, `EntityMutationResponse`, `EntityMutations.EntityOperation`,
  `AtlasRelationship.Status`
- `TimeBoundary`, `glossary/relations/AtlasTermAssignmentHeader`, `glossary/enums/AtlasTermAssignmentStatus`,
  `annotation/AtlasJSON`
- `webapp/.../web/util/AtlasJsonProvider`: the REST mapper; Jackson `2.12.7` (`pom.xml`)
- fixtures: `addons/hive-bridge/src/test/resources/json/hs2-*.json`, entities as Atlas writes them (`"proxy"`,
  no `status` after `init()`)

## Deviations

None.

## Acceptance

- `libs/python/aurelius-atlas-model/tests/instance/` — ENT-01 to ENT-18, one test file per module; the hive
  hook messages are vendored unchanged into `tests/fixtures/`. Run by `nx test aurelius-atlas-model -c ci`.
- `uv run aurelius-atlas-trace check`.
