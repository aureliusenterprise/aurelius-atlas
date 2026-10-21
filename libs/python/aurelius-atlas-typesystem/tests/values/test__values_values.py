"""What arrays and maps do with the values they hold (VAL-12, VAL-13).

Read from ``AtlasType.fromJson`` and Java's ``equals`` of the values a body holds (DD-040).
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelatedObjectId
from aurelius_atlas_typesystem.values import (
    java_class_name,
    java_distinct,
    java_equals,
    parse_json,
    relationship_type_of,
)

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


@pytest.mark.covers(f"{M}.relationship_type_of", rules=["EVL-08"])
def test__a_value_s_relationship_type_is_found_where_atlas_looks() -> None:
    """``AtlasEntityUtil.getRelationshipType``: a related object id, a map's key, else the first one found inside."""
    related = AtlasRelatedObjectId(guid="g", relationship_type="r1")

    assert relationship_type_of(related) == "r1"
    assert relationship_type_of({"relationshipType": 5, "x": related}) == "5"
    assert relationship_type_of({"relationshipType": None, "x": related}) is None
    assert relationship_type_of({"a": {"guid": "g"}, "b": related}) == "r1"
    assert relationship_type_of([{"guid": "g"}, {"relationshipType": "r2"}, related]) == "r2"
    assert relationship_type_of(AtlasObjectId(guid="g")) is None
    assert relationship_type_of("r") is None


@pytest.mark.covers(f"{M}.java_class_name", rules=["EVL-08"])
@pytest.mark.parametrize(
    ("value", "name"),
    [
        (True, "java.lang.Boolean"),
        (1, "java.lang.Integer"),
        (2**40, "java.lang.Long"),
        (2**70, "java.math.BigInteger"),
        (Decimal("1.5"), "java.math.BigDecimal"),
        (1.5, "java.lang.Double"),
        ("x", "java.lang.String"),
        ([1], "java.util.ArrayList"),
        ({"a": 1}, "java.util.LinkedHashMap"),
        (set(), "java.util.HashSet"),
        ((), "[Ljava.lang.Object;"),
        (datetime(1970, 1, 1, tzinfo=UTC), "java.util.Date"),
        (AtlasObjectId(), "org.apache.atlas.model.instance.AtlasObjectId"),
        (object(), "object"),
    ],
)
def test__a_value_s_java_class_is_what_jackson_would_have_made(value: object, name: str) -> None:
    """``obj.getClass().getName()`` of a body's values (DD-040)."""
    assert java_class_name(value) == name
