"""``AtlasObjectId`` (ENT-11), read from ``org.apache.atlas.model.instance.AtlasObjectId`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelatedObjectId

OBJECT_ID = "aurelius_atlas_model.instance.object_id.AtlasObjectId"


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
    assert by_guid != AtlasRelatedObjectId(guid="g")
    assert by_guid != "g"


@pytest.mark.covers(
    "aurelius_atlas_model.instance.object_id.AtlasObjectId.from_map",
    "aurelius_atlas_model.instance.object_id.AtlasObjectId.read_map",
    rules=["VAL-14"],
)
def test__an_object_id_made_from_a_map_reads_three_keys() -> None:
    """``AtlasObjectId(Map)``: ``guid`` and ``typeName`` as text, ``uniqueAttributes`` only when it is a map."""
    read = AtlasObjectId.from_map({"guid": 5, "typeName": "t", "uniqueAttributes": {"q": "n"}, "other": 1})

    assert (read.guid, read.type_name, read.unique_attributes) == ("5", "t", {"q": "n"})
    assert AtlasObjectId.from_map({"uniqueAttributes": ["q"]}).to_json() == {}


@pytest.mark.covers(f"{OBJECT_ID}.java_string", "aurelius_atlas_model.errors.java_string", rules=["EWR-05"])
def test__an_object_id_is_written_as_java_writes_it() -> None:
    """``AtlasObjectId.toString``: ``null`` for no GUID, unique attributes as ``name:value``."""
    by_values = AtlasObjectId(type_name="t", unique_attributes={"qualifiedName": "x", "n": 1})

    assert java_string(by_values) == "AtlasObjectId{guid='null', typeName='t', uniqueAttributes={qualifiedName:x, n:1}}"
    assert java_string(AtlasObjectId(guid="g")) == "AtlasObjectId{guid='g', typeName='null', uniqueAttributes={}}"
