"""``TaskWorker``: the tasks requests record, run in the background of every server process (TSK-04, DD-080).

Atlas's ``TaskManagement`` starts a ``TaskExecutor`` on its active instance and queues each request's tasks to it;
here every process runs a worker, woken by a write of its own that records a task and looking again every
``task_poll_seconds`` for those of other processes, each claimed before it runs (DV-38).
"""

import asyncio
import contextlib
import logging

from aurelius_atlas_core.task_management import TaskManagement

LOGGER = logging.getLogger("aurelius-atlas-server")


class TaskWorker:
    """Runs the pending tasks of ``management`` when woken, and at least every ``poll_seconds``."""

    def __init__(self, management: TaskManagement, *, poll_seconds: float) -> None:
        self._management = management
        self._poll_seconds = poll_seconds
        self._wake = asyncio.Event()
        self._running: asyncio.Task[None] | None = None

    def wake(self) -> None:
        """Run the pending tasks soon: a write recorded one (TSK-04)."""
        self._wake.set()

    def start(self) -> None:
        """Run in the background, beginning with the tasks already waiting."""
        self._wake.set()
        self._running = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop; a task being run is claimed again by a process once its lease has passed (DD-080)."""
        if self._running is not None:
            self._running.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._running
            self._running = None

    async def run_once(self) -> int:
        """Run the pending tasks once; a failure to reach the store is logged and tried at the next round."""
        try:
            return await self._management.run_pending()
        except Exception:
            LOGGER.exception("Running the pending tasks failed")
            return 0

    async def _loop(self) -> None:
        while True:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._wake.wait(), timeout=self._poll_seconds)
            self._wake.clear()
            await self.run_once()
