"""Saved searches and user profiles (SVS-01 to SVS-06) on the in-memory documents.

Read from ``UserProfileService``, ``EntityDiscoveryService``'s saved-search methods, ``AtlasUserProfileDTO``,
``AtlasSavedSearchDTO`` and ``DataAccess`` of Apache Atlas 2.4.0, with the cases of ``UserProfileServiceTest``.
"""

import json

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.user_profile_service import UserProfileService
from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity
from aurelius_atlas_model.profile import AtlasUserSavedSearch, SavedSearchType
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

D = "aurelius_atlas_core.discovery_service.EntityDiscoveryService"
P = "aurelius_atlas_core.user_profile_service.UserProfileService"
DTO = "aurelius_atlas_core.user_profile_dto"
MODELS = BUILTIN_MODELS_DIR / "0000-Area0"


@pytest.fixture
def store() -> EntityStore:
    """A store with the base model, which holds the profile and saved-search types."""
    registry = TypeRegistry()
    with registry.update() as transient:
        base = json.loads((MODELS / "0010-base_model.json").read_text(encoding="utf-8"))
        transient.add_types(AtlasTypesDef.model_validate(base))
    return EntityStore(registry, MemoryEntityDocuments())


def search(name: str, owner: str | None = None, **fields: object) -> AtlasUserSavedSearch:
    """A basic search of ``Asset`` under the name."""
    return AtlasUserSavedSearch.model_validate(
        {"name": name, "ownerName": owner, "searchParameters": {"typeName": "Asset", "limit": 10}, **fields}
    )


async def failure(awaitable: object) -> tuple[AtlasErrorCode, str]:
    """The code and message of the error the awaitable raises."""
    with pytest.raises(AtlasError) as raised:
        await awaitable  # type: ignore[misc]
    return raised.value.code, raised.value.message


@pytest.mark.covers(
    f"{D}.add_saved_search",
    f"{P}.add_saved_search",
    f"{P}.get_user_profile",
    f"{DTO}.AtlasUserProfileDTO.to_entities",
    f"{DTO}.AtlasUserProfileDTO.from_entity",
    f"{DTO}.AtlasUserProfileDTO.unique_attributes",
    f"{DTO}.saved_search_from",
    f"{DTO}.saved_search_entity",
    f"{DTO}.profile_data_access",
    *(
        f"aurelius_atlas_core.data_access.DataTransferObject.{name}"
        for name in ("type_name", "from_entity", "to_entities", "unique_attributes")
    ),
    rules=["SVS-01", "SVS-02"],
)
async def test__a_saved_search_is_owned_by_the_user_who_saves_it(store: EntityStore) -> None:
    """``testAddSavedSearch``: the profile is made with the first search; its entities hold the unique name."""
    discovery = EntityDiscoveryService(store)
    first = await discovery.add_saved_search("ann", search("tables"))
    second = await discovery.add_saved_search("ann", search("dsl", searchType="ADVANCED", uiParameters="{}"))
    assert (first.owner_name, first.name, first.search_type, first.guid.startswith("-")) == (
        "ann",
        "tables",
        SavedSearchType.BASIC,
        False,
    )
    assert (second.search_type, second.ui_parameters) == (SavedSearchType.ADVANCED, "{}")
    assert first.search_parameters == SearchParameters(type_name="Asset", limit=10)
    profile = await UserProfileService(store).get_user_profile("ann")
    assert (profile.name, [found.name for found in profile.saved_searches]) == ("ann", ["tables", "dsl"])
    entity = (await EntityRetriever(store).entity_with_ext_info(first.guid)).entity
    assert entity is not None
    assert (entity.get_attribute("uniqueName"), json.loads(entity.get_attribute("searchParameters"))["typeName"]) == (
        "ann:tables",
        "Asset",
    )
    assert (entity.created_by, first.to_json()["guid"]) == ("ann", first.guid)
    assert await failure(discovery.add_saved_search("ann", search("tables"))) == (
        AtlasErrorCode.SAVED_SEARCH_ALREADY_EXISTS,
        "search named tables already exists for user ann",
    )
    assert await failure(discovery.add_saved_search("ann", search("x", "bob"))) == (
        AtlasErrorCode.BAD_REQUEST,
        "invalid data",
    )
    assert (await discovery.add_saved_search("bob", search("tables", "bob"))).owner_name == "bob"


@pytest.mark.covers(
    f"{D}.update_saved_search",
    f"{P}.update_saved_search",
    f"{DTO}.AtlasSavedSearchDTO.to_entities",
    f"{DTO}.AtlasSavedSearchDTO.from_entity",
    f"{DTO}.AtlasSavedSearchDTO.unique_attributes",
    rules=["SVS-03"],
)
async def test__an_update_keeps_the_owner_and_a_free_name(store: EntityStore) -> None:
    """``testUpdateSavedSearch``: renamed and changed; no GUID, another owner, a taken name fail."""
    discovery = EntityDiscoveryService(store)
    first = await discovery.add_saved_search("ann", search("one"))
    await discovery.add_saved_search("ann", search("two"))
    first.name, first.search_parameters = "renamed", SearchParameters(type_name="DataSet")
    updated = await discovery.update_saved_search("ann", first)
    assert (updated.guid, updated.name, updated.search_parameters) == (
        first.guid,
        "renamed",
        SearchParameters(type_name="DataSet"),
    )
    assert [found.name for found in await discovery.get_saved_searches("ann", None) or []] == ["renamed", "two"]
    taken = updated.model_copy(update={"name": "two"})
    assert await failure(discovery.update_saved_search("ann", taken)) == (
        AtlasErrorCode.SAVED_SEARCH_ALREADY_EXISTS,
        "search named two already exists for user ann",
    )
    assert (await failure(discovery.update_saved_search("ann", search("x", guid=""))))[0] is (
        AtlasErrorCode.INVALID_OBJECT_ID
    )
    moved = updated.model_copy(update={"owner_name": "bob"})
    assert (await failure(UserProfileService(store).update_saved_search(moved))) == (
        AtlasErrorCode.SAVED_SEARCH_CHANGE_USER,
        "saved-search renamed can not be moved from user ann to bob",
    )


@pytest.mark.covers(
    f"{D}.get_saved_searches",
    f"{D}.get_saved_search_by_name",
    f"{D}.get_saved_search_by_guid",
    f"{D}.delete_saved_search",
    f"{P}.get_saved_searches",
    f"{P}.get_saved_search_by_name",
    f"{P}.get_saved_search",
    f"{P}.delete_saved_search",
    rules=["SVS-04", "SVS-05"],
)
async def test__a_user_reads_and_deletes_only_their_own_searches(store: EntityStore) -> None:
    """By name and by GUID; another user's, or naming another user, is ``invalid data``; none without a profile."""
    discovery = EntityDiscoveryService(store)
    mine = await discovery.add_saved_search("ann", search("mine"))
    theirs = await discovery.add_saved_search("bob", search("theirs"))
    assert await discovery.get_saved_searches("carl", None) is None
    assert (await discovery.get_saved_search_by_name("ann", "ann", "mine")).guid == mine.guid
    assert (await discovery.get_saved_search_by_guid("ann", mine.guid)).name == "mine"
    for refused in (
        discovery.get_saved_searches("ann", "bob"),
        discovery.get_saved_search_by_name("ann", "bob", "theirs"),
        discovery.get_saved_search_by_guid("ann", theirs.guid),
        discovery.delete_saved_search("ann", theirs.guid),
    ):
        assert await failure(refused) == (AtlasErrorCode.BAD_REQUEST, "invalid data")
    assert (await failure(discovery.get_saved_search_by_name("ann", None, "nope")))[0] is (
        AtlasErrorCode.INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND
    )
    await discovery.delete_saved_search("ann", mine.guid)
    assert await discovery.get_saved_searches("ann", None) == []
    assert (await failure(discovery.get_saved_search_by_guid("ann", mine.guid)))[0] is (
        AtlasErrorCode.INSTANCE_GUID_NOT_FOUND
    )
    profile = (await discovery.get_saved_searches("bob", "bob")) or []
    assert (await failure(discovery.get_saved_search_by_guid("bob", "nope")))[
        0
    ] is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND
    assert [found.name for found in profile] == ["theirs"]


@pytest.mark.covers(f"{D}.execute_saved_search", rules=["SVS-06"])
async def test__a_saved_search_runs_as_the_search_it_saved(store: EntityStore) -> None:
    """A basic search by its parameters, an ``ADVANCED`` one as its DSL query; none without parameters (DV-110)."""
    entity = AtlasEntity(type_name="Asset", attributes={"qualifiedName": "a", "name": "a"})
    await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo(entities=[entity]))
    discovery = EntityDiscoveryService(store)
    basic = await discovery.execute_saved_search(search("b"))
    advanced = await discovery.execute_saved_search(
        search("d", searchType="ADVANCED", searchParameters={"typeName": "Asset", "query": "where name = 'a'"})
    )
    assert [header.display_text for header in basic.entities or []] == ["a"]
    assert (advanced.query_text, [header.display_text for header in advanced.entities or []]) == (
        "`Asset` where name = 'a'",
        ["a"],
    )
    empty = AtlasUserSavedSearch(name="e")
    assert await failure(discovery.execute_saved_search(empty)) == (
        AtlasErrorCode.BAD_REQUEST,
        "The saved search has no search parameters",
    )
