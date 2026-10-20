"""``AtlasObjectId`` (ENT-11), read from ``org.apache.atlas.model.instance.AtlasObjectId`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelatedObjectId


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-11"])
def test__an_object_id_reads_and_writes_its_three_fields() -> None:
    """``guid``, ``typeName`` and ``uniqueAttributes``; missing ones are not written."""
    body = {"typeName": "hive_db", "uniqueAttributes": {"qualifiedName": "db@cm"}}

    assert AtlasObjectId.model_validate(body).to_json() == body


@pytest.mark.covers("aurelius_atlas_model.instance.object_id.AtlasObjectId.__eq__", rules=["ENT-11"])
def test__object_ids_are_equal_by_guid_when_either_has_one() -> None:
    """``AtlasObjectId.equals``: a GUID decides; without GUIDs, the type and unique attributes do."""
    by_guid = AtlasObjectId(guid="g", type_name="a")
    unique = {"qualifiedName": "q"}

    assert by_guid == AtlasObjectId(guid="g", type_name="b")
    assert by_guid != AtlasObjectId(type_name="a")
    assert AtlasObjectId(guid="", type_name="a", unique_attributes=unique) == AtlasObjectId(
        type_name="a", unique_attributes=unique
    )
    assert AtlasObjectId(type_name="a") != AtlasObjectId(type_name="b")
    assert by_guid == by_guid  # noqa: PLR0124 - the identity shortcut
    assert by_guid != AtlasRelatedObjectId(guid="g")
    assert by_guid != "g"
