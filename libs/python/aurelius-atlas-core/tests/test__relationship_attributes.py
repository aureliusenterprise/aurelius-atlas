"""Relationship attributes of entities (REL-11 to REL-19) on the in-memory documents.

The expected relationships and reads are read from ``EntityGraphMapper`` (``mapObjectIdValueUsingRelationship``,
``updateRelationship``, ``mapArrayValue``, ``addInverseReference``), ``AtlasRelationshipStoreV2#getOrCreate``,
``EntityGraphRetriever`` (``mapVertexToRelationshipAttribute``, ``mapVertexToRelatedObjectId``,
``toLegacyAttribute``) and ``DeleteHandlerV1`` (``deleteEdgeReference``, ``getOwnedVertices``) of Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import (
    AtlasEntitiesWithExtInfo,
    AtlasEntityWithExtInfo,
    AtlasRelationship,
    EntityStatus,
)

M = "aurelius_atlas_core.relationship_mapper.RelationshipMapper"
R = "aurelius_atlas_core.entity_retriever.EntityRetriever"
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


def as_json(value: Any) -> Any:  # noqa: ANN401 - Atlas JSON
    """A model's JSON as a client reads it."""
    return codec.loads(codec.dumps(value.to_json()))


def entity(type_name: str, guid: str, relationships: dict[str, Any] | None = None, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401
    """An entity as Atlas JSON, with ``relationshipAttributes`` when given."""
    found: dict[str, Any] = {"typeName": type_name, "guid": guid, "attributes": attributes}
    if relationships is not None:
        found["relationshipAttributes"] = relationships
    return found


def ref(request_guid: str, type_name: str, **more: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An object id of an entity created earlier, by its request GUID."""
    return {"guid": GUIDS.get(request_guid, request_guid), "typeName": type_name, **more}


async def write(
    store: EntityStore, *entities: dict[str, Any], delete_type: DeleteType = DeleteType.SOFT
) -> dict[str, Any]:
    """The JSON answer to creating or updating these entities; their GUIDs are kept for ``g``."""
    request = AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)})
    answer = as_json(await EntityWriter(store, delete_type=delete_type).create_or_update(request))
    GUIDS.update(answer.get("guidAssignments", {}))
    return answer


def mutated(answer: dict[str, Any], operation: str) -> list[str]:
    """The GUIDs the answer lists under ``operation``."""
    return [header["guid"] for header in answer.get("mutatedEntities", {}).get(operation, [])]


async def read(store: EntityStore, guid: str) -> dict[str, Any]:
    """The entity as ``GET /entity/guid`` answers it."""
    return as_json(await EntityRetriever(store).entity_with_ext_info(guid))


async def relationships(store: EntityStore, guid: str) -> list[StoredRelationship]:
    """The relationships entity ``guid`` lists, in its order."""
    found = await store.get(guid)
    assert found is not None
    listed = found.entity.relationship_guids or []
    stored = await store.get_relationships(listed)
    return [stored[relationship].relationship for relationship in listed]


def ends(found: list[StoredRelationship]) -> list[tuple[str, str, str]]:
    """Each relationship's ends and status."""
    return [(relationship.end1_guid, relationship.end2_guid, relationship.state.value) for relationship in found]


@pytest.mark.covers(
    f"{M}.map",
    f"{M}.relationship_changes",
    f"{M}.listings",
    f"{R}.entity_with_ext_info",
    rules=["REL-11", "REL-13", "REL-17", "REL-18"],
)
async def test__relationship_values_are_created_as_relationships_and_read_back(store: EntityStore) -> None:
    """A legacy end and an array end, with relationship attributes, in one request; both ends read them."""
    answer = await write(
        store,
        entity("s_database", "-1", qualifiedName="db@cl", title="DB"),
        entity("s_column", "-2", qualifiedName="c@cl"),
        entity(
            "w_item",
            "-3",
            {
                "links": [
                    {
                        "guid": "-2",
                        "typeName": "s_column",
                        "relationshipType": "w_link",
                        "relationshipAttributes": {"typeName": "w_link", "attributes": {"weight": 3}},
                    }
                ]
            },
            qualifiedName="i@cl",
            holder={"guid": "-1", "typeName": "s_database"},
        ),
    )
    item = await read(store, g("-3"))
    database = await read(store, g("-1"))
    column = await read(store, g("-2"))
    holder, link = item["entity"]["relationshipAttributes"]["holder"], item["entity"]["relationshipAttributes"]["links"]

    assert (mutated(answer, "CREATE"), mutated(answer, "UPDATE")) == ([g("-1"), g("-2"), g("-3")], [])
    assert item["entity"]["attributes"]["holder"] == {
        "guid": g("-1"),
        "typeName": "s_database",
        "uniqueAttributes": {"qualifiedName": "db@cl"},
    }
    assert {key: value for key, value in holder.items() if key != "relationshipGuid"} == {
        "guid": g("-1"),
        "typeName": "s_database",
        "entityStatus": "ACTIVE",
        "displayText": "DB",
        "qualifiedName": "db@cl",
        "relationshipType": "w_item_holder",
        "relationshipStatus": "ACTIVE",
        "relationshipAttributes": {"typeName": "w_item_holder"},
    }
    assert [(found["guid"], found["relationshipAttributes"]) for found in link] == [
        (g("-2"), {"typeName": "w_link", "attributes": {"weight": 3, "note": None}})
    ]
    assert [found["guid"] for found in database["entity"]["relationshipAttributes"]["items"]] == [g("-3")]
    assert database["entity"]["relationshipAttributes"]["tables"] == []
    assert column["entity"]["relationshipAttributes"]["linkedBy"][0]["displayText"] == "item-i@cl"
    assert ends(await relationships(store, g("-3"))) == [(g("-3"), g("-1"), "ACTIVE"), (g("-3"), g("-2"), "ACTIVE")]


@pytest.mark.covers(f"{M}.map", rules=["REL-12", "REL-15"])
async def test__a_replaced_single_end_deletes_its_relationship_softly_or_hard(store: EntityStore) -> None:
    """Both databases become updated; a soft delete keeps the old one ``DELETED``, a hard one removes it."""
    await write(
        store,
        entity("s_database", "-1", qualifiedName="a@cl"),
        entity("s_database", "-2", qualifiedName="b@cl"),
        entity("w_item", "-3", qualifiedName="i@cl", holder=ref("-1", "s_database")),
    )
    first = (await relationships(store, g("-3")))[0]

    moved = await write(store, entity("w_item", g("-3"), qualifiedName="i@cl", holder=ref("-2", "s_database")))
    soft = await relationships(store, g("-3"))
    back = await write(
        store,
        entity("w_item", g("-3"), qualifiedName="i@cl", holder=ref("-1", "s_database")),
        delete_type=DeleteType.HARD,
    )
    hard = await relationships(store, g("-3"))
    cleared = await write(store, entity("w_item", g("-3"), {"holder": None}, qualifiedName="i@cl"))
    database = await read(store, g("-1"))

    assert mutated(moved, "UPDATE") == [g("-3"), g("-2"), g("-1")]
    assert ends(soft) == [(g("-3"), g("-1"), "DELETED"), (g("-3"), g("-2"), "ACTIVE")]
    assert (soft[0].guid, soft[0].update_time) == (first.guid, NOW)
    assert mutated(back, "UPDATE") == [g("-3"), g("-1"), g("-2")]
    assert ends(hard) == [(g("-3"), g("-1"), "DELETED"), (g("-3"), g("-1"), "ACTIVE")]
    assert (await relationships(store, g("-2"))) == []
    assert mutated(cleared, "UPDATE") == [g("-3"), g("-1")]
    assert [found["relationshipStatus"] for found in database["entity"]["relationshipAttributes"]["items"]] == [
        "DELETED",
        "DELETED",
    ]


@pytest.mark.covers(f"{M}.map", rules=["REL-13", "REL-14", "REL-15"])
async def test__an_array_end_maps_by_position_reuses_and_deletes_what_it_drops(store: EntityStore) -> None:
    """``[c1, c2]`` then ``[c2, c3]``: c2's relationship is reused, c3's created, c1's deleted and kept first."""
    await write(
        store,
        entity("s_column", "-1", qualifiedName="c1@cl"),
        entity("s_column", "-2", qualifiedName="c2@cl"),
        entity("s_column", "-3", qualifiedName="c3@cl"),
        entity("w_item", "-4", {"links": [ref("-1", "s_column"), ref("-2", "s_column"), ref("-1", "s_column")]}),
    )
    before = await relationships(store, g("-4"))

    answer = await write(
        store, entity("w_item", g("-4"), {"links": [ref("-2", "s_column"), ref("-3", "s_column")]}, qualifiedName="i")
    )
    after = await relationships(store, g("-4"))
    item = await read(store, g("-4"))

    assert [(relationship.end2_guid, relationship.index) for relationship in before] == [(g("-1"), 0), (g("-2"), 1)]
    assert mutated(answer, "UPDATE") == [g("-4"), g("-2"), g("-3"), g("-1")]
    assert [(r.end2_guid, r.state.value, r.index) for r in after] == [
        (g("-1"), "DELETED", 0),
        (g("-2"), "ACTIVE", 1),
        (g("-3"), "ACTIVE", 2),
    ]
    assert after[1].guid == before[1].guid
    assert [found["guid"] for found in item["entity"]["relationshipAttributes"]["links"]] == [g("-1"), g("-2"), g("-3")]


@pytest.mark.covers(f"{M}.map", f"{R}.entity_with_ext_info", rules=["REL-14", "REL-18"])
async def test__appending_keeps_relationships_and_a_legacy_array_reads_in_index_order(store: EntityStore) -> None:
    """``members`` appends on a partial update; ``friends`` keeps its relationships on any update."""
    await write(
        store,
        entity("s_column", "-1", qualifiedName="c1@cl"),
        entity("s_column", "-2", qualifiedName="c2@cl"),
        entity("r_node", "-3", qualifiedName="b@cl"),
        entity("r_node", "-4", qualifiedName="c@cl"),
        entity(
            "r_node", "-5", {"friends": [ref("-3", "r_node")]}, qualifiedName="a@cl", members=[ref("-2", "s_column")]
        ),
    )
    node_type = store.registry.entity_type("r_node")
    assert node_type is not None
    partial = AtlasEntityWithExtInfo.model_validate({"entity": entity("r_node", "-9", members=[ref("-1", "s_column")])})

    appended = as_json(
        await EntityWriter(store).update_by_unique_attributes(node_type, {"qualifiedName": "a@cl"}, partial)
    )
    await write(store, entity("r_node", g("-5"), {"friends": [ref("-4", "r_node")]}, qualifiedName="a@cl"))
    node = await read(store, g("-5"))

    assert mutated(appended, "PARTIAL_UPDATE") == [g("-5"), g("-1")]
    assert [found["guid"] for found in node["entity"]["relationshipAttributes"]["friends"]] == [g("-3"), g("-4")]
    assert [found["guid"] for found in node["entity"]["attributes"]["members"]] == [g("-2"), g("-1")]


@pytest.mark.covers(f"{M}.map", rules=["REL-15"])
async def test__an_owned_relationship_an_update_drops_leaves_its_entity(store: EntityStore) -> None:
    """Only the relationship is deleted, and the part is not updated, until 3.2 (DV-31)."""
    await write(store, entity("r_node", "-1", qualifiedName="p@cl"))
    await write(
        store,
        entity("r_part", "-2", {"whole": ref("-1", "r_node")}, qualifiedName="k1@cl"),
        entity("r_part", "-3", {"whole": ref("-1", "r_node")}, qualifiedName="k2@cl"),
    )

    answer = await write(store, entity("r_node", g("-1"), {"parts": [ref("-2", "r_part")]}, qualifiedName="p@cl"))
    dropped = await store.get(g("-3"))
    kept = await read(store, g("-2"))

    assert mutated(answer, "UPDATE") == [g("-1")]
    assert dropped is not None
    assert dropped.entity.state is EntityStatus.ACTIVE
    assert ends(await relationships(store, g("-3"))) == [(g("-1"), g("-3"), "DELETED")]
    assert kept["entity"]["relationshipAttributes"]["whole"]["guid"] == g("-1")


@pytest.mark.covers(f"{M}.map", rules=["REL-16"])
async def test__an_inverse_reference_gets_a_relationship_back(store: EntityStore) -> None:
    """``lead`` and ``follower`` name each other: setting one creates both relationships, as Atlas's two edges.

    Setting ``lead`` again to another tag deletes the first ``lead`` relationship only; the first tag still follows.
    """
    await write(
        store,
        entity("r_node", "-1", qualifiedName="a@cl"),
        entity("r_tag", "-2", qualifiedName="t@cl"),
        entity("r_tag", "-3", qualifiedName="u@cl"),
    )

    answer = await write(store, entity("r_node", g("-1"), qualifiedName="a@cl", lead=ref("-2", "r_tag")))
    tag = await read(store, g("-2"))
    unchanged = await write(store, entity("r_tag", g("-2"), qualifiedName="t@cl", follower=ref("-1", "r_node")))
    moved = await write(store, entity("r_node", g("-1"), qualifiedName="a@cl", lead=ref("-3", "r_tag")))

    assert mutated(answer, "UPDATE") == [g("-1"), g("-2")]
    assert tag["entity"]["attributes"]["follower"]["guid"] == g("-1")
    assert mutated(unchanged, "UPDATE") == []
    assert mutated(moved, "UPDATE") == [g("-1"), g("-3"), g("-2")]
    assert [(r.label, r.end1_guid, r.end2_guid, r.state.value) for r in await relationships(store, g("-1"))] == [
        ("__r_node.lead", g("-1"), g("-2"), "DELETED"),
        ("__r_tag.follower", g("-2"), g("-1"), "ACTIVE"),
        ("__r_node.lead", g("-1"), g("-3"), "ACTIVE"),
        ("__r_tag.follower", g("-3"), g("-1"), "ACTIVE"),
    ]


@pytest.mark.covers(f"{M}.map", f"{R}.entity_with_ext_info", rules=["REL-12", "REL-17", "REL-18"])
async def test__ends_read_in_their_directions_and_a_legacy_end_without_attribute_reads_as_object_ids(
    store: EntityStore,
) -> None:
    """``keeper`` and ``kept``; ``friends`` both ways; ``badge`` (``IN``) and ``badgeOf``, read into ``attributes``."""
    await write(
        store,
        entity("s_database", "-1", qualifiedName="db@cl"),
        entity("s_column", "-2", qualifiedName="c@cl"),
        entity("r_node", "-3", qualifiedName="b@cl"),
        entity(
            "r_node",
            "-4",
            {"friends": [ref("-3", "r_node")], "badge": ref("-2", "s_column")},
            qualifiedName="a@cl",
            keeper=ref("-1", "s_database"),
        ),
    )
    database, column, friend = [await read(store, g(guid)) for guid in ("-1", "-2", "-3")]

    assert [found["guid"] for found in database["entity"]["relationshipAttributes"]["kept"]] == [g("-4")]
    assert [found["guid"] for found in friend["entity"]["relationshipAttributes"]["friends"]] == [g("-4")]
    assert column["entity"]["relationshipAttributes"]["badgeOf"]["guid"] == g("-4")
    assert column["entity"]["attributes"]["badgeOf"] == {"guid": g("-4"), "typeName": "r_node"}
    assert ends(await relationships(store, g("-2"))) == [(g("-2"), g("-4"), "ACTIVE")]


@pytest.mark.covers(f"{M}.map", rules=["REL-13"])
async def test__a_relationship_value_with_invalid_attributes_fails_and_writes_nothing(store: EntityStore) -> None:
    """The relationship type's checks run as the relationship is created (``RELATIONSHIP_CRUD_INVALID_PARAMS``)."""
    await write(store, entity("s_column", "-1", qualifiedName="c@cl"))
    link = ref(
        "-1",
        "s_column",
        relationshipType="w_link",
        relationshipAttributes={"typeName": "w_link", "attributes": {"weight": "heavy"}},
    )

    with pytest.raises(AtlasError) as raised:
        await write(store, entity("w_item", "-2", {"links": [link]}, qualifiedName="i@cl"))

    assert raised.value.code is AtlasErrorCode.RELATIONSHIP_CRUD_INVALID_PARAMS
    assert await relationships(store, g("-1")) == []


@pytest.mark.covers(f"{M}.map", rules=["REL-13"])
async def test__an_entity_write_reuses_a_relationship_created_over_rest(store: EntityStore) -> None:
    """``[c2, c1]`` over a relationship to c1: c2's replaces it at 0, then c1's is found again, unchanged, for 1."""
    await write(
        store,
        entity("s_column", "-1", qualifiedName="c1@cl"),
        entity("s_column", "-2", qualifiedName="c2@cl"),
        entity("w_item", "-3", qualifiedName="i@cl"),
    )
    created = await RelationshipStore(store).create(
        AtlasRelationship.model_validate({"typeName": "w_link", "end1": {"guid": g("-3")}, "end2": {"guid": g("-1")}})
    )

    answer = await write(
        store, entity("w_item", g("-3"), {"links": [ref("-2", "s_column"), ref("-1", "s_column")]}, qualifiedName="i")
    )
    found = await relationships(store, g("-3"))

    assert [(r.end2_guid, r.index) for r in found] == [(g("-1"), 1), (g("-2"), 0)]
    assert (found[0].guid, found[0].create_time) == (created.guid, NOW)
    assert mutated(answer, "UPDATE") == [g("-3"), g("-2")]


@pytest.mark.covers("aurelius_atlas_core.entity_writer.EntityWriter.delete_by_id", rules=["REL-19"])
async def test__deleting_a_whole_deletes_its_parts_through_the_composition(store: EntityStore) -> None:
    """A soft delete reaches the parts; a purge then removes them too; a part the whole dropped is left."""
    await write(store, entity("r_node", "-1", qualifiedName="p@cl"))
    await write(
        store,
        *(entity("r_part", f"-{n}", {"whole": ref("-1", "r_node")}, qualifiedName=f"k{n}@cl") for n in (2, 3, 4)),
    )
    await write(
        store, entity("r_node", g("-1"), {"parts": [ref("-2", "r_part"), ref("-3", "r_part")]}, qualifiedName="p@cl")
    )
    writer = EntityWriter(store)

    deleted = as_json(await writer.delete_by_id(g("-1")))
    purged = as_json(await writer.purge_by_ids([g("-1")]))
    left = await store.get(g("-4"))

    assert mutated(deleted, "DELETE") == [g("-1"), g("-3"), g("-2")]
    assert mutated(purged, "PURGE") == [g("-1"), g("-3"), g("-2")]
    assert left is not None
    assert left.entity.state is EntityStatus.ACTIVE
