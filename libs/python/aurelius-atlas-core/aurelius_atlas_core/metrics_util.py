"""``AtlasMetricsUtil`` and ``AtlasMetricJVMUtil``: the server's stats and its process's system details (MET-03,
MET-04).

Aurelius Atlas consumes no notifications (DV-01), so the notification stats are those of counters never counted:
zero, the last message at the epoch, the current day's and hour's start in UTC.
"""  # noqa: D205 - one sentence

import os
import platform
import resource
import time
from collections.abc import Callable
from typing import Any

from aurelius_atlas_model.metrics import (
    STAT_NOTIFY_AVG_TIME_CURR_DAY,
    STAT_NOTIFY_AVG_TIME_CURR_HOUR,
    STAT_NOTIFY_AVG_TIME_PREV_DAY,
    STAT_NOTIFY_AVG_TIME_PREV_HOUR,
    STAT_NOTIFY_AVG_TIME_TOTAL,
    STAT_NOTIFY_COUNT_CURR_DAY,
    STAT_NOTIFY_COUNT_CURR_HOUR,
    STAT_NOTIFY_COUNT_PREV_DAY,
    STAT_NOTIFY_COUNT_PREV_HOUR,
    STAT_NOTIFY_COUNT_TOTAL,
    STAT_NOTIFY_CREATES_COUNT_CURR_DAY,
    STAT_NOTIFY_CREATES_COUNT_CURR_HOUR,
    STAT_NOTIFY_CREATES_COUNT_PREV_DAY,
    STAT_NOTIFY_CREATES_COUNT_PREV_HOUR,
    STAT_NOTIFY_CREATES_COUNT_TOTAL,
    STAT_NOTIFY_DELETES_COUNT_CURR_DAY,
    STAT_NOTIFY_DELETES_COUNT_CURR_HOUR,
    STAT_NOTIFY_DELETES_COUNT_PREV_DAY,
    STAT_NOTIFY_DELETES_COUNT_PREV_HOUR,
    STAT_NOTIFY_DELETES_COUNT_TOTAL,
    STAT_NOTIFY_FAILED_COUNT_CURR_DAY,
    STAT_NOTIFY_FAILED_COUNT_CURR_HOUR,
    STAT_NOTIFY_FAILED_COUNT_PREV_DAY,
    STAT_NOTIFY_FAILED_COUNT_PREV_HOUR,
    STAT_NOTIFY_FAILED_COUNT_TOTAL,
    STAT_NOTIFY_LAST_MESSAGE_PROCESSED_TIME,
    STAT_NOTIFY_START_TIME_CURR_DAY,
    STAT_NOTIFY_START_TIME_CURR_HOUR,
    STAT_NOTIFY_TOPIC_DETAILS,
    STAT_NOTIFY_UPDATES_COUNT_CURR_DAY,
    STAT_NOTIFY_UPDATES_COUNT_CURR_HOUR,
    STAT_NOTIFY_UPDATES_COUNT_PREV_DAY,
    STAT_NOTIFY_UPDATES_COUNT_PREV_HOUR,
    STAT_NOTIFY_UPDATES_COUNT_TOTAL,
    STAT_SERVER_ACTIVE_TIMESTAMP,
    STAT_SERVER_START_TIMESTAMP,
    STAT_SERVER_STATUS_BACKEND_STORE,
    STAT_SERVER_STATUS_INDEX_STORE,
    STAT_SERVER_UP_TIME,
)

SEC_MS = 1000
MIN_MS = 60 * SEC_MS
HOUR_MS = 60 * MIN_MS
DAY_MS = 24 * HOUR_MS

STATUS_CONNECTED = "connected"
STATUS_NOT_CONNECTED = "not-connected"

NOTIFY_COUNTS = (
    STAT_NOTIFY_COUNT_TOTAL,
    STAT_NOTIFY_AVG_TIME_TOTAL,
    STAT_NOTIFY_FAILED_COUNT_TOTAL,
    STAT_NOTIFY_CREATES_COUNT_TOTAL,
    STAT_NOTIFY_UPDATES_COUNT_TOTAL,
    STAT_NOTIFY_DELETES_COUNT_TOTAL,
    STAT_NOTIFY_COUNT_CURR_DAY,
    STAT_NOTIFY_AVG_TIME_CURR_DAY,
    STAT_NOTIFY_FAILED_COUNT_CURR_DAY,
    STAT_NOTIFY_CREATES_COUNT_CURR_DAY,
    STAT_NOTIFY_UPDATES_COUNT_CURR_DAY,
    STAT_NOTIFY_DELETES_COUNT_CURR_DAY,
    STAT_NOTIFY_COUNT_CURR_HOUR,
    STAT_NOTIFY_AVG_TIME_CURR_HOUR,
    STAT_NOTIFY_FAILED_COUNT_CURR_HOUR,
    STAT_NOTIFY_CREATES_COUNT_CURR_HOUR,
    STAT_NOTIFY_UPDATES_COUNT_CURR_HOUR,
    STAT_NOTIFY_DELETES_COUNT_CURR_HOUR,
    STAT_NOTIFY_COUNT_PREV_HOUR,
    STAT_NOTIFY_AVG_TIME_PREV_HOUR,
    STAT_NOTIFY_FAILED_COUNT_PREV_HOUR,
    STAT_NOTIFY_CREATES_COUNT_PREV_HOUR,
    STAT_NOTIFY_UPDATES_COUNT_PREV_HOUR,
    STAT_NOTIFY_DELETES_COUNT_PREV_HOUR,
    STAT_NOTIFY_COUNT_PREV_DAY,
    STAT_NOTIFY_AVG_TIME_PREV_DAY,
    STAT_NOTIFY_FAILED_COUNT_PREV_DAY,
    STAT_NOTIFY_CREATES_COUNT_PREV_DAY,
    STAT_NOTIFY_UPDATES_COUNT_PREV_DAY,
    STAT_NOTIFY_DELETES_COUNT_PREV_DAY,
)
"""The notification counts and average times, each zero: no notification is consumed (DV-01)."""


class AtlasMetricsUtil:
    """``AtlasMetricsUtil``: when the server started and became active, and the stats ``admin/metrics`` answers."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self.server_start_time = 0
        self.server_active_time = 0

    def on_server_start(self) -> None:
        """``onServerStart``: the server's start time is now."""
        self.server_start_time = self._now()

    def on_server_activation(self) -> None:
        """``onServerActivation``: the time the server became active is now."""
        self.server_active_time = self._now()

    def stats(self, *, backend_connected: bool, index_connected: bool) -> dict[str, Any]:
        """``getStats``: the server's times, up time and store statuses, and the notification stats (MET-03)."""
        now = self._now()
        found: dict[str, Any] = {
            STAT_SERVER_START_TIMESTAMP: self.server_start_time,
            STAT_SERVER_ACTIVE_TIMESTAMP: self.server_active_time,
            STAT_SERVER_UP_TIME: millis_to_time_diff(now - self.server_start_time),
            STAT_SERVER_STATUS_BACKEND_STORE: STATUS_CONNECTED if backend_connected else STATUS_NOT_CONNECTED,
            STAT_SERVER_STATUS_INDEX_STORE: STATUS_CONNECTED if index_connected else STATUS_NOT_CONNECTED,
            STAT_NOTIFY_TOPIC_DETAILS: {},
            STAT_NOTIFY_LAST_MESSAGE_PROCESSED_TIME: 0,
            STAT_NOTIFY_START_TIME_CURR_DAY: now - now % DAY_MS,
            STAT_NOTIFY_START_TIME_CURR_HOUR: now - now % HOUR_MS,
        }
        found.update(dict.fromkeys(NOTIFY_COUNTS, 0))
        return found

    def _now(self) -> int:
        return int(self._clock() * 1000)


def millis_to_time_diff(ms_diff: int) -> str:
    """``millisToTimeDiff``: days, hours, minutes and seconds, each left out when zero (MET-03)."""
    parts = (
        (ms_diff // DAY_MS, "day "),
        (ms_diff // HOUR_MS % 24, "hour "),
        (ms_diff // MIN_MS % 60, "min "),
        (ms_diff // SEC_MS % 60, "sec"),
    )
    return "".join(f"{value} {unit}" for value, unit in parts if value > 0)


def runtime_info() -> dict[str, Any]:
    """``getRuntimeInfo``: the Python implementation and its version, for the JVM's (MET-04, DV-135)."""
    return {"name": platform.python_implementation(), "version": platform.python_version()}


def memory_details() -> dict[str, Any]:
    """``getMemoryDetails``: the process's largest resident set in bytes, for the JVM's heap (MET-04, DV-135)."""
    return {"maxResidentSetSize": str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)}


def system_info() -> dict[str, Any]:
    """``getSystemInfo``: the operating system's name, architecture and release, and the processors (MET-04)."""
    spec = (platform.system(), platform.machine(), platform.release())
    return {"os.spec": ", ".join(spec), "os.vcpus": str(os.cpu_count() or 1)}
