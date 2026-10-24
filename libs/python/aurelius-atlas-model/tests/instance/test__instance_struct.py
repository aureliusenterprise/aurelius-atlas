"""``AtlasStruct`` (ENT-01 to ENT-03), read from ``org.apache.atlas.model.instance.AtlasStruct`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.instance import AtlasStruct


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-01", "ENT-02"])
def test__attribute_values_are_kept_as_read_null_included() -> None:
    """Nested objects, arrays and null values stay in the map and are written; unknown fields are ignored."""
    body = {"typeName": "t", "attributes": {"a": None, "b": [1, "x"], "c": {"d": None}}, "unknown": 1}

    struct = AtlasStruct.model_validate(body)

    assert struct.to_json() == {"typeName": "t", "attributes": {"a": None, "b": [1, "x"], "c": {"d": None}}}


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-02"])
def test__missing_attributes_stay_null_and_are_not_written() -> None:
    """``AtlasStruct()`` leaves the map null; an empty one is written."""
    assert AtlasStruct.model_validate({"typeName": "t"}).to_json() == {"typeName": "t"}
    assert AtlasStruct(attributes={}).to_json() == {"attributes": {}}


@pytest.mark.covers(
    "aurelius_atlas_model.instance.struct.AtlasStruct.has_attribute",
    "aurelius_atlas_model.instance.struct.AtlasStruct.get_attribute",
    "aurelius_atlas_model.instance.struct.AtlasStruct.set_attribute",
    "aurelius_atlas_model.instance.struct.AtlasStruct.remove_attribute",
    rules=["ENT-03"],
)
def test__attributes_are_found_set_and_removed_by_exact_name() -> None:
    """``hasAttribute`` counts a null value; ``setAttribute`` creates the map; names keep their case."""
    struct = AtlasStruct()

    assert (struct.has_attribute("a"), struct.get_attribute("a"), struct.remove_attribute("a")) == (False, None, None)
    struct.set_attribute("a", None)
    struct.set_attribute("B", 2)

    assert struct.has_attribute("a")
    assert not struct.has_attribute("b")
    assert struct.get_attribute("B") == 2
    assert struct.remove_attribute("B") == 2
    assert struct.attributes == {"a": None}


@pytest.mark.covers("aurelius_atlas_model.instance.struct.AtlasStruct.from_map", rules=["VAL-14"])
def test__a_struct_made_from_a_map_takes_its_attributes_or_the_whole_map() -> None:
    """``AtlasStruct(Map)``: ``typeName`` as text; ``attributes`` when that is a map, else every entry."""
    with_attributes = AtlasStruct.from_map({"typeName": 5, "attributes": {"a": 1}, "other": 2})
    without = AtlasStruct.from_map({"typeName": "t", "a": 1})

    assert (with_attributes.type_name, with_attributes.attributes) == ("5", {"a": 1})
    assert (without.type_name, without.attributes) == ("t", {"typeName": "t", "a": 1})
    assert AtlasStruct.from_map({"attributes": "not a map"}).attributes == {"attributes": "not a map"}
