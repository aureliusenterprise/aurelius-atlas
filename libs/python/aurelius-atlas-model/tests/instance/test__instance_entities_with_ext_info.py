"""``AtlasEntitiesWithExtInfo`` (ENT-10, ENT-18).

Read from ``AtlasEntity.AtlasEntitiesWithExtInfo`` of Atlas 2.4.0 and the bodies of its hive hook tests
(``addons/hive-bridge/src/test/resources/json``).
"""

import json
from pathlib import Path

import pytest
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity

M = "aurelius_atlas_model.instance.entities_with_ext_info.AtlasEntitiesWithExtInfo"
FIXTURES = Path(__file__).parents[1] / "fixtures"
HIVE_MESSAGES = sorted(FIXTURES.glob("hs2-create-*.json"))


@pytest.mark.covers(f"{M}.add_entity", f"{M}.get_entity", f"{M}.compact", rules=["ENT-10"])
def test__main_entities_are_found_and_compacted_away_from_the_referred_ones() -> None:
    """``getEntity`` looks in the referred entities, then the list; ``compact`` drops the duplicates."""
    body = AtlasEntitiesWithExtInfo()
    first, second = AtlasEntity(guid="-1"), AtlasEntity(guid="-2")
    body.add_entity(first)
    body.add_entity(second)
    body.add_referred_entity(AtlasEntity(guid="-2", type_name="copy"))
    body.add_referred_entity(AtlasEntity(guid="-3"))

    assert (body.get_entity("-2") or AtlasEntity()).type_name == "copy"
    body.compact()

    assert body.get_entity("-2") is second
    assert body.get_entity("-1") is first
    assert body.get_entity("-4") is None
    assert list(body.referred_entities or {}) == ["-3"]


@pytest.mark.covers(f"{M}.remove_entity", rules=["ENT-10"])
def test__an_entity_or_a_guid_is_removed() -> None:
    """Java's two ``removeEntity``: by entity from the list, by GUID from the referred entities."""
    body = AtlasEntitiesWithExtInfo()
    listed = AtlasEntity(guid="-1")
    body.add_entity(listed)
    body.add_referred_entity(AtlasEntity(guid="-2"))

    assert body.remove_entity(AtlasEntity(guid="-9")) is None
    body.remove_entity(listed)
    removed = body.remove_entity("-2")

    assert body.entities == []
    assert removed is not None
    assert removed.guid == "-2"
    assert AtlasEntitiesWithExtInfo().remove_entity(listed) is None


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-18"])
@pytest.mark.parametrize("message", HIVE_MESSAGES, ids=[path.stem for path in HIVE_MESSAGES])
def test__atlas_s_hive_hook_messages_read_and_write_back_unchanged(message: Path) -> None:
    """Entities as Atlas writes them: ``"proxy"``, no ``status`` after ``init()``, nested structs as maps."""
    body = json.loads(message.read_text())

    assert AtlasEntitiesWithExtInfo.model_validate(body).to_json() == body
    assert len(HIVE_MESSAGES) == 6
