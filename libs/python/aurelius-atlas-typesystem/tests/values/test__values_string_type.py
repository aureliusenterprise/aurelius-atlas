"""``string`` (VAL-09, VAL-15), read from ``TestAtlasStringType`` of Atlas 2.4.0."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from aurelius_atlas_typesystem.builtin import StringType

M = "aurelius_atlas_typesystem.builtin.string_type.StringType"


@pytest.mark.covers(
    f"{M}.create_default_value",
    f"{M}.create_optional_default_value",
    f"{M}.is_valid_value",
    f"{M}.get_normalized_value",
    rules=["VAL-09", "VAL-15"],
)
def test__every_value_is_valid_and_normalises_to_java_s_text() -> None:
    """``value.toString()``: ``Float.valueOf(1)`` is ``1.0``, ``BigDecimal.valueOf(1)`` is ``1``."""
    strings = StringType()
    values = [1, 1.0, Decimal(1), Decimal("1E+3"), "12ab", "", True, None, {"a": [1, None]}, 1e7]
    texts = ["1", "1.0", "1", "1E+3", "12ab", "", "true", None, "{a=[1, null]}", "1.0E7"]

    assert (strings.create_default_value(), strings.create_optional_default_value()) == ("", None)
    assert all(strings.is_valid_value(value) for value in values)
    assert [strings.get_normalized_value(value) for value in values] == texts
    assert strings.get_normalized_value(datetime(1970, 1, 1, tzinfo=UTC)) == "Thu Jan 01 00:00:00 UTC 1970"
