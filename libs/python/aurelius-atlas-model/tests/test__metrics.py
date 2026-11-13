"""``AtlasMetrics`` (MET-01), ``AtlasMetricsStat`` and ``AtlasMetricsMapToChart`` (MHS-01), as Apache Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.metrics import (
    AtlasMetrics,
    AtlasMetricsCharts,
    AtlasMetricsMapToChart,
    AtlasMetricsStat,
    new_guid,
)


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


@pytest.mark.covers("aurelius_atlas_model.metrics.AtlasMetricsStat.of", rules=["MHS-01", "MHS-03"])
@pytest.mark.covers("aurelius_atlas_model.metrics.new_guid", rules=["MHS-03"])
def test__a_metrics_stat_is_made_of_the_metrics_of_a_time() -> None:
    """Its id of the collection time and namespace; type data only for type names; a new negative GUID each."""
    metrics = AtlasMetrics.model_validate(
        {"data": {"general": {"collectionTime": 42}, "entity": {"entityActive": {"t": 2}, "entityShell": {}}}}
    )
    stat = AtlasMetricsStat.of(metrics, 1000, "cl1", ["t"])
    plain = AtlasMetricsStat.of(metrics, 1000, "cl1")
    assert stat.to_json() == {
        "guid": stat.guid,
        "metricsId": "atlas_metrics_42@cl1",
        "collectionTime": 42,
        "timeToLiveMillis": 1000,
        "typeData": {"t": {"Active": 2, "Deleted": 0, "Shell": 0}},
        "metrics": metrics.to_json(),
    }
    assert plain.type_data is None
    assert stat.guid.startswith("-")
    assert stat.guid != plain.guid != new_guid()


def test__a_chart_series_is_a_key_and_its_pairs() -> None:
    """``AtlasMetricsMapToChart``: the state and its ``[time, count]`` pairs."""
    chart = AtlasMetricsMapToChart(key="Active", values=[[1, 2]])
    assert chart.to_json() == {"key": "Active", "values": [[1, 2]]}


@pytest.mark.covers(rules=["MHS-04"])
def test__the_charts_answer_series_per_type_name() -> None:
    """``metricsstats/charts``: Java's ``Map<String, List<AtlasMetricsMapToChart>>``, dumped as the wire map."""
    charts = AtlasMetricsCharts.model_validate(
        {"DataSet": [{"key": "Active", "values": [[1, 2]]}, {"key": "Deleted", "values": []}]}
    )

    assert charts.model_dump(mode="python", by_alias=True, exclude_none=True) == {
        "DataSet": [{"key": "Active", "values": [[1, 2]]}, {"key": "Deleted", "values": []}]
    }
