"""Keeping the App Search documents up to date in the background: the indexer's worker (ASU-06, LAS-10, ASG-06).

The worker runs ``AppSearchIndexer`` rounds in the background of every server process, a round at start and then
every poll interval, as the embedding worker does (DD-521). Each round goes on with the ``QualityIndexer``'s, over
the documents just written (DD-529, ASQ-07), and ends with the ``GovernanceIndexer``'s (DD-535). A failed round, as
when the store cannot be reached, is logged and the next one tries again; the start doesn't wait for it.

A write wakes the worker (ASU-07, DD-676). A request that writes also waits for a round before its answer goes out,
up to a time limit, so the page that reloads after a save reads the derived breadcrumb (ASU-08, DD-678).
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, MutableMapping
from contextvars import ContextVar
from typing import Any

from aurelius_atlas_core.app_search_governance import GovernanceIndexer
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.app_search_quality import QualityIndexer

LOGGER = logging.getLogger("aurelius-atlas-server")

_ANSWERING: ContextVar[set[AppSearchWorker] | None] = ContextVar("aurelius_atlas_app_search_answering", default=None)
"""The workers whose store the request being answered wrote to, to run before its answer (ASU-08)."""


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
        self._round = asyncio.Lock()
        self._running: asyncio.Task[None] | None = None

    def wake(self) -> None:
        """Run a round soon: a write changed the entities the documents derive from (ASU-07)."""
        self._wake.set()

    def wrote(self) -> None:
        """A write to the worker's store: wake it (ASU-07) and, inside a request, run a round before its answer
        (ASU-08).
        """  # noqa: D205 - one sentence
        self.wake()
        answering = _ANSWERING.get()
        if answering is not None:
            answering.add(self)

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
        """Run one round, after any round under way; a failure is logged and the next round tries again."""
        async with self._round:
            return await self._run_round()

    async def _run_round(self) -> int:
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


Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class DeriveBeforeAnsweringMiddleware:
    """Holds a writing request's answer until its stores' App Search documents are derived (ASU-08, DD-678).

    A request whose writes reach a store set's entity store registers that set's worker (``AppSearchWorker.wrote``).
    The answer's last body part waits for a round of each, up to ``timeout_seconds``; a round still running then
    goes on in the background and the answer leaves. A request that wrote nothing passes unchanged.
    """

    def __init__(self, app: ASGIApp, *, timeout_seconds: float) -> None:
        """Around ``app``, waiting at most ``timeout_seconds`` for the rounds."""
        self._app = app
        self._timeout_seconds = timeout_seconds

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve the request, its answer's end after the rounds its writes call for."""
        if scope["type"] != "http" or self._timeout_seconds <= 0:
            await self._app(scope, receive, send)
            return
        answering: set[AppSearchWorker] = set()
        token = _ANSWERING.set(answering)

        async def send_after_rounds(message: Message) -> None:
            if message["type"] == "http.response.body" and not message.get("more_body", False) and answering:
                await derive(sorted(answering, key=id), self._timeout_seconds)
                answering.clear()
            await send(message)

        try:
            await self._app(scope, receive, send_after_rounds)
        finally:
            _ANSWERING.reset(token)


async def derive(workers: list[AppSearchWorker], timeout_seconds: float) -> bool:
    """Run a round of each worker, waiting at most ``timeout_seconds``; whether all ended in time (ASU-08)."""
    if not workers:
        return True
    rounds = [asyncio.ensure_future(worker.run_once()) for worker in workers]
    _, pending = await asyncio.wait(rounds, timeout=timeout_seconds)
    if pending:
        LOGGER.info("The App Search documents of a write are still being derived after %.1f s", timeout_seconds)
    return not pending
