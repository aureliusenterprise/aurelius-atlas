# 3.2 Ownership cascades

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-068, DD-069, DV-33; ends DV-31; relies on DD-052, DD-056 to DD-058, DD-062, DD-064, DD-066,
  DD-067

What is left of ownership after 2.5 and 3.1b (DD-060, DD-067): an entity write that replaces or drops an owned
reference deletes the owned entity, as Atlas's `deleteEdgeReference` does, and an owned map entry naming a
deleted entity revives it.

## Scope

No new endpoint: the entity writes of 2.4 change.

| Endpoint                                                                                                              | Change                                     |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `POST /api/atlas/v2/entity`, `POST /entity/bulk`, `PUT /entity/uniqueAttribute/type/{typeName}`, `PUT /entity/guid/…` | Owned entities an update drops are deleted |

In `aurelius-atlas-core`: `transaction_view` (`TransactionView`, the entity store as a write request has changed
it, DD-068), and changes to `entity_mapper`, `relationship_mapper`, `entity_writer` and `delete_handler`.

Not in scope:

| Not delivered here                                                    | Delivered by |
| --------------------------------------------------------------------- | ------------ |
| Entities an import marks `DELETED` (`entitiesToDelete`), or activates | 6.3          |
| Owned references inside structs                                       | –            |
| Classifications of the deleted entities, audit events                 | 3.3 to 3.5   |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OWN-01 | An update drops an owned entity when an owned attribute of the entity it updates no longer names it: a plain one (not soft, EDL-05), single, array or map, whose stored value named it and whose new value does not; or a relationship one whose relationship to it REL-15 deletes, the entity being the relationship's end 2. A partial update that appends (EWR-11) drops none                          |
| OWN-02 | Each dropped entity is deleted with the write's delete type (EDL-04) as a delete of it deletes it (EDL-03 to EDL-07, REL-09, REL-19): with what it owns, and changing the entities that refer to it, as the update has changed them; one already `DELETED` is skipped; a mandatory reference to it fails the request (`INTERNAL_ERROR`). The deletes are written with the update, all or nothing (DD-068) |
| OWN-03 | The response lists the deleted entities under `DELETE`, after the created and updated ones and before those the request made updated (EWR-13); the entities the deletes changed are among the latter, under the request's operation. A deleted entity the request also made updated is listed under both, with the header taken before it was deleted                                                     |
| OWN-04 | An owned map entry, not soft, that keeps naming the entity it named makes that entity `ACTIVE` again when it is `DELETED` (`updateInConsistentOwnedMapVertices`, DD-069); nothing else of it changes, and it is not reported                                                                                                                                                                              |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../store/graph/v1/DeleteHandlerV1.java`: `deleteEdgeReference`, `deleteTypeVertex`,
  `deleteEntities`
- `repository/.../store/graph/v2/EntityGraphMapper.java`: `mapToVertexByTypeCategory` (`OBJECT_ID_TYPE`),
  `removeUnusedArrayEntries`, `removeUnusedMapEntries`, `updateInConsistentOwnedMapVertices`,
  `mapAttributesAndClassifications` (the response)

## Deviations

DV-31 ends: an owned entity whose relationship an update deletes is deleted with it. DV-33: a reference an update
drops from an array or map of plain references stays in Atlas, its edge soft-deleted, and reads back with a soft
delete; Aurelius Atlas drops it, since a plain reference keeps no state of its own (DD-049, DD-058). It was so
since 2.4 and is recorded here.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — OWN-01 to OWN-04 on the in-memory documents.
- `libs/python/aurelius-atlas-core/e2e/` — an owned part an update drops is deleted on the dev store.
- `apps/aurelius-atlas-server/scenarios/entity/` — OWN-01 to OWN-03 over HTTP.
- `uv run aurelius-atlas-trace check`.
