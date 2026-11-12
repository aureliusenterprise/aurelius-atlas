"""The App Search worker in the server: its rounds, a failed round, its settings, and the wiring (ASU-06, LAS-10),
on the fake store.
"""  # noqa: D205 - one sentence

import asyncio
import logging

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_server.app import create_app
from aurelius_atlas_server.app_search import AppSearchWorker
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_store_es.testing.fake import FakeClient

W = "aurelius_atlas_server.app_search.AppSearchWorker"


class Indexer:
    """An indexer whose rounds answer ``results`` in turn; an exception is raised."""

    def __init__(self, *results: int | Exception) -> None:
        self.results = list(results)
        self.rounds = 0

    async def run_once(self) -> int:
        """The next result."""
        self.rounds += 1
        result = self.results.pop(0) if self.results else 0
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.covers(f"{W}.run_once", rules=["ASU-06"])
async def test__a_failed_round_is_logged_and_the_next_one_tries_again(caplog: pytest.LogCaptureFixture) -> None:
    """The store down: logged, 0 written; the next round writes."""
    worker = AppSearchWorker(Indexer(RuntimeError("store down"), 3), poll_seconds=60)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="aurelius-atlas-server"):
        assert await worker.run_once() == 0
        assert await worker.run_once() == 3

    assert "Deriving the App Search documents failed" in caplog.text
    assert "Wrote 3 App Search documents" in caplog.text


@pytest.mark.covers(f"{W}.start", rules=["ASU-06"])
@pytest.mark.covers(f"{W}.stop", rules=["ASU-06"])
async def test__the_worker_runs_a_round_at_start_and_then_every_poll_interval() -> None:
    """Started, it runs at once and again after each interval; stopping twice is harmless."""
    indexer = Indexer(1, 0, 0)
    worker = AppSearchWorker(indexer, poll_seconds=0.01)  # type: ignore[arg-type]

    worker.start()
    for _ in range(100):
        if indexer.rounds >= 3:
            break
        await asyncio.sleep(0.01)
    await worker.stop()
    await worker.stop()

    assert indexer.rounds >= 3


@pytest.mark.covers(rules=["ASU-06", "LAS-10"])
def test__the_worker_is_on_by_default_and_configured_by_its_settings() -> None:
    """On, 100 a page, every ten seconds; the environment turns it off and sets the rest."""
    defaults = ServerSettings.model_fields

    assert defaults["app_search_enabled"].default is True
    assert (defaults["app_search_batch_size"].default, defaults["app_search_poll_seconds"].default) == (100, 10.0)


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
