"""Keeping the App Search documents up to date in the background: the indexer's worker (ASU-06, LAS-10, ASG-06).

The worker runs ``AppSearchIndexer`` rounds in the background of every server process, a round at start and then
every poll interval, as the embedding worker does (DD-521). Each round goes on with the ``QualityIndexer``'s, over
the documents just written (DD-529, ASQ-07), and ends with the ``GovernanceIndexer``'s (DD-535). A failed round, as
when the store cannot be reached, is logged and the next one tries again; neither the start nor a request waits for
it.
"""

import asyncio
import contextlib
import logging

from aurelius_atlas_core.app_search_governance import GovernanceIndexer
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.app_search_quality import QualityIndexer

LOGGER = logging.getLogger("aurelius-atlas-server")


class AppSearchWorker:
    """Runs rounds of ``indexer``, then ``quality``, then ``governance`` in the background (ASU-06, ASQ-07, ASG-06).

    One round runs at start, one ``settle_seconds`` after a write wakes it, and one at the latest every
    ``poll_seconds`` (ASU-07). A write during a round wakes the next one at once, so a stream of changes is
    derived batch after batch; the settle lets a burst of writes land in one round (DD-676).
    """

    def __init__(
        self,
        indexer: AppSearchIndexer,
        quality: QualityIndexer,
        governance: GovernanceIndexer,
        *,
        poll_seconds: float,
        settle_seconds: float = 0.0,
    ) -> None:
        """A worker of ``indexer``, ``quality`` and ``governance``, woken by writes, looking again every
        ``poll_seconds``.
        """  # noqa: D205 - one sentence
        self._indexer = indexer
        self._quality = quality
        self._governance = governance
        self._poll_seconds = poll_seconds
        self._settle_seconds = settle_seconds
        self._wake = asyncio.Event()
        self._running: asyncio.Task[None] | None = None

    def wake(self) -> None:
        """Run a round soon: a write changed the entities the documents derive from (ASU-07)."""
        self._wake.set()

    def start(self) -> None:
        """Run in the background, beginning at once."""
        self._running = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop; a document being written is derived again later (ASU-05)."""
        if self._running is not None:
            self._running.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._running
            self._running = None

    async def run_once(self) -> int:
        """Run one round; a failure is logged and the next round tries again."""
        try:
            written = await self._indexer.run_once()
            written += await self._quality.run_once()
            written += await self._governance.run_once()
        except Exception:
            LOGGER.exception("Deriving the App Search documents failed; trying again in %.0f s", self._poll_seconds)
            return 0
        if written:
            LOGGER.info("Wrote %d App Search documents, relationships, quality results, totals and verdicts", written)
        return written

    async def _loop(self) -> None:
        while True:
            self._wake.clear()
            await self.run_once()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._wake.wait(), timeout=self._poll_seconds)
                await asyncio.sleep(self._settle_seconds)
