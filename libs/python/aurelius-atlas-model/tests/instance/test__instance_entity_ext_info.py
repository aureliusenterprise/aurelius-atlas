"""``AtlasEntityExtInfo`` (ENT-10), read from ``AtlasEntity.AtlasEntityExtInfo`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityExtInfo

M = "aurelius_atlas_model.instance.entity_ext_info.AtlasEntityExtInfo"


@pytest.mark.covers(
    f"{M}.add_referred_entity",
    f"{M}.add_referred_entity_as",
    f"{M}.get_referred_entity",
    f"{M}.get_entity",
    f"{M}.has_entity",
    rules=["ENT-10"],
)
def test__referred_entities_are_kept_by_guid() -> None:
    """``addReferredEntity`` creates the map even for an entity it cannot add, one without a GUID."""
    ext_info = AtlasEntityExtInfo()
    entity = AtlasEntity(guid="-1")

    ext_info.add_referred_entity(AtlasEntity(guid=None))
    assert ext_info.to_json() == {"referredEntities": {}}

    ext_info.add_referred_entity(entity)
    ext_info.add_referred_entity_as("-2", AtlasEntity(guid="other"))

    assert ext_info.get_referred_entity("-1") is entity
    assert ext_info.get_entity("-2") is not None
    assert ext_info.has_entity("-1")
    assert not ext_info.has_entity(None)
    assert ext_info.get_referred_entity(None) is None


@pytest.mark.covers(f"{M}.remove_referred_entity", f"{M}.remove_entity", rules=["ENT-10"])
def test__referred_entities_are_removed_by_guid() -> None:
    """Removing returns the entity, or None for an unknown or null GUID and without a map."""
    ext_info = AtlasEntityExtInfo()
    assert ext_info.remove_entity("-1") is None
    ext_info.add_referred_entity(AtlasEntity(guid="-1"))

    assert ext_info.remove_referred_entity(None) is None
    assert ext_info.remove_entity("-1") is not None
    assert ext_info.referred_entities == {}


@pytest.mark.covers(f"{M}.update_entity_guid", f"{M}.compact", rules=["ENT-10"])
def test__a_referred_entity_moves_to_its_new_guid() -> None:
    """``updateEntityGuid`` sets the GUID and re-keys the map; an unknown GUID changes nothing."""
    ext_info = AtlasEntityExtInfo()
    ext_info.add_referred_entity(AtlasEntity(guid="-1"))

    ext_info.update_entity_guid("-1", "real")
    ext_info.update_entity_guid("missing", "other")
    ext_info.compact()

    assert list(ext_info.referred_entities or {}) == ["real"]
    assert (ext_info.referred_entities or {})["real"].guid == "real"
