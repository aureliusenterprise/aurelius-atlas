# 6.3d An import holds its propagation tasks

- **Status:** in review
- **Pull request:** to follow
- **Records:** DD-361, DV-138; relies on DD-052 (a lost race runs the request again once), DD-080 (the task
  worker) and DD-081 (tasks on or off)

With tasks enabled, an import of entities whose classifications propagate failed part-way with `entity <guid>
was changed by another write`. Each entity the import writes records propagation tasks; the task worker runs
them while the import goes on, and its writes reach entities the import is about to write again. An entity
write that loses that race runs once more (EWR-16), and with hundreds of tasks running it loses twice. The
sample export of the standalone stack, 687 entities with 654 propagating classifications, failed this way on
Elasticsearch every time.

The import now holds the tasks it records: no worker runs them until the import ends, successful or not, and
then the worker runs them all.

## Scope

In `aurelius-atlas-core`: `task_hold` (`TaskHold`, `held`), the hold on `StoredTask` (`held_by`, `held_until`)
and `Deferral`, `EntityWriter.hold_tasks` and `defers_tasks`, `EntityClassifications`' `hold`, the hold
checked by `TaskManagement`'s claim and by TSK-03, and `ImportService` holding and releasing. In
`aurelius-atlas-server`, the standalone stack runs with tasks enabled again.

Not in scope: other concurrent writers. Two requests, or a request and a task it did not record, still meet as
DD-052 says. A re-import while the previous import's tasks still run is refused as Atlas refuses it (TSK-03).

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                          |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| IMT-01 | With tasks enabled, every task an import's entity writes record is held by the import: recorded `PENDING` with the hold, it is not claimed by any server process while the hold lasts. `admin/tasks` answers it as any `PENDING` task. With tasks disabled, an import records none and holds nothing (TSK-08) |
| IMT-02 | When the import ends, whether it succeeded or failed, it releases every task it still holds and wakes the workers, which run them as TSK-04 says. Released in batches; a task that changed since it was read is passed over, and the rest are released                                                        |
| IMT-03 | A hold passes on its own an hour after the import began (`HOLD_MILLISECONDS`): a task whose hold has passed is claimed and run as any other, so an import that stops without releasing delays the propagation of what it wrote, and never drops it                                                            |
| IMT-04 | TSK-03's refusal to delete a classification while a `PENDING` task names it and its entity passes over the tasks the deleting import holds: they have not run, so nothing they would propagate needs undoing, and once they run, an instance deleted meanwhile propagates nothing                             |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../impexp/ImportService.java`, `store/graph/v2/bulkimport/RegularImport.java`: the import writes
  its entities one by one, each in its own transaction.
- `repository/.../tasks/TaskManagement.java`, `TaskExecutor.java`: the tasks each commit queues run at once, on
  the executor's thread.
- `repository/.../store/graph/v2/EntityGraphMapper.java` (`addClassifications`, `deleteClassification`): an
  import's classification with `propagate` set keeps it (it defaults to off only when unset), and the deletion's
  check of pending tasks.
- `repository/.../graph/GraphTransactionInterceptor.java` (`lockObjectAndReleasePostCommit`): Atlas locks the
  GUIDs a transaction changes, so a task and an import wait for each other instead of one failing.

## Deviations

- **DV-138:** the tasks an import records run once it ends, not while it runs.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__task_hold.py`: IMT-01 to IMT-04, the workers' turns taken between
  the import's writes: nothing they run while it runs, everything after; a failed import releases; a hold that
  passed; a release that loses a race; an import deleting a classification whose task it holds.
- By hand, on Elasticsearch with tasks enabled: the standalone stack's `sample_data.zip` imports into an empty
  store and over itself without one lost race, and its tasks drain without a failure. Before, it failed every
  time. The e2e stacks run with tasks disabled (DD-081), so no e2e test covers this.
