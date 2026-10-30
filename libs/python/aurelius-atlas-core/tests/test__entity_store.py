"""``EntityStore`` (ENS-02 to ENS-09) on the in-memory documents, with failures injected at each step of a write.

After ``AtlasEntityStoreV2``, ``EntityGraphMapper`` and ``AtlasGraphUtilsV2.findByUniqueAttributes`` of Atlas 2.4.0.
"""

import re
import uuid

import pytest
from aurelius_atlas_core.entity_documents import JournalEntry
from aurelius_atlas_core.entity_store import (
    LEASE_MILLISECONDS,
    EntityChange,
    EntityStore,
    EntityVersionConflictError,
    EntityWriteError,
    UniqueValueTakenError,
)
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, SimulatedCrashError
from aurelius_atlas_core.unique_key import UniqueKey
from aurelius_atlas_model.instance import AtlasEntity, EntityStatus
from aurelius_atlas_model.typedef import AtlasAttributeDef, AtlasEntityDef, AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

S = "aurelius_atlas_core.entity_store.EntityStore"


class Clock:
    """A settable clock in seconds."""

    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        """The current time."""
        return self.now


def registry() -> TypeRegistry:
    """``ref`` with a unique ``qualifiedName``; ``table`` and ``view`` are its sub types; ``table`` adds ``size``."""
    types = TypeRegistry()
    unique = AtlasAttributeDef(name="qualifiedName", type_name="string", is_unique=True)
    with types.update() as transient:
        transient.add_types(
            AtlasTypesDef(
                entity_defs=[
                    AtlasEntityDef(name="ref", attribute_defs=[unique]),
                    AtlasEntityDef(
                        name="table",
                        super_types=["ref"],
                        attribute_defs=[
                            AtlasAttributeDef(name="size", type_name="int", is_optional=True),
                            AtlasAttributeDef(name="code", type_name="int", is_optional=True, is_unique=True),
                        ],
                    ),
                    AtlasEntityDef(name="view", super_types=["ref"]),
                ]
            )
        )
    return types


@pytest.fixture
def documents() -> MemoryEntityDocuments:
    """Empty in-memory documents."""
    return MemoryEntityDocuments()


@pytest.fixture
def clock() -> Clock:
    """The store's clock."""
    return Clock()


@pytest.fixture
def store(documents: MemoryEntityDocuments, clock: Clock) -> EntityStore:
    """A store of the test types on ``documents``."""
    return EntityStore(registry(), documents, clock=clock)


def new(store: EntityStore, type_name: str = "table", **attributes: object) -> StoredEntity:
    """A new entity of ``type_name`` with ``attributes``, as stored."""
    entity_type = store.registry.entity_type(type_name)
    assert entity_type is not None
    return StoredEntity.of(
        AtlasEntity(type_name=type_name, attributes=attributes),
        entity_type,
        guid=store.new_guid(),
        now=store.now(),
        user=None,
    )


@pytest.mark.covers(f"{S}.prepare", f"{S}.new_guid", f"{S}.now", rules=["ENS-01", "ENS-02"])
async def test__guids_are_random_uuids_and_times_milliseconds(
    store: EntityStore, documents: MemoryEntityDocuments
) -> None:
    """``UUID.randomUUID().toString()``: canonical lower-case, version 4; times are epoch milliseconds."""
    await store.prepare()
    guid = store.new_guid()

    assert documents.prepared
    assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", guid)
    assert uuid.UUID(guid).version == 4
    assert guid != store.new_guid()
    assert store.now() == 1_000_000_000


@pytest.mark.covers(f"{S}.write", f"{S}.get", f"{S}.get_many", rules=["ENS-04", "ENS-07"])
async def test__written_entities_read_back_by_guid(store: EntityStore, documents: MemoryEntityDocuments) -> None:
    """A write of several entities is read back at once; unknown GUIDs read as nothing; the journal is empty after."""
    table, view = new(store, qualifiedName="t"), new(store, "view", qualifiedName="v")

    await store.write([EntityChange(table), EntityChange(view)])

    found = await store.get(table.guid)
    assert found is not None
    assert found.entity.attributes == {"ref.qualifiedName": "t"}
    assert found.entity.write_id is not None
    assert set(await store.get_many([table.guid, view.guid, table.guid, "missing"])) == {table.guid, view.guid}
    assert await store.get("missing") is None
    assert documents.journal_entries == {}


@pytest.mark.covers(f"{S}.write", rules=["ENS-05"])
async def test__a_unique_value_is_held_once_per_type(store: EntityStore, documents: MemoryEntityDocuments) -> None:
    """``PER_TYPE_UNIQUE``: another table may not take ``t``, a view may; nothing is written on a clash."""
    await store.write([EntityChange(new(store, qualifiedName="t"))])
    clash = new(store, qualifiedName="t")

    with pytest.raises(UniqueValueTakenError, match=r"unique value ref\.qualifiedName=t of type table") as raised:
        await store.write([EntityChange(clash), EntityChange(new(store, qualifiedName="other"))])
    await store.write([EntityChange(new(store, "view", qualifiedName="t"))])

    assert raised.value.key == UniqueKey("table", "ref.qualifiedName", "t")
    assert await store.get(clash.guid) is None
    assert len(documents.unique_values) == 2
    assert documents.journal_entries == {}


@pytest.mark.covers(f"{S}.write", rules=["ENS-05"])
async def test__two_entities_of_one_write_may_not_share_a_value(store: EntityStore) -> None:
    """The second reservation of one value in a write meets the first."""
    with pytest.raises(UniqueValueTakenError):
        await store.write([EntityChange(new(store, qualifiedName="t")), EntityChange(new(store, qualifiedName="t"))])


@pytest.mark.covers(f"{S}.write", f"{S}.find_by_unique_attributes", rules=["ENS-05", "ENS-06"])
async def test__a_changed_or_deleted_value_is_released(store: EntityStore) -> None:
    """A new value is reserved and the old released; a deleted entity releases its values (``removeProperty``)."""
    table = new(store, qualifiedName="t")
    await store.write([EntityChange(table)])
    table_type = store.registry.entity_type("table")
    assert table_type is not None
    found = await store.get(table.guid)
    assert found is not None

    renamed = found.entity.model_copy(update={"attributes": {"ref.qualifiedName": "u"}})
    await store.write([EntityChange(renamed, found.version)])
    assert await store.find_by_unique_attributes(table_type, {"qualifiedName": "t"}) is None
    found = await store.find_by_unique_attributes(table_type, {"qualifiedName": "u"})
    assert found is not None

    await store.write([EntityChange(found.entity.model_copy(update={"state": EntityStatus.DELETED}), found.version)])
    assert await store.find_by_unique_attributes(table_type, {"qualifiedName": "u"}) is None
    await store.write([EntityChange(new(store, qualifiedName="u"))])


@pytest.mark.covers(f"{S}.find_by_unique_attributes", rules=["ENS-06"])
async def test__a_unique_lookup_falls_back_to_sub_types(store: EntityStore) -> None:
    """``findByUniqueAttributes``: the type, else its sub types; every given unique value must match one entity."""
    table = new(store, qualifiedName="t", code=7)
    await store.write([EntityChange(table)])
    ref, table_type = store.registry.entity_type("ref"), store.registry.entity_type("table")
    assert ref is not None
    assert table_type is not None

    by_ref = await store.find_by_unique_attributes(ref, {"qualifiedName": "t"})
    by_both = await store.find_by_unique_attributes(table_type, {"qualifiedName": "t", "code": "7", "size": 1})

    assert by_ref is not None
    assert by_ref.entity.guid == table.guid
    assert by_both is not None
    assert by_both.entity.guid == table.guid
    assert await store.find_by_unique_attributes(table_type, {"qualifiedName": "t", "code": 8}) is None
    assert await store.find_by_unique_attributes(table_type, {"size": 1, "qualifiedName": None}) is None
    assert await store.find_by_unique_attributes(table_type, {"code": "x"}) is None


@pytest.mark.covers(f"{S}.write", rules=["ENS-07", "ENS-08"])
async def test__a_stale_read_fails_before_anything_is_written(store: EntityStore) -> None:
    """A version that is no longer current, or an entity that is gone, is a version conflict."""
    table = new(store, qualifiedName="t")
    await store.write([EntityChange(table)])
    found = await store.get(table.guid)
    assert found is not None
    await store.write([EntityChange(found.entity.touched(now=2, user=None), found.version)])

    with pytest.raises(EntityVersionConflictError, match=table.guid):
        await store.write([EntityChange(found.entity, found.version)])
    with pytest.raises(EntityVersionConflictError):
        await store.write([EntityChange(new(store), found.version)])


@pytest.mark.covers(f"{S}.write", rules=["ENS-07", "ENS-08"])
@pytest.mark.parametrize(("failure", "error"), [("conflict", EntityVersionConflictError), ("error", EntityWriteError)])
async def test__a_failing_entity_undoes_the_whole_write(
    store: EntityStore, documents: MemoryEntityDocuments, failure: str, error: type[Exception]
) -> None:
    """Entities written are restored or removed, reservations released, the journal entry dropped."""
    table = new(store, qualifiedName="t", size=1)
    await store.write([EntityChange(table)])
    found = await store.get(table.guid)
    assert found is not None
    added, failing = new(store, qualifiedName="added"), new(store, qualifiedName="failing")
    changed = found.entity.model_copy(update={"attributes": {"ref.qualifiedName": "t2", "table.size": 2}})
    documents.fail[failing.guid] = failure

    with pytest.raises(error):
        await store.write([EntityChange(added), EntityChange(changed, found.version), EntityChange(failing)])

    restored = await store.get(table.guid)
    assert restored is not None
    assert restored.entity.attributes == {"ref.qualifiedName": "t", "table.size": 1}
    assert await store.get(added.guid) is None
    assert len(documents.unique_values) == 1
    assert documents.journal_entries == {}


@pytest.mark.covers(f"{S}.write", rules=["ENS-07"])
async def test__a_write_past_its_lease_gives_up(
    store: EntityStore, documents: MemoryEntityDocuments, clock: Clock
) -> None:
    """A write must not start writing after recovery may have undone it (DD-046)."""
    original_reserve = documents.reserve

    async def slow_reserve(reservation: object) -> object:
        clock.now += LEASE_MILLISECONDS / 1000 + 1
        return await original_reserve(reservation)  # type: ignore[arg-type]

    documents.reserve = slow_reserve  # type: ignore[method-assign]
    table = new(store, qualifiedName="t")

    with pytest.raises(EntityWriteError, match="longer than its lease"):
        await store.write([EntityChange(table)])

    assert await store.get(table.guid) is None
    assert documents.unique_values == {}
    assert documents.journal_entries == {}


@pytest.mark.covers(f"{S}.write", rules=["ENS-07"])
async def test__an_entity_of_an_unknown_type_is_not_written(store: EntityStore) -> None:
    """The type registry must know the entity's type."""
    with pytest.raises(EntityWriteError, match="nope is not an entity type"):
        await store.write([EntityChange(StoredEntity(guid="g", type_name="nope"))])


@pytest.mark.covers(f"{S}.recover", rules=["ENS-07"])
async def test__recovery_undoes_a_write_cut_short(
    store: EntityStore, documents: MemoryEntityDocuments, clock: Clock
) -> None:
    """A crash after the bulk write leaves its entry; once its lease passed, recovery undoes it, and only it."""
    table = new(store, qualifiedName="t", size=1)
    await store.write([EntityChange(table)])
    found = await store.get(table.guid)
    assert found is not None
    added = new(store, qualifiedName="added")
    changed = found.entity.model_copy(update={"attributes": {"ref.qualifiedName": "t2"}})
    documents.crash_after_write = True

    with pytest.raises(SimulatedCrashError):
        await store.write([EntityChange(added), EntityChange(changed, found.version)])
    assert await store.recover() == 0
    clock.now += LEASE_MILLISECONDS / 1000 + 1
    assert await store.recover() == 1

    restored = await store.get(table.guid)
    assert restored is not None
    assert restored.entity.attributes == {"ref.qualifiedName": "t", "table.size": 1}
    assert await store.get(added.guid) is None
    assert {reservation.guid for reservation in documents.unique_values.values()} == {table.guid}
    assert documents.journal_entries == {}


@pytest.mark.covers(f"{S}.recover", rules=["ENS-07"])
async def test__recovery_leaves_entities_a_later_write_changed(
    store: EntityStore, documents: MemoryEntityDocuments, clock: Clock
) -> None:
    """An entity no longer carrying the write's id was written again since, and is kept."""
    table = new(store, qualifiedName="t")
    documents.crash_after_write = True
    with pytest.raises(SimulatedCrashError):
        await store.write([EntityChange(table)])
    found = await store.get(table.guid)
    assert found is not None
    later = found.entity.model_copy(update={"write_id": "later"})
    documents.entities[table.guid] = (later.to_json(), found.version)
    clock.now += LEASE_MILLISECONDS / 1000 + 1

    await store.recover()

    assert await store.get(table.guid) is not None


@pytest.mark.covers(f"{S}.recover", rules=["ENS-07"])
async def test__recovery_finishes_a_committed_write(store: EntityStore, documents: MemoryEntityDocuments) -> None:
    """A committed entry is never undone: recovery releases the values its entities no longer hold."""
    table = new(store, qualifiedName="t")
    await store.write([EntityChange(table)])
    found = await store.get(table.guid)
    assert found is not None
    old_key = UniqueKey("table", "ref.qualifiedName", "t").id
    renamed = found.entity.model_copy(update={"attributes": {"ref.qualifiedName": "u"}, "write_id": "w"})
    documents.entities[table.guid] = (renamed.to_json(), found.version)
    await documents.put_journal(
        JournalEntry(
            write_id="w", lease_until=0, before={table.guid: found.entity.to_json()}, released=[old_key], committed=True
        )
    )
    documents.unique_values[UniqueKey("table", "ref.qualifiedName", "u").id] = documents.unique_values[old_key]

    assert await store.recover() == 1

    assert old_key not in documents.unique_values
    current = await store.get(table.guid)
    assert current is not None
    assert current.entity.attributes == {"ref.qualifiedName": "u"}


@pytest.mark.covers(f"{S}.type_in_use", rules=["ENS-09"])
async def test__a_type_is_in_use_while_an_entity_of_it_exists(store: EntityStore) -> None:
    """Exactly the type, in any state: a super type of a stored entity is not in use."""
    table = new(store, qualifiedName="t")
    await store.write([EntityChange(table.model_copy(update={"state": EntityStatus.DELETED}))])

    assert await store.type_in_use("table")
    assert not await store.type_in_use("ref")


@pytest.mark.covers(f"{S}.recover", rules=["ENS-07"])
async def test__recovery_acts_on_each_entry_as_it_is_now(
    store: EntityStore, documents: MemoryEntityDocuments, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The listing may lag the journal's writes (DD-247): an entry already deleted, or committed since, as listed
    uncommitted, is not undone.
    """  # noqa: D205 - one sentence
    table = new(store, qualifiedName="t")
    await store.write([EntityChange(table)])
    stale = JournalEntry(write_id="gone", lease_until=0, before={table.guid: None})
    committed = JournalEntry(write_id="done", lease_until=0, before={table.guid: None}, committed=True)
    await documents.put_journal(committed)
    listed = [stale, committed.model_copy(update={"committed": False})]

    async def lagging() -> list[JournalEntry]:
        return listed

    monkeypatch.setattr(documents, "journal", lagging)

    assert await store.recover() == 1

    assert await store.get(table.guid) is not None
    assert await documents.get_journal("done") is None
