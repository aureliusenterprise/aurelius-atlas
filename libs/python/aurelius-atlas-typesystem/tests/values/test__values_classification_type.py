"""``AtlasClassificationType``'s value side and validity periods (EVL-03 to EVL-07, EVL-11).

Read from ``AtlasClassificationType``, ``TestAtlasClassificationType`` and ``TestAtlasClassification`` of Atlas 2.4.0,
on ``ModelTestUtil``'s classification with two super types.
"""

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasClassification, TimeBoundary
from aurelius_atlas_typesystem.classification_type import (
    ClassificationType,
    parse_time_boundary,
    validate_time_boundaries,
)
from aurelius_atlas_typesystem.testing.model_test_util import CLASSIFICATION_DEFS, model_registry

M = "aurelius_atlas_typesystem.classification_type"
C = f"{M}.ClassificationType"
VALID_PERIODS = [
    TimeBoundary(start_time="2018/07/07 04:38:55"),
    TimeBoundary(end_time="2018/07/08 04:38:55"),
    TimeBoundary(start_time="2018/07/07 04:38:55", end_time="2018/07/08 04:38:55"),
    TimeBoundary(start_time="2018/07/07 04:38:55", end_time="2018/07/08 04:38:55", time_zone="America/Los_Angeles"),
    TimeBoundary(end_time="2018/07/08 04:38:55", time_zone="GMT+10:30"),
    TimeBoundary(start_time="2018/07/07 04:38:55", end_time="2018/07/08 04:38:55", time_zone="GMT"),
    TimeBoundary(start_time="2018/07/07 04:38:55", end_time="2019/07/08 04:38:55"),
]
INVALID_PERIODS = [
    TimeBoundary(start_time="2018-07-07 04:38:55"),
    TimeBoundary(end_time="2018-07-08 04:38:55"),
    TimeBoundary(start_time="2018/07/08 04:38:55", end_time="2018/07/07 04:38:55"),
    TimeBoundary(start_time="2018/07/08 04:38:55", end_time="2018/07/07 04:38:55", time_zone=""),
    TimeBoundary(start_time="2018/07/08 04:38:55", end_time="2018/07/07 04:38:55", time_zone="GMT+10:-30"),
    TimeBoundary(start_time="2018/07/08 04:38:55", end_time="2018/07/07 04:38:55", time_zone="abcd"),
]


@pytest.fixture(scope="module")
def classification_type() -> ClassificationType:
    """``ModelTestUtil.getClassificationDefWithSuperTypes()``."""
    found = model_registry().classification_type(CLASSIFICATION_DEFS[2])
    assert found is not None
    return found


def with_period(classification_type: ClassificationType, period: TimeBoundary) -> AtlasClassification:
    """A default classification with one validity period."""
    classification = classification_type.create_default_value()
    classification.add_validity_period(period)
    return classification


@pytest.mark.covers(
    f"{C}.create_default_value",
    f"{C}.is_valid_value",
    f"{C}.validate_value",
    f"{C}.populate_default_values",
    f"{C}.normalize_attribute_values",
    rules=["EVL-04", "EVL-05", "EVL-07", "EVL-11"],
)
def test__atlas_s_classification_type_test_holds(classification_type: ClassificationType) -> None:
    """``testClassificationType…``: defaults, attribute values and validity periods."""
    bad_int, bad_date = classification_type.create_default_value(), classification_type.create_default_value()
    bad_int.set_attribute("attr-int", "xyz")
    bad_date.set_attribute("attr-date", "xyz")
    bad_map = dict(classification_type.create_default_value().attributes or {}) | {"attr-biginteger": "xyz"}
    valid = [
        None,
        classification_type.create_default_value(),
        classification_type.create_default_value().attributes,
        *(with_period(classification_type, period) for period in VALID_PERIODS),
    ]
    invalid = [bad_int, bad_date, bad_map, *(with_period(classification_type, p) for p in INVALID_PERIODS)]
    invalid += [AtlasClassification(), {}, 1, set(), [], ()]

    assert classification_type.create_default_value().type_name == CLASSIFICATION_DEFS[2]
    for value in valid:
        messages: list[str] = []
        assert classification_type.is_valid_value(value), value
        assert classification_type.validate_value(value, "testObj", messages), messages
        assert (classification_type.get_normalized_value(value) is None) == (value is None)
    for value in invalid:
        messages = []
        assert not classification_type.is_valid_value(value), value
        assert not classification_type.validate_value(value, "testObj", messages), value
        assert messages, value
        assert classification_type.get_normalized_value(value) is None, value


@pytest.mark.covers(f"{C}.validate_value", f"{M}.validate_time_boundaries", rules=["EVL-07"])
def test__invalid_periods_are_reported_once_with_atlas_s_messages(classification_type: ClassificationType) -> None:
    """``INVALID_TIMEBOUNDRY_*`` messages, each once.

    A map's periods are never read: ``AtlasClassification(Map)`` takes none.
    """
    bad = classification_type.create_default_value()
    for period in (
        TimeBoundary(start_time="2018/07/08 04:38:55", end_time="2018/07/07 04:38:55", time_zone="abcd"),
        TimeBoundary(start_time="x", end_time="y"),
        TimeBoundary(start_time="x"),
        None,
    ):
        bad.validity_periods = [*(bad.validity_periods or []), period]
    messages: list[str] = []

    assert not classification_type.validate_value(bad, "c", messages)
    assert messages == [
        "Invalid timezone abcd",
        "Invalid dateRange: startTime 2018/07/08 04:38:55 must be before endTime 2018/07/07 04:38:55",
        "Invalid startTime x",
        "Invalid endTime y",
    ]
    assert validate_time_boundaries({"validityPeriods": [{"startTime": "x"}]}, None)
    assert validate_time_boundaries(5, None)


@pytest.mark.covers(f"{M}.parse_time_boundary", rules=["EVL-07"])
@pytest.mark.parametrize(
    ("text", "zone", "expected"),
    [
        ("2018/07/07 04:38:55", UTC, datetime(2018, 7, 7, 4, 38, 55, tzinfo=UTC)),
        ("2018/7/7 4:38:55", UTC, datetime(2018, 7, 7, 4, 38, 55, tzinfo=UTC)),
        (" 2018/ 07/07  04:38:55", UTC, datetime(2018, 7, 7, 4, 38, 55, tzinfo=UTC)),
        ("2018/07/07 04:38:55", timezone(timedelta(hours=10, minutes=30)), datetime(2018, 7, 6, 18, 8, 55, tzinfo=UTC)),
        ("2018/02/30 00:00:00", UTC, None),
        ("2018/07/07 24:00:00", UTC, None),
        ("2018/07/07 04:38:55 extra", UTC, None),
        ("2018/07/07T04:38:55", UTC, None),
        ("+2018/07/07 04:38:55", UTC, None),
    ],
)
def test__a_period_s_time_parses_strictly_and_whole(text: str, zone: timezone, expected: datetime | None) -> None:
    """``DateValidator``: a strict ``yyyy/MM/dd HH:mm:ss``; ``SimpleDateFormat`` skips whitespace before a number."""
    assert parse_time_boundary(text, zone) == expected


@pytest.mark.covers(
    f"{C}.is_valid_value_for_update",
    f"{C}.validate_value_for_update",
    f"{C}.normalize_attribute_values_for_update",
    f"{C}.are_equal_values",
    rules=["EVL-03", "EVL-06", "EVL-07"],
)
def test__updates_and_equality_go_through_the_super_types(classification_type: ClassificationType) -> None:
    """Each super type's check runs first; validity periods are checked for update too."""
    update = AtlasClassification(type_name=CLASSIFICATION_DEFS[2], attributes={"attr-int": "7"})
    bad_period = AtlasClassification(type_name=CLASSIFICATION_DEFS[2], validity_periods=[TimeBoundary(start_time="x")])
    messages: list[str] = []

    assert classification_type.is_valid_value_for_update(None)
    assert classification_type.is_valid_value_for_update(update)
    assert not classification_type.is_valid_value_for_update(bad_period)
    assert not classification_type.is_valid_value_for_update({"attr-int": "x"})
    assert classification_type.validate_value_for_update(None, "c", messages)
    assert not classification_type.validate_value_for_update(bad_period, "c", messages)
    assert messages == ["Invalid startTime x"]
    assert classification_type.get_normalized_value_for_update(update) is update
    assert update.attributes == {"attr-int": 7}
    default = classification_type.create_default_value()
    changed = classification_type.create_default_value()
    changed.set_attribute("attr-int", 1)
    assert classification_type.are_equal_values(default, classification_type.create_default_value(), None)
    assert not classification_type.are_equal_values(default, changed, None)


@pytest.mark.covers(f"{C}.normalize_attribute_values", rules=["EVL-11"])
def test__a_default_classification_survives_json_and_normalising(classification_type: ClassificationType) -> None:
    """``TestAtlasClassification.testClassificationSerDe…``: written, read back and normalised, it is equal."""
    for name in CLASSIFICATION_DEFS:
        typed = model_registry().classification_type(name)
        assert typed is not None
        original = typed.create_default_value()
        read = AtlasClassification.model_validate(codec.loads(codec.dumps(original)))
        typed.normalize_attribute_values(read)
        assert read == original
    assert classification_type is not None
    assert parse_time_boundary("2018/07/07 04:38:55", ZoneInfo("Asia/Kolkata")) == datetime(
        2018, 7, 6, 23, 8, 55, tzinfo=UTC
    )
