"""``UserProfileService``: users' profiles and the searches they saved (SVS-02 to SVS-05).

A profile is created with its user's first saved search; a search's name is unique among its owner's searches.
"""

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.profile import AtlasUserProfile, AtlasUserSavedSearch

from aurelius_atlas_core.authorization import ALLOW_ALL, Authorizer
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.user_profile_dto import profile_data_access


class UserProfileService:
    """The profiles and saved searches of ``store``, written as ``user`` and checked by ``authorizer`` (AUZ-10)."""

    def __init__(self, store: EntityStore, *, user: str | None = None, authorizer: Authorizer = ALLOW_ALL) -> None:
        self._data_access = profile_data_access(store, user=user, authorizer=authorizer)

    async def get_user_profile(self, user_name: str | None) -> AtlasUserProfile:
        """``getUserProfile``: the profile of the user's name.

        Raises:
            AtlasError: ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` when the user has none.
        """
        return await self._data_access.load(AtlasUserProfile(name=user_name))

    async def add_saved_search(self, saved_search: AtlasUserSavedSearch) -> AtlasUserSavedSearch:
        """``addSavedSearch``: the search added to its owner's profile, made when there is none (SVS-02).

        Raises:
            AtlasError: ``SAVED_SEARCH_ALREADY_EXISTS`` when the owner has a search of the name.
        """
        try:
            profile = await self.get_user_profile(saved_search.owner_name)
        except AtlasError:
            profile = AtlasUserProfile(name=saved_search.owner_name)
        for existing in profile.saved_searches:
            if (existing.owner_name, existing.name) == (saved_search.owner_name, saved_search.name):
                raise AtlasError(AtlasErrorCode.SAVED_SEARCH_ALREADY_EXISTS, saved_search.name, saved_search.owner_name)
        profile.saved_searches.append(saved_search)
        profile = await self._data_access.save(profile)
        return next((found for found in profile.saved_searches if found.name == saved_search.name), saved_search)

    async def update_saved_search(self, saved_search: AtlasUserSavedSearch) -> AtlasUserSavedSearch:
        """``updateSavedSearch``: the search of the GUID, its owner kept, its new name not another's (SVS-03).

        Raises:
            AtlasError: ``INVALID_OBJECT_ID`` without a GUID, ``SAVED_SEARCH_CHANGE_USER`` for another owner,
                ``SAVED_SEARCH_ALREADY_EXISTS`` for the name of another of the owner's searches.
        """
        if not saved_search.guid or not saved_search.guid.strip():
            raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, saved_search.guid)
        existing = await self.get_saved_search(saved_search.guid)
        if existing.owner_name != saved_search.owner_name:
            raise AtlasError(
                AtlasErrorCode.SAVED_SEARCH_CHANGE_USER, existing.name, existing.owner_name, saved_search.owner_name
            )
        if existing.name != saved_search.name:
            profile = await self.get_user_profile(existing.owner_name)
            for search in profile.saved_searches:
                if search.name == saved_search.name and search.guid != saved_search.guid:
                    raise AtlasError(
                        AtlasErrorCode.SAVED_SEARCH_ALREADY_EXISTS, saved_search.name, saved_search.owner_name
                    )
        return await self._data_access.save(saved_search)

    async def get_saved_searches(self, user_name: str | None) -> list[AtlasUserSavedSearch] | None:
        """``getSavedSearches``: the user's searches in their profile's order; None without a profile (SVS-04)."""
        try:
            profile = await self.get_user_profile(user_name)
        except AtlasError:
            return None
        return profile.saved_searches

    async def get_saved_search_by_name(self, user_name: str | None, search_name: str) -> AtlasUserSavedSearch:
        """``getSavedSearch(userName, searchName)``: by its unique name (SVS-04).

        Raises:
            AtlasError: ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` when the user has no search of the name.
        """
        return await self._data_access.load(AtlasUserSavedSearch(owner_name=user_name, name=search_name))

    async def get_saved_search(self, guid: str) -> AtlasUserSavedSearch:
        """``getSavedSearch(guid)`` (SVS-04).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND``, or ``UNEXPECTED_TYPE`` for another entity.
        """
        return await self._data_access.load(AtlasUserSavedSearch(guid=guid))

    async def delete_saved_search(self, guid: str) -> None:
        """``deleteSavedSearch``: the search's entity, gone from its profile (SVS-05)."""
        await self._data_access.delete(guid)
