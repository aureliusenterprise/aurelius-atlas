"""The user profile models: ``AtlasUserSavedSearch`` and ``AtlasUserProfile`` (SVS-01).

Atlas writes both without nulls; a new object has a negative GUID, as every ``AtlasBaseModelObject``.
"""

from enum import StrEnum

from pydantic import Field

from aurelius_atlas_model.base import AtlasModel, new_model_guid
from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.errors import java_string


class SavedSearchType(StrEnum):
    """``AtlasUserSavedSearch.SavedSearchType``."""

    BASIC = "BASIC"
    ADVANCED = "ADVANCED"
    BASIC_RELATIONSHIP = "BASIC_RELATIONSHIP"

    @classmethod
    def to(cls, value: str | None) -> SavedSearchType:
        """``to``: the type of the name in any case, ``BASIC`` for any other (SVS-01)."""
        for found in (cls.ADVANCED, cls.BASIC_RELATIONSHIP):
            if value is not None and value.lower() == found.value.lower():
                return found
        return cls.BASIC


class AtlasUserSavedSearch(AtlasModel):
    """``AtlasUserSavedSearch``: a search its owner saved under a name (SVS-01)."""

    guid: str = Field(default_factory=new_model_guid)
    owner_name: str | None = None
    name: str | None = None
    search_type: SavedSearchType | None = SavedSearchType.BASIC
    search_parameters: SearchParameters | None = None
    ui_parameters: str | None = None

    @property
    def unique_name(self) -> str:
        """``getUniqueValue``: ``<owner>:<name>``, Java's text of each (SVS-01)."""
        return f"{java_string(self.owner_name)}:{java_string(self.name)}"


class AtlasUserProfile(AtlasModel):
    """``AtlasUserProfile``: a user's name, full name and saved searches."""

    guid: str = Field(default_factory=new_model_guid)
    name: str | None = None
    full_name: str | None = None
    saved_searches: list[AtlasUserSavedSearch] = Field(default_factory=list)
