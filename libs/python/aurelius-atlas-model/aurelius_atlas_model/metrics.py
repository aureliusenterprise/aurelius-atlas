"""``AtlasMetrics``: what ``admin/metrics`` answers, grouped metrics by name (MET-01).

Ported from Apache Atlas 2.4.0 ``org.apache.atlas.model.metrics.AtlasMetrics``.
"""

from typing import Any

from aurelius_atlas_model.base import AtlasModel

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
