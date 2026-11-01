"""The stores' checks (AUZ-03, AUZ-07 to AUZ-10) on the in-memory documents.

Read from ``AtlasAuthorizationUtils`` and the checks of ``AtlasEntityStoreV2``, ``AtlasRelationshipStoreV2``,
``DataAccess`` and ``GlossaryService#getGlossaries`` of Apache Atlas 2.4.0, with their action texts.
"""

import json
from typing import Any

import pytest
from aurelius_atlas_core.authorization import ALLOW_ALL, AtlasPrivilege, Granted, joined
from aurelius_atlas_core.classification_associator import ClassificationAssociator
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.glossary_service import GlossaryService, SortOrder
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.user_profile_service import UserProfileService
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import AtlasGlossary, AtlasGlossaryHeader, AtlasGlossaryTerm
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasEntityHeader,
    AtlasEntityWithExtInfo,
    AtlasRelatedObjectId,
    AtlasRelationship,
)
from aurelius_atlas_model.profile import AtlasUserProfile, AtlasUserSavedSearch
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

A = "aurelius_atlas_core.authorization"
W = "aurelius_atlas_core.entity_writer.EntityWriter"
C = "aurelius_atlas_core.entity_classifications.EntityClassifications"
R = "aurelius_atlas_core.relationship_store.RelationshipStore"
P = AtlasPrivilege
MODELS = BUILTIN_MODELS_DIR / "0000-Area0"
WRITE = frozenset(
    {
        P.ENTITY_READ,
        P.ENTITY_CREATE,
        P.ENTITY_UPDATE,
        P.ENTITY_DELETE,
        P.ENTITY_ADD_CLASSIFICATION,
        P.ENTITY_UPDATE_CLASSIFICATION,
        P.ENTITY_REMOVE_CLASSIFICATION,
        P.RELATIONSHIP_ADD,
        P.RELATIONSHIP_UPDATE,
        P.RELATIONSHIP_REMOVE,
    }
)


def granted(*privileges: AtlasPrivilege) -> Granted:
    """User ``u`` holding the privileges."""
    return Granted("u", frozenset(privileges))


def but(*privileges: AtlasPrivilege) -> Granted:
    """User ``u`` holding every write privilege but these."""
    return Granted("u", WRITE - set(privileges))


async def refused(call: Any) -> str:  # noqa: ANN401 - a coroutine
    """The action of the refusal the call fails with."""
    with pytest.raises(AtlasError) as raised:
        await call
    assert raised.value.code is AtlasErrorCode.UNAUTHORIZED_ACCESS
    return raised.value.message.removeprefix("u is not authorized to perform ")


@pytest.fixture
def store() -> EntityStore:
    """A store of the sample, write and classification types."""
    return EntityStore(sample_registry(classifications=True), MemoryEntityDocuments())


async def entities(store: EntityStore, *bodies: dict[str, Any]) -> list[str]:
    """The GUIDs of entities created unchecked."""
    request = AtlasEntitiesWithExtInfo.model_validate(
        {"entities": [{**b, "guid": f"-{n}"} for n, b in enumerate(bodies, 1)]}
    )
    created = await EntityWriter(store).create_or_update(request)
    return [(created.guid_assignments or {})[f"-{n}"] for n in range(1, len(bodies) + 1)]


def table(qualified_name: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - attribute values
    """An ``s_table`` of the qualified name."""
    return {"typeName": "s_table", "attributes": {"qualifiedName": qualified_name, **attributes}}


@pytest.mark.covers(
    f"{A}.Authorizer.verify_access",
    f"{A}.Granted.verify_access",
    f"{A}.Granted.is_access_allowed",
    f"{A}.joined",
    rules=["AUZ-03"],
)
def test__a_refusal_names_the_user_and_the_action() -> None:
    """``<user> is not authorized to perform <action>``, the action joined as ``StringUtils.join`` joins."""
    with pytest.raises(AtlasError) as raised:
        granted(P.ENTITY_READ).verify_access(P.ENTITY_DELETE, "delete entity: guid=", "g1")
    assert (raised.value.code, raised.value.message) == (
        AtlasErrorCode.UNAUTHORIZED_ACCESS,
        "u is not authorized to perform delete entity: guid=g1",
    )
    granted(P.ENTITY_READ).verify_access(P.ENTITY_READ, "read entity: guid=", "g1")
    assert joined(["purge: ", ["a", "b"], ", ", {"qualifiedName": "t"}, None, 3]) == "purge: [a, b], {qualifiedName=t}3"
    assert joined([]) == ""


@pytest.mark.covers(f"{A}.AllowAll.verify_access", rules=["AUZ-07"])
async def test__a_store_without_an_authorizer_checks_nothing(store: EntityStore) -> None:
    """DD-301: the stores' own tests, and the server's startup, write unchecked."""
    ALLOW_ALL.verify_access(P.ADMIN_PURGE)
    assert len(await entities(store, table("t@cl"))) == 1


@pytest.mark.covers(f"{W}.create_or_update", f"{W}.update_by_unique_attributes", rules=["AUZ-07"])
async def test__creating_and_updating_entities_needs_their_privileges(store: EntityStore) -> None:
    """Each entity created, then each one changed; an unchanged one is not checked; nothing is written refused."""
    (guid,) = await entities(store, table("t@cl", name="t"))
    request = AtlasEntitiesWithExtInfo.model_validate({"entities": [table("t@cl", name="t"), table("n@cl")]})
    creator = EntityWriter(store, authorizer=granted(P.ENTITY_CREATE))

    assert await refused(EntityWriter(store, authorizer=but(P.ENTITY_CREATE)).create_or_update(request)) == (
        "create entity: type=s_table"
    )
    assert (await creator.create_or_update(request)).get_created_entities()
    changed = AtlasEntitiesWithExtInfo.model_validate({"entities": [table("t@cl", name="changed")]})
    assert await refused(creator.create_or_update(changed)) == "update entity: type=s_table"
    entity_type = store.registry.entity_type("s_table")
    assert entity_type is not None
    partial = AtlasEntityWithExtInfo(entity=AtlasEntity(type_name="s_table", attributes={"name": "partly"}))
    assert await refused(creator.update_by_unique_attributes(entity_type, {"qualifiedName": "t@cl"}, partial)) == (
        "update entity ByUniqueAttributes"
    )
    found = await store.get(guid)
    assert found is not None
    assert found.entity.attributes["s_ref.name"] == "t"


@pytest.mark.covers(f"{W}.update_attribute_by_guid", rules=["AUZ-07"])
async def test__setting_one_attribute_needs_update_once_the_entity_is_found(store: EntityStore) -> None:
    """An unknown GUID is not found before the check; a known one is refused."""
    (guid,) = await entities(store, table("t@cl"))
    reader = EntityWriter(store, authorizer=granted(P.ENTITY_READ))

    with pytest.raises(AtlasError) as missing:
        await reader.update_attribute_by_guid("missing", "name", "x")
    assert missing.value.code is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND
    assert await refused(reader.update_attribute_by_guid(guid, "name", "x")) == (
        f"update entity ByUniqueAttributes : guid={guid}"
    )


@pytest.mark.covers(f"{W}.delete_by_id", f"{W}.delete_by_ids", f"{W}.delete_by_unique_attributes", rules=["AUZ-07"])
async def test__deleting_entities_needs_delete_for_each_found(store: EntityStore) -> None:
    """Missing entities are skipped unchecked; each found one is checked, by GUID or by its unique values."""
    first, second = await entities(store, table("t@cl"), table("u@cl"))
    reader = EntityWriter(store, authorizer=granted(P.ENTITY_READ))
    entity_type = store.registry.entity_type("s_table")
    assert entity_type is not None

    assert (await reader.delete_by_id("missing")).get_deleted_entities() is None
    assert await refused(reader.delete_by_id(first)) == f"delete entity: guid={first}"
    assert await refused(reader.delete_by_ids(["missing", second, first])) == f"delete entity: guid={second}"
    assert await refused(reader.delete_by_unique_attributes(entity_type, {"qualifiedName": "t@cl"})) == (
        "delete entity: typeName=s_table, uniqueAttributes={qualifiedName=t@cl}"
    )
    assert await reader.delete_by_unique_attributes(entity_type, {"qualifiedName": "none@cl"}) is not None
    assert len(await store.get_many([first, second])) == 2


@pytest.mark.covers(
    f"{C}.get_classifications",
    f"{C}.get_classification",
    f"{C}.add_classifications",
    f"{C}.add_classification",
    f"{C}.update_classifications",
    f"{C}.delete_classification",
    rules=["AUZ-08"],
)
async def test__classifications_are_read_and_changed_with_their_privileges(store: EntityStore) -> None:
    """Reading needs ``ENTITY_READ``; adding, updating and removing each its own privilege, per classification."""
    (guid,) = await entities(store, table("t@cl"))
    pii = AtlasClassification(type_name="c_pii")

    assert await refused(EntityClassifications(store, authorizer=granted()).get_classifications(guid)) == (
        f"get classifications: guid={guid}"
    )
    assert await refused(EntityClassifications(store, authorizer=granted()).get_classification(guid, "c_pii")) == (
        f"get classification: guid={guid}, classification=c_pii"
    )
    refusing = EntityClassifications(store, authorizer=but(P.ENTITY_ADD_CLASSIFICATION))
    assert (
        await refused(refusing.add_classifications(guid, [pii]))
        == f"add classification: guid={guid}, classification=c_pii"
    )
    assert (
        await refused(refusing.add_classification([guid], pii))
        == f"add classification: guid={guid}, classification=c_pii"
    )
    await EntityClassifications(store, authorizer=granted(P.ENTITY_ADD_CLASSIFICATION)).add_classifications(guid, [pii])
    updating = EntityClassifications(store, authorizer=but(P.ENTITY_UPDATE_CLASSIFICATION))
    assert await refused(updating.update_classifications(guid, [pii])) == (
        f"update classification: guid={guid}, classification=c_pii"
    )
    removing = EntityClassifications(store, authorizer=but(P.ENTITY_REMOVE_CLASSIFICATION))
    assert await refused(removing.delete_classification(guid, "c_pii")) == (
        f"remove classification: guid={guid}, classification=c_pii"
    )
    found = await EntityClassifications(store, authorizer=granted(P.ENTITY_READ)).get_classification(guid, "c_pii")
    assert found.type_name == "c_pii"


@pytest.mark.covers(f"{C}.delete_classification", rules=["AUZ-08"])
async def test__a_propagated_classification_is_let_go_unchecked(store: EntityStore) -> None:
    """Only a classification attached directly is checked: one propagated from a deleted entity is not."""
    data, process = await entities(
        store,
        {"typeName": "p_data", "attributes": {"qualifiedName": "a"}},
        {"typeName": "p_process", "attributes": {"qualifiedName": "p"}},
    )
    await RelationshipStore(store).create(
        AtlasRelationship.model_validate(
            {"typeName": "p_input", "end1": {"guid": data}, "end2": {"guid": process}, "propagateTags": "ONE_TO_TWO"}
        )
    )
    await EntityClassifications(store).add_classifications(data, [AtlasClassification(type_name="c_pii")])
    await EntityWriter(store).delete_by_id(data)

    await EntityClassifications(store, authorizer=granted()).delete_classification(process, "c_pii", data)

    assert await EntityClassifications(store).get_classifications(process) == []


@pytest.mark.covers(
    "aurelius_atlas_core.classification_associator.ClassificationAssociator.set_classifications", rules=["AUZ-08"]
)
async def test__setting_classifications_records_a_refused_step_as_partial(store: EntityStore) -> None:
    """The associator reads the classifications unchecked; a refused add is the step's ``(Partial)``."""
    (guid,) = await entities(store, table("t@cl"))
    header = AtlasEntityHeader(
        type_name="s_table",
        attributes={"qualifiedName": "t@cl"},
        classifications=[AtlasClassification(type_name="c_pii")],
    )

    summary = await ClassificationAssociator(store, authorizer=granted()).set_classifications({guid: header})

    assert summary == f'["Add:{guid}:s_table:qualifiedName -> c_pii:(Partial)"]'
    assert await EntityClassifications(store).get_classifications(guid) == []


@pytest.mark.covers(f"{R}.create", f"{R}.update", f"{R}.delete_by_id", rules=["AUZ-09"])
async def test__relationships_are_added_updated_and_removed_with_their_privileges(store: EntityStore) -> None:
    """Without an action text, after the request is validated; a type with a legacy end is not checked on add."""
    item, database, column = await entities(
        store,
        {"typeName": "w_item", "attributes": {"qualifiedName": "i@cl"}},
        {"typeName": "s_database", "attributes": {"qualifiedName": "d@cl"}},
        {"typeName": "s_column", "attributes": {"qualifiedName": "c@cl"}},
    )
    link = AtlasRelationship.model_validate({"typeName": "w_link", "end1": {"guid": item}, "end2": {"guid": column}})
    holder = AtlasRelationship.model_validate(
        {"typeName": "w_item_holder", "end1": {"guid": item}, "end2": {"guid": database}}
    )

    assert await refused(RelationshipStore(store, authorizer=but(P.RELATIONSHIP_ADD)).create(link)) == ""
    assert (await RelationshipStore(store, authorizer=granted()).create(holder)).guid
    created = await RelationshipStore(store, authorizer=granted(P.RELATIONSHIP_ADD)).create(link)
    created.propagate_tags = None
    assert await refused(RelationshipStore(store, authorizer=but(P.RELATIONSHIP_UPDATE)).update(created)) == ""
    assert (
        await refused(RelationshipStore(store, authorizer=but(P.RELATIONSHIP_REMOVE)).delete_by_id(str(created.guid)))
        == ""
    )
    await RelationshipStore(store, authorizer=granted(P.RELATIONSHIP_REMOVE)).delete_by_id(str(created.guid))


def glossary_store() -> EntityStore:
    """A store with the base and glossary models."""
    registry = TypeRegistry()
    with registry.update() as transient:
        for name in ("0010-base_model.json", "0011-glossary_model.json"):
            transient.add_types(AtlasTypesDef.model_validate(json.loads((MODELS / name).read_text(encoding="utf-8"))))
    return EntityStore(registry, MemoryEntityDocuments())


@pytest.mark.covers(
    "aurelius_atlas_core.data_access.DataAccess.save",
    "aurelius_atlas_core.data_access.DataAccess.load",
    "aurelius_atlas_core.data_access.DataAccess.delete",
    "aurelius_atlas_core.glossary_service.GlossaryService.get_glossaries",
    "aurelius_atlas_core.glossary_service.GlossaryService.assign_term_to_entities",
    rules=["AUZ-10"],
)
async def test__the_glossary_is_checked_as_its_entities_and_relationships() -> None:
    """Saving creates or updates entities, loading reads one, deleting deletes them, assigning a term relates."""
    store = glossary_store()
    created = await GlossaryService(store).create_glossary(AtlasGlossary(name="bank"))
    term = await GlossaryService(store).create_term(
        AtlasGlossaryTerm(name="loan", anchor=AtlasGlossaryHeader(glossary_guid=created.guid))
    )
    asset = (await entities(store, {"typeName": "Asset", "attributes": {"qualifiedName": "a", "name": "a"}}))[0]

    assert await refused(GlossaryService(store, authorizer=granted()).create_glossary(AtlasGlossary(name="other"))) == (
        "create entity: type=AtlasGlossary"
    )
    assert await refused(GlossaryService(store, authorizer=granted()).get_glossary(created.guid)) == (
        f"read entity: guid={created.guid}"
    )
    assert await refused(GlossaryService(store, authorizer=granted()).get_glossaries(-1, 0, SortOrder.ASCENDING)) == (
        f"read entity: guid={created.guid}"
    )
    assert await refused(GlossaryService(store, authorizer=but(P.ENTITY_DELETE)).delete_glossary(created.guid)) == (
        f"delete entity: guid={term.guid}"
    )
    assign = GlossaryService(store, authorizer=but(P.RELATIONSHIP_ADD))
    assert await refused(assign.assign_term_to_entities(term.guid, [AtlasRelatedObjectId(guid=asset)])) == ""
    assert [g.name for g in await GlossaryService(store).get_glossaries(-1, 0, SortOrder.ASCENDING)] == ["bank"]


@pytest.mark.covers("aurelius_atlas_core.user_profile_service.UserProfileService.get_user_profile", rules=["AUZ-10"])
async def test__a_profile_is_read_by_its_unique_name_with_read() -> None:
    """``read entity: typeName=__AtlasUserProfile, uniqueAttributes={name=<user>}``; saving needs create."""
    store = glossary_store()
    saved = AtlasUserSavedSearch.model_validate(
        {"name": "s", "ownerName": "u", "searchParameters": {"typeName": "Asset"}}
    )
    assert await refused(UserProfileService(store, user="u", authorizer=granted()).add_saved_search(saved)) == (
        "create entity: type=__AtlasUserProfile"
    )
    await UserProfileService(store, user="u").add_saved_search(saved)

    assert await refused(UserProfileService(store, user="u", authorizer=granted()).get_user_profile("u")) == (
        "read entity: typeName=__AtlasUserProfile, uniqueAttributes={name=u}"
    )
    found = await UserProfileService(store, user="u", authorizer=granted(P.ENTITY_READ)).get_user_profile("u")
    assert isinstance(found, AtlasUserProfile)
