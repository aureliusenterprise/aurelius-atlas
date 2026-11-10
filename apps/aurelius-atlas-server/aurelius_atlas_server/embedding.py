"""Embedding entities in the background: the embeddings API's client and the indexer's worker (VEC-07, VEC-09).

The client speaks OpenAI's embeddings API, as the embedder of 11.2 does (DD-430), so another server that speaks it
can stand in. The worker runs ``EntityEmbeddingIndexer`` rounds in the background of every server process, a round
at start and then every poll interval; a failed round, as when the embedder cannot be reached, is logged and the
next one tries again, and neither the start nor a request waits for it (DD-436).
"""

import asyncio
import contextlib
import logging
import ssl
from collections.abc import Sequence
from pathlib import Path

import httpx2 as httpx
from aurelius_atlas_core.entity_embedding_indexer import EntityEmbeddingIndexer

LOGGER = logging.getLogger("aurelius-atlas-server")

HTTP_TIMEOUT_SECONDS = 60.0
"""How long a request to the embedder may take: a page of texts on a CPU takes about a second."""


class EmbeddingError(RuntimeError):
    """The embeddings API answered with something else than one vector per text of the configured dimensions."""


class EmbeddingClient:
    """``POST {url}/v1/embeddings`` with the texts as passages, checked for count and dimensions (VEC-09)."""

    def __init__(self, url: str, model: str, dimensions: int, *, http: httpx.AsyncClient) -> None:
        """A client of the embeddings API at ``url`` for ``model``'s vectors of ``dimensions``."""
        self._url = f"{url.rstrip('/')}/v1/embeddings"
        self._model = model
        self._dimensions = dimensions
        self._http = http

    @property
    def model(self) -> str:
        """The model the vectors are computed with."""
        return self._model

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in their order.

        Raises:
            EmbeddingError: The answer has another number of vectors, or vectors of other dimensions.
            httpx.HTTPError: The embedder could not be reached or refused the request.
        """
        response = await self._http.post(
            self._url, json={"input": list(texts), "model": self._model, "input_type": "passage"}
        )
        response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda entry: entry["index"])
        vectors = [[float(value) for value in entry["embedding"]] for entry in data]
        if len(vectors) != len(texts):
            message = f"The embedder answered {len(vectors)} embeddings for {len(texts)} texts"
            raise EmbeddingError(message)
        if any(len(vector) != self._dimensions for vector in vectors):
            message = f"The embedder answered vectors of other dimensions than {self._dimensions}"
            raise EmbeddingError(message)
        return vectors


def embedding_http(ca_file: Path | None) -> httpx.AsyncClient:
    """The HTTP client of the embedder, verifying its TLS against ``ca_file`` or the system trust store."""
    context = ssl.create_default_context(cafile=ca_file) if ca_file else ssl.create_default_context()
    return httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, verify=context)


class EmbeddingWorker:
    """Runs rounds of ``indexer`` in the background, one at start and then every ``poll_seconds`` (VEC-07)."""

    def __init__(
        self, indexer: EntityEmbeddingIndexer, *, poll_seconds: float, http: httpx.AsyncClient | None = None
    ) -> None:
        """A worker of ``indexer``, looking again every ``poll_seconds``; ``http``, its client's, closes with it."""
        self._indexer = indexer
        self._poll_seconds = poll_seconds
        self._http = http
        self._running: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Run in the background, beginning at once."""
        self._running = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop, and close the client's HTTP; an embedding being written is written again later (DD-436)."""
        if self._running is not None:
            self._running.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._running
            self._running = None
        if self._http is not None:
            await self._http.aclose()

    async def run_once(self) -> int:
        """Run one round; a failure is logged and the next round tries again."""
        try:
            written = await self._indexer.run_once()
        except Exception:
            LOGGER.exception("Embedding the entities failed; trying again in %.0f s", self._poll_seconds)
            return 0
        if written:
            LOGGER.info("Embedded %d entities", written)
        return written

    async def _loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self._poll_seconds)
