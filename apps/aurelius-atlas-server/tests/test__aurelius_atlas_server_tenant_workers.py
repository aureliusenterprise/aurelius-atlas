"""The workers of each store set, and the store sets kept in step with the tenants index (WPT-01 to WPT-04, WPT-06,
WPT-11).

Apache Atlas has no tenants (ADR 063); the expected answers are the spec's.
"""  # noqa: D205 - one sentence

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_core.entity_documents import INDEX_PREFIX
from aurelius_atlas_core.entity_store import StoredEntity
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server import app as app_module
from aurelius_atlas_server.tenant_stores import TenantStoreSets, tenant_prefix
from aurelius_atlas_server.tenant_workers import MIN_FOLLOW_SECONDS, TenantFollower, WorkerFactory
from aurelius_atlas_server.tenants import TenantState
from fake_issuer import FakeIssuer
from fastapi import FastAPI
from test__aurelius_atlas_server_embedding import URL, embedder

W = "aurelius_atlas_server.tenant_workers"
EXPORT = "/api/atlas/admin/export"
EVERY_GROUP = ["/atlas-read", "/atlas-write", "/atlas-types", "/atlas-admin"]

type Record = Callable[..., Awaitable[None]]


def member(issuer: FakeIssuer, tenant: str) -> dict[str, str]:
    """The ``Authorization`` header of a token acting in the tenant with every role of its groups."""
    token = issuer.token("ann", atlas_roles=(), organization={tenant: {"groups": EVERY_GROUP}})
    return {"Authorization": f"Bearer {token}"}


async def serve(settings: ServerSettings, **update: object) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    """The started application with the settings updated, and a client without credentials."""
    app = create_app(settings.model_copy(update=update))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas") as client:
            yield app, client


@pytest_asyncio.fixture(loop_scope="function")  # the test's loop, which stops the workers the start began
async def served(
    settings: ServerSettings, record_tenants: Record, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    """Tenancy, tasks and embedding on, acme provisioned before the start; the follower left to the tests."""
    monkeypatch.setattr(app_module, "embedding_http", lambda _ca: httpx.AsyncClient(transport=embedder([])))
    await record_tenants("acme")
    update: dict[str, Any] = {
        "tenancy_enabled": True,
        "tenancy_refresh_seconds": 3600,
        "tasks_enabled": True,
        "embedding_url": URL,
        "embedding_dimensions": 3,
        "embedding_poll_seconds": 0.01,
    }
    async for both in serve(settings, **update):
        yield both


def workers_of(app: FastAPI) -> WorkerFactory:
    """The application's workers, by store set."""
    return app.state.tenant_workers


@pytest.mark.covers(
    f"{W}.WorkerFactory.started",
    f"{W}.task_worker",
    f"{W}.embedding_worker",
    f"{W}.app_search_worker",
    "aurelius_atlas_server.tenant_stores.TenantStoreSets.add",
    rules=["WPT-01", "WPT-02", "WPT-03"],
)
async def test__each_store_set_runs_its_own_workers_on_its_own_stores(
    served: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    """The default's and acme's workers apart, acme's task worker woken by acme's writes, and an entity of acme
    embedded in acme's index through the one shared client.
    """  # noqa: D205 - one sentence
    app, _ = served
    acme = app.state.tenant_stores[tenant_prefix("acme")]
    running = workers_of(app).running
    assert set(running) == {INDEX_PREFIX, tenant_prefix("acme")}
    default_tasks, acme_tasks = running[INDEX_PREFIX].task_worker, running[tenant_prefix("acme")].task_worker
    assert acme_tasks is not None
    assert default_tasks is app.state.task_worker
    assert acme_tasks is not default_tasks
    assert acme_tasks.wake in acme.entity_store.task_listeners
    assert acme_tasks.wake not in app.state.entity_store.task_listeners
    assert len(running[tenant_prefix("acme")].others) == len(running[INDEX_PREFIX].others)
    await acme.documents.write([(StoredEntity(guid="e", type_name="m4i_data_entity", attributes={}), None)])
    for _ in range(200):
        if (await acme.documents.get(["e"]))["e"].entity.embedding is not None:
            break
        await asyncio.sleep(0.01)
    assert (await acme.documents.get(["e"]))["e"].entity.embedding is not None
    assert await app.state.entity_documents.get(["e"]) == {}


@pytest.mark.covers(
    f"{W}.WorkerFactory.stopping",
    f"{W}.WorkerFactory.stop",
    f"{W}.StoreSetWorkers.stop",
    f"{W}.TenantFollower.follow_once",
    "aurelius_atlas_server.tenant_stores.TenantStoreSets.follow",
    "aurelius_atlas_server.tenant_stores.TenantStoreSets.close",
    rules=["WPT-02", "WPT-04"],
)
async def test__the_follower_opens_and_closes_tenants_without_a_request(
    served: tuple[FastAPI, httpx.AsyncClient], record_tenants: Record
) -> None:
    """Globex recorded ``active`` is opened with its workers, acme recorded ``removing`` closed with its workers
    stopped first; the default stays.
    """  # noqa: D205 - one sentence
    app, _ = served
    follower: TenantFollower = app.state.tenant_follower
    acme_workers = workers_of(app).running[tenant_prefix("acme")]
    await record_tenants("globex")
    await record_tenants("acme", state=TenantState.REMOVING)
    tenancy = await follower.follow_once()
    assert tenancy is not None
    assert tenancy.tenants == {"globex"}
    assert set(app.state.tenant_stores) == {INDEX_PREFIX, tenant_prefix("globex")}
    assert set(workers_of(app).running) == {INDEX_PREFIX, tenant_prefix("globex")}
    assert acme_workers.task_worker is not None
    assert acme_workers.task_worker._running is None  # noqa: SLF001 - stopped


@pytest.mark.covers(f"{W}.TenantFollower.start", f"{W}.TenantFollower.stop", rules=["WPT-04"])
async def test__the_follower_reads_every_interval_one_second_at_least_and_survives_a_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An interval of 0 waits a second; a read that fails is logged, and the next one comes."""
    waits: list[float] = []
    reads: list[int] = []
    done = asyncio.Event()

    class Failing:
        async def load(self) -> None:
            reads.append(1)
            if len(reads) == 2:
                done.set()
            raise RuntimeError

    async def sleep(seconds: float) -> None:
        waits.append(seconds)
        await asyncio.sleep(0)

    async def opener(prefix: str) -> Any:  # noqa: ANN401 - never called
        raise AssertionError(prefix)

    sets = TenantStoreSets(opener)
    follower = TenantFollower(Failing(), sets, seconds=0, sleep=sleep)  # type: ignore[arg-type]
    follower.start()
    await asyncio.wait_for(done.wait(), 1)
    await follower.stop()
    await follower.stop()
    assert waits[:2] == [MIN_FOLLOW_SECONDS, MIN_FOLLOW_SECONDS]
    assert "Following the tenants index failed" in caplog.text


@pytest.mark.covers("aurelius_atlas_server.routes.admin.export", rules=["WPT-06"])
async def test__an_export_in_one_tenant_runs_while_another_tenant_holds_its_lock(
    served: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """The default store set's lock held: acme exports, the operator organization is refused."""
    app, client = served
    lock: asyncio.Lock = app.state.tenant_stores[INDEX_PREFIX].import_export_lock
    assert lock is app.state.import_export_lock
    await lock.acquire()
    try:
        acme = await client.post(EXPORT, json={"itemsToExport": []}, headers=member(issuer, "acme"))
        operators = await client.post(EXPORT, json={"itemsToExport": []}, headers=member(issuer, "operators"))
    finally:
        lock.release()
    assert acme.status_code == 200
    assert (operators.status_code, operators.json()["errorCode"]) == (409, "ATLAS-500-00-006")


@pytest.mark.usefixtures("fake_es")
@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["WPT-11"])
async def test__without_tenancy_one_set_of_workers_runs_and_nothing_follows(settings: ServerSettings) -> None:
    """The default store set's workers alone, no follower, and every worker stopped with the server."""
    app = create_app(settings.model_copy(update={"tasks_enabled": True}))
    async with app.router.lifespan_context(app):
        workers = workers_of(app)
        assert (set(workers.running), app.state.tenant_follower) == ({INDEX_PREFIX}, None)
        task_worker = workers.running[INDEX_PREFIX].task_worker
    assert workers.running == {}
    assert task_worker is not None
    assert task_worker._running is None  # noqa: SLF001 - stopped
