"""Deleting and purging entities (EDL-02 to EDL-10) on the in-memory documents.

The expected states and responses are read from ``AtlasEntityStoreV2`` (``deleteById``, ``deleteByIds``,
``deleteByUniqueAttributes``, ``purgeByIds``), ``DeleteHandlerV1``, ``SoftDeleteHandlerV1``, ``HardDeleteHandlerV1``
and ``DeleteType`` of Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.delete_handler import owned_guids
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_types, write_types
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, SimulatedCrashError
from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, EntityStatus
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

W = "aurelius_atlas_core.entity_writer.EntityWriter"
S = "aurelius_atlas_core.entity_store.EntityStore"

STRICT_TYPES = {
    "entityDefs": [
        {"name": "__internal"},
        {"name": "w_hidden", "superTypes": ["__internal", "s_ref"]},
        {
            "name": "w_strict",
            "superTypes": ["s_ref"],
            "attributeDefs": [
                {"name": "must", "typeName": "s_database", "isOptional": True, "cardinality": "SINGLE"},
                {"name": "musts", "typeName": "array<s_database>", "isOptional": True, "cardinality": "LIST"},
                {"name": "named", "typeName": "map<string,s_database>", "isOptional": True, "cardinality": "SINGLE"},
            ],
        },
    ]
}
"""Types with references made mandatory by a test, and an internal type."""


class Clock:
    """A clock a test moves on."""

    def __init__(self) -> None:
        self.now = 1000

    def __call__(self) -> float:
        """The time in seconds, as ``time.time`` gives it."""
        return self.now / 1000


@pytest.fixture
def clock() -> Clock:
    """The store's clock, at 1000."""
    return Clock()


@pytest.fixture
def documents() -> MemoryEntityDocuments:
    """The documents the store keeps entities in."""
    return MemoryEntityDocuments()


def registry(*, strict: bool = False) -> TypeRegistry:
    """The sample and write types, and the strict ones with ``strict``."""
    found = TypeRegistry()
    with found.update() as transient:
        transient.add_types(sample_types())
        transient.add_types(write_types())
        transient.add_types(AtlasTypesDef.model_validate(STRICT_TYPES))
        if strict:
            for name in ("must", "musts", "named"):
                attribute = transient.entity_type("w_strict").struct_def.get_attribute(name)  # type: ignore[union-attr]
                assert attribute is not None
                attribute.is_optional = False
                attribute.values_min_count = 1
    return found


@pytest.fixture
def store(documents: MemoryEntityDocuments, clock: Clock) -> EntityStore:
    """A store of the sample, write and strict types."""
    return EntityStore(registry(), documents, clock=clock)


GUIDS: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _guids() -> None:
    GUIDS.clear()


def g(request_guid: str) -> str:
    """The GUID given to the request's ``request_guid``."""
    return GUIDS[request_guid]


def as_json(value: Any) -> Any:  # noqa: ANN401 - Atlas JSON
    """A model's JSON as a client reads it."""
    return codec.loads(codec.dumps(value.to_json()))


async def create(store: EntityStore, *entities: dict[str, Any]) -> None:
    """Create these entities, given as ``(type, request GUID, attributes)`` JSON; their GUIDs are kept for ``g``."""
    answer = await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": entities}))
    GUIDS.update(answer.guid_assignments or {})


def entity(type_name: str, guid: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An entity as Atlas JSON."""
    return {"typeName": type_name, "guid": guid, "attributes": attributes}


def ref(request_guid: str, type_name: str = "s_column") -> dict[str, str]:
    """A reference to an entity of the request."""
    return {"guid": request_guid, "typeName": type_name}


async def state(store: EntityStore, request_guid: str) -> EntityStatus | None:
    """The state of an entity, or None when it is removed."""
    found = await store.get(g(request_guid))
    return None if found is None else found.entity.state


async def table_with_columns(store: EntityStore) -> None:
    """Database ``-1``; table ``-2`` owning ``-3`` in an array, ``-4`` in a map, ``-5`` by a soft reference."""
    await create(
        store,
        entity("s_database", "-1", qualifiedName="db@cl"),
        entity(
            "s_table",
            "-2",
            qualifiedName="t@cl",
            db=ref("-1", "s_database"),
            columns=[ref("-3")],
            byName={"x": ref("-4")},
            spare=[ref("-5")],
        ),
        entity("s_column", "-3", qualifiedName="c3@cl"),
        entity("s_column", "-4", qualifiedName="c4@cl"),
        entity("s_column", "-5", qualifiedName="c5@cl"),
    )


@pytest.mark.covers(
    f"{W}.delete_by_id",
    "aurelius_atlas_core.delete_handler.DeleteHandler.delete_entities",
    rules=["EDL-03", "EDL-05", "EDL-06", "EDL-08"],
)
async def test__a_soft_delete_marks_the_entity_and_what_it_owns_deleted(store: EntityStore, clock: Clock) -> None:
    """Depth first, the last owned reference first; headers as read before; unique values are free again."""
    await table_with_columns(store)
    clock.now = 2000

    answer = as_json(await EntityWriter(store).delete_by_id(g("-2")))

    assert [(h["guid"], h["status"]) for h in answer["mutatedEntities"]["DELETE"]] == [
        (g("-2"), "ACTIVE"),
        (g("-5"), "ACTIVE"),
        (g("-4"), "ACTIVE"),
        (g("-3"), "ACTIVE"),
    ]
    assert "classifications" not in answer["mutatedEntities"]["DELETE"][0]
    assert "guidAssignments" not in answer
    table = await store.get(g("-2"))
    assert table is not None
    assert (table.entity.state, table.entity.update_time, table.entity.attributes["s_table.db"]) == (
        EntityStatus.DELETED,
        2000,
        g("-1"),
    )
    assert await state(store, "-1") is EntityStatus.ACTIVE
    await create(store, entity("s_table", "-9", qualifiedName="t@cl"))
    assert g("-9") != g("-2")
    assert as_json(await EntityWriter(store).delete_by_id(g("-2"))) == {}
    assert as_json(await EntityWriter(store).delete_by_id("nope")) == {}


@pytest.mark.covers(f"{W}.delete_by_ids", rules=["EDL-04", "EDL-06", "EDL-07", "EDL-08"])
async def test__deleting_a_referenced_entity_changes_those_referring_to_it(store: EntityStore, clock: Clock) -> None:
    """Soft: the reference stays; hard: it goes; either way the referrer is reported updated."""
    await table_with_columns(store)
    await create(
        store,
        entity("s_database", "-6", qualifiedName="db2@cl"),
        entity(
            "w_strict",
            "-7",
            musts=[ref(g("-1"), "s_database"), ref("-6", "s_database")],
            named={"a": ref("-6", "s_database")},
        ),
    )
    clock.now = 2000

    soft = as_json(await EntityWriter(store).delete_by_ids([g("-1")]))
    hard = as_json(await EntityWriter(store, delete_type=DeleteType.HARD).delete_by_ids([g("-6")]))

    assert [h["guid"] for h in soft["mutatedEntities"]["DELETE"]] == [g("-1")]
    assert sorted(h["guid"] for h in soft["mutatedEntities"]["UPDATE"]) == sorted([g("-2"), g("-7")])
    assert [h["guid"] for h in hard["mutatedEntities"]["UPDATE"]] == [g("-7")]
    strict = await store.get(g("-7"))
    assert strict is not None
    assert strict.entity.attributes["w_strict.musts"] == [g("-1")]
    assert strict.entity.attributes["w_strict.named"] == {}
    assert strict.entity.update_time == 2000
    assert await state(store, "-6") is None
    with pytest.raises(AtlasError, match="invalid parameters: Guid\\(s\\) not specified"):
        await EntityWriter(store).delete_by_ids([])


@pytest.mark.covers(
    f"{W}.purge_by_ids",
    rules=["EDL-03", "EDL-05", "EDL-06", "EDL-07", "EDL-08"],
)
async def test__a_purge_removes_deleted_entities_and_the_references_to_them(store: EntityStore) -> None:
    """``ACTIVE`` ones are left; headers with ``classifications``; referrers change but are not reported."""
    await table_with_columns(store)
    await create(store, entity("w_item", "-8", qualifiedName="i@cl", peers=[ref(g("-3"))]))
    writer = EntityWriter(store)

    untouched = as_json(await writer.purge_by_ids([g("-2")]))
    await writer.delete_by_id(g("-2"))
    purged = as_json(await writer.purge_by_ids([g("-2"), "nope"]))

    assert untouched == {}
    assert list(purged["mutatedEntities"]) == ["PURGE"]
    assert [h["guid"] for h in purged["mutatedEntities"]["PURGE"]] == [g("-2"), g("-5"), g("-4"), g("-3")]
    assert {(h["status"], str(h["classifications"])) for h in purged["mutatedEntities"]["PURGE"]} == {("DELETED", "[]")}
    assert [await state(store, guid) for guid in ("-2", "-3", "-4", "-5")] == [None] * 4
    item = await store.get(g("-8"))
    assert item is not None
    assert item.entity.attributes["w_item.peers"] == []
    with pytest.raises(AtlasError, match="invalid parameters: Guid\\(s\\) not specified"):
        await writer.purge_by_ids([])


@pytest.mark.covers(f"{W}.delete_by_unique_attributes", rules=["EDL-02", "EDL-03", "EDL-04"])
async def test__an_entity_is_deleted_by_its_unique_values(store: EntityStore) -> None:
    """The ``ACTIVE`` holder, hard on request; no values fail with Java's one-parameter message."""
    await create(store, entity("s_database", "-1", qualifiedName="db@cl"))
    database_type = store.registry.entity_type("s_database")
    assert database_type is not None
    writer = EntityWriter(store)

    answer = as_json(
        await writer.delete_by_unique_attributes(database_type, {"qualifiedName": "db@cl"}, DeleteType.HARD)
    )

    assert [h["guid"] for h in answer["mutatedEntities"]["DELETE"]] == [g("-1")]
    assert await state(store, "-1") is None
    assert as_json(await writer.delete_by_unique_attributes(database_type, {"qualifiedName": "db@cl"})) == {}
    with pytest.raises(AtlasError) as raised:
        await writer.delete_by_unique_attributes(database_type, {})
    assert raised.value.message == "Instance {} with unique attribute {1} does not exist"
    with pytest.raises(AtlasError, match="Given instance guid  is invalid/not found"):
        await writer.delete_by_id("")


@pytest.mark.covers(
    f"{W}.delete_by_id", "aurelius_atlas_model.errors.AtlasError.of_message", rules=["EDL-07", "EDL-09"]
)
async def test__a_mandatory_reference_to_a_deleted_entity_fails_the_delete(documents: MemoryEntityDocuments) -> None:
    """``INTERNAL_ERROR`` with Atlas's text, naming the referrer's GUID (DV-26); nothing is written."""
    lenient = EntityStore(registry(), documents)
    await create(
        lenient,
        entity("s_database", "-1", qualifiedName="db@cl"),
        entity("w_strict", "-2", must=ref("-1", "s_database")),
        entity("w_strict", "-3", musts=[ref("-1", "s_database")]),
        entity("w_strict", "-4", named={"k": ref("-1", "s_database")}),
    )
    strict = EntityStore(registry(strict=True), documents)
    writer = EntityWriter(strict)
    expected = {
        "-2": f"Cannot unset required attribute w_strict.must on {g('-2')} edge = __w_strict.must",
        "-3": f"Cannot remove array element from required attribute w_strict.musts on {g('-3')} __w_strict.musts",
        "-4": (
            f"Cannot remove map entry w_strict.named from required attribute w_strict.named on {g('-4')} "
            "__w_strict.named"
        ),
    }

    for referrer, message in expected.items():
        with pytest.raises(AtlasError) as raised:
            await writer.delete_by_id(g("-1"))
        assert (raised.value.code, raised.value.message) == (AtlasErrorCode.INTERNAL_ERROR, message)
        assert await state(strict, "-1") is EntityStatus.ACTIVE
        await EntityWriter(lenient, delete_type=DeleteType.HARD).delete_by_id(g(referrer))


@pytest.mark.covers(f"{W}.delete_by_id", rules=["EDL-06", "EDL-09"])
async def test__an_internal_entity_is_removed_even_by_a_soft_delete_and_races_are_run_again(
    store: EntityStore, documents: MemoryEntityDocuments
) -> None:
    """``isInternalType`` forces the removal; one lost race runs the delete again."""
    await create(store, entity("w_hidden", "-1", qualifiedName="h@cl"), entity("s_ref", "-2", qualifiedName="r@cl"))
    documents.fail[g("-2")] = "conflict"

    await EntityWriter(store).delete_by_id(g("-1"))
    retried = as_json(await EntityWriter(store).delete_by_id(g("-2")))

    assert await state(store, "-1") is None
    assert [h["guid"] for h in retried["mutatedEntities"]["DELETE"]] == [g("-2")]


@pytest.mark.covers(f"{S}.write", f"{S}.recover", f"{S}.referring", rules=["EDL-09", "EDL-10"])
async def test__a_removal_is_journaled_undone_on_failure_and_recovered_after_a_crash(
    store: EntityStore, documents: MemoryEntityDocuments, clock: Clock
) -> None:
    """A failed or interrupted write puts a removed entity back; referrers are found by their references."""
    await create(
        store, entity("s_database", "-1", qualifiedName="db@cl"), entity("s_table", "-2", db=ref("-1", "s_database"))
    )
    database = await store.get(g("-1"))
    table = await store.get(g("-2"))
    assert database is not None
    assert table is not None
    assert [found.entity.guid for found in await store.referring([g("-1")])] == [g("-2")]
    assert table.entity.references == [g("-1")]

    documents.fail[g("-2")] = "error"
    with pytest.raises(Exception, match="could not be written"):
        await store.write(
            [EntityChange(database.entity, database.version, remove=True), EntityChange(table.entity, table.version)]
        )
    assert await store.get(g("-1")) is not None

    database = await store.get(g("-1"))
    assert database is not None
    documents.crash_after_write = True
    with pytest.raises(SimulatedCrashError):
        await store.write([EntityChange(database.entity, database.version, remove=True)])
    assert await store.get(g("-1")) is None
    clock.now += 3_600_000
    assert await store.recover() == 1
    restored = await store.get(g("-1"))
    assert restored is not None
    assert restored.entity.state is EntityStatus.ACTIVE
    with pytest.raises(Exception, match="without the version"):
        await store.write([EntityChange(restored.entity, remove=True)])


@pytest.mark.covers(
    "aurelius_atlas_core.delete_type.DeleteType.of",
    "aurelius_atlas_core.delete_handler.owned_guids",
    "aurelius_atlas_core.stored_entity.StoredEntity.reference_guids",
    rules=["EDL-04", "EDL-05", "EDL-10"],
)
async def test__delete_types_owned_guids_and_reference_guids(store: EntityStore) -> None:
    """``soft``/``hard`` in any case; owned GUIDs in attribute order; references without soft or struct ones."""
    await table_with_columns(store)
    table = await store.get(g("-2"))
    table_type = store.registry.entity_type("s_table")
    assert table is not None
    assert table_type is not None

    assert [DeleteType.of(text) for text in ("SOFT", "hard", "purge", None)] == [
        DeleteType.SOFT,
        DeleteType.HARD,
        DeleteType.DEFAULT,
        DeleteType.DEFAULT,
    ]
    assert owned_guids(table.entity, table_type) == [g("-3"), g("-4"), g("-5")]
    assert table.entity.reference_guids(table_type) == [g("-1"), g("-3"), g("-4")]
