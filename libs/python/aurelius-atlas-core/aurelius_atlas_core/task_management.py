"""``TaskManagement``: the tasks requests record, listed, removed and run (TSK-04 to TSK-06, DD-080).

Atlas's ``TaskManagement``, ``TaskRegistry`` and ``TaskExecutor``. Atlas runs a task on its active instance in
one thread; here every process may run tasks, each claimed by one with a lease (DV-38): the claim is a conditional
write of the task as ``IN_PROGRESS``, and one claimed by a process that stopped is claimed again once its lease
has passed.
"""

from collections.abc import Sequence

from aurelius_atlas_model.tasks import MAX_ATTEMPT_COUNT, AtlasTask, TaskStatus

from aurelius_atlas_core.classification_tasks import ClassificationTasks
from aurelius_atlas_core.entity_store import (
    EntityStore,
    EntityVersionConflictError,
    EntityWriteError,
    RelationshipChange,
    TaskChange,
)
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.tag_propagation import TagPropagation
from aurelius_atlas_core.typedef_document import DocumentVersion

LEASE_MILLISECONDS = 300_000
"""How long a claim holds before another process may run the task (DD-080)."""


class TaskManagement:
    """The tasks of ``store``; ``lease`` is how long a claim holds, in milliseconds."""

    def __init__(self, store: EntityStore, *, lease: int = LEASE_MILLISECONDS) -> None:
        self._store = store
        self._lease = lease

    async def get_all(self) -> list[AtlasTask]:
        """``getAll``: every task, oldest first (TSK-06)."""
        return [task.to_task() for task, _ in await self._store.list_tasks()]

    async def get_by_guids(self, guids: Sequence[str]) -> list[AtlasTask]:
        """``getByGuids``: the tasks of these GUIDs that exist, in their order (TSK-06)."""
        found = await self._store.get_tasks(guids)
        return [found[guid][0].to_task() for guid in dict.fromkeys(guids) if guid in found]

    async def delete_by_guids(self, guids: Sequence[str]) -> None:
        """``deleteByGuids``: remove the tasks of these GUIDs that exist (TSK-06)."""
        found = await self._store.get_tasks(guids)
        if found:
            await self._store.write(
                [], [], [], [TaskChange(task, version, remove=True) for task, version in found.values()]
            )

    async def run_pending(self) -> int:
        """Run the tasks waiting, oldest first, each claimed first; the number run to their end (TSK-04, TSK-05)."""
        done = 0
        for task, version in await self._store.list_tasks(open_only=True):
            claimed = await self._claim(task, version)
            if claimed is not None and await self._run(*claimed):
                done += 1
        return done

    async def _claim(self, task: StoredTask, version: DocumentVersion) -> tuple[StoredTask, DocumentVersion] | None:
        """``IN_PROGRESS`` with a lease, over the version read; None for one held, failed or claimed by another."""
        now = self._store.now()
        if task.attempt_count >= MAX_ATTEMPT_COUNT:
            return None
        if task.status is TaskStatus.IN_PROGRESS and (task.claimed_until or 0) > now:
            return None
        claimed = task.model_copy(
            update={
                "status": TaskStatus.IN_PROGRESS,
                "start_time": now,
                "updated_time": now,
                "claimed_until": now + self._lease,
            }
        )
        try:
            await self._store.write([], [], [], [TaskChange(claimed, version)])
        except EntityVersionConflictError, EntityWriteError:
            return None
        found = (await self._store.get_tasks([task.guid])).get(task.guid)
        if found is None or found[0].claimed_until != claimed.claimed_until:
            return None
        return found

    async def _run(self, task: StoredTask, version: DocumentVersion) -> bool:
        """Run a claimed task; one that fails is ``PENDING`` again, or ``FAILED`` at the last attempt (TSK-05)."""
        try:
            await ClassificationTasks(self._store).run(task, version)
        except Exception as failure:  # noqa: BLE001 - AbstractTask: any failure counts as an attempt
            await self._failed(task, version, failure)
            return False
        return True

    async def _failed(self, task: StoredTask, version: DocumentVersion, failure: Exception) -> None:
        """``AbstractTask.run`` and ``updateStatusFromAttemptCount``; its entity or relationship no longer lists it."""
        now = self._store.now()
        attempts = task.attempt_count + 1
        failed = task.model_copy(
            update={
                "status": TaskStatus.FAILED if attempts >= MAX_ATTEMPT_COUNT else TaskStatus.PENDING,
                "attempt_count": attempts,
                "error_message": str(failure),
                "end_time": now,
                "updated_time": now,
                "claimed_until": None,
            }
        )
        parameters = task.parameters or {}
        propagation = TagPropagation(self._store)
        entity_guid = parameters.get("entityGuid")
        if isinstance(entity_guid, str):
            await propagation.unqueue(task.guid, entity_guid)
        relationships = await _unlisted(self._store, task.guid, parameters.get("relationshipEdgeId"))
        try:
            await self._store.write(propagation.entity_changes([]), relationships, [], [TaskChange(failed, version)])
        except EntityVersionConflictError, EntityWriteError:
            return


async def _unlisted(store: EntityStore, task_guid: str, guid: object) -> list[RelationshipChange]:
    """``removePendingTaskFromEdge``: the relationship ``guid`` without the task in its ``pendingTasks``."""
    found = (await store.get_relationships([guid])).get(guid) if isinstance(guid, str) else None
    if found is None or task_guid not in (found.relationship.pending_tasks or []):
        return []
    listed = [listed for listed in found.relationship.pending_tasks or [] if listed != task_guid]
    return [RelationshipChange(found.relationship.model_copy(update={"pending_tasks": listed or None}), found.version)]
