"""``array<T>`` (VAL-12, VAL-15), read from ``AtlasArrayType`` and ``TestAtlasArrayType`` of Atlas 2.4.0."""

from decimal import Decimal

import pytest
from aurelius_atlas_model.typedef import Cardinality
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.builtin import BigDecimalType, IntType, ObjectIdType, StringType

M = "aurelius_atlas_typesystem.array_type.ArrayType"


def array_of(element: object, **counts: object) -> ArrayType:
    """An array type over a resolved element type."""
    return ArrayType(str(element.type_name), element_type=element, **counts)  # type: ignore[attr-defined, arg-type]


INTS = list(range(10))
VALID = [None, (), INTS, set(INTS), (1, 2, 3), [str(i) for i in INTS], {str(i) for i in INTS}, [1.0], [Decimal(1)]]
INVALID = [1, 1.0, Decimal(1), "1", "[1, 2]", {"a": 1}]


@pytest.mark.covers(
    f"{M}.create_default_value",
    f"{M}.is_valid_value",
    f"{M}.is_valid_value_for_update",
    f"{M}.get_normalized_value",
    rules=["VAL-12", "VAL-15"],
)
def test__lists_sets_and_arrays_of_valid_elements_are_valid() -> None:
    """``TestAtlasArrayType``: a collection is valid, a single value or a string is not; one default element."""
    ints = array_of(IntType())

    assert ints.create_default_value() == [0]
    assert array_of(IntType(), min_count=3).create_default_value() == [0, 0, 0]
    assert all(ints.is_valid_value(value) for value in VALID)
    assert all(ints.is_valid_value_for_update(value) for value in VALID)
    assert not any(ints.is_valid_value(value) for value in INVALID)
    assert ints.get_normalized_value([str(i) for i in INTS]) == INTS
    assert ints.get_normalized_value('[1, null, "2"]') == [1, None, 2]
    assert [ints.get_normalized_value(value) for value in ("not json", "{}", None, 1, ["x"])] == [None] * 5


@pytest.mark.covers(f"{M}.get_normalized_value", f"{M}.get_normalized_value_for_update", rules=["VAL-12"])
def test__a_wrong_count_normalises_the_array_to_null() -> None:
    """``isValidElementCount``: within ``minCount`` and ``maxCount``, each when set."""
    counted = array_of(IntType(), min_count=1, max_count=2)

    assert [counted.get_normalized_value(value) for value in ([], [1], [1, 2], [1, 2, 3])] == [None, [1], [1, 2], None]
    assert counted.get_normalized_value_for_update(["1"]) == [1]
    assert not counted.is_valid_value([1, 2, 3])
    assert array_of(BigDecimalType()).get_normalized_value("[1.10]") == [Decimal("1.10")]


@pytest.mark.covers(f"{M}.validate_value", f"{M}.validate_value_for_update", rules=["VAL-12"])
def test__invalid_counts_and_elements_are_reported_each() -> None:
    """The count message, then each element as ``<name>[<i>]``; a value that is no collection is invalid."""
    counted, messages = array_of(IntType(), min_count=1, max_count=2), []

    assert counted.validate_value(None, "a", messages)
    assert not counted.validate_value(["x", 1, "y"], "a", messages)
    assert not counted.validate_value_for_update(5, "b", messages)
    assert counted.validate_value_for_update([1], "c", messages)
    assert messages == [
        "a: incorrect number of values. found=3; expected: minCount=1, maxCount=2",
        "a[0]=x: invalid value for type int",
        "a[2]=y: invalid value for type int",
        "b=5: invalid value for type array<int>",
    ]


@pytest.mark.covers(f"{M}.are_equal_values", rules=["VAL-12"])
def test__lists_compare_in_order_sets_by_content() -> None:
    """``areEqualLists`` element by element; ``areEqualSets`` after Java's de-duplication, in any order."""
    lists = array_of(IntType())
    sets = array_of(StringType(), cardinality=Cardinality.SET)
    references = array_of(ObjectIdType(), cardinality=Cardinality.SET)

    assert lists.are_equal_values([1, 2], ["1", "2"], None)
    assert not lists.are_equal_values([1, 2], [2, 1], None)
    assert not lists.are_equal_values([1], [1, 1], None)
    assert lists.are_equal_values("[1]", [1], None)
    assert sets.are_equal_values(["a", "b", "a"], ["b", "a"], None)
    assert not sets.are_equal_values(["a", "b"], ["a", "c"], None)
    assert not sets.are_equal_values(["a"], ["a", "b"], None)
    assert references.are_equal_values([{"guid": "-1"}], [{"guid": "g"}], {"-1": "g"})
    assert lists.are_equal_values(None, None, None)
    assert not lists.are_equal_values(None, [], None)
    value = [1]
    assert lists.are_equal_values(value, value, None)
