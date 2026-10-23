# 3.5b Classification audit

- **Status:** in progress
- **Pull request:** [#136](https://github.com/aureliusenterprise/aurelius-atlas/pull/136)
- **Records:** DD-085, DD-086, DV-41, DV-42; relies on DD-074, DD-077, DD-079, DD-082 to DD-084

The second part of increment 3.5 (DD-082): audit events for classifications attached, changed and removed, and
for those propagated or no longer propagated, recorded after the change as 3.5a's entity events are; and
`GET v2/entity/bulk/headers`, which lists the entities whose classifications changed since a time (DD-074).

## Scope

| Endpoint                                                        | Takes            | Answers              |
| --------------------------------------------------------------- | ---------------- | -------------------- |
| `GET /api/atlas/v2/entity/bulk/headers?tagUpdateStartTime=<ms>` | the start, in ms | `AtlasEntityHeaders` |

In `aurelius-atlas-core`, the change notifier and the audit listener gain the classification methods of
`AtlasEntityChangeNotifier` and `EntityAuditListenerV2`; `TagPropagation` records the propagations a request
added and removed, as Atlas's `RequestContext` does (DD-086). The classification operations, the entity writer,
the relationship store and the propagation tasks tell the notifier (DD-085). `classification_associator` gains
`ClassificationRetriever` (`ClassificationAssociator.Retriever`); the audit repository finds the entities with
classification events in a time range. The server's `routes/entity` answers `bulk/headers`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CAU-01 | A classification event names the entity and writes the classification as read (DV-42): on its own entity `CLASSIFICATION_ADD` `Added classification: <JSON>`, `CLASSIFICATION_UPDATE` `Updated classification: <JSON>`, `CLASSIFICATION_DELETE` `Deleted classification: <name>`; on another entity `PROPAGATED_CLASSIFICATION_ADD` `Added propagated classification: <JSON>`, `PROPAGATED_CLASSIFICATION_UPDATE` `Updated propagated classification: <JSON>`, `PROPAGATED_CLASSIFICATION_DELETE` `Deleted propagated classification: <name>` |
| CAU-02 | Adding classifications to an entity (also by `bulk/classification`, `bulk/setClassifications` and an entity create) records, per classification in the request's order, an add on its entity and on each entity it was propagated to within the request (none while tasks are enabled). An entity create records them before its entity events                                                                                                                                                                                                |
| CAU-03 | Updating classifications records, on the entity, on the entities the updated classifications are propagated to when their attributes, validity periods or `removePropagationsOnEntityDelete` changed, and on those `propagate` turned on reached, each `ACTIVE`, one update event per updated classification; on another entity an update is an add when the request propagated it there, a delete when it removed it. Those `propagate` turned off removed it from then record a delete                                                      |
| CAU-04 | Deleting a classification records a delete on each entity its propagation was removed from within the request, then on its entity. Removing a propagated classification of a deleted entity (`associatedEntityGuid`) records nothing                                                                                                                                                                                                                                                                                                          |
| CAU-05 | After an entity write or delete, and after a relationship is created, updated or deleted, each entity the request propagated a classification to records an add, and each it removed one from a delete, unless the request deleted it (`notifyPropagatedEntities`); an add CAU-02 recorded is recorded again, as Atlas does                                                                                                                                                                                                                   |
| CAU-06 | A propagation task records its own changes: `ADD` an add on each entity it propagated to, `DELETE` a delete on each it removed the classification from, `RELATIONSHIP_UPDATE` as CAU-05                                                                                                                                                                                                                                                                                                                                                       |
| CAU-07 | `bulk/headers` answers, in `guidHeaderMap`, the header with classifications of each entity with a `CLASSIFICATION_ADD`, `CLASSIFICATION_UPDATE` or `CLASSIFICATION_DELETE` event (propagated ones not counted) from `tagUpdateStartTime` (default 0) to now, both included; entities that can no longer be read are left out. A start after now fails with `BAD_REQUEST` `fromTimestamp should be less than toTimestamp`                                                                                                                      |
| CAU-08 | A `tagUpdateStartTime` that is no Java `long` fails with `BAD_REQUEST` (DV-41)                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../store/graph/v2/EntityGraphMapper.java`: `addClassifications`, `updateClassifications`,
  `deleteClassification`, `propagateClassification`, `deleteClassificationPropagation`, `updateTagPropagations`
- `repository/.../store/graph/v2/AtlasEntityChangeNotifier.java`: `onClassificationsAddedToEntities`,
  `onClassificationUpdatedToEntity`, `onClassificationsDeletedFromEntities`, `notifyPropagatedEntities`
- `repository/.../store/graph/v1/DeleteHandlerV1.java`: `addTagPropagation`, `removeTagPropagation`,
  `deletePropagatedClassification`; `server-api/.../RequestContext.java`: `recordAddedPropagation`,
  `recordRemovedPropagation`
- `repository/.../audit/EntityAuditListenerV2.java`: `onClassificationsAdded`, `onClassificationsUpdated`,
  `onClassificationsDeleted`; `HBaseBasedAuditRepository.java#getEntitiesWithTagChanges`
- `repository/.../store/graph/v2/ClassificationAssociator.java#Retriever`; `EntityREST.java#getEntityHeaders`

## Deviations

DV-41: a `tagUpdateStartTime` that is not a number fails in Atlas with Jersey's parameter error, a `500` with
a text body; Aurelius Atlas answers `BAD_REQUEST`. DV-42: Atlas writes in add and update events the
classification object of the request, normalised; Aurelius Atlas writes the instance as a read answers it,
which has the same fields, the defaults filled in. Events are written after the change as in 3.5a (DV-40).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — CAU-01 to CAU-07 on the in-memory documents and repository. -
  `libs/python/aurelius-atlas-core/e2e/` — classification events and their entities found on the dev store. -
  `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/entity/` — CAU-02, CAU-04,
  CAU-07, CAU-08 over HTTP. - `uv run aurelius-atlas-trace check`.
