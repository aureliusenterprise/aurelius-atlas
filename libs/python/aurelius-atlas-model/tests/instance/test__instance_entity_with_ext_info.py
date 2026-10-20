"""``AtlasEntityWithExtInfo`` (ENT-10), read from ``AtlasEntity.AtlasEntityWithExtInfo`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo

M = "aurelius_atlas_model.instance.entity_with_ext_info.AtlasEntityWithExtInfo"


@pytest.mark.covers(f"{M}.get_entity", f"{M}.compact", rules=["ENT-10"])
def test__the_main_entity_is_found_and_compacted_away_from_the_referred_ones() -> None:
    """``getEntity`` looks in the referred entities first, then at ``entity``; ``compact`` drops its duplicate."""
    main = AtlasEntity(guid="-1")
    body = AtlasEntityWithExtInfo(entity=main)
    body.add_referred_entity(AtlasEntity(guid="-1", type_name="copy"))
    body.add_referred_entity(AtlasEntity(guid="-2"))

    assert (body.get_entity("-1") or AtlasEntity()).type_name == "copy"
    body.compact()

    assert body.get_entity("-1") is main
    assert body.get_entity("-3") is None
    assert list(body.referred_entities or {}) == ["-2"]
    assert AtlasEntityWithExtInfo().get_entity("-1") is None


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-10"])
def test__it_reads_and_writes_entity_and_referred_entities() -> None:
    """The getters ``getEntity`` and ``getReferredEntities``."""
    body = {"entity": {"guid": "-1", "typeName": "t"}, "referredEntities": {"-2": {"guid": "-2"}}}

    written = AtlasEntityWithExtInfo.model_validate(body).to_json()

    assert (written["entity"]["typeName"], list(written["referredEntities"])) == ("t", ["-2"])
