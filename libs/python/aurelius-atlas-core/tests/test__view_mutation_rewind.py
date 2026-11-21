"""The view door's ``RewindStore`` composes the store and wakes its listeners only on a write that lands.

ASU-07, ASU-08, DD-679, WRS-03, WRS-04, WRS-08, DD-775, DD-777.
"""

import pytest
from aurelius_atlas_core.entity_store import EntityChange, EntityStore, TaskChange, WriteStore
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.view_mutation import RewindStore
from test__entity_store import Clock, new, registry

R = "aurelius_atlas_core.view_mutation.RewindStore"


def store() -> EntityStore:
    """A store over the in-memory documents (WRS-02: no server)."""
    return EntityStore(registry(), MemoryEntityDocuments(), clock=Clock())


def task() -> StoredTask:
    """A new propagation task, as a write records one (TSK-02)."""
    return StoredTask(guid="task-1", type="PROPAGATION")


@pytest.mark.covers(f"{R}.write", f"{R}.flush", rules=["ASU-07", "ASU-08", "WRS-03", "WRS-04"])
async def test__a_write_wakes_the_listeners_only_when_the_wrapper_is_flushed() -> None:
    """The wrapper is built on the store contract and shares its listeners by name, but it holds back the wake
    until ``flush`` - and then the real store's workers hear it, including one hooked on later (WRS-08).
    """  # noqa: D205 - one sentence
    real = store()
    heard: list[str] = []
    real.write_listeners.append(lambda: heard.append("early"))
    rewind = RewindStore(real)
    real.write_listeners.append(lambda: heard.append("late"))

    assert isinstance(rewind, WriteStore)
    assert not isinstance(rewind, EntityStore)  # it composes one, it is not one (WRS-03)
    assert rewind.documents is real.documents

    await rewind.write([EntityChange(new(rewind, qualifiedName="t"))])
    assert heard == []  # nothing wakes while the apply is open (WRS-08)

    rewind.flush()
    assert heard == ["early", "late"]
    assert rewind.write_listeners == real.write_listeners
    assert rewind.task_listeners == real.task_listeners


@pytest.mark.covers(f"{R}.write", f"{R}.undo", f"{R}.flush", rules=["WRS-08"])
async def test__a_rolled_back_write_wakes_no_worker() -> None:
    """A write the apply rolls back wakes neither the write worker nor the task worker, and the undo's own
    restore write wakes none either: the workers see nothing of documents that were prepared and undone (WRS-08).
    """  # noqa: D205 - one sentence
    real = store()
    heard: list[str] = []
    real.write_listeners.append(lambda: heard.append("write"))
    real.task_listeners.append(lambda: heard.append("task"))
    rewind = RewindStore(real)

    await rewind.write([EntityChange(new(rewind, qualifiedName="t"))], task_changes=[TaskChange(task())])
    assert heard == []  # neither wake reached the workers while the apply was open

    await rewind.undo()  # the apply fails and rewinds
    assert heard == []  # the pending wakes are dropped with the rolled-back write
    rewind.flush()  # a flush after the undo has nothing left to wake
    assert heard == []


@pytest.mark.covers(f"{R}.flush", rules=["WRS-08", "ASU-08"])
async def test__a_flush_wakes_the_task_worker_only_for_a_new_task() -> None:
    """The write worker hears every landed write; the task worker hears one that recorded a new task, and a
    write that only changed a task already stored leaves it quiet (DD-080, DD-777).
    """  # noqa: D205 - one sentence
    real = store()
    await real.write([], [], [], [TaskChange(task())])  # a task already stored, to change
    _, version = (await real.get_tasks(["task-1"]))["task-1"]
    heard: list[str] = []
    real.write_listeners.append(lambda: heard.append("write"))
    real.task_listeners.append(lambda: heard.append("task"))

    changed = RewindStore(real)
    await changed.write([EntityChange(new(changed, qualifiedName="t"))], task_changes=[TaskChange(task(), version)])
    changed.flush()
    assert heard == ["write"]  # the task changed, none was recorded: the task worker stays quiet

    recorded = RewindStore(real)
    second = StoredTask(guid="task-2", type="PROPAGATION")
    await recorded.write([EntityChange(new(recorded, qualifiedName="u"))], task_changes=[TaskChange(second)])
    recorded.flush()
    assert heard == ["write", "write", "task"]
