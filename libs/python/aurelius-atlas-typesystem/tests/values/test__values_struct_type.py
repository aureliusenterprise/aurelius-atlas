"""``AtlasStructType``'s value side (EVL-01 to EVL-06, EVL-11).

Read from ``AtlasStructType``, ``AtlasTypeUtil`` and ``TestAtlasStructType`` of Atlas 2.4.0, on ``ModelTestUtil``'s
struct.
"""

from typing import Any

import pytest
from aurelius_atlas_model.instance import AtlasEntity, AtlasStruct
from aurelius_atlas_model.typedef import AtlasAttributeDef, AtlasStructDef, AtlasTypesDef, Cardinality
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.struct_type import StructType, relationship_attributes_of, struct_attributes
from aurelius_atlas_typesystem.testing.model_test_util import STRUCT_DEF, model_registry

M = "aurelius_atlas_typesystem.struct_type"
S = f"{M}.StructType"
COUNTED = (
    AtlasAttributeDef(
        name="multiValMinMax",
        type_name="array<int>",
        cardinality=Cardinality.LIST,
        values_min_count=2,
        values_max_count=5,
    ),
    AtlasAttributeDef(name="multiValMin", type_name="array<int>", cardinality=Cardinality.LIST, values_min_count=2),
    AtlasAttributeDef(name="multiValMax", type_name="array<int>", cardinality=Cardinality.SET, values_max_count=5),
)


@pytest.fixture(scope="module")
def model_struct() -> StructType:
    """``TestAtlasStructType``'s struct: ``ModelTestUtil``'s, plus three arrays with counts."""
    found = model_registry(*COUNTED).struct_type(STRUCT_DEF)
    assert found is not None
    return found


def small_struct(*attribute_defs: AtlasAttributeDef, name: str = "s") -> StructType:
    """A struct type of the given attributes."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(AtlasTypesDef(struct_defs=[AtlasStructDef(name=name, attribute_defs=list(attribute_defs))]))
    found = registry.struct_type(name)
    assert found is not None
    return found


def invalid_values(struct_type: StructType) -> list[object]:
    """``TestAtlasStructType``'s invalid values: bad attribute values, wrong counts, missing attributes, no struct."""
    changes: list[tuple[str, object]] = [
        ("attr-int", "xyz"),
        ("attr-date", "xyz"),
        ("attr-biginteger", "xyz"),
        ("multiValMinMax", [1]),
        ("multiValMinMax", [1, 2, 3, 4, 5, 6]),
        ("multiValMin", []),
        ("multiValMax", list(range(1, 11))),
    ]
    values: list[object] = []
    for name, value in changes:
        struct = struct_type.create_default_value()
        struct.set_attribute(name, value)
        values.append(struct)
    return [*values, AtlasStruct(), {}, 1, set(), [], ()]


@pytest.mark.covers(
    f"{S}.create_default_value",
    f"{S}.is_valid_value",
    f"{S}.get_normalized_value",
    f"{S}.validate_value",
    f"{S}.populate_default_values",
    rules=["EVL-01", "EVL-02", "EVL-04", "EVL-05", "EVL-11"],
)
def test__atlas_s_struct_type_test_holds(model_struct: StructType) -> None:
    """``testStructTypeDefaultValue``, ``…IsValidValue``, ``…GetNormalizedValue``, ``…ValidateValue``."""
    default = model_struct.create_default_value()
    valid: list[object] = [None, model_struct.create_default_value(), model_struct.create_default_value().attributes]

    assert default.type_name == STRUCT_DEF
    for value in valid:
        messages: list[str] = []
        assert model_struct.is_valid_value(value), value
        assert model_struct.validate_value(value, "testObj", messages), messages
        assert messages == []
        assert (model_struct.get_normalized_value(value) is None) == (value is None)
    for value in invalid_values(model_struct):
        messages = []
        assert not model_struct.is_valid_value(value), value
        assert model_struct.get_normalized_value(value) is None, value
        assert not model_struct.validate_value(value, "testObj", messages), value
        assert messages, value


@pytest.mark.covers(f"{M}.struct_attributes", f"{M}.relationship_attributes_of", rules=["EVL-01", "EVL-02"])
def test__a_map_s_attributes_are_its_attributes_map_when_it_names_a_type() -> None:
    """``AtlasTypeUtil.toStructAttributes`` and ``toRelationshipAttributes`` need a ``typeName`` key."""
    full = {"typeName": "t", "attributes": {"a": 1}, "relationshipAttributes": {"r": 2}}

    assert (struct_attributes(full), relationship_attributes_of(full)) == ({"a": 1}, {"r": 2})
    assert struct_attributes({"attributes": {"a": 1}}) == {"attributes": {"a": 1}}
    assert struct_attributes({"typeName": "t", "attributes": 5}) == {"typeName": "t", "attributes": 5}
    assert relationship_attributes_of({"relationshipAttributes": {}}) is None
    assert relationship_attributes_of({"typeName": "t", "relationshipAttributes": [1]}) is None


@pytest.mark.covers(f"{S}.is_valid_value", f"{S}.validate_value", rules=["EVL-01", "EVL-02"])
def test__a_mandatory_attribute_may_be_given_another_way() -> None:
    """An entity's relationship attribute or being incomplete, or a map's relationship attributes, stand in."""
    struct_type = small_struct(AtlasAttributeDef(name="db", type_name="string"))
    by_relationship = AtlasEntity(type_name="s", attributes={})
    by_relationship.set_relationship_attribute("db", {"guid": "g"})
    map_with = {"typeName": "s", "attributes": {}, "relationshipAttributes": {"db": None}}
    messages: list[str] = []

    assert not struct_type.is_valid_value(by_relationship)
    assert struct_type.validate_value(by_relationship, "e", messages)
    assert struct_type.validate_value(AtlasEntity(type_name="s", is_incomplete=True), "e", messages)
    assert struct_type.validate_value(map_with, "m", messages)
    assert messages == []
    assert not struct_type.validate_value(AtlasEntity(type_name="s"), "e", messages)
    assert not struct_type.validate_value(AtlasStruct(type_name="s"), "s", messages)
    assert not struct_type.validate_value({"typeName": "s", "attributes": {}}, "m", messages)
    assert not struct_type.validate_value("x", "v", messages)
    assert messages == [
        "e.db: mandatory attribute value missing in type s",
        "s.db: mandatory attribute value missing in type s",
        "m.db: mandatory attribute value missing in type s",
        "v=x: invalid value for type s",
    ]


@pytest.mark.covers(
    f"{S}.is_valid_value_for_update",
    f"{S}.validate_value_for_update",
    f"{S}.get_normalized_value_for_update",
    f"{S}.normalize_attribute_values_for_update",
    rules=["EVL-03"],
)
def test__an_update_checks_and_normalises_only_what_it_has() -> None:
    """Missing mandatory attributes are no error; attributes without a definition are skipped."""
    struct_type = small_struct(
        AtlasAttributeDef(name="n", type_name="int"), AtlasAttributeDef(name="o", type_name="int", is_optional=True)
    )
    update = AtlasStruct(type_name="s", attributes={"n": "7", "x": "ignored", "o": None})
    messages: list[str] = []

    assert struct_type.is_valid_value_for_update(None)
    assert struct_type.is_valid_value_for_update(AtlasStruct(type_name="s"))
    assert struct_type.is_valid_value_for_update({"N": "7"})
    assert not struct_type.is_valid_value_for_update({"n": "x"})
    assert not struct_type.is_valid_value_for_update(5)
    assert struct_type.validate_value_for_update(None, "u", messages)
    assert not struct_type.validate_value_for_update(
        {"typeName": "s", "attributes": {"n": "x", "o": None}}, "u", messages
    )
    assert not struct_type.validate_value_for_update([], "w", messages)
    assert messages == ["u.n=x: invalid value for type int", "w=[]: invalid value for type s"]
    assert struct_type.get_normalized_value_for_update(update) is update
    assert update.attributes == {"n": 7, "x": "ignored", "o": None}
    assert struct_type.get_normalized_value_for_update({"n": "y"}) is None
    assert struct_type.get_normalized_value_for_update(None) is None
    as_map: dict[str, Any] = {"n": "8"}
    assert struct_type.get_normalized_value_for_update(as_map) == {"n": 8}
    struct_type.normalize_attribute_values_for_update(AtlasStruct(type_name="s"))


@pytest.mark.covers(
    f"{S}.normalize_attribute_values",
    f"{S}.get_normalized_value",
    f"{S}.create_default_value_of",
    f"{S}.populate_default_values",
    rules=["EVL-04", "EVL-05"],
)
def test__normalising_fills_mandatory_attributes_with_their_defaults() -> None:
    """A null mandatory attribute gets the type's default; a missing one the attribute's ``defaultValue``.

    ``getNormalizedValue`` checks first, so only a valid struct is normalised that way.
    """
    struct_type = small_struct(
        AtlasAttributeDef(name="n", type_name="int", default_value="5"),
        AtlasAttributeDef(name="m", type_name="int"),
        AtlasAttributeDef(name="o", type_name="int", is_optional=True),
    )
    struct = AtlasStruct(type_name="s", attributes={"m": None, "o": "3"})
    as_map: dict[str, Any] = {"typeName": "s", "attributes": {"n": "x"}}

    valid = AtlasStruct(type_name="s", attributes={"n": "1", "m": "2"})

    assert struct_type.get_normalized_value(struct) is None
    struct_type.normalize_attribute_values(struct)
    assert struct.attributes == {"m": 0, "o": 3, "n": 5}
    assert struct_type.get_normalized_value(valid) is valid
    assert valid.attributes == {"n": 1, "m": 2}
    struct_type.normalize_attribute_values(as_map)
    assert as_map == {"typeName": "s", "attributes": {"n": "x"}, "n": 5, "m": 0}
    struct_type.normalize_attribute_values(empty := AtlasStruct(type_name="s"))
    assert empty.attributes == {"n": 5, "m": 0}
    replaced = AtlasStruct(type_name="s", attributes={"n": 9, "o": 1})
    struct_type.populate_default_values(replaced)
    assert replaced.attributes == {"n": 5, "o": 1, "m": 0}
    assert struct_type.create_default_value_of(AtlasStruct(attributes={"n": 1})).attributes == {"n": 5, "m": 0}


@pytest.mark.covers(f"{S}.are_equal_values", rules=["EVL-06"])
def test__structs_are_equal_by_type_name_ignoring_case_and_every_attribute() -> None:
    """``areEqualValues`` reads maps by ``AtlasStruct(Map)``; a JSON string fails as Java's cast does."""
    struct_type = small_struct(AtlasAttributeDef(name="n", type_name="int"))
    struct = AtlasStruct(type_name="s", attributes={"n": 1})

    assert struct_type.are_equal_values(None, None, None)
    assert not struct_type.are_equal_values(struct, None, None)
    assert struct_type.are_equal_values(struct, {"typeName": "S", "attributes": {"n": "1"}}, None)
    assert not struct_type.are_equal_values(struct, {"typeName": "s", "attributes": {"n": 2}}, None)
    assert not struct_type.are_equal_values(struct, {"typeName": "other", "attributes": {"n": 1}}, None)
    assert not struct_type.are_equal_values(struct, {"attributes": {"n": 1}}, None)
    assert struct_type.are_equal_values({"n": 1}, {"n": 1}, None)
    assert not struct_type.are_equal_values(struct, 5, None)
    assert not struct_type.are_equal_values(struct, "not json", None)
    with pytest.raises(TypeError, match="no struct value"):
        struct_type.are_equal_values(struct, '{"typeName": "s"}', None)
