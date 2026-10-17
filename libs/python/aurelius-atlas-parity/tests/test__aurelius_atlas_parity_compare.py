from typing import Any

import pytest
from aurelius_atlas_parity.compare import Difference, Marker, apply_deviation, compare, mask_volatile
from aurelius_atlas_parity.path import parse_path


@pytest.mark.covers("aurelius_atlas_parity.compare.compare", rules=["SCN-09"])
@pytest.mark.parametrize(
    "value",
    [{"a": [1, {"b": None}], "c": "x"}, [], {}, 0, 1.5, "", None, True],
)
def test__compare_finds_nothing_between_equal_values(value: Any) -> None:  # noqa: ANN401 - any JSON value
    """Equal JSON values have no differences."""
    assert compare(value, value) == []


@pytest.mark.covers("aurelius_atlas_parity.compare.compare", rules=["SCN-09"])
@pytest.mark.parametrize(
    ("expected", "actual", "differences"),
    [
        ({"a": 1}, {"a": 2}, [Difference(("a",), 1, 2)]),
        ({"a": 1}, {}, [Difference(("a",), 1, Marker.ABSENT)]),
        ({}, {"a": None}, [Difference(("a",), Marker.ABSENT, None)]),
        ({"a": None}, {}, [Difference(("a",), None, Marker.ABSENT)]),
        ([1, 2], [2, 1], [Difference((0,), 1, 2), Difference((1,), 2, 1)]),
        ([1], [1, 2], [Difference((1,), Marker.ABSENT, 2)]),
        ([1, 2], [1], [Difference((1,), 2, Marker.ABSENT)]),
        (True, 1, [Difference(location=(), expected=True, actual=1)]),
        (0, False, [Difference(location=(), expected=0, actual=False)]),
        ("1", 1, [Difference((), "1", 1)]),
        ({"a": [1]}, {"a": {"0": 1}}, [Difference(("a",), [1], {"0": 1})]),
    ],
)
def test__compare_is_exact(expected: Any, actual: Any, differences: list[Difference]) -> None:  # noqa: ANN401
    """Missing and extra keys, null against absent, order, length and JSON types all count."""
    assert compare(expected, actual) == differences


@pytest.mark.covers("aurelius_atlas_parity.compare.compare", rules=["SCN-09"])
def test__compare_treats_equal_numbers_as_equal() -> None:
    """``1`` and ``1.0`` are the same JSON number."""
    assert compare({"version": 1}, {"version": 1.0}) == []


@pytest.mark.covers("aurelius_atlas_parity.compare.compare", rules=["SCN-11"])
def test__compare_reports_every_difference_with_its_path() -> None:
    """All differences come back, each printable with its path and both values."""
    differences = compare({"a": 1, "b": [True]}, {"a": 2, "b": [False], "c": "x"})

    assert [str(difference) for difference in differences] == [
        "$.a: expected 1, got 2",
        "$.b[0]: expected true, got false",
        '$.c: expected (absent), got "x"',
    ]


@pytest.mark.covers("aurelius_atlas_parity.compare.mask_volatile", rules=["SCN-10"])
def test__mask_volatile_hides_values_but_keeps_presence() -> None:
    """A volatile value is not compared; a volatile field that is missing still differs."""
    paths = [parse_path("$.guid"), parse_path("$.items[*].time")]
    expected = {"guid": "x", "items": [{"time": 1}, {"time": 2}]}

    same = mask_volatile({"guid": "y", "items": [{"time": 7}, {"time": 8}]}, paths)
    missing = mask_volatile({"items": [{"time": 7}, {}]}, paths)

    assert compare(mask_volatile(expected, paths), same) == []
    assert compare(mask_volatile(expected, paths), missing) == [
        Difference(("guid",), Marker.VOLATILE, Marker.ABSENT),
        Difference(("items", 1, "time"), Marker.VOLATILE, Marker.ABSENT),
    ]
    assert expected == {"guid": "x", "items": [{"time": 1}, {"time": 2}]}


@pytest.mark.covers("aurelius_atlas_parity.compare.mask_volatile", rules=["SCN-10"])
def test__mask_volatile_at_the_root_masks_the_whole_body() -> None:
    """``$`` as a volatile path ignores the body's value."""
    assert mask_volatile({"a": 1}, [parse_path("$")]) is Marker.VOLATILE


@pytest.mark.covers("aurelius_atlas_parity.compare.apply_deviation", rules=["SCN-12"])
@pytest.mark.parametrize(
    ("path", "change", "result"),
    [
        ("$.name", {"value": "y"}, {"name": "y", "list": [1, 2]}),
        ("$.extra", {"value": {"k": 1}}, {"name": "x", "list": [1, 2], "extra": {"k": 1}}),
        ("$.name", {"absent": True}, {"list": [1, 2]}),
        ("$.list[1]", {"value": 9}, {"name": "x", "list": [1, 9]}),
        ("$.list[0]", {"absent": True}, {"name": "x", "list": [2]}),
        ("$.list[*]", {"absent": True}, {"name": "x", "list": []}),
        ("$.list[*]", {"value": 0}, {"name": "x", "list": [0, 0]}),
        ("$[*]", {"value": None}, {"name": None, "list": None}),
        ("$", {"value": "replaced"}, "replaced"),
    ],
)
def test__apply_deviation_changes_the_expectation(path: str, change: dict[str, Any], result: Any) -> None:  # noqa: ANN401
    """A deviation sets, adds or removes values in a copy of the expectation."""
    expected = {"name": "x", "list": [1, 2]}

    assert apply_deviation(expected, id="DV-01", path=parse_path(path), **change) == result
    assert expected == {"name": "x", "list": [1, 2]}


@pytest.mark.covers("aurelius_atlas_parity.compare.apply_deviation", rules=["SCN-12"])
@pytest.mark.parametrize(
    ("path", "change"),
    [
        ("$.missing", {"absent": True}),
        ("$.list[5]", {"value": 1}),
        ("$.nowhere.name", {"value": 1}),
        ("$.list.name", {"value": 1}),
        ("$.name[0]", {"value": 1}),
        ("$", {"absent": True}),
    ],
)
def test__apply_deviation_refuses_a_path_that_matches_nothing(path: str, change: dict[str, Any]) -> None:
    """A deviation that changes nothing is a mistake in the scenario, so it fails, naming the deviation."""
    parsed = parse_path(path)

    with pytest.raises(ValueError, match=r"deviation DV-07 at .* matches nothing"):
        apply_deviation({"name": "x", "list": [1, 2]}, id="DV-07", path=parsed, **change)
