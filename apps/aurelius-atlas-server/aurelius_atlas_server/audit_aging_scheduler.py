"""``AuditAgingScheduler``: the configured aging of the entity audits queued on a schedule (AGE-05).

Atlas's ``AtlasAuditReductionService.configureTasks``: with ``atlas.audit.aging.enabled``, a fixed-rate task
starts the aging of the configuration after an initial delay and then every ``frequency`` days. Atlas runs it on
its active instance; here every process schedules it, the tasks it queues bounded by the pending ones (DV-133).
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from aurelius_atlas_core.audit_reduction_service import AtlasAuditReductionService

LOGGER = logging.getLogger("aurelius-atlas-server")

MINUTE_SECONDS = 60
DAY_SECONDS = 86_400


class AuditAgingScheduler:
    """Queues ``service``'s configured aging after ``initial_delay_minutes``, then every ``frequency_days``."""

    def __init__(
        self,
        service: AtlasAuditReductionService,
        *,
        frequency_days: int,
        initial_delay_minutes: int,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._service = service
        self._frequency = max(frequency_days, 1) * DAY_SECONDS
        self._delay = max(initial_delay_minutes, 1) * MINUTE_SECONDS
        self._sleep = sleep
        self._running: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Run in the background."""
        self._running = asyncio.create_task(self.run())

    async def stop(self) -> None:
        """Stop the schedule; the tasks it queued stay."""
        if self._running is not None:
            self._running.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._running
            self._running = None

    async def run(self) -> None:
        """Wait the initial delay, then queue the aging and wait the frequency, again and again."""
        await self._sleep(self._delay)
        while True:
            await self.age_out()
            await self._sleep(self._frequency)

    async def age_out(self) -> None:
        """``startAuditAgingByConfig``; a failure to reach the store is logged and tried at the next round."""
        try:
            await self._service.start_by_config()
        except Exception:
            LOGGER.exception("Aging out the audits failed")
