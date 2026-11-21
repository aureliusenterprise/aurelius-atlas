"""The view door's ``RewindStore`` composes the store and reaches the real store's listeners.

ASU-07, ASU-08, DD-679, WRS-03, WRS-04, DD-775.
"""

import pytest
from aurelius_atlas_core.entity_store import EntityChange, EntityStore, WriteStore
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.view_mutation import RewindStore
from test__entity_store import Clock, new, registry

R = "aurelius_atlas_core.view_mutation.RewindStore"


@pytest.mark.covers(f"{R}.write", rules=["ASU-07", "ASU-08", "WRS-03", "WRS-04"])
async def test__the_rewind_store_s_writes_reach_the_real_store_s_listeners() -> None:
    """The rewind store shares the real store's write and task listeners by name, and it is built on the store
    contract: the workers hooked to the real store hear a write made through the wrapper, and one hooked
    later too. The wrapper is not an ``EntityStore`` - it composes one (WRS-03) - and it reaches no private
    field of it (WRS-04).
    """  # noqa: D205 - one sentence
    real = EntityStore(registry(), MemoryEntityDocuments(), clock=Clock())
    heard: list[str] = []
    real.write_listeners.append(lambda: heard.append("early"))
    rewind = RewindStore(real)
    real.write_listeners.append(lambda: heard.append("late"))

    assert isinstance(rewind, WriteStore)
    assert not isinstance(rewind, EntityStore)
    assert rewind.documents is real.documents

    await rewind.write([EntityChange(new(rewind, qualifiedName="t"))])

    assert heard == ["early", "late"]
    assert rewind.write_listeners == real.write_listeners
    assert rewind.task_listeners == real.task_listeners
