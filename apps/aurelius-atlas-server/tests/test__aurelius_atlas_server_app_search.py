"""The App Search worker in the server: its rounds, the quality and governance rounds after the documents', a
failed round, its settings, and the wiring (ASU-06, LAS-10, ASQ-07, ASG-06), on the fake store.
"""  # noqa: D205 - one sentence

import asyncio
import logging
from typing import Any

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_server.app import create_app
from aurelius_atlas_server.app_search import AppSearchWorker, DeriveBeforeAnsweringMiddleware, derive
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_store_es.testing.fake import FakeClient

W = "aurelius_atlas_server.app_search.AppSearchWorker"


class Indexer:
    """An indexer whose rounds answer ``results`` in turn; an exception is raised. Each round is logged in ``log``."""

    def __init__(self, *results: int | Exception, name: str = "documents", log: list[str] | None = None) -> None:
        self.results = list(results)
        self.rounds = 0
        self.name = name
        self.log = [] if log is None else log

    async def run_once(self) -> int:
        """The next result."""
        self.rounds += 1
        self.log.append(self.name)
        result = self.results.pop(0) if self.results else 0
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.covers(f"{W}.run_once", rules=["ASU-06"])
async def test__a_failed_round_is_logged_and_the_next_one_tries_again(caplog: pytest.LogCaptureFixture) -> None:
    """The store down: logged, 0 written; the next round writes."""
    worker = AppSearchWorker(Indexer(RuntimeError("store down"), 3), Indexer(), Indexer(), poll_seconds=60)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="aurelius-atlas-server"):
        assert await worker.run_once() == 0
        assert await worker.run_once() == 3

    assert "Deriving the App Search documents failed" in caplog.text
    assert "Wrote 3 App Search documents" in caplog.text


@pytest.mark.covers(f"{W}.run_once", rules=["ASQ-07", "ASG-06"])
async def test__a_round_derives_the_quality_and_the_verdicts_after_the_documents() -> None:
    """The documents' round first, then the quality round over them, the governance round last; the written add up."""
    log: list[str] = []
    rounds = Indexer(2, log=log), Indexer(5, name="quality", log=log), Indexer(4, name="governance", log=log)
    worker = AppSearchWorker(*rounds, poll_seconds=60)  # type: ignore[arg-type]

    assert await worker.run_once() == 11
    assert log == ["documents", "quality", "governance"]


@pytest.mark.covers(f"{W}.run_once", rules=["ASU-08"])
async def test__a_request_s_round_leaves_the_data_quality_to_the_background() -> None:
    """Without quality: the documents, then the verdicts; the quality indexer doesn't run (DD-679)."""
    log: list[str] = []
    rounds = Indexer(2, log=log), Indexer(5, name="quality", log=log), Indexer(4, name="governance", log=log)
    worker = AppSearchWorker(*rounds, poll_seconds=60)  # type: ignore[arg-type]

    assert await worker.run_once(quality=False) == 6
    assert log == ["documents", "governance"]


@pytest.mark.covers(f"{W}.start", rules=["ASU-06"])
@pytest.mark.covers(f"{W}.stop", rules=["ASU-06"])
async def test__the_worker_runs_a_round_at_start_and_then_every_poll_interval() -> None:
    """Started, it runs at once and again after each interval; stopping twice is harmless."""
    indexer = Indexer(1, 0, 0)
    worker = AppSearchWorker(indexer, Indexer(), Indexer(), poll_seconds=0.01)  # type: ignore[arg-type]

    worker.start()
    for _ in range(100):
        if indexer.rounds >= 3:
            break
        await asyncio.sleep(0.01)
    await worker.stop()
    await worker.stop()

    assert indexer.rounds >= 3


async def _rounds_reach(indexer: Indexer, rounds: int) -> None:
    for _ in range(200):
        if indexer.rounds >= rounds:
            return
        await asyncio.sleep(0.005)


@pytest.mark.covers(f"{W}.wake", f"{W}.start", rules=["ASU-07"])
async def test__a_write_wakes_the_worker_long_before_its_poll() -> None:
    """After the round at start it waits; woken, it runs the next round within its settle, not its hour of poll."""
    indexer = Indexer()
    worker = AppSearchWorker(indexer, Indexer(), Indexer(), poll_seconds=3600, settle_seconds=0.01)  # type: ignore[arg-type]
    worker.start()
    await _rounds_reach(indexer, 1)
    await asyncio.sleep(0.05)
    assert indexer.rounds == 1

    worker.wake()
    await _rounds_reach(indexer, 2)
    await worker.stop()

    assert indexer.rounds == 2


class SlowIndexer(Indexer):
    """An indexer whose round takes a while, waking ``worker`` during its first, as a write would."""

    worker: AppSearchWorker

    async def run_once(self) -> int:
        """A round of 20 ms; a write lands during the first."""
        result = await super().run_once()
        if self.rounds == 1:
            self.worker.wake()
        await asyncio.sleep(0.02)
        return result


@pytest.mark.covers(f"{W}.wake", rules=["ASU-07"])
async def test__a_write_during_a_round_brings_the_next_round_at_once() -> None:
    """The changes a round didn't see are derived in the very next one, batch after batch, not a poll later."""
    indexer = SlowIndexer()
    worker = AppSearchWorker(indexer, Indexer(), Indexer(), poll_seconds=3600)  # type: ignore[arg-type]
    indexer.worker = worker
    worker.start()
    await _rounds_reach(indexer, 2)
    await asyncio.sleep(0.05)
    await worker.stop()

    assert indexer.rounds == 2


@pytest.mark.covers(rules=["ASU-06", "ASU-07", "LAS-10"])
def test__the_worker_is_on_by_default_and_configured_by_its_settings() -> None:
    """On, 100 a page, every ten seconds; the environment turns it off and sets the rest."""
    defaults = ServerSettings.model_fields

    assert defaults["app_search_enabled"].default is True
    assert (defaults["app_search_batch_size"].default, defaults["app_search_poll_seconds"].default) == (100, 10.0)
    assert defaults["app_search_settle_seconds"].default == 0.5
    assert defaults["app_search_answer_seconds"].default == 5.0


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["ASU-06", "LAS-10"])
async def test__the_server_derives_a_written_entity_s_document_in_the_background(
    settings: ServerSettings, fake_es: FakeClient
) -> None:
    """With the worker on, an m4i entity written to the store gets its document without a request."""
    app = create_app(settings.model_copy(update={"app_search_enabled": True, "app_search_poll_seconds": 0.01}))

    async with app.router.lifespan_context(app):
        documents = ElasticsearchEntityDocuments(fake_es)  # type: ignore[arg-type]
        await documents.write([(StoredEntity(guid="d", type_name="m4i_data_domain", attributes={}), None)])
        for _ in range(200):
            if (await documents.get(["d"]))["d"].entity.app_search is not None:
                break
            await asyncio.sleep(0.01)
        stored = (await documents.get(["d"]))["d"].entity

    assert stored.app_search is not None
    assert stored.app_search.referenceablequalifiedname == "d"


@pytest.mark.covers("aurelius_atlas_server.tenant_workers.app_search_worker", rules=["ASU-07"])
async def test__the_server_s_entity_store_wakes_its_app_search_worker(
    settings: ServerSettings, fake_es: FakeClient
) -> None:
    """The running worker's wake is one of the entity store's write listeners (DD-678)."""
    del fake_es  # the store the app connects to
    app = create_app(settings.model_copy(update={"app_search_enabled": True, "app_search_poll_seconds": 3600}))

    async with app.router.lifespan_context(app):
        running = next(iter(app.state.tenant_workers.running.values()))
        workers = [worker for worker in running.others if isinstance(worker, AppSearchWorker)]
        listeners = list(app.state.entity_store.write_listeners)

    assert len(workers) == 1
    assert workers[0].wrote in listeners


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["ASU-06"])
async def test__turned_off_the_server_derives_no_document(settings: ServerSettings, fake_es: FakeClient) -> None:
    """The test settings' default: an entity written keeps no document."""
    app = create_app(settings.model_copy(update={"app_search_poll_seconds": 0.01}))

    async with app.router.lifespan_context(app):
        documents = ElasticsearchEntityDocuments(fake_es)  # type: ignore[arg-type]
        await documents.write([(StoredEntity(guid="d", type_name="m4i_data_domain", attributes={}), None)])
        await asyncio.sleep(0.05)
        stored = (await documents.get(["d"]))["d"].entity

    assert stored.app_search is None


M = "aurelius_atlas_server.app_search.DeriveBeforeAnsweringMiddleware"


class SlowRounds(Indexer):
    """An indexer whose rounds take ``seconds``, logging when each ends."""

    def __init__(self, seconds: float, log: list[str]) -> None:
        super().__init__(log=log)
        self.seconds = seconds

    async def run_once(self) -> int:
        """A round of ``seconds``."""
        await asyncio.sleep(self.seconds)
        self.log.append("round")
        return 1


def handler(worker: AppSearchWorker, *, writes: bool) -> Any:  # noqa: ANN401 - an ASGI app
    """An ASGI app that writes (the worker hears it) when ``writes``, then answers in two body parts."""

    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:  # noqa: ANN401, ARG001
        if writes:
            worker.wrote()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{", "more_body": True})
        await send({"type": "http.response.body", "body": b"}"})

    return app


async def serve(app: Any, log: list[str]) -> None:  # noqa: ANN401 - an ASGI app
    """One HTTP request through ``app``, logging each part of the answer as it is sent."""

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b""}

    async def send(message: dict[str, Any]) -> None:
        log.append("start" if message["type"] == "http.response.start" else f"body:{message['body'].decode()}")

    await app({"type": "http"}, receive, send)


@pytest.mark.covers(f"{M}.__call__", f"{W}.wrote", rules=["ASU-08"])
async def test__a_writing_request_answers_once_its_documents_are_derived() -> None:
    """The write registers the worker; the answer's last part leaves after its documents and verdicts (DD-679)."""
    log: list[str] = []
    quality = Indexer(name="quality", log=log)
    worker = AppSearchWorker(SlowRounds(0.02, log), quality, Indexer(name="governance", log=log), poll_seconds=3600)  # type: ignore[arg-type]

    await serve(DeriveBeforeAnsweringMiddleware(handler(worker, writes=True), timeout_seconds=5), log)

    assert log == ["start", "body:{", "round", "governance", "body:}"]
    assert quality.rounds == 0


@pytest.mark.covers(f"{M}.__call__", rules=["ASU-08"])
async def test__a_request_that_writes_nothing_answers_without_a_round() -> None:
    """No write, no round: the answer passes as the handler sends it."""
    log: list[str] = []
    worker = AppSearchWorker(SlowRounds(0.02, log), Indexer(), Indexer(), poll_seconds=3600)  # type: ignore[arg-type]

    await serve(DeriveBeforeAnsweringMiddleware(handler(worker, writes=False), timeout_seconds=5), log)

    assert log == ["start", "body:{", "body:}"]


@pytest.mark.covers(f"{M}.__call__", "aurelius_atlas_server.app_search.derive", rules=["ASU-08"])
async def test__a_slow_round_holds_the_answer_no_longer_than_the_limit() -> None:
    """Past the limit the answer leaves; the round goes on and ends in the background."""
    log: list[str] = []
    worker = AppSearchWorker(SlowRounds(0.2, log), Indexer(), Indexer(), poll_seconds=3600)  # type: ignore[arg-type]

    await serve(DeriveBeforeAnsweringMiddleware(handler(worker, writes=True), timeout_seconds=0.02), log)
    assert log == ["start", "body:{", "body:}"]
    await asyncio.sleep(0.3)

    assert log[-1] == "round"
    assert await derive([], 1) is True


@pytest.mark.covers(f"{W}.wrote", rules=["ASU-07", "ASU-08"])
async def test__a_write_outside_a_request_only_wakes_the_worker() -> None:
    """A background write (a task, say) wakes the worker and registers it with no request."""
    indexer = Indexer()
    worker = AppSearchWorker(indexer, Indexer(), Indexer(), poll_seconds=3600, settle_seconds=0)  # type: ignore[arg-type]
    worker.start()
    await _rounds_reach(indexer, 1)

    worker.wrote()
    await _rounds_reach(indexer, 2)
    await worker.stop()

    assert indexer.rounds == 2


@pytest.mark.covers(f"{W}.run_once", rules=["ASU-08"])
async def test__rounds_run_one_after_the_other() -> None:
    """A request's round waits for the round under way, so the two never derive the same documents at once."""
    log: list[str] = []
    slow = SlowRounds(0.02, log)
    worker = AppSearchWorker(slow, Indexer(), Indexer(), poll_seconds=3600)  # type: ignore[arg-type]
    original = slow.run_once
    running = 0
    overlapped = False

    async def counted() -> int:
        nonlocal running, overlapped
        running += 1
        overlapped = overlapped or running > 1
        try:
            return await original()
        finally:
            running -= 1

    slow.run_once = counted
    await asyncio.gather(worker.run_once(), worker.run_once())

    assert not overlapped
    assert log == ["round", "round"]
