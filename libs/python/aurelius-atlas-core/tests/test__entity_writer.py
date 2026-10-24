"""``EntityWriter`` (EWR-02 to EWR-17, REL-11) on the in-memory documents.

The expected stored values and responses are read from ``AtlasEntityStoreV2`` (``createOrUpdate``,
``preCreateOrUpdate``, ``updateByUniqueAttributes``, ``updateEntityAttributeByGuid``), ``EntityGraphMapper`` and the
discovery classes of Apache Atlas 2.4.0, and its tests ``AtlasEntityStoreV2Test`` and ``EntityV2JerseyResourceIT``.
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter, compact_attributes
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasEntityWithExtInfo

W = "aurelius_atlas_core.entity_writer"
NOW = 5000


@pytest.fixture
def documents() -> MemoryEntityDocuments:
    """The documents the store keeps entities in."""
    return MemoryEntityDocuments()


@pytest.fixture
def store(documents: MemoryEntityDocuments) -> EntityStore:
    """A store of the sample and write types at time ``NOW``."""
    return EntityStore(sample_registry(writes=True), documents, clock=lambda: NOW / 1000)


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


def bulk(*entities: dict[str, Any], referred: dict[str, Any] | None = None) -> AtlasEntitiesWithExtInfo:
    """A bulk request of these entities as Atlas JSON."""
    return AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities), "referredEntities": referred or {}})


def entity(type_name: str, guid: str | None, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An entity as Atlas JSON."""
    return {"typeName": type_name, "guid": guid, "attributes": attributes}


async def write(store: EntityStore, *entities: dict[str, Any], **referred: Any) -> dict[str, Any]:  # noqa: ANN401
    """The JSON answer to creating or updating these entities; their GUIDs are kept for ``g``."""
    answer = as_json(await EntityWriter(store).create_or_update(bulk(*entities, referred=referred)))
    GUIDS.update(answer.get("guidAssignments", {}))
    return answer


async def stored(store: EntityStore, guid: str) -> dict[str, Any]:
    """The stored attribute values of an entity, by attribute name."""
    found = await store.get(guid)
    assert found is not None
    return {name.rpartition(".")[2]: value for name, value in found.entity.attributes.items()}


async def failure(store: EntityStore, *entities: dict[str, Any]) -> tuple[AtlasErrorCode, str]:
    """The code and message a write of these entities fails with."""
    with pytest.raises(AtlasError) as raised:
        await EntityWriter(store).create_or_update(bulk(*entities))
    return raised.value.code, raised.value.message


def header(
    guid: str, type_name: str, qualified_name: str, name: str | None = None, *, classifications: bool = True
) -> dict[str, Any]:
    """A header as a mutation response has it: ``""`` for no name, displayed by name, else qualified name (ERD-07)."""
    found: dict[str, Any] = {
        "typeName": type_name,
        "attributes": {"qualifiedName": qualified_name, "name": "" if name is None else name},
        "guid": guid,
        "status": "ACTIVE",
        "displayText": qualified_name if name is None else name,
        "classificationNames": [],
        "meaningNames": [],
        "meanings": [],
        "isIncomplete": False,
        "labels": [],
    }
    if classifications:
        found["classifications"] = []
    return found


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update", rules=["EWR-02"])
async def test__a_request_without_entities_or_with_a_null_or_unknown_one_fails(store: EntityStore) -> None:
    """``INVALID_PARAMETERS`` for none and for a null entity; ``TYPE_NAME_INVALID`` for an unknown type."""
    writer = EntityWriter(store)
    for request, message in [
        (bulk(), "invalid parameters: no entities to create/update."),
        (None, "invalid parameters: no entities to create/update."),
        (AtlasEntityWithExtInfo(), "invalid parameters: found null entity"),
    ]:
        with pytest.raises(AtlasError) as raised:
            await writer.create_or_update(request)
        assert (raised.value.code, raised.value.message) == (AtlasErrorCode.INVALID_PARAMETERS, message)

    assert await failure(store, entity("s_place", "-1")) == (
        AtlasErrorCode.TYPE_NAME_INVALID,
        "Type ENTITY with name s_place does not exist",
    )


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update", rules=["EWR-03", "EWR-06", "EWR-09", "EWR-13"])
async def test__an_entity_is_created_with_defaults_and_a_new_guid(store: EntityStore) -> None:
    """Every primitive attribute gets its default; the dynamic ``name``; system properties not from the request."""
    request = {
        **entity("w_item", "-1", qualifiedName="i@cl", count=None, tags=["a"]),
        "isProxy": True,
        "provenanceType": 2,
        "homeId": "h",
        "isIncomplete": True,
        "version": 7,
        "labels": ["x", "x", "y"],
        "customAttributes": {"k": "v"},
    }

    answer = await write(store, request)

    created = header(g("-1"), "w_item", "i@cl", "item-i@cl")
    created["labels"] = ["x", "y"]
    assert answer == {"mutatedEntities": {"CREATE": [created]}, "guidAssignments": {"-1": g("-1")}}
    assert await stored(store, g("-1")) == {
        "qualifiedName": "i@cl",
        "name": "item-i@cl",
        "count": 0,
        "flag": False,
        "when": 0,
        "label": "none",
        "tags": ["a"],
    }
    found = await store.get(g("-1"))
    assert found is not None
    assert found.entity.model_dump(
        include={"create_time", "update_time", "version", "labels", "is_proxy", "provenance_type", "home_id"}
    ) == {
        "create_time": NOW,
        "update_time": NOW,
        "version": 7,
        "labels": ["x", "y"],
        "is_proxy": None,
        "provenance_type": 0,
        "home_id": None,
    }
    assert (found.entity.is_incomplete, found.entity.custom_attributes) == (False, {"k": "v"})


@pytest.mark.covers(
    f"{W}.EntityWriter.create_or_update", rules=["EWR-04", "EWR-05", "EWR-06", "EWR-11", "EWR-12", "EWR-13"]
)
async def test__references_resolve_to_entities_of_the_request_and_of_the_store(store: EntityStore) -> None:
    """Referred entities named by GUID are created, others ignored; references are stored as GUIDs."""
    await write(store, entity("s_database", "-1", qualifiedName="db@cl"))

    answer = await write(
        store,
        entity(
            "s_table",
            "-2",
            qualifiedName="t@cl",
            db={"typeName": "s_database", "uniqueAttributes": {"qualifiedName": "db@cl"}},
            columns=[{"guid": "-3", "typeName": "s_column"}],
            primary={"guid": "-3", "typeName": "s_column"},
            place={"typeName": "s_place", "attributes": {"x": 1, "at": {"guid": "-4", "typeName": "s_column"}}},
        ),
        **{
            "-3": entity("s_column", "-3", qualifiedName="c1@cl"),
            "-4": entity("s_column", "-4", qualifiedName="c2@cl"),
            "-5": entity("s_column", "-5", qualifiedName="unused@cl"),
        },
    )

    assert list(answer["guidAssignments"]) == ["-2", "-4", "-3"]  # the struct attribute comes before the columns
    assert [h["guid"] for h in answer["mutatedEntities"]["CREATE"]] == [g("-2"), g("-4"), g("-3")]
    assert answer["mutatedEntities"]["UPDATE"] == [header(g("-1"), "s_database", "db@cl", classifications=False)]
    values = await stored(store, g("-2"))
    assert (values["db"], values["columns"], values["primary"]) == (g("-1"), [g("-3")], f"s_column:{g('-3')}")
    assert values["place"] == {"typeName": "s_place", "attributes": {"x": 1, "at": g("-4")}}
    database = await store.get(g("-1"))
    assert database is not None
    assert database.entity.update_time == NOW


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update", rules=["EWR-04", "EWR-05", "EWR-11"])
async def test__references_that_are_invalid_or_name_nothing_fail(store: EntityStore) -> None:
    """``INVALID_OBJECT_ID``, ``INVALID_STRUCT_VALUE`` and ``REFERENCED_ENTITY_NOT_FOUND`` with Java's text."""
    by_unique = {"typeName": "s_database", "uniqueAttributes": {"qualifiedName": "nowhere"}}

    assert await failure(store, entity("s_table", "-1", db="d")) == (
        AtlasErrorCode.INVALID_OBJECT_ID,
        "ObjectId is not valid d",
    )
    assert await failure(store, entity("s_table", "-1", db={"typeName": "s_database"})) == (
        AtlasErrorCode.INVALID_OBJECT_ID,
        "ObjectId is not valid AtlasObjectId{guid='null', typeName='s_database', uniqueAttributes={}}",
    )
    assert await failure(store, entity("s_table", "-1", place=5)) == (
        AtlasErrorCode.INVALID_STRUCT_VALUE,
        "not a valid struct value 5",
    )
    assert await failure(store, entity("s_table", "-1", db={"guid": "-9"})) == (
        AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND,
        "Referenced entity -9 is not found",
    )
    assert await failure(store, entity("s_table", "-1", db={"guid": "nope"})) == (
        AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND,
        "Referenced entity nope is not found",
    )
    assert await failure(store, entity("s_table", "-1", db=by_unique)) == (
        AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND,
        (
            "Referenced entity AtlasObjectId{guid='null', typeName='s_database', "
            "uniqueAttributes={qualifiedName:nowhere}} is not found"
        ),
    )
    assert await failure(store, entity("s_table", "-1", columns=[None, {"guid": "-1"}])) == (
        AtlasErrorCode.INVALID_OBJECT_ID,
        "ObjectId is not valid null",
    )


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update", rules=["EWR-06", "EWR-08", "EWR-10", "EWR-13"])
async def test__an_entity_found_by_its_unique_values_is_updated_and_unchanged_ones_are_skipped(
    store: EntityStore,
) -> None:
    """A second create with the same values updates; with nothing changed it is skipped, labels aside."""
    place = {"typeName": "s_place", "attributes": {"x": 1, "label": "p"}}
    await write(store, entity("s_table", "-1", qualifiedName="t@cl", name="a", place=place))
    table = g("-1")

    unchanged = await write(store, {**entity("s_table", "-7", qualifiedName="t@cl", place=place), "labels": ["new"]})
    changed = await write(store, {**entity("s_table", table, name="b"), "customAttributes": {"k": "v"}})

    assert unchanged == {"guidAssignments": {"-7": table}}
    assert changed == {
        "mutatedEntities": {"UPDATE": [header(table, "s_table", "t@cl", "b")]},
        "guidAssignments": {},
    }
    found = await store.get(table)
    assert found is not None
    assert (found.entity.labels, found.entity.custom_attributes) == (None, {"k": "v"})


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update", rules=["EWR-10", "EWR-11"])
async def test__an_update_maps_the_given_attributes_onto_the_stored_ones(store: EntityStore) -> None:
    """Structs merge attribute by attribute, a null struct stays, nulls get defaults, sets keep first elements."""
    await write(
        store,
        entity(
            "s_table",
            "-1",
            qualifiedName="t@cl",
            place={"typeName": "s_place", "attributes": {"x": 1, "label": "p"}},
            places=[{"x": 1}, {"x": 2}],
            sizes=[1, None, 2],
        ),
        entity("w_item", "-2", qualifiedName="i@cl", count=3),
    )
    assert (await stored(store, g("-1")))["sizes"] == [1, 2]

    await write(
        store,
        entity(
            "s_table",
            g("-1"),
            place={"typeName": "s_place", "attributes": {"label": "q"}},
            places=[{"label": "a"}],
            sizes=None,
        ),
        entity("w_item", g("-2"), count=None, tags=["b", "a", "b"], peers=None),
    )

    table, item = await stored(store, g("-1")), await stored(store, g("-2"))
    assert table["place"] == {"typeName": "s_place", "attributes": {"x": 1, "label": "q"}}
    assert table["places"] == [{"typeName": "s_place", "attributes": {"x": 1, "label": "a"}}]
    assert "sizes" not in table
    assert (item["count"], item["tags"], item.get("peers")) == (0, ["b", "a"], None)
    await write(store, entity("s_table", g("-1"), place=None))
    assert (await stored(store, g("-1")))["place"]["attributes"]["label"] == "q"


@pytest.mark.covers(f"{W}.EntityWriter.update_by_unique_attributes", rules=["EWR-10", "EWR-11", "EWR-13", "EWR-14"])
async def test__a_partial_update_by_unique_attributes_appends_where_asked(store: EntityStore) -> None:
    """``PARTIAL_UPDATE`` of the entity holding the values; arrays and maps with the option append."""
    await write(store, entity("w_item", "-1", qualifiedName="i@cl", tags=["a"], notes={"k": "1"}))
    item_type = store.registry.entity_type("w_item")
    assert item_type is not None
    update = AtlasEntityWithExtInfo.model_validate(
        {"entity": {"typeName": "w_item", "attributes": {"tags": ["b", "a"], "notes": {"k": "2", "j": "3"}}}}
    )

    answer = as_json(
        await EntityWriter(store).update_by_unique_attributes(item_type, {"qualifiedName": "i@cl"}, update)
    )

    item_header = header(g("-1"), "w_item", "i@cl", "item-i@cl")
    assert answer == {
        "mutatedEntities": {"PARTIAL_UPDATE": [item_header]},
        "partialUpdatedEntities": [item_header],
        "guidAssignments": {},
    }
    assert (await stored(store, g("-1")))["tags"] == ["a", "b"]
    assert (await stored(store, g("-1")))["notes"] == {"k": "2", "j": "3"}


@pytest.mark.covers(f"{W}.EntityWriter.update_by_unique_attributes", rules=["EWR-14"])
async def test__a_partial_update_by_unique_attributes_needs_an_entity_and_a_holder(store: EntityStore) -> None:
    """``INVALID_PARAMETERS`` without an entity; ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` without a holder."""
    item_type = store.registry.entity_type("w_item")
    assert item_type is not None
    writer = EntityWriter(store)

    with pytest.raises(AtlasError) as raised:
        await writer.update_by_unique_attributes(item_type, {"qualifiedName": "x"}, AtlasEntityWithExtInfo())
    assert raised.value.message == "invalid parameters: no entity to update."
    with pytest.raises(AtlasError) as raised:
        await writer.update_by_unique_attributes(
            item_type, {"qualifiedName": "x"}, AtlasEntityWithExtInfo(entity=AtlasEntity(type_name="w_item"))
        )
    assert raised.value.message == "Instance w_item with unique attribute {qualifiedName=x} does not exist"


@pytest.mark.covers(f"{W}.EntityWriter.update_attribute_by_guid", rules=["EWR-12", "EWR-15"])
async def test__one_attribute_is_set_by_guid(store: EntityStore) -> None:
    """A primitive as given, a string GUID as a reference; other kinds and unknown names fail."""
    await write(store, entity("s_database", "-1", qualifiedName="db@cl"), entity("s_table", "-2", qualifiedName="t@cl"))
    writer = EntityWriter(store)
    table = g("-2")

    named = as_json(await writer.update_attribute_by_guid(table, "name", "orders"))
    referenced = as_json(await writer.update_attribute_by_guid(table, "db", g("-1")))

    assert named["mutatedEntities"] == {"PARTIAL_UPDATE": [header(table, "s_table", "t@cl", "orders")]}
    assert [h["guid"] for h in referenced["mutatedEntities"]["PARTIAL_UPDATE"]] == [table, g("-1")]
    assert (await stored(store, table))["db"] == g("-1")
    for guid, name, value, message in [
        ("nope", "name", "x", "Given instance guid nope is invalid/not found"),
        (table, "nothing", "x", "Attribute nothing not found for type s_table"),
        (table, None, "x", "Attribute null not found for type s_table"),
        (table, "color", "RED", "color.s_color : attribute update not supported"),
    ]:
        with pytest.raises(AtlasError) as raised:
            await writer.update_attribute_by_guid(guid, name, value)
        assert raised.value.message == message


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update", rules=["EWR-17", "REL-11"])
async def test__relationship_attribute_values_become_relationships_and_must_name_an_entity(
    store: EntityStore,
) -> None:
    """``holder`` (a legacy end) and ``home`` are relationships, not attribute values (DD-064)."""
    await write(store, entity("s_database", "-1", qualifiedName="db@cl"))
    database = {"guid": g("-1"), "typeName": "s_database"}

    await write(
        store,
        entity("w_item", "-2", qualifiedName="i@cl", holder=database),
        {**entity("s_table", "-3", qualifiedName="t@cl"), "relationshipAttributes": {"home": database}},
    )

    held = await store.get(g("-1"))
    assert held is not None
    relationships = await store.get_relationships(held.entity.relationship_guids or [])
    assert "holder" not in await stored(store, g("-2"))
    assert "home" not in await stored(store, g("-3"))
    assert sorted((found.relationship.type_name, found.relationship.end1_guid) for found in relationships.values()) == (
        sorted([("w_item_holder", g("-2")), ("s_table_home", g("-3"))])
    )
    assert await failure(store, {**entity("s_table", "-3"), "relationshipAttributes": {"home": {"guid": "x"}}}) == (
        AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND,
        "Referenced entity x is not found",
    )


@pytest.mark.covers(f"{W}.compact_attributes", rules=["EWR-06"])
def test__a_relationship_attribute_in_attributes_moves_to_relationship_attributes() -> None:
    """Unless ``relationshipAttributes`` holds it: then it is dropped."""
    item_type = sample_registry(writes=True).entity_type("w_item")
    assert item_type is not None
    moved = AtlasEntity(type_name="w_item", attributes={"holder": {"guid": "a"}, "count": 1})
    dropped = AtlasEntity(
        type_name="w_item", attributes={"holder": {"guid": "a"}}, relationship_attributes={"holder": {"guid": "b"}}
    )

    compact_attributes(moved, item_type)
    compact_attributes(dropped, item_type)

    assert (moved.attributes, moved.relationship_attributes) == ({"count": 1}, {"holder": {"guid": "a"}})
    assert (dropped.attributes, dropped.relationship_attributes) == ({}, {"holder": {"guid": "b"}})


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update", rules=["EWR-06", "EWR-07"])
async def test__a_full_update_completes_an_incomplete_entity_and_invalid_entities_fail(store: EntityStore) -> None:
    """``isIncomplete`` is cleared; a null GUID, bad labels and invalid values fail before anything is written."""
    await write(store, entity("s_table", "-1", qualifiedName="t@cl"))
    found = await store.get(g("-1"))
    assert found is not None
    await store.write([EntityChange(found.entity.model_copy(update={"is_incomplete": True}), found.version)])

    await write(store, entity("s_table", g("-1"), name="x"))

    completed = await store.get(g("-1"))
    assert completed is not None
    assert completed.entity.is_incomplete is False
    assert await failure(store, entity("s_table", None, qualifiedName="n@cl")) == (
        AtlasErrorCode.INVALID_OBJECT_ID,
        "ObjectId is not valid invalid guid null",
    )
    assert await failure(store, {**entity("s_table", "-2"), "labels": ["a b"]}) == (
        AtlasErrorCode.INVALID_LABEL_CHARACTERS,
        "Invalid label: a b, label should contain alphanumeric characters, _ or -",
    )
    code, message = await failure(store, entity("w_item", "-2", count="many"))
    assert code is AtlasErrorCode.INSTANCE_CRUD_INVALID_PARAMS
    assert message.startswith("Invalid instance creation/updation parameters passed : [w_item.count")


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update", rules=["EWR-16"])
async def test__a_lost_race_is_run_again_once(store: EntityStore, documents: MemoryEntityDocuments) -> None:
    """One conflict: the request runs again; two: ``INTERNAL_ERROR``; a held unique value likewise."""
    await write(store, entity("s_table", "-1", qualifiedName="t@cl"))
    table = g("-1")

    documents.fail[table] = "conflict"
    retried = await write(store, entity("s_table", table, name="a"))
    assert [h["attributes"]["name"] for h in retried["mutatedEntities"]["UPDATE"]] == ["a"]

    original = documents.write

    async def always_conflicting(*arguments: Any) -> Any:  # noqa: ANN401 - the documents' signature
        documents.fail[table] = "conflict"
        return await original(*arguments)

    documents.write = always_conflicting  # pyright: ignore[reportAttributeAccessIssue]
    assert await failure(store, entity("s_table", table, name="b")) == (
        AtlasErrorCode.INTERNAL_ERROR,
        f"Internal server error entity {table} was changed by another write",
    )
    documents.write = original

    code, message = await failure(
        store, entity("s_ref", "-5", qualifiedName="same"), entity("s_ref", "-6", qualifiedName="same")
    )
    assert code is AtlasErrorCode.INTERNAL_ERROR
    assert message.startswith("Internal server error unique value s_ref.qualifiedName=same of type s_ref is held by")


@pytest.mark.covers(f"{W}.EntityWriter.create_or_update", rules=["EWR-12"])
async def test__a_new_reference_from_a_struct_also_updates_the_referenced_entity(store: EntityStore) -> None:
    """Only where none was stored."""
    await write(store, entity("s_column", "-1", qualifiedName="c@cl"), entity("s_table", "-2", qualifiedName="t@cl"))
    place = {"typeName": "s_place", "attributes": {"at": {"guid": g("-1"), "typeName": "s_column"}}}

    first = await write(store, entity("s_table", g("-2"), place=place))
    again = await write(store, entity("s_table", g("-2"), place=place))

    assert [h["guid"] for h in first["mutatedEntities"]["UPDATE"]] == [g("-2"), g("-1")]
    assert "mutatedEntities" not in again


@pytest.mark.covers("aurelius_atlas_core.entity_retriever.EntityRetriever.entity_attribute", rules=["EWR-08"])
async def test__an_entity_attribute_reads_as_a_read_answers_it(store: EntityStore) -> None:
    """A reference as an object id with its unique values."""
    await write(store, entity("s_database", "-1", qualifiedName="db@cl"), entity("s_table", "-2", db={"guid": "-1"}))
    table_type = store.registry.entity_type("s_table")
    found = await store.get(g("-2"))
    assert table_type is not None
    assert found is not None

    value = await EntityRetriever(store).entity_attribute(found.entity, table_type.all_attributes["db"])

    assert as_json(value) == {"guid": g("-1"), "typeName": "s_database", "uniqueAttributes": {"qualifiedName": "db@cl"}}
