"""``MetricsScheduler``: the metrics stored, and those past their time to live purged, on a schedule (MHS-05).

Atlas's ``AdminResource#scheduleSaveAndDeleteMetrics`` runs on the cron ``atlas.metrics.persist.schedule``, by
default at the start of every hour. Here the schedule is an interval in minutes, each run at a multiple of it
since the epoch, so the default of 60 runs at the start of every hour too (DV-137).
"""

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable

from aurelius_atlas_core.metrics_service import MetricsService

LOGGER = logging.getLogger("aurelius-atlas-server")

MINUTE_SECONDS = 60


class MetricsScheduler:
    """Stores ``service``'s metrics and purges the expired ones every ``interval_minutes``, on the minute."""

    def __init__(
        self,
        service: MetricsService,
        connected: Callable[[], Awaitable[bool]],
        *,
        interval_minutes: int,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._service = service
        self._connected = connected
        self._interval = max(interval_minutes, 1) * MINUTE_SECONDS
        self._clock = clock
        self._sleep = sleep
        self._running: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Run in the background."""
        self._running = asyncio.create_task(self.run())

    async def stop(self) -> None:
        """Stop the schedule; the metrics it stored stay."""
        if self._running is not None:
            self._running.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._running
            self._running = None

    async def run(self) -> None:
        """Wait for the next multiple of the interval, then save and purge, again and again."""
        while True:
            await self._sleep(self._interval - self._clock() % self._interval)
            await self.save_and_purge()

    async def save_and_purge(self) -> None:
        """``scheduleSaveAndDeleteMetrics``: save the metrics of now, then purge; a failure is only logged."""
        try:
            await self._service.save_metrics(store_connected=await self._connected())
        except Exception:
            LOGGER.exception("Saving the metrics failed")
        try:
            await self._service.purge_metrics_stats()
        except Exception:
            LOGGER.exception("Purging the metrics failed")
