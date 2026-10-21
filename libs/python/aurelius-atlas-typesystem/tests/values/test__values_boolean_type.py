"""``boolean`` (VAL-03, VAL-15), read from ``TestAtlasBooleanType`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_typesystem.builtin import BooleanType

M = "aurelius_atlas_typesystem.builtin.boolean_type.BooleanType"
VALID = [None, True, False, "true", "false", "TRUE", "FALSE", "tRue", "FaLse"]
INVALID = [1, 0.5, 123456789, "abcd", "101010"]


@pytest.mark.covers(
    f"{M}.create_default_value", f"{M}.is_valid_value", f"{M}.get_normalized_value", rules=["VAL-03", "VAL-15"]
)
def test__booleans_and_their_text_are_valid_numbers_are_not() -> None:
    """``testBooleanTypeDefaultValue``, ``…IsValidValue``, ``…GetNormalizedValue``."""
    boolean = BooleanType()

    assert boolean.create_default_value() is False
    assert all(boolean.is_valid_value(value) for value in VALID)
    assert not any(boolean.is_valid_value(value) for value in INVALID)
    assert [boolean.get_normalized_value(value) for value in VALID] == [
        None,
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
    ]
    assert all(boolean.get_normalized_value(value) is None for value in INVALID)
