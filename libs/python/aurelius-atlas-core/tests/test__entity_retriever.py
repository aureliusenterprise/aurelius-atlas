"""``EntityRetriever`` (ERD-02 to ERD-07, ERD-09) on entities written through the in-memory store (DD-051).

The expected responses are read from ``EntityGraphRetriever`` (``mapVertexToAtlasEntity``, ``mapSystemAttributes``,
``mapAttributes``, ``mapVertexToObjectId``, ``mapVertexToAtlasEntityHeader``) and ``AtlasEntityStoreV2`` of Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.testing.entity_samples import sample_entities, sample_entity, sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import EntityStatus
from aurelius_atlas_typesystem.entity_type import EntityType

R = "aurelius_atlas_core.entity_retriever.EntityRetriever"

TABLE_ATTRIBUTES_UNSET = {
    "qualifiedName": None,
    "name": None,
    "created": None,
    "color": None,
    "place": None,
    "places": None,
    "sizes": None,
    "props": None,
    "db": None,
    "columns": None,
    "byName": None,
    "primary": None,
    "spare": None,
}


@pytest.fixture
async def store() -> EntityStore:
    """A store of the sample types holding a database ``d``, columns ``c1`` to ``c3`` and table ``t``."""
    store = EntityStore(sample_registry(), MemoryEntityDocuments())
    await store.write([EntityChange(entity) for entity in sample_entities(store.registry)])
    return store


def table_type(store: EntityStore) -> EntityType:
    """``s_table``."""
    found = store.registry.entity_type("s_table")
    assert found is not None
    return found


def system(guid: str, type_name: str, **more: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """The system properties ``mapSystemAttributes`` gives an entity created at time 1000 (ERD-03)."""
    return {
        "typeName": type_name,
        "guid": guid,
        "proxy": False,
        "isIncomplete": False,
        "provenanceType": 0,
        "status": "ACTIVE",
        "createTime": 1000,
        "updateTime": 1000,
        "version": 0,
        "labels": [],
        **more,
    }


@pytest.mark.covers(f"{R}.entity_with_ext_info", rules=["ERD-02", "ERD-03", "ERD-04", "ERD-05", "ERD-06"])
async def test__an_entity_reads_with_every_attribute_and_its_owned_entities(store: EntityStore) -> None:
    """All attributes, null when unset; owned entities in ``referredEntities``; others as object ids."""
    found = await EntityRetriever(store).entity_with_ext_info("t")

    column = system(
        "c1", "s_column", attributes={"qualifiedName": "c1@cl", "name": None, "position": 1, "comment": None}
    )
    column2 = system(
        "c2", "s_column", attributes={"qualifiedName": "c2@cl", "name": None, "position": None, "comment": "x"}
    )
    column3 = system(
        "c3", "s_column", attributes={"qualifiedName": "c3@cl", "name": None, "position": None, "comment": None}
    )
    assert found.to_json() == {
        "entity": system(
            "t",
            "s_table",
            homeId="home",
            labels=["gold"],
            attributes={
                "qualifiedName": "t@cl",
                "name": "orders",
                "created": 1_700_000_000_000,
                "color": "BLUE",
                "place": {
                    "typeName": "s_place",
                    "attributes": {
                        "x": 3,
                        "label": None,
                        "at": {"guid": "c3", "typeName": "s_column", "uniqueAttributes": {"qualifiedName": "c3@cl"}},
                    },
                },
                "places": [{"typeName": "s_place", "attributes": {"x": None, "label": "p", "at": None}}],
                "sizes": [1, 2],
                "props": {"k": "v"},
                "db": {"guid": "d", "typeName": "s_database", "uniqueAttributes": {"qualifiedName": "db@cl"}},
                "columns": [{"guid": "c1", "typeName": "s_column"}],
                "byName": {"second": {"guid": "c2", "typeName": "s_column"}},
                "primary": {"guid": "c3", "typeName": "s_column"},
                "spare": [
                    {"guid": "c3", "typeName": "s_column", "uniqueAttributes": {"qualifiedName": "c3@cl"}},
                    {"guid": "nowhere", "typeName": "s_column"},
                ],
            },
            relationshipAttributes={"home": None},
        ),
        "referredEntities": {"c1": column, "c2": column2, "c3": column3},
    }


@pytest.mark.covers(f"{R}.entity_with_ext_info", rules=["ERD-05", "ERD-06"])
async def test__min_ext_info_reads_owned_entities_with_their_minimal_attributes(store: EntityStore) -> None:
    """``mapVertexToAtlasEntityMin``: header and schema attributes that have a value; no relationships if ignored."""
    found = await EntityRetriever(store, min_ext_info=True, ignore_relationships=True).entity_with_ext_info("t")

    assert found.entity is not None
    assert found.entity.relationship_attributes is None
    assert found.to_json()["referredEntities"] == {
        "c1": system("c1", "s_column", attributes={"qualifiedName": "c1@cl", "position": 1}),
        "c2": system("c2", "s_column", attributes={"qualifiedName": "c2@cl"}),
        "c3": system("c3", "s_column", attributes={"qualifiedName": "c3@cl"}),
    }


@pytest.mark.covers(f"{R}.entity_with_ext_info", rules=["ERD-02", "ERD-03", "ERD-06"])
async def test__an_entity_reads_in_any_state_and_unknown_guids_fail(store: EntityStore) -> None:
    """A deleted entity is read; a missing one fails with ``INSTANCE_GUID_NOT_FOUND``; the set of a database."""
    deleted = sample_entity(store.registry, "s_database", "e", state=EntityStatus.DELETED, is_proxy=None)
    await store.write([EntityChange(deleted)])

    found = await EntityRetriever(store).entity_with_ext_info("e")
    with pytest.raises(AtlasError) as missing:
        await EntityRetriever(store).entity_with_ext_info("nope")

    assert found.to_json() == {
        "entity": {
            key: value
            for key, value in system(
                "e",
                "s_database",
                status="DELETED",
                attributes={"qualifiedName": None, "name": None, "title": None},
                relationshipAttributes={"tables": []},
            ).items()
            if key != "proxy"
        },
        "referredEntities": {},
    }
    assert (missing.value.code, missing.value.params) == (AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, ("nope",))


@pytest.mark.covers(f"{R}.entities_with_ext_info", rules=["ERD-02", "ERD-06"])
async def test__entities_read_in_order_and_one_unknown_guid_fails_them_all(store: EntityStore) -> None:
    """``getByIds``: the order given; an entity asked for is not also referred; an unknown GUID fails."""
    retriever = EntityRetriever(store, ignore_relationships=True)

    found = await retriever.entities_with_ext_info(["c1", "t"])
    with pytest.raises(AtlasError) as missing:
        await retriever.entities_with_ext_info(["t", "nope", "never"])

    assert [entity.guid for entity in found.entities or []] == ["c1", "t"]
    assert sorted(found.referred_entities or {}) == ["c2", "c3"]
    assert missing.value.params == ("nope",)
    assert (await retriever.entities_with_ext_info([])).to_json() == {}


@pytest.mark.covers(f"{R}.entity_by_unique_attributes", f"{R}.entities_by_unique_attributes", rules=["ERD-09"])
async def test__unique_attributes_find_active_entities(store: EntityStore) -> None:
    """``getByUniqueAttributes`` by the values; not found names them as a Java map; the bulk read skips misses."""
    retriever = EntityRetriever(store, ignore_relationships=True)
    column_type = store.registry.entity_type("s_column")
    assert column_type is not None

    found = await retriever.entity_by_unique_attributes(table_type(store), {"qualifiedName": "t@cl"})
    ref_type = store.registry.entity_type("s_ref")
    assert ref_type is not None
    by_super_type = await retriever.entity_by_unique_attributes(ref_type, {"qualifiedName": "c1@cl"})
    with pytest.raises(AtlasError) as missing:
        await retriever.entity_by_unique_attributes(column_type, {"qualifiedName": "t@cl"})
    many = await retriever.entities_by_unique_attributes(
        column_type, [{"qualifiedName": "c2@cl"}, {"qualifiedName": "none"}, {"qualifiedName": "c1@cl"}]
    )

    assert (found.entity and found.entity.guid, by_super_type.entity and by_super_type.entity.guid) == ("t", "c1")
    assert (missing.value.code, missing.value.params) == (
        AtlasErrorCode.INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND,
        ("s_column", "{qualifiedName=t@cl}"),
    )
    assert [entity.guid for entity in many.entities or []] == ["c2", "c1"]
    assert (await retriever.entities_by_unique_attributes(column_type, [])).to_json() == {}


@pytest.mark.covers(f"{R}.header", f"{R}.header_by_unique_attributes", rules=["ERD-07"])
async def test__a_header_holds_header_attributes_and_display_text(store: EntityStore) -> None:
    """``mapVertexToAtlasEntityHeader``: ``""`` for header attributes without a value; the display text attribute."""
    retriever = EntityRetriever(store)
    database_type = store.registry.entity_type("s_database")
    assert database_type is not None

    by_guid = await retriever.header("t")
    by_unique = await retriever.header_by_unique_attributes(database_type, {"qualifiedName": "db@cl"})
    with pytest.raises(AtlasError) as missing:
        await retriever.header("nope")

    header = {
        "typeName": "s_table",
        "attributes": {"qualifiedName": "t@cl", "name": "orders"},
        "guid": "t",
        "status": "ACTIVE",
        "displayText": "orders",
        "classificationNames": [],
        "classifications": [],
        "meaningNames": [],
        "meanings": [],
        "isIncomplete": False,
        "labels": ["gold"],
    }
    assert by_guid.to_json() == header
    assert by_unique.to_json() == {
        **{key: value for key, value in header.items() if key != "classifications"},
        "typeName": "s_database",
        "guid": "d",
        "attributes": {"qualifiedName": "db@cl", "name": ""},
        "displayText": "DB",
        "labels": [],
    }
    assert missing.value.code is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND


@pytest.mark.covers(f"{R}.header", rules=["ERD-07"])
async def test__display_text_falls_back_to_the_qualified_name(store: EntityStore) -> None:
    """Without a value for ``name``, the display text is ``qualifiedName``; with neither, there is none."""
    await store.write([EntityChange(StoredEntity(guid="bare", type_name="s_column"))])

    assert (await EntityRetriever(store).header("c1")).display_text == "c1@cl"
    assert (await EntityRetriever(store).header("bare")).display_text is None
