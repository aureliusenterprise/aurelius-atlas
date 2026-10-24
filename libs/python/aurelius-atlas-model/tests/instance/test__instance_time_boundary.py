"""``TimeBoundary`` (ENT-13), read from ``org.apache.atlas.model.TimeBoundary`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.instance import TimeBoundary
from aurelius_atlas_model.instance.time_boundary import TIME_FORMAT


@pytest.mark.covers(rules=["ENT-13"])
def test__a_time_boundary_keeps_its_times_as_strings() -> None:
    """``startTime``, ``endTime`` and ``timeZone`` are strings; a missing one is not written."""
    body = {"startTime": "2026/01/01 00:00:00", "timeZone": "UTC"}

    assert TimeBoundary.model_validate(body).to_json() == body
    assert TIME_FORMAT == "yyyy/MM/dd HH:mm:ss"
