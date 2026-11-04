"""``AtlasMetrics`` (MET-01), read from Apache Atlas 2.4.0's ``AtlasMetrics``."""

import pytest
from aurelius_atlas_model.metrics import AtlasMetrics


@pytest.mark.covers("aurelius_atlas_model.metrics.AtlasMetrics.add_metric", rules=["MET-01"])
def test__a_metric_adds_its_group() -> None:
    """Metrics without groups have no ``data``; a metric adds its group, or joins it."""
    metrics = AtlasMetrics()
    assert metrics.to_json() == {}
    metrics.add_metric("general", "entityCount", 3)
    metrics.add_metric("general", "typeCount", 4)
    metrics.add_metric("tag", "tagEntities", {})
    assert metrics.to_json() == {"data": {"general": {"entityCount": 3, "typeCount": 4}, "tag": {"tagEntities": {}}}}


@pytest.mark.covers("aurelius_atlas_model.metrics.AtlasMetrics.metric", rules=["MET-01"])
@pytest.mark.covers("aurelius_atlas_model.metrics.AtlasMetrics.numeric_metric", rules=["MET-01"])
def test__a_metric_is_read_by_group_and_name() -> None:
    """A missing group or name reads as None; ``getNumericMetric`` only answers numbers, not flags."""
    metrics = AtlasMetrics.model_validate({"data": {"general": {"entityCount": 3, "upTime": "1 sec", "on": True}}})
    assert metrics.metric("general", "upTime") == "1 sec"
    assert metrics.metric("general", "missing") is None
    assert metrics.metric("missing", "entityCount") is None
    assert metrics.numeric_metric("general", "entityCount") == 3
    assert metrics.numeric_metric("general", "upTime") is None
    assert metrics.numeric_metric("general", "on") is None
