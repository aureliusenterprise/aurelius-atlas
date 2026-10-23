# 3.1b Relationship attributes

- **Status:** in progress
- **Pull request:** [#116](https://github.com/aureliusenterprise/aurelius-atlas/pull/116)
- **Records:** DD-064 to DD-067, DV-31, DV-32; supersedes DD-050 and DD-053; relies on DD-049, DD-052, DD-061,
  DD-062

The second part of increment 3.1 (DD-063): the relationship attributes of entities. An entity write creates,
reuses and deletes relationships for the values of its relationship attributes; an entity read answers them in
`relationshipAttributes`, and the legacy ends among its attributes, through the relationships.

## Scope

No new endpoint: the entity endpoints of 2.3 to 2.5 change.

| Endpoint                                                             | Change                                                                               |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `POST /api/atlas/v2/entity`, `POST /entity/bulk`                     | Relationship attribute values become relationships (REL-11 to REL-16)                |
| `PUT /entity/uniqueAttribute/type/{typeName}`, `PUT /entity/guid/…`  | The same, for a partial update and a single attribute                                |
| `GET /entity/guid/{guid}`, `/entity/bulk`, `/entity/uniqueAttribute` | `relationshipAttributes` and legacy ends read through relationships (REL-17, REL-18) |
| `DELETE /entity/…`, `PUT /admin/purge`                               | Owned relationship attributes are followed (REL-19)                                  |

In `aurelius-atlas-core`: `graph_helper` (`GraphHelper`'s edge lookups, over an entity's stored relationships),
`relationship_mapper` (`RelationshipMapper`, the relationship side of `EntityGraphMapper`), and changes to
`entity_mapper`, `entity_writer`, `entity_comparator`, `entity_retriever`, `delete_handler`,
`relationship_store` and `stored_relationship`.

Not in scope:

| Not delivered here                                                                       | Delivered by |
| ---------------------------------------------------------------------------------------- | ------------ |
| Deleting the owned entity of an owned relationship an update replaces or drops (DV-31)   | 3.2          |
| Classifications propagated over relationships                                            | 3.4          |
| `parentCategoryGuid` in the relationship attributes of a related `AtlasGlossaryCategory` | 5.2          |
| Import's relationship GUIDs (`isImportInProgress`)                                       | 6.3          |
| Inverse references whose inverse attribute is not a relationship attribute (DV-32)       | –            |

## Semantics

A relationship _of an attribute_ is one of the entity's relationships with the attribute's edge label, in the
attribute's direction: `OUT` when the entity is its end 1, `IN` when it is end 2, `BOTH` either way. Its _other
end_ is the end that is not the entity (end 2 when both are). The relationships are in the order the entity lists
them (DD-061).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REL-11 | A write maps an entity's relationship attributes before its attributes (`mapRelationshipAttributes`): on create every relationship attribute of its type, on an update those given; a legacy end given in `attributes` has moved to `relationshipAttributes` (EWR-06). The attribute is the one of the relationship type the value names (`relationshipType`), else of the attribute's first. Its value is written as relationships, never as an attribute value (DD-064); its references resolve as 2.4's do (`INVALID_OBJECT_ID`, EWR-17). An update that gives relationship attributes changes the entity's `updateTime` and `updatedBy`                                                                                                                                                                                                                                                                                                                                                                                                                                |
| REL-12 | A single end. The current relationship is the one the value's `relationshipGuid` names, else the attribute's relationship that is `ACTIVE`, else its latest updated `DELETED` one. Given a value: with a current relationship whose other end, by the attribute's direction, is the value's entity, that relationship stays; with another, REL-13 gets or creates one from the current one's end 1 to the value's entity (`OUT`), from the value's entity to the current one's end 2 (`IN`), or from the value's entity to the entity (`BOTH`), and the value's entity becomes updated. Without a current relationship, REL-13 gets or creates one from the entity to the value's entity (from the value's entity to the entity for `IN`), and the value's entity becomes updated. A current relationship the result is not, or a null value on update, is deleted as REL-15 deletes it                                                                                                                                                                                    |
| REL-13 | Getting or creating a relationship of type T from entity A to entity B: an `ACTIVE` relationship from A to B with the label REL-05 gives them is reused, unchanged. Else one is created as REL-05 creates it, after REL-04's checks of T, the ends' types, and its attributes (`INVALID_VALUE`, `INVALID_RELATIONSHIP_END_TYPE`, `RELATIONSHIP_CRUD_INVALID_PARAMS`) but not `RELATIONSHIP_ALREADY_EXISTS`: with a new GUID, version 0, provenance type 0, and the attributes the value's `relationshipAttributes` gives, null for the others. Both ends list it (DD-061) and it is written with the entities, all or nothing (DD-066)                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| REL-14 | A `LIST` or `SET` end. The current relationships are the attribute's, in any state, ordered by their index when the first has one (DD-065). A partial update of an attribute with `isAppendOnPartialUpdate` keeps the current ones and adds the given ones (DV-23). Each given element is mapped as REL-12 maps a value, the current relationship being the one at its position, but its entity becomes updated only when its relationship replaces the current one or is created by this request. Unless the type's `appendRelationshipsOnPartialUpdate` option names the attribute, each current relationship not among the mapped ones is deleted (REL-15); the ones that stay (soft-deleted, or kept by appending) come before the mapped ones. Each `ACTIVE` one gets its position as index. A null value on update maps no element                                                                                                                                                                                                                                   |
| REL-15 | A relationship an update replaces or drops is deleted with the write's delete type (EDL-04): a soft delete sets it `DELETED`, its `updateTime` and `updatedBy`, unless it is already `DELETED`, which changes nothing; a hard delete removes it and both ends stop listing it. The entity at its other end (by the attribute's direction) becomes updated, unless the attribute is owned (DV-31)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| REL-16 | An attribute with an `inverseRef` constraint: after REL-12 or REL-14 maps an element to a relationship, the inverse attribute of the relationship's end 2 gets, through REL-13, a relationship from end 2 to end 1 of its own relationship type, with the element's relationship attributes, when that attribute is a relationship attribute of end 2's type (DV-32). For a single inverse attribute, end 2's relationship of it, when another, is deleted (REL-15); end 2 becomes updated unless its relationship stayed the same, or for an array, was reused                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| REL-17 | Unless `ignoreRelationships=true`, `relationshipAttributes` holds every relationship attribute of the type. Its relationship type is the attribute's only one, else the type of the first relationship the entity is end 2 of that is one of the attribute's, else its first; the end of that type the entity's type and the attribute's name match decides the cardinality. A `SINGLE` end reads REL-12's current relationship, a `LIST` or `SET` end all of the attribute's, in any state. Each is an `AtlasRelatedObjectId`: the other end's `guid`, `typeName`, `entityStatus`, `displayText` (as ERD-07 finds it) and `qualifiedName` when it has one; `relationshipType`, `relationshipGuid`, `relationshipStatus` and `relationshipAttributes`, a struct of the relationship's type with every attribute. An owned one adds the other entity to `referredEntities` (ERD-05). A legacy end that is not an attribute of the type is also answered in `attributes`, as object ids without the relationship, leaving out a `DELETED` relationship to an `ACTIVE` entity |
| REL-18 | An attribute that is a relationship end (a legacy end) reads through its relationships, in `attributes`, in headers and where the comparator reads it (EWR-08): a single one as REL-12's current relationship's other end, an array as the attribute's relationships' other ends in any state, ordered as REL-14 orders them, `[]` when there is none. Each is an object id with its unique attribute values; an owned one adds its entity to `referredEntities` and is named by GUID and type alone (ERD-04)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| REL-19 | Deleting an entity also deletes, with it, the entities its owned relationship attributes name (EDL-05): for a single one the other end of its relationship with the attribute's label in which it is end 1, `ACTIVE` else latest `DELETED`; for an array the end 2 of each of the attribute's relationships; a relationship that is `DELETED` (`ACTIVE` for a purge) is skipped (DD-067)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../store/graph/v2/EntityGraphMapper.java`: `mapRelationshipAttributes`, `mapToVertexByTypeCategory`
  (`OBJECT_ID_TYPE`), `mapObjectIdValueUsingRelationship`, `updateRelationship`, `mapArrayValue`,
  `removeUnusedArrayEntries`, `unionCurrentAndNewElements`, `getAppendOptionForRelationship`,
  `addInverseReference`, `createInverseReferenceUsingRelationship`, `getOrCreateRelationship`,
  `recordEntityUpdate`, `getRelationshipGuid`, `getRelationshipAttributes`
- `repository/.../store/graph/v2/AtlasRelationshipStoreV2.java`: `getOrCreate`, `getRelationship`,
  `createRelationship(…, false)`
- `repository/.../store/graph/v2/EntityGraphRetriever.java`: `mapRelationshipAttributes`,
  `mapVertexToRelationshipAttribute`, `mapRelatedVertexToObjectId`, `mapRelationshipArrayAttribute`,
  `mapVertexToRelatedObjectId`, `toLegacyAttribute`, `mapVertexToObjectId`, `mapVertexToArray`,
  `getReferencedEntityVertex`, `getDisplayText`, `getQualifiedName`
- `repository/.../graph/GraphHelper.java`: `getEdgeForLabel`, `getEdgesForLabel`,
  `getCollectionElementsUsingRelationship`, `sortCollectionElements`, `getRelationshipTypeName`
- `repository/.../store/graph/v1/DeleteHandlerV1.java`: `deleteEdgeReference`, `getOwnedVertices`;
  `SoftDeleteHandlerV1#deleteEdge`

## Deviations

DV-31: a relationship of an owned attribute that an update replaces or drops deletes, in Atlas, the owned entity
with it (`deleteEdgeReference` then `deleteTypeVertex`); until 3.2 Aurelius Atlas deletes only the relationship
(ended by 3.2, OWN-01).
DV-32: an inverse reference whose inverse attribute is not a relationship attribute is kept by Atlas as a legacy
edge; Aurelius Atlas does not maintain it. DV-21 now also covers the order of an array's relationships: Atlas
indexes them in the hash order of a union of edges, Aurelius Atlas keeps the ones that stay first, then the
mapped ones in the request's order.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — REL-11 to REL-19 on the in-memory documents.
- `libs/python/aurelius-atlas-core/e2e/` — relationship attributes written, read and deleted on the dev store.
- `apps/aurelius-atlas-server/scenarios/relationship/relationship-attributes.scenario.yaml` — REL-11 to REL-13,
  REL-15, REL-17 and REL-18 over HTTP: a legacy end created, read from both ends, moved and purged.
- `uv run aurelius-atlas-trace check`.
