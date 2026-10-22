# 2.5 Delete semantics

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-056 to DD-060, DV-25 to DV-27; relies on DD-043 to DD-049, DD-052, DD-053, DV-16

## Scope

Deleting and purging entities: the delete endpoints of `EntityREST`, `PUT admin/purge` of `AdminResource`, the delete methods of `AtlasEntityStoreV2` and the delete handlers (`DeleteHandlerV1`, `SoftDeleteHandlerV1`, `HardDeleteHandlerV1`, `DeleteHandlerDelegate`), including the cascade over owned references, which moves here from 3.2 (DD-060).

| Endpoint | Answers |
| --- | --- |
| `DELETE /api/atlas/v2/entity/guid/{guid}` | `EntityMutationResponse` |
| `DELETE /api/atlas/v2/entity/bulk?guid=<guid>&guid=…` | `EntityMutationResponse` |
| `DELETE /api/atlas/v2/entity/uniqueAttribute/type/{typeName}?attr:<name>=<value>` | `EntityMutationResponse` |
| `PUT /api/atlas/admin/purge` with a JSON array of GUIDs | `EntityMutationResponse` |

In `aurelius-atlas-core`, one module per Java class: `delete_type` (`DeleteType`), `delete_handler` (`DeleteHandler`, `DeleteHandlerV1`'s logic), `soft_delete_handler` and `hard_delete_handler`; `EntityWriter` gains the store's delete methods. `EntityStore` writes can remove documents (DD-056), and every entity document indexes the GUIDs it refers to, to find the entities that refer to a deleted one (DD-057). The server's `routes/entity` and `routes/admin` answer the endpoints; two settings choose the delete type (DD-059). The entity scenarios of 2.4 now delete and purge what they create, and then delete their types (DD-055).

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Relationship edges of a deleted entity, inverse references, composition through `relationshipDefs` | 3.1, 3.2 |
| Deleting an owned entity whose reference an update drops | 3.2 |
| Classifications of deleted entities and their propagation | 3.3, 3.4 |
| Audit events of deletes and purges | 3.5 |
| Access checks (`ENTITY_DELETE`, `ADMIN_PURGE`) | 6.2 |

## Semantics

"Deleting" below is a soft delete, a hard delete or a purge, as EDL-04 chooses. "A reference" of an entity is an object id value of one of its own attributes, or an element or value of one of its arrays or maps of object ids; soft references and references inside structs are none (Atlas keeps them as properties, not edges).

| Id | Rule |
| --- | --- |
| EDL-01 | `guid`, each `guid` of `bulk` and of `purge`, and `typeName` longer than 4096 characters fail with `INVALID_QUERY_PARAM_LENGTH` before anything else |
| EDL-02 | `DELETE bulk` without `guid` and `purge` without GUIDs fail with `INVALID_PARAMETERS` (`Guid(s) not specified`). `DELETE uniqueAttribute` checks the type as ERD-08 does (`TYPE_NAME_INVALID`); without `attr:` values it fails with `INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND` given one parameter, `{}`, so the message keeps `{1}`; the values are not checked to be unique ones |
| EDL-03 | A GUID no entity has, or values no `ACTIVE` entity holds (ENS-06), deletes nothing and is no error. A delete skips an entity already `DELETED`; a purge takes only `DELETED` entities. A request that deletes nothing answers `{}` |
| EDL-04 | A delete is soft unless the server's default delete type is hard (`atlas.DeleteHandlerV1.impl`); with the override enabled (`atlas.rest.enable.delete.type.override`, off by default) the query parameter `deleteType` chooses: `soft` or `hard` in any case, anything else the default. A purge is hard |
| EDL-05 | Each entity to delete is deleted with the entities it owns, transitively: those its owned reference attributes name (`ownedRef`, single, array or map, a soft one by the GUID in `typeName:guid`), each once, skipping those in the state EDL-03 skips. Each deleted entity's header is taken before it is deleted, as `toAtlasEntityHeader` gives it; a purge's headers also have `classifications: []` |
| EDL-06 | A soft delete sets the entity's state to `DELETED` and its `updateTime` and `updatedBy`; its attribute values stay, references included, as Atlas keeps soft-deleted edges that reads still follow. A hard delete and a purge remove the entity. Either way the entity holds no unique value any more (ENS-05) |
| EDL-07 | Each entity with a reference to a deleted one, unless itself deleted by this request or `DELETED`, is changed: a hard delete and a purge remove the reference (a single one becomes null, an element or entry is dropped), a soft delete keeps it; its `updateTime` becomes the request's time. A mandatory single reference fails the request with `INTERNAL_ERROR` (`Cannot unset required attribute <attribute> on <guid> edge = <label>`), and so does a mandatory array or map holding no more than its minimum count (`Cannot remove array element from required attribute …`, `Cannot remove map entry …`) (DV-26) |
| EDL-08 | The response's `mutatedEntities` has the deleted entities under `DELETE` (`PURGE` for a purge) in the order they were reached, then, except for a purge, the entities EDL-07 changed under `UPDATE`, with their headers after the change (DV-25). It has no `guidAssignments` |
| EDL-09 | A request's deletes and changes are written together, all or nothing, documents removed with the others (DD-056); a lost race runs the request again once, as EWR-16 |
| EDL-10 | Every entity document holds, indexed, the GUIDs of its references; the entities referring to one are found by searching them after a refresh (DD-057). Preparing the store adds the field to an existing entity index |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/EntityREST.java`: `deleteByGuid`, `deleteByGuids`, `deleteByUniqueAttribute`; `webapp/.../web/resources/AdminResource.java#purgeByIds`; `webapp/.../web/filters/AuditFilter.java` (`deleteType`)
- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `deleteById`, `deleteByIds`, `deleteByUniqueAttributes`, `purgeByIds`, `deleteVertices`, `purgeVertices`
- `repository/.../store/graph/v1/DeleteHandlerV1.java`: `deleteEntities`, `getOwnedVertices`, `deleteEdgeReference`, `deleteTypeVertex`, `deleteVertex`, `deleteEdgeBetweenVertices`, `skipVertexForDelete`; `SoftDeleteHandlerV1.java`, `HardDeleteHandlerV1.java`, `DeleteHandlerDelegate.java`
- `server-api/.../DeleteType.java`, `RequestContext.java` (`recordEntityDelete`, `recordEntityUpdate`); `intg/.../AtlasConfiguration.java#REST_API_ENABLE_DELETE_TYPE_OVERRIDE`; `intg/.../exception/AtlasBaseException.java` (a message without an error code is `INTERNAL_ERROR`)

## Deviations

DV-25: Atlas lists deleted and changed entities in the hash order of its request context's maps; Aurelius Atlas in the order they were reached. DV-26: Atlas's message for a mandatory reference names the referring vertex with its graph details; Aurelius Atlas names its GUID. DV-27: Atlas changes every entity referring to a deleted one in the same transaction; Aurelius Atlas finds them by a search, which may miss one written at the same moment as the delete (DD-057).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — EDL-02 to EDL-10 on the in-memory documents: soft and hard deletes, purges, cascades, referrers, mandatory references, removals undone by recovery.
- `libs/python/aurelius-atlas-core/e2e/` — references found by search, a hard delete, a purge against the dev store.
- `apps/aurelius-atlas-server/tests/` — EDL-01 to EDL-08 over HTTP, the delete type settings.
- `apps/aurelius-atlas-server/scenarios/entity/` — deleting and purging what a scenario created, then its types.
- `uv run aurelius-atlas-trace check`.
