"""``TaskHold``: the tasks an import records, held from the workers until it ends (IMT-01 to IMT-03, DD-361).

An import writes its entities one by one while the workers would run the propagation tasks each write records,
and a task's write to an entity the import is about to write again makes the import lose that race (ENS-08).
The import holds its tasks instead: each is recorded with the hold, no worker claims it while the hold lasts, and
the import releases them all when it ends. A hold passes on its own after ``HOLD_MILLISECONDS``, so an import
that stops part-way only delays the propagation of what it wrote.
"""

from dataclasses import dataclass

from aurelius_atlas_core.entity_store import EntityStore, EntityVersionConflictError, EntityWriteError, TaskChange
from aurelius_atlas_core.stored_task import StoredTask

HOLD_MILLISECONDS = 3_600_000
"""How long a hold lasts unless released: an hour, longer than an import is expected to take (DD-361)."""

RELEASE_BATCH = 500
"""How many held tasks one write releases."""


@dataclass(frozen=True)
class TaskHold:
    """A hold on the tasks recorded with it: ``id`` names it, ``until`` is when it passes (epoch ms)."""

    id: str
    until: int

    @classmethod
    def start(cls, store: EntityStore) -> TaskHold:
        """A new hold of the store's clock, passing after ``HOLD_MILLISECONDS`` (IMT-01)."""
        return cls(store.new_guid(), store.now() + HOLD_MILLISECONDS)

    def holds(self, task: StoredTask) -> bool:
        """Whether the task was recorded with this hold and is still held by it."""
        return task.held_by == self.id and task.held_until is not None

    async def release(self, store: EntityStore) -> int:
        """Release every task still held by this hold and wake the workers; the number released (IMT-02).

        A task another process claimed once the hold had passed is no longer held and is left as it is.
        """
        held = [(task, version) for task, version in await store.list_tasks(open_only=True) if self.holds(task)]
        released = 0
        for start in range(0, len(held), RELEASE_BATCH):
            batch = held[start : start + RELEASE_BATCH]
            changes = [TaskChange(_released(task), version) for task, version in batch]
            try:
                await store.write([], [], [], changes)
                released += len(changes)
            except EntityVersionConflictError, EntityWriteError:
                released += await _release_each(store, changes)
        if released:
            for listener in store.task_listeners:
                listener()
        return released


def held(task: StoredTask, now: int) -> bool:
    """Whether a hold keeps the task from the workers now (IMT-01, IMT-03)."""
    return task.held_until is not None and task.held_until > now


def _released(task: StoredTask) -> StoredTask:
    return task.model_copy(update={"held_by": None, "held_until": None})


async def _release_each(store: EntityStore, changes: list[TaskChange]) -> int:
    """Release the tasks of a batch that lost a race one by one, passing over those that changed since."""
    released = 0
    for change in changes:
        try:
            await store.write([], [], [], [change])
            released += 1
        except EntityVersionConflictError, EntityWriteError:
            continue
    return released
