"""``AtlasMetrics``, ``AtlasMetricsStat`` and ``AtlasMetricsMapToChart``: what ``admin/metrics`` answers, grouped
metrics by name (MET-01), and the metrics stored on a schedule (MHS-01).

Ported from Apache Atlas 2.4.0 ``org.apache.atlas.model.metrics``.
"""  # noqa: D205 - one sentence

import itertools
import time
from typing import Any

from pydantic import Field

from aurelius_atlas_model.base import AtlasModel, JavaInt

PREFIX_CONNECTION_STATUS = "ConnectionStatus:"
PREFIX_NOTIFICATION = "Notification:"
PREFIX_SERVER = "Server:"

STAT_NOTIFY_COUNT_CURR_DAY = PREFIX_NOTIFICATION + "currentDay"
STAT_NOTIFY_AVG_TIME_CURR_DAY = PREFIX_NOTIFICATION + "currentDayAvgTime"
STAT_NOTIFY_CREATES_COUNT_CURR_DAY = PREFIX_NOTIFICATION + "currentDayEntityCreates"
STAT_NOTIFY_UPDATES_COUNT_CURR_DAY = PREFIX_NOTIFICATION + "currentDayEntityUpdates"
STAT_NOTIFY_DELETES_COUNT_CURR_DAY = PREFIX_NOTIFICATION + "currentDayEntityDeletes"
STAT_NOTIFY_FAILED_COUNT_CURR_DAY = PREFIX_NOTIFICATION + "currentDayFailed"
STAT_NOTIFY_START_TIME_CURR_DAY = PREFIX_NOTIFICATION + "currentDayStartTime"
STAT_NOTIFY_COUNT_CURR_HOUR = PREFIX_NOTIFICATION + "currentHour"
STAT_NOTIFY_AVG_TIME_CURR_HOUR = PREFIX_NOTIFICATION + "currentHourAvgTime"
STAT_NOTIFY_CREATES_COUNT_CURR_HOUR = PREFIX_NOTIFICATION + "currentHourEntityCreates"
STAT_NOTIFY_UPDATES_COUNT_CURR_HOUR = PREFIX_NOTIFICATION + "currentHourEntityUpdates"
STAT_NOTIFY_DELETES_COUNT_CURR_HOUR = PREFIX_NOTIFICATION + "currentHourEntityDeletes"
STAT_NOTIFY_FAILED_COUNT_CURR_HOUR = PREFIX_NOTIFICATION + "currentHourFailed"
STAT_NOTIFY_START_TIME_CURR_HOUR = PREFIX_NOTIFICATION + "currentHourStartTime"
STAT_NOTIFY_LAST_MESSAGE_PROCESSED_TIME = PREFIX_NOTIFICATION + "lastMessageProcessedTime"
STAT_NOTIFY_TOPIC_DETAILS = PREFIX_NOTIFICATION + "topicDetails"
STAT_NOTIFY_COUNT_PREV_DAY = PREFIX_NOTIFICATION + "previousDay"
STAT_NOTIFY_AVG_TIME_PREV_DAY = PREFIX_NOTIFICATION + "previousDayAvgTime"
STAT_NOTIFY_CREATES_COUNT_PREV_DAY = PREFIX_NOTIFICATION + "previousDayEntityCreates"
STAT_NOTIFY_UPDATES_COUNT_PREV_DAY = PREFIX_NOTIFICATION + "previousDayEntityUpdates"
STAT_NOTIFY_DELETES_COUNT_PREV_DAY = PREFIX_NOTIFICATION + "previousDayEntityDeletes"
STAT_NOTIFY_FAILED_COUNT_PREV_DAY = PREFIX_NOTIFICATION + "previousDayFailed"
STAT_NOTIFY_COUNT_PREV_HOUR = PREFIX_NOTIFICATION + "previousHour"
STAT_NOTIFY_AVG_TIME_PREV_HOUR = PREFIX_NOTIFICATION + "previousHourAvgTime"
STAT_NOTIFY_CREATES_COUNT_PREV_HOUR = PREFIX_NOTIFICATION + "previousHourEntityCreates"
STAT_NOTIFY_UPDATES_COUNT_PREV_HOUR = PREFIX_NOTIFICATION + "previousHourEntityUpdates"
STAT_NOTIFY_DELETES_COUNT_PREV_HOUR = PREFIX_NOTIFICATION + "previousHourEntityDeletes"
STAT_NOTIFY_FAILED_COUNT_PREV_HOUR = PREFIX_NOTIFICATION + "previousHourFailed"
STAT_NOTIFY_COUNT_TOTAL = PREFIX_NOTIFICATION + "total"
STAT_NOTIFY_AVG_TIME_TOTAL = PREFIX_NOTIFICATION + "totalAvgTime"
STAT_NOTIFY_CREATES_COUNT_TOTAL = PREFIX_NOTIFICATION + "totalCreates"
STAT_NOTIFY_UPDATES_COUNT_TOTAL = PREFIX_NOTIFICATION + "totalUpdates"
STAT_NOTIFY_DELETES_COUNT_TOTAL = PREFIX_NOTIFICATION + "totalDeletes"
STAT_NOTIFY_FAILED_COUNT_TOTAL = PREFIX_NOTIFICATION + "totalFailed"
STAT_SERVER_ACTIVE_TIMESTAMP = PREFIX_SERVER + "activeTimeStamp"
STAT_SERVER_START_TIMESTAMP = PREFIX_SERVER + "startTimeStamp"
STAT_SERVER_STATUS_BACKEND_STORE = PREFIX_SERVER + "statusBackendStore"
STAT_SERVER_STATUS_INDEX_STORE = PREFIX_SERVER + "statusIndexStore"
STAT_SERVER_UP_TIME = PREFIX_SERVER + "upTime"
"""The keys of the server's stats, as ``AtlasMetrics`` names them."""


class AtlasMetrics(AtlasModel):
    """``AtlasMetrics``: each group's metrics by name; no groups is no ``data``."""

    data: dict[str, dict[str, Any]] | None = None

    def add_metric(self, group_key: str, key: str, value: Any) -> None:  # noqa: ANN401 - any metric value
        """``addMetric``: the metric set in its group, the group added when missing."""
        if self.data is None:
            self.data = {}
        self.data.setdefault(group_key, {})[key] = value

    def metric(self, group_key: str, key: str) -> Any:  # noqa: ANN401 - any metric value
        """``getMetric``: the metric of the group, None when either is missing."""
        return (self.data or {}).get(group_key, {}).get(key)

    def numeric_metric(self, group_key: str, key: str) -> int | float | None:
        """``getNumericMetric``: the metric when it is a number, else None."""
        found = self.metric(group_key, key)
        return found if isinstance(found, int | float) and not isinstance(found, bool) else None


STATUS_CATEGORY = ("Active", "Deleted", "Shell")
"""The states a stored metric's type data counts, as ``AtlasEntityUtil`` names them."""

METRICS_ID_PREFIX = "atlas_metrics_"

_next_id = itertools.count(time.monotonic_ns())


def new_guid() -> str:
    """``AtlasBaseModelObject#init``: a new object's negative GUID."""
    return f"-{next(_next_id)}"


class AtlasMetricsStat(AtlasModel):
    """``AtlasMetricsStat``: the metrics collected at a time, kept ``timeToLiveMillis``; ``typeData`` the counts of
    the types a range asks for, by state (MHS-01).
    """  # noqa: D205 - one sentence

    guid: str = Field(default_factory=new_guid)
    metrics_id: str | None = None
    collection_time: JavaInt = 0
    time_to_live_millis: JavaInt = 0
    type_data: dict[str, Any] | None = None
    metrics: AtlasMetrics | None = None

    @classmethod
    def of(
        cls, metrics: AtlasMetrics, time_to_live_millis: int, namespace: str, type_names: list[str] | None = None
    ) -> AtlasMetricsStat:
        """``AtlasMetricsStat(metrics, timeToLiveMillis, listOfTypeNames)``: collected at the metrics' collection
        time, its id of that time and ``namespace``, the type data of ``type_names`` (none without names).
        """  # noqa: D205 - one sentence
        collection_time = int(metrics.metric("general", "collectionTime") or 0)
        type_data = None
        if type_names:
            entity = (metrics.data or {}).get("entity", {})
            type_data = {
                name: {status: (entity.get(f"entity{status}") or {}).get(name, 0) for status in STATUS_CATEGORY}
                for name in type_names
            }
        return cls(
            metrics_id=f"{METRICS_ID_PREFIX}{collection_time}@{namespace}",
            collection_time=collection_time,
            time_to_live_millis=time_to_live_millis,
            type_data=type_data,
            metrics=metrics,
        )


class AtlasMetricsMapToChart(AtlasModel):
    """``AtlasMetricsMapToChart``: a state's counts of a type, as ``[collectionTime, count]`` pairs (MHS-04)."""

    key: str
    values: list[list[int]]
