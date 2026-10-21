"""The value contract every type has (VAL-02), read from ``AtlasType`` of Atlas 2.4.0."""

from decimal import Decimal

import pytest
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved, type_name_of
from aurelius_atlas_typesystem.builtin import IntType, StringType

M = "aurelius_atlas_typesystem.atlas_type"


@pytest.mark.covers(
    f"{M}.AtlasType.create_default_value",
    f"{M}.AtlasType.is_valid_value",
    f"{M}.AtlasType.get_normalized_value",
    rules=["VAL-02"],
)
def test__a_type_without_a_value_side_says_so() -> None:
    """Java's abstract methods; the struct and entity types get theirs in 2.1c."""
    bare = AtlasType("t", TypeCategory.STRUCT, None)

    for call in (bare.create_default_value, lambda: bare.is_valid_value(1), lambda: bare.get_normalized_value(1)):
        with pytest.raises(NotImplementedError, match="t has no value side yet"):
            call()


@pytest.mark.covers(
    f"{M}.AtlasType.create_default_value_of",
    f"{M}.AtlasType.create_optional_default_value",
    rules=["VAL-02"],
)
def test__a_default_of_a_value_is_the_normalised_value() -> None:
    """``createDefaultValue(Object)``: the default for null, else ``getNormalizedValue``; optional is the default."""
    int_type = IntType()

    assert (int_type.create_default_value_of(None), int_type.create_default_value_of("7")) == (0, 7)
    assert int_type.create_optional_default_value() == 0
    assert StringType().create_optional_default_value() is None


@pytest.mark.covers(
    f"{M}.AtlasType.validate_value",
    f"{M}.AtlasType.validate_value_for_update",
    f"{M}.AtlasType.is_valid_value_for_update",
    f"{M}.AtlasType.get_normalized_value_for_update",
    rules=["VAL-02"],
)
def test__an_invalid_value_is_reported_with_java_s_text_of_it() -> None:
    """``<name>=<value>: invalid value for type <type>``; the update variants are the plain ones."""
    int_type, messages = IntType(), []

    assert int_type.validate_value(5, "a", messages)
    assert not int_type.validate_value(Decimal("1E+10"), "a", messages)
    assert not int_type.validate_value_for_update({"k": [True, None]}, "b", messages)
    assert messages == [
        "a=1E+10: invalid value for type int",
        "b={k=[true, null]}: invalid value for type int",
    ]
    assert (int_type.is_valid_value_for_update("1"), int_type.get_normalized_value_for_update("1")) == (True, 1)


@pytest.mark.covers(f"{M}.AtlasType.are_equal_values", rules=["VAL-02"])
def test__values_are_equal_when_they_normalise_to_equal_values() -> None:
    """Null only equals null; a value that does not normalise equals nothing."""
    int_type = IntType()

    assert int_type.are_equal_values(None, None, None)
    assert not int_type.are_equal_values(None, 1, None)
    assert not int_type.are_equal_values(1, None, None)
    assert int_type.are_equal_values("1", Decimal("1.9"), None)
    assert not int_type.are_equal_values("x", "x", None)
    assert not int_type.are_equal_values(1, "x", None)


@pytest.mark.covers(f"{M}.resolved", f"{M}.type_name_of", rules=["VAL-02"])
def test__a_resolved_type_and_its_name() -> None:
    """The helpers the containing types use."""
    int_type = IntType()

    assert resolved(int_type) is int_type
    assert type_name_of(int_type) == "int"
