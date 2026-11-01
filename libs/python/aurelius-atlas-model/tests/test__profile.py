"""The user profile models (SVS-01), as Atlas 2.4.0's ``AtlasUserSavedSearch`` and ``AtlasUserProfile`` are."""

import pytest
from aurelius_atlas_model.base import new_model_guid
from aurelius_atlas_model.profile import AtlasUserProfile, AtlasUserSavedSearch, SavedSearchType

P = "aurelius_atlas_model.profile"


@pytest.mark.covers(f"{P}.SavedSearchType.to", rules=["SVS-01"])
def test__a_search_type_is_read_by_its_name_in_any_case() -> None:
    """``SavedSearchType.to``: ``ADVANCED`` and ``BASIC_RELATIONSHIP`` by name, anything else ``BASIC``."""
    assert [SavedSearchType.to(name) for name in ("advanced", "Basic_Relationship", "x", None)] == [
        SavedSearchType.ADVANCED,
        SavedSearchType.BASIC_RELATIONSHIP,
        SavedSearchType.BASIC,
        SavedSearchType.BASIC,
    ]


@pytest.mark.covers(
    f"{P}.AtlasUserSavedSearch.unique_name", "aurelius_atlas_model.base.new_model_guid", rules=["SVS-01"]
)
def test__a_new_search_has_a_negative_guid_and_a_unique_name() -> None:
    """A new object's GUID is negative and new; the unique name is ``<owner>:<name>``, ``null`` for none."""
    first, second = AtlasUserSavedSearch(owner_name="ann", name="s"), AtlasUserSavedSearch(name="t")
    assert (first.guid.startswith("-"), first.guid != second.guid, new_model_guid() != first.guid) == (True, True, True)
    assert (first.unique_name, second.unique_name) == ("ann:s", "null:t")
    assert first.to_json() == {"guid": first.guid, "ownerName": "ann", "name": "s", "searchType": "BASIC"}
    assert AtlasUserProfile(guid="g", name="ann").to_json() == {"guid": "g", "name": "ann", "savedSearches": []}
