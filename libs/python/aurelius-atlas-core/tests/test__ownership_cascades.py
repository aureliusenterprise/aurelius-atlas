"""Owned entities an update drops, and their revival (OWN-01 to OWN-04), on the in-memory documents.

The expected deletes and responses are read from ``EntityGraphMapper`` (``mapToVertexByTypeCategory``,
``removeUnusedArrayEntries``, ``removeUnusedMapEntries``, ``updateInConsistentOwnedMapVertices``,
``mapAttributesAndClassifications``) and ``DeleteHandlerV1`` (``deleteEdgeReference``, ``deleteTypeVertex``) of
Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntityWithExtInfo, EntityStatus

W = "aurelius_atlas_core.entity_writer.EntityWriter"
T = "aurelius_atlas_core.transaction_view"
V = f"{T}.TransactionView"
P = f"{T}.EntityView"
NOW = 5000


@pytest.fixture
def store() -> EntityStore:
    """A store of the sample, write and relationship types at time ``NOW``."""
    return EntityStore(sample_registry(relationships=True), MemoryEntityDocuments(), clock=lambda: NOW / 1000)


GUIDS: dict[str, str] = {}
"""The GUIDs the writes of a test assigned, by the request's GUID."""


@pytest.fixture(autouse=True)
def _guids() -> None:
    GUIDS.clear()


def g(request_guid: str) -> str:
    """The GUID assigned to the request's ``request_guid``."""
    return GUIDS[request_guid]


def entity(type_name: str, guid: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An entity as Atlas JSON."""
    return {"typeName": type_name, "guid": guid, "attributes": attributes}


def ref(request_guid: str, type_name: str = "s_column") -> dict[str, Any]:
    """An object id of an entity created earlier, by its request GUID."""
    return {"guid": GUIDS.get(request_guid, request_guid), "typeName": type_name}


async def write(
    store: EntityStore, *entities: dict[str, Any], delete_type: DeleteType = DeleteType.SOFT
) -> dict[str, Any]:
    """The JSON answer to creating or updating these entities; their GUIDs are kept for ``g``."""
    request = AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)})
    answer = codec.loads(
        codec.dumps((await EntityWriter(store, delete_type=delete_type).create_or_update(request)).to_json())
    )
    GUIDS.update(answer.get("guidAssignments", {}))
    return answer


def mutated(answer: dict[str, Any]) -> dict[str, list[str]]:
    """The GUIDs the answer lists, by operation."""
    return {
        operation: [header["guid"] for header in headers]
        for operation, headers in answer.get("mutatedEntities", {}).items()
    }


async def state(store: EntityStore, request_guid: str) -> EntityStatus | None:
    """The state of an entity, or None when it is gone."""
    found = await store.get(g(request_guid))
    return None if found is None else found.entity.state


def stored(found: Any, name: str) -> Any:  # noqa: ANN401 - a stored value
    """The stored value of attribute ``name`` of a found entity."""
    return next((value for key, value in found.entity.attributes.items() if key.rpartition(".")[2] == name), None)


async def columns(store: EntityStore, *names: str) -> None:
    """Columns ``-1``, ``-2``, … with these qualified names."""
    await write(store, *(entity("s_column", f"-{n}", qualifiedName=name) for n, name in enumerate(names, start=1)))


@pytest.mark.covers(
    f"{W}.create_or_update",
    f"{V}.get_many",
    f"{V}.referring",
    f"{P}.get_many",
    f"{P}.get_relationships",
    f"{P}.referring",
    rules=["OWN-01", "OWN-02", "OWN-03"],
)
async def test__owned_entities_an_update_drops_are_deleted_and_their_referrers_changed(store: EntityStore) -> None:
    """A single replaced, an array element and a map entry dropped; a referrer of one is reported as updated."""
    await columns(store, "c1@cl", "c2@cl", "c3@cl", "c4@cl")
    await write(
        store,
        entity("s_table", "-5", qualifiedName="t@cl", columns=[ref("-1"), ref("-2")], byName={"x": ref("-3")}),
        entity("w_item", "-6", qualifiedName="i@cl", peers=[ref("-2")]),
    )

    answer = await write(
        store, entity("s_table", g("-5"), qualifiedName="t@cl", columns=[ref("-1")], byName={"x": ref("-4")})
    )

    assert mutated(answer) == {"UPDATE": [g("-5"), g("-6")], "DELETE": [g("-2"), g("-3")]}
    assert [await state(store, guid) for guid in ("-1", "-2", "-3", "-4")] == [
        EntityStatus.ACTIVE,
        EntityStatus.DELETED,
        EntityStatus.DELETED,
        EntityStatus.ACTIVE,
    ]
    referrer = await store.get(g("-6"))
    assert referrer is not None
    assert (referrer.entity.update_time, stored(referrer, "peers")) == (NOW, [g("-2")])


@pytest.mark.covers(
    f"{W}.create_or_update",
    f"{V}.get_relationships",
    "aurelius_atlas_core.relationship_mapper.RelationshipMapper.pending",
    "aurelius_atlas_core.relationship_mapper.RelationshipMapper.is_new",
    rules=["OWN-01", "OWN-02"],
)
async def test__a_hard_update_removes_what_it_drops_with_what_that_owns(store: EntityStore) -> None:
    """The dropped part goes, its relationship and the referrer's reference with it; a partial append drops none."""
    await columns(store, "c1@cl", "c2@cl")
    await write(store, entity("r_node", "-3", qualifiedName="n@cl", owns=[ref("-1")]))
    await write(
        store,
        {**entity("r_part", "-4", qualifiedName="p@cl"), "relationshipAttributes": {"whole": ref("-3", "r_node")}},
    )
    node_type = store.registry.entity_type("r_node")
    assert node_type is not None
    partial = AtlasEntityWithExtInfo.model_validate({"entity": entity("r_node", "-9", owns=[ref("-2")])})

    appended = await EntityWriter(store).update_by_unique_attributes(node_type, {"qualifiedName": "n@cl"}, partial)
    answer = await write(
        store,
        {**entity("r_node", g("-3"), qualifiedName="n@cl", owns=[ref("-2")]), "relationshipAttributes": {"parts": []}},
        delete_type=DeleteType.HARD,
    )
    node = await store.get(g("-3"))

    assert appended.mutated_entities is not None
    assert "DELETE" not in codec.loads(codec.dumps(appended.to_json()))["mutatedEntities"]
    assert mutated(answer) == {"UPDATE": [g("-3")], "DELETE": [g("-4"), g("-1")]}
    assert (await state(store, "-1"), await state(store, "-4")) == (None, None)
    assert node is not None
    assert (node.entity.relationship_guids, stored(node, "owns")) == (None, [g("-2")])


@pytest.mark.covers(f"{W}.create_or_update", rules=["OWN-02"])
async def test__a_mandatory_reference_to_a_dropped_entity_fails_the_update(store: EntityStore) -> None:
    """``INTERNAL_ERROR``, and nothing of the update is written."""
    await columns(store, "c1@cl")
    await write(store, entity("r_node", "-2", qualifiedName="n@cl", owns=[ref("-1")]))
    await write(store, entity("r_pin", "-3", qualifiedName="pin@cl", pinned=ref("-1")))

    with pytest.raises(AtlasError) as raised:
        await write(store, entity("r_node", g("-2"), qualifiedName="n@cl", owns=[]), delete_type=DeleteType.HARD)

    node = await store.get(g("-2"))
    assert raised.value.code is AtlasErrorCode.INTERNAL_ERROR
    assert await state(store, "-1") is EntityStatus.ACTIVE
    assert node is not None
    assert stored(node, "owns") == [g("-1")]


@pytest.mark.covers(f"{W}.create_or_update", rules=["OWN-04"])
async def test__an_owned_map_entry_that_keeps_a_deleted_entity_revives_it(store: EntityStore) -> None:
    """The column, deleted on its own, is ``ACTIVE`` again after the table's next update keeps it; not reported."""
    await columns(store, "c1@cl")
    await write(store, entity("s_table", "-2", qualifiedName="t@cl", byName={"x": ref("-1")}))
    await EntityWriter(store).delete_by_id(g("-1"))

    answer = await write(store, entity("s_table", g("-2"), qualifiedName="t@cl", name="again", byName={"x": ref("-1")}))

    assert mutated(answer) == {"UPDATE": [g("-2")]}
    assert await state(store, "-1") is EntityStatus.ACTIVE


@pytest.mark.covers(f"{W}.create_or_update", rules=["OWN-02", "AUD-02"])
@pytest.mark.parametrize("delete_type", [DeleteType.SOFT, DeleteType.HARD])
async def test__a_part_moved_and_dropped_in_one_request_is_deleted_with_its_new_relationship(
    store: EntityStore, delete_type: DeleteType
) -> None:
    """B takes the part, A drops it: the delete still reaches it, and the relationship B just got with it.

    The part, made updated by B's new relationship, is listed as deleted only, as ``pruneResponse`` leaves it.
    """
    await write(store, entity("r_node", "-1", qualifiedName="a@cl"), entity("r_node", "-2", qualifiedName="b@cl"))
    part = {**entity("r_part", "-3", qualifiedName="p@cl"), "relationshipAttributes": {"whole": ref("-1", "r_node")}}
    await write(store, part)

    answer = await write(
        store,
        {**entity("r_node", g("-2"), qualifiedName="b@cl"), "relationshipAttributes": {"parts": [ref("-3", "r_part")]}},
        {**entity("r_node", g("-1"), qualifiedName="a@cl"), "relationshipAttributes": {"parts": []}},
        delete_type=delete_type,
    )
    taker = await store.get(g("-2"))
    listed = await store.get_relationships((taker.entity.relationship_guids or []) if taker else [])

    assert mutated(answer) == {"UPDATE": [g("-2"), g("-1")], "DELETE": [g("-3")]}
    if delete_type is DeleteType.SOFT:
        assert await state(store, "-3") is EntityStatus.DELETED
        assert [found.relationship.state.value for found in listed.values()] == ["DELETED"]
    else:
        assert await state(store, "-3") is None
        assert listed == {}
