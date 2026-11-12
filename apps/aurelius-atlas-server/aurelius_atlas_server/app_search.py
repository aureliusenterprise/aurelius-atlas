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
    """Runs rounds of ``indexer``, then of ``quality``, then of ``governance``, in the background, one at start and
    then every ``poll_seconds`` (ASU-06, ASQ-07, ASG-06).
    """  # noqa: D205 - one sentence

    def __init__(
        self,
        indexer: AppSearchIndexer,
        quality: QualityIndexer,
        governance: GovernanceIndexer,
        *,
        poll_seconds: float,
    ) -> None:
        """A worker of ``indexer``, ``quality`` and ``governance``, looking again every ``poll_seconds``."""
        self._indexer = indexer
        self._quality = quality
        self._governance = governance
        self._poll_seconds = poll_seconds
        self._running: asyncio.Task[None] | None = None

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
            await self.run_once()
            await asyncio.sleep(self._poll_seconds)
