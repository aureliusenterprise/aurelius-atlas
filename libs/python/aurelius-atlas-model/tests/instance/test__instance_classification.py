"""``AtlasClassification`` (ENT-13).

Read from ``org.apache.atlas.model.instance.AtlasClassification`` of Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.instance import AtlasClassification, TimeBoundary


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-13"])
def test__a_classification_reads_and_writes_its_fields() -> None:
    """The struct's fields and the classification's; ``propagate`` once."""
    body = {
        "typeName": "PII",
        "attributes": {"level": 1},
        "entityGuid": "g",
        "entityStatus": "DELETED",
        "propagate": True,
        "validityPeriods": [{"startTime": "2026/01/01 00:00:00", "endTime": "2026/12/31 00:00:00"}],
        "removePropagationsOnEntityDelete": False,
    }

    assert AtlasClassification.model_validate(body).to_json() == body


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-13"])
def test__a_classification_without_entity_status_is_active() -> None:
    """The field's initial value ``Status.ACTIVE``; the no-argument constructor keeps it."""
    assert AtlasClassification.model_validate({"typeName": "PII"}).to_json() == {
        "typeName": "PII",
        "entityStatus": "ACTIVE",
    }


@pytest.mark.covers(
    "aurelius_atlas_model.instance.classification.AtlasClassification.add_validity_period", rules=["ENT-13"]
)
def test__validity_periods_are_appended() -> None:
    """``addValityPeriod`` creates the list, then appends."""
    classification = AtlasClassification()

    classification.add_validity_period(TimeBoundary(start_time="a"))
    classification.add_validity_period(TimeBoundary(end_time="b"))

    assert [(p.start_time, p.end_time) for p in classification.validity_periods or []] == [("a", None), (None, "b")]
