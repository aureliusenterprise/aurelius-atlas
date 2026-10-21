"""Enum types (VAL-11), read from ``AtlasEnumType`` of Atlas 2.4.0."""

from decimal import Decimal

import pytest
from aurelius_atlas_model.typedef import AtlasEnumDef, AtlasEnumElementDef
from aurelius_atlas_typesystem.enum_type import EnumType

M = "aurelius_atlas_typesystem.enum_type.EnumType"


@pytest.mark.covers(f"{M}.create_default_value", f"{M}.is_valid_value", f"{M}.get_normalized_value", rules=["VAL-11"])
def test__a_value_is_an_element_s_value_ignoring_case() -> None:
    """``elementDefs.containsKey(obj.toString().toLowerCase())``; normalised to the element's own value."""
    enum = EnumType(
        AtlasEnumDef(
            name="e",
            default_value="Two",
            element_defs=[AtlasEnumElementDef(value="One", ordinal=1), AtlasEnumElementDef(value="Two", ordinal=2)],
        )
    )
    numbered = EnumType(AtlasEnumDef(name="n", element_defs=[AtlasEnumElementDef(value="1", ordinal=1)]))

    assert (enum.create_default_value(), numbered.create_default_value()) == ("Two", "1")
    assert (enum.is_valid_value(None), enum.is_valid_value("oNe"), enum.is_valid_value("three")) == (True, True, False)
    assert (enum.get_normalized_value("ONE"), enum.get_normalized_value("x"), enum.get_normalized_value(None)) == (
        "One",
        None,
        None,
    )
    assert (numbered.get_normalized_value(1), numbered.get_normalized_value(Decimal("1.0"))) == ("1", None)
