"""Propagation tasks over HTTP (TSK-06, TSK-07) and the worker that runs them (TSK-04, DD-080).

Read from ``AdminResource`` (``getTaskStatus``, ``deleteTask``) and ``EntityGraphMapper`` of Apache Atlas 2.4.0; the
task rules themselves are tested on ``TaskManagement`` in ``aurelius-atlas-core``.
"""

import asyncio
import logging
from typing import Any

import httpx
import pytest
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.testing.entity_samples import CLASSIFICATION_TYPES, SAMPLE_TYPES
from aurelius_atlas_server import ServerSettings
from aurelius_atlas_server.task_worker import TaskWorker
from fastapi import FastAPI

# The worker runs on the loop the application started on, the module's (asyncio_default_fixture_loop_scope).
pytestmark = pytest.mark.asyncio(loop_scope="module")

A = "aurelius_atlas_server.routes.admin"
W = "aurelius_atlas_server.task_worker.TaskWorker"
ENTITY = "/api/atlas/v2/entity"
TASKS = "/api/atlas/admin/tasks"


@pytest.fixture
def settings(settings: ServerSettings) -> ServerSettings:
    """The test settings with tasks enabled, as a server runs by default (DD-081)."""
    return settings.model_copy(update={"tasks_enabled": True})


async def lineage(client: httpx.AsyncClient) -> dict[str, str]:
    """``a -> p -> b`` of the classification sample types; the GUIDs by name."""
    for types in (SAMPLE_TYPES, CLASSIFICATION_TYPES):
        created = await client.post("/api/atlas/v2/types/typedefs", json=types)
        assert created.status_code == 200, created.text
    body: dict[str, Any] = {
        "entities": [
            {"typeName": "p_data", "guid": "-a", "attributes": {"qualifiedName": "a"}},
            {"typeName": "p_data", "guid": "-b", "attributes": {"qualifiedName": "b"}},
            {
                "typeName": "p_process",
                "guid": "-p",
                "attributes": {"qualifiedName": "p"},
                "relationshipAttributes": {"inputs": [{"guid": "-a"}], "outputs": [{"guid": "-b"}]},
            },
        ]
    }
    response = await client.post(f"{ENTITY}/bulk", json=body)
    return {key.removeprefix("-"): guid for key, guid in response.json()["guidAssignments"].items()}


async def drained(client: httpx.AsyncClient) -> None:
    """Wait until the worker has run every task."""
    for _ in range(200):
        if (await client.get(TASKS)).json() == []:
            return
        await asyncio.sleep(0.01)
    pytest.fail(f"the tasks did not run: {(await client.get(TASKS)).json()}")


async def names(client: httpx.AsyncClient, guid: str) -> list[str]:
    """The classification type names the entity lists."""
    return [c["typeName"] for c in (await client.get(f"{ENTITY}/guid/{guid}/classifications")).json()["list"]]


@pytest.mark.covers(
    f"{A}.get_task_status",
    f"{A}.get_session",
    f"{W}.wake",
    f"{W}.start",
    "aurelius_atlas_server.routes.entity.tasks_enabled",
    "aurelius_atlas_server.routes.entity.classifications",
    rules=["TSK-04", "TSK-06", "TSK-07"],
)
async def test__a_classification_propagates_after_the_request_through_its_task(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """``a`` lists the task until the worker ran it; then ``b`` has ``c_pii`` and no task is left."""
    guids = await lineage(client)
    management: TaskManagement = app.state.task_management
    run_pending, held = management.run_pending, True

    async def hold() -> int:
        return 0 if held else await run_pending()

    management.run_pending = hold
    added = await client.post(f"{ENTITY}/guid/{guids['a']}/classifications", json=[{"typeName": "c_pii"}])
    waiting = (await client.get(TASKS)).json()
    pending = (await client.get(f"{ENTITY}/guid/{guids['a']}")).json()["entity"].get("pendingTasks")
    by_guid = (await client.get(TASKS, params={"guids": [waiting[0]["guid"], "nope"]})).json()
    before = await names(client, guids["b"])
    held = False
    app.state.task_worker.wake()
    await drained(client)

    assert added.status_code == 204
    assert [(t["type"], t["status"], t["parameters"]["entityGuid"]) for t in waiting] == [
        ("CLASSIFICATION_PROPAGATION_ADD", "PENDING", guids["a"])
    ]
    assert pending == [waiting[0]["guid"]]
    assert by_guid == waiting
    assert before == []
    assert await names(client, guids["b"]) == ["c_pii"]
    assert "pendingTasks" not in (await client.get(f"{ENTITY}/guid/{guids['a']}")).json()["entity"]
    assert (await client.get("/api/atlas/admin/session")).json()["atlas.tasks.enabled"] is True


@pytest.mark.covers(f"{A}.delete_task", rules=["TSK-06"])
async def test__tasks_are_deleted_by_guid(client: httpx.AsyncClient, app: FastAPI) -> None:
    """``204``, with or without ``guids``; the deleted task is gone."""
    guids = await lineage(client)
    management: TaskManagement = app.state.task_management

    async def nothing() -> int:
        return 0

    management.run_pending = nothing
    await client.post(f"{ENTITY}/guid/{guids['a']}/classifications", json=[{"typeName": "c_pii"}])
    waiting = (await client.get(TASKS)).json()

    none = await client.delete(TASKS)
    some = await client.delete(TASKS, params={"guids": [waiting[0]["guid"]]})

    assert (none.status_code, some.status_code) == (204, 204)
    assert (await client.get(TASKS)).json() == []


@pytest.mark.covers(f"{W}.run_once", f"{W}.stop", rules=["TSK-04"])
async def test__a_round_that_fails_is_logged_and_the_worker_goes_on(caplog: pytest.LogCaptureFixture) -> None:
    """A store that fails is logged and counts no task; stopping before starting is fine."""

    class Failing:
        async def run_pending(self) -> int:
            message = "store down"
            raise RuntimeError(message)

    worker = TaskWorker(Failing(), poll_seconds=60)  # type: ignore[arg-type]
    await worker.stop()

    with caplog.at_level(logging.ERROR, logger="aurelius-atlas-server"):
        ran = await worker.run_once()

    assert ran == 0
    assert "Running the pending tasks failed" in caplog.text


@pytest.mark.covers(f"{W}.start", f"{W}.stop", rules=["TSK-04"])
async def test__the_worker_looks_again_after_its_poll_interval() -> None:
    """Without a wake, it runs again once ``poll_seconds`` passed."""
    rounds: list[int] = []

    class Counting:
        async def run_pending(self) -> int:
            rounds.append(1)
            return 0

    worker = TaskWorker(Counting(), poll_seconds=0.01)  # type: ignore[arg-type]
    worker.start()
    for _ in range(100):
        if len(rounds) >= 3:
            break
        await asyncio.sleep(0.01)
    await worker.stop()

    assert len(rounds) >= 3
