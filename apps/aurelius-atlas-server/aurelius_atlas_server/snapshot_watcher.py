"""``SnapshotWatcher``: how the store's snapshot policy last ran, read on a schedule and reported (SNP-03).

Elasticsearch takes the snapshots; the server checks that they succeed. Each check logs an error when the
last run failed, and keeps the time of the last success, which the gauge ``aurelius_atlas.snapshot.last_success``
reports for the alert rule ``aurelius-atlas-snapshot-overdue``.
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Iterable

from aurelius_atlas_store_es.snapshots import SnapshotStatus
from opentelemetry.metrics import CallbackOptions, Meter, Observation

LOGGER = logging.getLogger("aurelius-atlas-server")

MINUTE_SECONDS = 60

LAST_SUCCESS_GAUGE = "aurelius_atlas.snapshot.last_success"
"""The gauge of the last successful snapshot's time, in seconds since the epoch; Prometheus reads it as
``aurelius_atlas_snapshot_last_success_seconds``."""


class SnapshotWatcher:
    """Reads the policy's status every ``interval_minutes``, first at start, and reports it."""

    def __init__(
        self,
        read: Callable[[], Awaitable[SnapshotStatus]],
        *,
        interval_minutes: int,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._read = read
        self._interval = max(interval_minutes, 1) * MINUTE_SECONDS
        self._sleep = sleep
        self._running: asyncio.Task[None] | None = None
        self.status: SnapshotStatus | None = None
        """The status the last check read; None before the first, or when it could not be read."""

    def register(self, meter: Meter) -> None:
        """Report the last success on ``meter``'s gauge (SNP-03)."""
        meter.create_observable_gauge(
            LAST_SUCCESS_GAUGE,
            callbacks=[self.observe],
            unit="s",
            description="When the store's last successful snapshot was taken",
        )

    def observe(self, _options: CallbackOptions) -> Iterable[Observation]:
        """The last success's time, while the watcher runs and a snapshot has succeeded."""
        if self._running is not None and self.status is not None and self.status.last_success is not None:
            yield Observation(self.status.last_success.timestamp())

    def start(self) -> None:
        """Run in the background."""
        self._running = asyncio.create_task(self.run())

    async def stop(self) -> None:
        """Stop checking; the gauge reports nothing more."""
        if self._running is not None:
            self._running.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._running
            self._running = None

    async def run(self) -> None:
        """Check, then wait for the interval, again and again."""
        while True:
            await self.check()
            await self._sleep(self._interval)

    async def check(self) -> SnapshotStatus | None:
        """Read the status, and log an error when the last run failed; a failure to read is logged too."""
        try:
            self.status = await self._read()
        except Exception:
            LOGGER.exception("Reading the snapshot policy failed")
            self.status = None
            return None
        if self.status.failing:
            LOGGER.error(
                "The last snapshot failed at %s: %s; the last success was at %s",
                self.status.last_failure,
                self.status.last_failure_details,
                self.status.last_success,
            )
        return self.status
