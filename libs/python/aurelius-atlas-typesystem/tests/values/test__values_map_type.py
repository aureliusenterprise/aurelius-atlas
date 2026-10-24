"""``map<K,V>`` (VAL-13, VAL-15), read from ``AtlasMapType`` and ``TestAtlasMapType`` of Atlas 2.4.0."""

from decimal import Decimal

import pytest
from aurelius_atlas_typesystem.builtin import DoubleType, IntType, StringType
from aurelius_atlas_typesystem.map_type import MapType

M = "aurelius_atlas_typesystem.map_type.MapType"


def map_of(key: IntType | StringType, value: IntType | StringType | DoubleType) -> MapType:
    """A map type over resolved key and value types."""
    return MapType(str(key.type_name), str(value.type_name), key_type=key, value_type=value)


TEN = range(10)
VALID = [
    None,
    {},
    {str(i): i for i in TEN},
    {str(i): float(i) for i in TEN},
    {str(i): str(i) for i in TEN},
    {i: i for i in TEN},
]
INVALID = [{"xyz": "123"}, {"123": "xyz"}, [1], "{}"]


@pytest.mark.covers(
    f"{M}.create_default_value",
    f"{M}.is_valid_value",
    f"{M}.is_valid_value_for_update",
    f"{M}.get_normalized_value",
    rules=["VAL-13", "VAL-15"],
)
def test__maps_of_valid_keys_and_values_are_valid() -> None:
    """``TestAtlasMapType``: an invalid key or value makes the map invalid; the default has one entry."""
    ints = map_of(IntType(), IntType())

    assert ints.create_default_value() == {0: 0}
    assert all(ints.is_valid_value(value) for value in VALID)
    assert all(ints.is_valid_value_for_update(value) for value in VALID)
    assert not any(ints.is_valid_value(value) for value in INVALID)
    assert ints.get_normalized_value({"1": "2", "3": None}) == {1: 2, 3: None}
    assert ints.get_normalized_value('{"1": 2.5}') == {1: 2}
    assert [ints.get_normalized_value(value) for value in ({"x": 1}, {"1": "x"}, "[1]", "x", 5, None)] == [None] * 6


@pytest.mark.covers(f"{M}.get_normalized_value_for_update", rules=["VAL-13"])
def test__a_string_map_type_keeps_java_s_text_of_keys() -> None:
    """Keys are normalised by the key type: ``map<string,double>`` of ``{1: "2"}`` is ``{"1": 2.0}``."""
    assert map_of(StringType(), DoubleType()).get_normalized_value_for_update({1: "2"}) == {"1": 2.0}
    assert map_of(StringType(), IntType()).create_default_value() == {"": 0}


@pytest.mark.covers(f"{M}.validate_value", f"{M}.validate_value_for_update", rules=["VAL-13"])
def test__invalid_keys_and_values_are_reported_each() -> None:
    """``<name>.<key>: invalid key for type <type>``; values as ``<name>.<key>``; a value that is no map."""
    ints, messages = map_of(IntType(), IntType()), []

    assert ints.validate_value(None, "m", messages)
    assert not ints.validate_value({"x": 1, "2": "y", "3": 4}, "m", messages)
    assert not ints.validate_value_for_update([1], "n", messages)
    assert ints.validate_value_for_update({1: 1}, "o", messages)
    assert messages == [
        "m.x: invalid key for type map<int,int>",
        "m.2=y: invalid value for type int",
        "n=[1]: invalid value for type map<int,int>",
    ]


@pytest.mark.covers(f"{M}.are_equal_values", rules=["VAL-13"])
def test__null_equals_an_empty_map_and_maps_compare_by_key() -> None:
    """``isEmptyMapValue`` for a null side; otherwise the same size and equal values by key."""
    ints = map_of(StringType(), IntType())

    assert ints.are_equal_values(None, None, None)
    assert ints.are_equal_values(None, {}, None)
    assert ints.are_equal_values("{}", None, None)
    assert ints.are_equal_values(None, "not json", None)
    assert not ints.are_equal_values(None, {"a": 1}, None)
    assert not ints.are_equal_values(None, 5, None)
    assert ints.are_equal_values({"a": 1}, '{"a": "1"}', None)
    assert not ints.are_equal_values({"a": 1}, {"a": 2}, None)
    assert not ints.are_equal_values({"a": 1}, {"a": 1, "b": 2}, None)
    assert not ints.are_equal_values({"a": 1}, Decimal(1), None)
