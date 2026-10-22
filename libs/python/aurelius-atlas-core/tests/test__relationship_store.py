"""``RelationshipStore`` (REL-04 to REL-10) on the in-memory documents.

The expected answers are read from ``AtlasRelationshipStoreV2`` (``create``, ``update``, ``getById``,
``getExtInfoById``, ``deleteById``, ``validateRelationship``), ``EntityGraphRetriever.mapEdgeToAtlasRelationship``
and ``DeleteHandlerV1`` of Apache Atlas 2.4.0, and its test ``AtlasRelationshipStoreV2Test``.
"""

from typing import Any

import pytest
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, SimulatedCrashError
from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import (
    AtlasEntitiesWithExtInfo,
    AtlasObjectId,
    AtlasRelationship,
    RelationshipStatus,
)

S = "aurelius_atlas_core.relationship_store"
R = f"{S}.RelationshipStore"
NOW = 7000


@pytest.fixture
async def store() -> EntityStore:
    """A store of the sample and write types at ``NOW``.

    It holds table ``t`` (``t@cl``), database ``d``, column ``c`` and item ``i``.
    """
    store = EntityStore(sample_registry(writes=True), MemoryEntityDocuments(), clock=lambda: NOW / 1000)
    entities = [
        {"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@cl"}},
        {"typeName": "s_database", "guid": "-2", "attributes": {"qualifiedName": "d@cl"}},
        {"typeName": "s_column", "guid": "-3", "attributes": {"qualifiedName": "c@cl"}},
        {"typeName": "w_item", "guid": "-4", "attributes": {"qualifiedName": "i@cl"}},
    ]
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": entities})
    )
    GUIDS.clear()
    GUIDS.update(dict(zip("tdci", [(created.guid_assignments or {})[f"-{n}"] for n in range(1, 5)], strict=True)))
    return store


GUIDS: dict[str, str] = {}


def g(name: str) -> str:
    """The GUID of sample entity ``name``."""
    return GUIDS[name]


def relationship(type_name: str | None, end1: str | None, end2: str | None, **fields: Any) -> AtlasRelationship:  # noqa: ANN401
    """A relationship between sample entities, given by name."""
    body: dict[str, Any] = {"typeName": type_name, **fields}
    if end1 is not None:
        body["end1"] = {"guid": g(end1)}
    if end2 is not None:
        body["end2"] = {"guid": g(end2)}
    return AtlasRelationship.model_validate(body)


def as_json(value: Any) -> Any:  # noqa: ANN401 - Atlas JSON
    """A model's JSON as a client reads it."""
    return codec.loads(codec.dumps(value.to_json()))


async def failure(call: Any) -> tuple[AtlasErrorCode, str]:  # noqa: ANN401 - a coroutine
    """The code and message a call fails with."""
    with pytest.raises(AtlasError) as raised:
        await call
    return raised.value.code, raised.value.message


@pytest.mark.covers(
    f"{R}.create",
    f"{R}.get_by_id",
    f"{S}.created_relationship",
    f"{S}.relationship_edge_label",
    rules=["REL-04", "REL-05", "REL-06"],
)
async def test__a_relationship_is_created_between_two_entities_and_listed_by_both(store: EntityStore) -> None:
    """Its label and tag propagation from the type; its ends as object ids; twice is refused."""
    relationships = RelationshipStore(store)

    created = as_json(await relationships.create(relationship("s_table_home", "t", "d", guid="-7")))

    assert created == {
        "typeName": "s_table_home",
        "guid": created["guid"],
        "provenanceType": 0,
        "end1": {"guid": g("t"), "typeName": "s_table", "uniqueAttributes": {"qualifiedName": "t@cl"}},
        "end2": {"guid": g("d"), "typeName": "s_database", "uniqueAttributes": {"qualifiedName": "d@cl"}},
        "label": "r:s_table_home",
        "propagateTags": "NONE",
        "status": "ACTIVE",
        "createTime": NOW,
        "updateTime": NOW,
        "version": 0,
        "propagatedClassifications": [],
        "blockedPropagatedClassifications": [],
    }
    assert not created["guid"].startswith("-")
    assert as_json(await relationships.get_by_id(created["guid"])) == created
    for end in ("t", "d"):
        found = await store.get(g(end))
        assert found is not None
        assert found.entity.relationship_guids == [created["guid"]]
    assert await failure(relationships.create(relationship("s_table_home", "t", "d"))) == (
        AtlasErrorCode.RELATIONSHIP_ALREADY_EXISTS,
        f"relationship s_table_home already exists between entities {g('t')} and {g('d')}",
    )


@pytest.mark.covers(f"{R}.create", f"{S}.validate_relationship", rules=["REL-04"])
async def test__a_relationship_is_checked_before_it_is_created(store: EntityStore) -> None:
    """Type, ends (missing or of other types), tag propagation and attribute values."""
    relationships = RelationshipStore(store)
    missing = AtlasRelationship.model_validate(
        {"typeName": "s_table_home", "end1": {"guid": g("t")}, "end2": {"guid": "nope"}}
    )

    assert await failure(relationships.create(relationship("nope", "t", "d"))) == (
        AtlasErrorCode.INVALID_VALUE,
        "invalid value: unknown relationship type'nope'",
    )
    assert await failure(relationships.create(missing)) == (
        AtlasErrorCode.RELATIONSHIP_END_IS_NULL,
        "Relationship end is invalid. Expected s_database but is NULL",
    )
    assert (await failure(relationships.create(relationship("s_table_home", "t", None))))[0] is (
        AtlasErrorCode.RELATIONSHIP_END_IS_NULL
    )
    assert await failure(relationships.create(relationship("s_table_home", "c", "d"))) == (
        AtlasErrorCode.INVALID_RELATIONSHIP_END_TYPE,
        "invalid relationshipDef: s_table_home: end type 1: s_database, end type 2: s_column",
    )
    assert await failure(relationships.create(relationship("s_table_home", "t", "d", propagateTags="BOTH"))) == (
        AtlasErrorCode.INVALID_PROPAGATION_TYPE,
        "Invalid propagation BOTH for relationship-type=s_table_home. Default value is NONE",
    )
    code, message = await failure(relationships.create(relationship("w_link", "i", "c", attributes={"weight": "x"})))
    assert code is AtlasErrorCode.RELATIONSHIP_CRUD_INVALID_PARAMS
    assert (
        message
        == "Invalid relationship creation/updation parameters passed : [w_link.weight=x: invalid value for type int]"
    )


@pytest.mark.covers(f"{R}.create", f"{R}.update", rules=["REL-05", "REL-07"])
async def test__an_update_sets_attributes_defaults_and_tag_propagation_but_not_type_or_ends(store: EntityStore) -> None:
    """Ends in either order swap the propagation; defaults fill what an update leaves out; nothing else may change.

    A type name differing in case passes Atlas's change check and then names no type.
    """
    relationships = RelationshipStore(store)
    created = await relationships.create(relationship("w_link", "c", "i", attributes={"weight": 3}))
    guid = str(created.guid)

    updated = as_json(await relationships.update(relationship(None, None, None, guid=guid)))
    reset = as_json(
        await relationships.update(
            relationship("w_link", "c", None, guid=guid, propagateTags="ONE_TO_TWO", attributes={"weight": None})
        )
    )

    assert (created.propagate_tags, created.attributes) == ("TWO_TO_ONE", {"weight": 3, "note": None})
    assert (updated["propagateTags"], updated["attributes"], updated["updateTime"]) == (
        "TWO_TO_ONE",
        {"weight": 3, "note": "n"},
        NOW,
    )
    assert (reset["propagateTags"], reset["attributes"]) == ("ONE_TO_TWO", {"weight": None, "note": "n"})
    for change, code, message in [
        (
            relationship(None, None, None, guid=""),
            AtlasErrorCode.RELATIONSHIP_GUID_NOT_FOUND,
            "Given relationship guid  is invalid/not found",
        ),
        (
            relationship(None, None, None, guid="nope"),
            AtlasErrorCode.RELATIONSHIP_GUID_NOT_FOUND,
            "Given relationship guid nope is invalid/not found",
        ),
        (
            relationship("s_table_home", None, None, guid=guid),
            AtlasErrorCode.RELATIONSHIP_UPDATE_TYPE_CHANGE_NOT_ALLOWED,
            (
                f"change of relationship type is not permitted. relationship-guid={guid}, current-type=w_link, "
                "new-type=s_table_home"
            ),
        ),
        (
            relationship(None, "d", None, guid=guid),
            AtlasErrorCode.RELATIONSHIP_UPDATE_END_CHANGE_NOT_ALLOWED,
            (
                f"change of relationship end is not permitted. relationship-type=w_link, relationship-guid={guid}, "
                f"end-guid={g('c')}, updated-end-guid={g('d')}"
            ),
        ),
        (
            AtlasRelationship.model_validate(
                {"guid": guid, "end2": {"typeName": "w_item", "uniqueAttributes": {"qualifiedName": "i@cl"}}}
            ),
            AtlasErrorCode.RELATIONSHIP_UPDATE_END_CHANGE_NOT_ALLOWED,
            (
                f"change of relationship end is not permitted. relationship-type=w_link, relationship-guid={guid}, "
                f"end-guid={g('i')}, updated-end-guid=null"
            ),
        ),
    ]:
        assert await failure(relationships.update(change)) == (code, message)


@pytest.mark.covers(f"{R}.get_ext_info_by_id", f"{R}.delete_by_id", rules=["REL-06", "REL-08"])
async def test__a_relationship_is_read_with_its_ends_and_deleted_soft_or_hard(store: EntityStore) -> None:
    """Headers of both ends; a soft delete once; a hard delete removes it from its ends too."""
    soft, hard = RelationshipStore(store), RelationshipStore(store, delete_type=DeleteType.HARD)
    first = str((await soft.create(relationship("s_table_home", "t", "d"))).guid)
    second = str((await soft.create(relationship("w_link", "i", "c"))).guid)

    extended = as_json(await soft.get_ext_info_by_id(first))
    await soft.delete_by_id(first)
    await hard.delete_by_id(second)

    assert sorted(extended["referredEntities"]) == sorted([g("t"), g("d")])
    assert "classifications" not in extended["referredEntities"][g("t")]
    assert (await soft.get_by_id(first)).status is RelationshipStatus.DELETED
    assert await failure(soft.delete_by_id(first)) == (
        AtlasErrorCode.RELATIONSHIP_ALREADY_DELETED,
        f"Attempting to delete a relationship which is already deleted : {first}",
    )
    assert (await failure(soft.get_by_id(second)))[0] is AtlasErrorCode.RELATIONSHIP_GUID_NOT_FOUND
    item = await store.get(g("i"))
    assert item is not None
    assert item.entity.relationship_guids is None
    assert await failure(soft.delete_by_id("")) == (
        AtlasErrorCode.RELATIONSHIP_CRUD_INVALID_PARAMS,
        "Invalid relationship creation/updation parameters passed :  empty/null guid",
    )
    assert (await failure(soft.delete_by_id("nope")))[0] is AtlasErrorCode.RELATIONSHIP_GUID_NOT_FOUND


@pytest.mark.covers(
    f"{R}.delete_by_id", "aurelius_atlas_core.entity_store.EntityStore.type_in_use", rules=["REL-09", "REL-10"]
)
async def test__deleting_an_entity_deletes_its_relationships(store: EntityStore) -> None:
    """Soft: those it is end 2 of; hard: all of them, which the other ends stop listing; a type stays in use."""
    relationships = RelationshipStore(store)
    home = str((await relationships.create(relationship("s_table_home", "t", "d"))).guid)
    link = str((await relationships.create(relationship("w_link", "i", "c"))).guid)

    await EntityWriter(store).delete_by_id(g("t"))
    assert (await relationships.get_by_id(home)).status is RelationshipStatus.ACTIVE
    await EntityWriter(store).delete_by_id(g("c"))
    assert (await relationships.get_by_id(link)).status is RelationshipStatus.DELETED
    assert await store.type_in_use("w_link")

    await EntityWriter(store, delete_type=DeleteType.HARD).delete_by_id(g("d"))
    assert (await failure(relationships.get_by_id(home)))[0] is AtlasErrorCode.RELATIONSHIP_GUID_NOT_FOUND
    table = await store.get(g("t"))
    assert table is not None
    assert table.entity.relationship_guids is None
    assert not await store.type_in_use("s_table_home")


@pytest.mark.covers(
    "aurelius_atlas_core.entity_store.EntityStore.write",
    "aurelius_atlas_core.entity_store.EntityStore.get_relationships",
    "aurelius_atlas_core.entity_store.EntityStore.recover",
    "aurelius_atlas_core.entity_documents.JournalEntry.before_relationship",
    "aurelius_atlas_core.stored_entity.StoredEntity.listing",
    "aurelius_atlas_core.stored_entity.StoredEntity.unlisting",
    "aurelius_atlas_core.stored_relationship.StoredRelationship.ends",
    "aurelius_atlas_core.stored_relationship.StoredRelationship.to_relationship",
    "aurelius_atlas_core.entity_retriever.EntityRetriever.object_id_of",
    "aurelius_atlas_core.delete_handler.Deletion.change",
    rules=["REL-05", "REL-09"],
)
async def test__relationships_are_written_with_their_ends_all_or_nothing() -> None:
    """A failed write restores a relationship it changed; a crash part-way is undone by recovery (DD-062)."""
    documents = MemoryEntityDocuments()
    clock = [NOW / 1000]
    store = EntityStore(sample_registry(writes=True), documents, clock=lambda: clock[0])
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {
                "entities": [
                    {"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@cl"}},
                    {"typeName": "s_database", "guid": "-2", "attributes": {}},
                ]
            }
        )
    )
    table, database = (created.guid_assignments or {})["-1"], (created.guid_assignments or {})["-2"]
    relationships = RelationshipStore(store)
    home = str(
        (
            await relationships.create(
                AtlasRelationship.model_validate(
                    {"typeName": "s_table_home", "end1": {"guid": table}, "end2": {"guid": database}}
                )
            )
        ).guid
    )
    found = (await store.get_relationships([home]))[home]
    assert found.relationship.ends() == (table, database)
    assert (await relationships.get_by_id(home)).end2 == AtlasObjectId(guid=database, type_name="s_database")

    documents.fail[table] = "error"
    with pytest.raises(AtlasError):
        await relationships.delete_by_id(home, DeleteType.HARD)
    assert home in await store.get_relationships([home])

    documents.crash_after_write = True
    with pytest.raises(SimulatedCrashError):
        await relationships.delete_by_id(home, DeleteType.HARD)
    assert await store.get_relationships([home]) == {}
    clock[0] += 3600
    assert await store.recover() == 1
    restored = (await store.get_relationships([home]))[home].relationship
    assert restored.state is RelationshipStatus.ACTIVE
    entity = await store.get(table)
    assert entity is not None
    assert entity.entity.unlisting({home}).relationship_guids is None
    assert entity.entity.listing(home).relationship_guids == [home]
