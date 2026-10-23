# 3.4b Propagation tasks

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-079 to DD-081, DV-38; ends DV-37; relies on DD-071, DD-075 to DD-078

The second part of increment 3.4 (DD-078): propagation deferred to tasks, as Atlas does by default
(`atlas.tasks.enabled=true`). A request records a task with its change; a worker in every server process runs
the tasks after it, each as one write (DD-080). The propagation itself is 3.4a's.

## Scope

| Endpoint                                       | Takes | Answers               |
| ---------------------------------------------- | ----- | --------------------- |
| `GET /api/atlas/admin/tasks?guids=<guid>&…`    | –     | a list of `AtlasTask` |
| `DELETE /api/atlas/admin/tasks?guids=<guid>&…` | –     | nothing (`204`)       |

Entities read their `pendingTasks`. In `aurelius-atlas-model`, `AtlasTask`. In `aurelius-atlas-core`,
`stored_task` (`StoredTask`), `task_management` (`TaskManagement`: Atlas's `TaskManagement`, `TaskRegistry`
and `TaskExecutor`) and `classification_tasks` (`ClassificationTasks`: `ClassificationPropagationTasks` and
`ClassificationTask`); tasks are documents of their own index, listed by the entity they are queued on
(DD-079). The server runs a worker and answers `admin/tasks`; `AURELIUS_ATLAS_SERVER_TASKS_ENABLED` chooses
(DD-081).

Not in scope:

| Not delivered here                                                               | Delivered by |
| -------------------------------------------------------------------------------- | ------------ |
| Audit reduction tasks (`AuditReductionTaskFactory`) and the dashboard's task tab | 3.5, –       |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TSK-01 | `AtlasTask` reads and writes `type`, `guid`, `createdBy`, `createdTime`, `updatedTime`, `startTime`, `endTime`, `parameters`, `attemptCount`, `errorMessage` and `status` (`PENDING`, `IN_PROGRESS`, `COMPLETE`, `FAILED`); times as epoch milliseconds, nulls left out. A new task is `PENDING`, has a new GUID, both times now and no attempts                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| TSK-02 | With tasks enabled, a change that 3.4a propagates at once records a task instead, written with the change (DD-079), its GUID added to `pendingTasks` of the entity it is queued on: `CLASSIFICATION_PROPAGATION_ADD` for an added classification that propagates (on its entity), for `propagate` turned on (likewise), and for a created relationship, one per propagation-enabled classification of each end it propagates from (on the other end, with the relationship's GUID); `CLASSIFICATION_PROPAGATION_DELETE` for `propagate` turned off, for a deleted classification that propagates, and for an entity deleted with a classification that removes propagations; `CLASSIFICATION_PROPAGATION_RELATIONSHIP_UPDATE` for every relationship update (on the relationship). Its parameters are `entityGuid`, `classificationVertexId` (the instance's GUID), `classificationName` and `relationshipGuid`, or `relationshipEdgeId` and `relationshipObject` (the update's JSON). Removed relationships and blocks on create propagate at once, as in 3.4a |
| TSK-03 | Deleting a classification that propagates fails with `DELETE_TAG_PROPAGATION_NOT_ALLOWED` (instance GUID, entity GUID) while a `PENDING` task names them both                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| TSK-04 | Tasks run after the request, oldest first, each once at a time (DD-080). `ADD` propagates the classification to the entity and the entities it reaches from it, the relationship excluded and its blocks counted (`propagateClassification`); `DELETE` removes every propagation of it and removes the instance when no entity lists it (`deleteClassificationPropagation`); `RELATIONSHIP_UPDATE` updates the relationship's propagation as PRO-05 does with the given relationship. One whose entity or classification is gone does nothing                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| TSK-05 | A task that runs to its end is removed, and so is its GUID from `pendingTasks`, in the task's write. One that fails is `PENDING` again with its `attemptCount` one higher and its `errorMessage`, `FAILED` from the third attempt; one with three attempts is not run                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| TSK-06 | `GET admin/tasks` answers every task, oldest first, or those of the given `guids` that exist, in their order; `DELETE admin/tasks` removes those of the given `guids`, and answers `204`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| TSK-07 | An entity reads `pendingTasks`, the GUIDs of its tasks, when it has any                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| TSK-08 | With tasks disabled, propagation happens within the request, as 3.4a says, and no task is recorded                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../tasks/`: `TaskManagement`, `TaskRegistry`, `TaskExecutor`, `AbstractTask`
- `repository/.../store/graph/v2/tasks/`: `ClassificationPropagateTaskFactory`,
  `ClassificationPropagationTasks`, `ClassificationTask`
- `repository/.../store/graph/v2/EntityGraphMapper.java`: `addClassifications`, `updateClassifications`,
  `deleteClassification`, `propagateClassification`, `deleteClassificationPropagation`,
  `updateTagPropagations`, `removePendingTaskFromEntity`
- `repository/.../store/graph/v1/DeleteHandlerV1.java`: `addTagPropagation`, `deleteAllClassifications`,
  `createAndQueueTask`; `AtlasRelationshipStoreV2#updateTagPropagations`
- `webapp/.../web/resources/AdminResource.java`: `getTaskStatus`, `deleteTask`
- `intg/.../model/tasks/AtlasTask.java`

## Deviations

DV-37 ends with tasks enabled, the default. DV-38: Atlas runs tasks one at a time on its active instance;
Aurelius Atlas runs them in every server process, each task claimed by one (DD-080), so tasks of different
entities may run side by side and finish out of order.

## Acceptance

- `libs/python/aurelius-atlas-model/tests/` — TSK-01.
- `libs/python/aurelius-atlas-core/tests/` — TSK-02 to TSK-08 on the in-memory documents.
- `libs/python/aurelius-atlas-core/e2e/` — a task claimed and run on the dev store.
- `apps/aurelius-atlas-server/tests/` — TSK-06, TSK-07 and the worker over HTTP.
- `uv run aurelius-atlas-trace check`.
