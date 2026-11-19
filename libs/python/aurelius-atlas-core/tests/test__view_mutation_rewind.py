"""The view door's ``RewindStore``: its writes reach the real store's listeners (ASU-07, ASU-08, DD-679)."""

import pytest
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.view_mutation import RewindStore
from test__entity_store import Clock, new, registry

R = "aurelius_atlas_core.view_mutation.RewindStore"


@pytest.mark.covers(f"{R}.write", rules=["ASU-07", "ASU-08"])
async def test__the_rewind_store_s_writes_reach_the_real_store_s_listeners() -> None:
    """The rewind store shares the real store's write and task listeners: the workers hooked to the real store
    hear a write made through it, and one hooked later too.
    """  # noqa: D205 - one sentence
    real = EntityStore(registry(), MemoryEntityDocuments(), clock=Clock())
    heard: list[str] = []
    real.write_listeners.append(lambda: heard.append("early"))
    rewind = RewindStore(real)
    real.write_listeners.append(lambda: heard.append("late"))

    await rewind.write([EntityChange(new(rewind, qualifiedName="t"))])

    assert heard == ["early", "late"]
    assert rewind.write_listeners is real.write_listeners
    assert rewind.task_listeners is real.task_listeners
