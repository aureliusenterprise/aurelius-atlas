"""What arrays and maps do with the values they hold (VAL-12, VAL-13).

Read from ``AtlasType.fromJson`` and Java's ``equals`` of the values a body holds (DD-040).
"""

from decimal import Decimal

import pytest
from aurelius_atlas_typesystem.values import java_distinct, java_equals, parse_json

M = "aurelius_atlas_typesystem.values"


@pytest.mark.covers(f"{M}.parse_json", rules=["VAL-12", "VAL-13"])
def test__a_string_is_parsed_with_atlas_s_mapper_or_is_nothing() -> None:
    """``AtlasJson.fromJson`` reads floats as decimals and answers null for what is not JSON."""
    assert parse_json('[1.10, {"a": null}]') == [Decimal("1.10"), {"a": None}]
    assert parse_json("not json") is None


@pytest.mark.covers(f"{M}.java_equals", rules=["VAL-12"])
@pytest.mark.parametrize(
    ("left", "right", "equal"),
    [
        (1, 1, True),
        (True, 1, False),
        (True, True, True),
        (1, 1.0, False),
        (Decimal("1.0"), Decimal("1.00"), False),
        (Decimal("1.0"), Decimal("1.0"), True),
        ({"a": [1]}, {"a": [1]}, True),
        ({"a": 1}, {"b": 1}, False),
        ([1, 2], [1], False),
        ("a", "a", True),
    ],
)
def test__values_are_equal_as_java_s_equals_says(left: object, right: object, *, equal: bool) -> None:
    """Classes must match; a ``BigDecimal`` compares its scale; maps and lists element by element."""
    assert java_equals(left, right) is equal


@pytest.mark.covers(f"{M}.java_distinct", rules=["VAL-12"])
def test__a_hash_set_keeps_each_value_once() -> None:
    """``new HashSet<>(collection)`` by Java's ``equals``: ``1`` and ``true`` are two values."""
    assert java_distinct([1, True, 1, {"a": 1}, {"a": 1}, Decimal("1.0"), Decimal("1.00")]) == [
        1,
        True,
        {"a": 1},
        Decimal("1.0"),
        Decimal("1.00"),
    ]
