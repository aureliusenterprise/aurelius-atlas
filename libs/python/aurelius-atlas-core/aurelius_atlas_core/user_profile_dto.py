"""``AtlasUserProfileDTO`` and ``AtlasSavedSearchDTO``: a user's profile and saved searches as entities (SVS-01).

A profile is an ``__AtlasUserProfile`` of the user's name, owning its searches in ``savedSearches``; a search is an
``__AtlasUserSavedSearch`` whose ``uniqueName`` is ``<owner>:<name>`` and whose parameters are their JSON text.
"""

import json
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo, AtlasObjectId, EntityStatus
from aurelius_atlas_model.profile import AtlasUserProfile, AtlasUserSavedSearch, SavedSearchType

from aurelius_atlas_core.authorization import ALLOW_ALL, Authorizer
from aurelius_atlas_core.data_access import DataAccess, Registry
from aurelius_atlas_core.entity_store import EntityStore

USER_PROFILE_TYPE = "__AtlasUserProfile"
SAVED_SEARCH_TYPE = "__AtlasUserSavedSearch"


class AtlasSavedSearchDTO:
    """``AtlasSavedSearchDTO``: a saved search as its entity, its profile named by the owner."""

    type_name = SAVED_SEARCH_TYPE

    def from_entity(self, found: AtlasEntityWithExtInfo) -> AtlasUserSavedSearch:
        """``from``: the search's attributes, its parameters read from their JSON text."""
        return saved_search_from(found.entity)  # type: ignore[arg-type]  # a read answers the entity

    def to_entities(self, obj: AtlasUserSavedSearch) -> list[AtlasEntity]:
        """``toEntity``: the search's entity, its profile by the owner's name."""
        return [
            saved_search_entity(
                obj, AtlasObjectId(type_name=USER_PROFILE_TYPE, unique_attributes={"name": obj.owner_name})
            )
        ]

    def unique_attributes(self, obj: AtlasUserSavedSearch) -> dict[str, Any]:
        """``getUniqueAttributes``: ``uniqueName``."""
        return {"uniqueName": obj.unique_name}


class AtlasUserProfileDTO:
    """``AtlasUserProfileDTO``: a profile as its entity and the entities of its searches."""

    type_name = USER_PROFILE_TYPE

    def from_entity(self, found: AtlasEntityWithExtInfo) -> AtlasUserProfile:
        """``from``: the name and full name, and the active searches the profile owns, in its order."""
        entity = found.entity
        if entity is None:  # pragma: no cover - a read answers the entity
            return AtlasUserProfile()
        profile = AtlasUserProfile(
            guid=str(entity.guid), name=entity.get_attribute("name"), full_name=entity.get_attribute("fullName")
        )
        for item in entity.get_attribute("savedSearches") or []:
            object_id = item if isinstance(item, AtlasObjectId) else AtlasObjectId.model_validate(item)
            referred = None if object_id.guid is None else found.get_referred_entity(object_id.guid)
            if referred is not None and referred.status is EntityStatus.ACTIVE:
                profile.saved_searches.append(saved_search_from(referred))
        return profile

    def to_entities(self, obj: AtlasUserProfile) -> list[AtlasEntity]:
        """``toEntityWithExtInfo``: the profile's entity listing its searches, then theirs, each naming the profile."""
        profile = AtlasEntity(
            type_name=USER_PROFILE_TYPE, guid=obj.guid, attributes={"name": obj.name, "fullName": obj.full_name}
        )
        profile_id = AtlasObjectId(guid=obj.guid, type_name=USER_PROFILE_TYPE, unique_attributes={"name": obj.name})
        searches = [saved_search_entity(search, profile_id) for search in obj.saved_searches]
        if searches:
            profile.set_attribute(
                "savedSearches",
                [
                    AtlasObjectId(
                        guid=search.guid,
                        type_name=SAVED_SEARCH_TYPE,
                        unique_attributes={"uniqueName": saved.unique_name},
                    )
                    for search, saved in zip(searches, obj.saved_searches, strict=True)
                ],
            )
        return [profile, *searches]

    def unique_attributes(self, obj: AtlasUserProfile) -> dict[str, Any]:
        """``getUniqueAttributes``: the user's name."""
        return {"name": obj.name}


PROFILE_DTOS: Registry = {AtlasUserProfile: AtlasUserProfileDTO(), AtlasUserSavedSearch: AtlasSavedSearchDTO()}


def profile_data_access(
    store: EntityStore, *, user: str | None = None, authorizer: Authorizer = ALLOW_ALL
) -> DataAccess:
    """The ``DataAccess`` of profiles and saved searches in ``store``, as ``user``, checked by ``authorizer``."""
    return DataAccess(store, PROFILE_DTOS, user=user, authorizer=authorizer)


def saved_search_from(entity: AtlasEntity) -> AtlasUserSavedSearch:
    """``AtlasSavedSearchDTO.from``: the attributes, the type by its name, the parameters from their JSON text."""
    text = entity.get_attribute("searchParameters")
    return AtlasUserSavedSearch(
        guid=str(entity.guid),
        name=entity.get_attribute("name"),
        owner_name=entity.get_attribute("ownerName"),
        search_type=SavedSearchType.to(entity.get_attribute("searchType")),
        search_parameters=SearchParameters.model_validate(json.loads(text)) if text else None,
        ui_parameters=entity.get_attribute("uiParameters"),
    )


def saved_search_entity(obj: AtlasUserSavedSearch, profile: AtlasObjectId) -> AtlasEntity:
    """``AtlasSavedSearchDTO.toEntity``: the search's attributes and ``uniqueName``, referring to its profile."""
    attributes: dict[str, Any] = {
        "name": obj.name,
        "ownerName": obj.owner_name,
        "searchType": None if obj.search_type is None else obj.search_type.value,
        "uniqueName": obj.unique_name,
        "userProfile": profile,
        "uiParameters": obj.ui_parameters,
    }
    if obj.search_parameters is not None:
        attributes["searchParameters"] = codec.dumps(obj.search_parameters.to_json()).decode()
    return AtlasEntity(type_name=SAVED_SEARCH_TYPE, guid=obj.guid, attributes=attributes)
