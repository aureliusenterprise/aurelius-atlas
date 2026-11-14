"""``GET /api/atlas/admin/metricsstats``, ``metricsstat/{collectionTime}``, ``metricsstats/range`` and
``metricsstats/charts``, and the metrics' schedule (MHS-01 to MHS-05), as Apache Atlas 2.4.0's ``AdminResource``.
"""  # noqa: D205 - one sentence

import asyncio
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_core.metrics_service import MetricsService
from aurelius_atlas_server.metrics_scheduler import MetricsScheduler
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.tenant_workers import metrics_schedule
from base_models import base_models
from fastapi import FastAPI

ADMIN = "/api/atlas/admin"


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model: the metrics are stored as ``__AtlasMetricsStat`` entities (MHS-01)."""
    return base_models(tmp_path)


async def saved(app: FastAPI) -> int:
    """The collection time of the metrics of now, stored."""
    settings: ServerSettings = app.state.settings
    service = MetricsService(app.state.entity_store, app.state.metrics_util, namespace=settings.cluster_name)
    return (await service.save_metrics(store_connected=True)).collection_time


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_all_metrics", rules=["MHS-02"])
@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_metrics_by_collection_time", rules=["MHS-02"])
async def test__the_stored_metrics_are_listed_and_read_by_time(app: FastAPI, client: httpx.AsyncClient) -> None:
    """``mininfo``, by default, leaves out the metrics; a time not stored is not found, text is no time."""
    collected = await saved(app)

    brief = await client.get(f"{ADMIN}/metricsstats")
    full = await client.get(f"{ADMIN}/metricsstats", params={"mininfo": "FALSE"})
    found = await client.get(f"{ADMIN}/metricsstat/{collected}")
    missing = await client.get(f"{ADMIN}/metricsstat/5")
    text = await client.get(f"{ADMIN}/metricsstat/x")

    [stat] = brief.json()
    assert (stat["collectionTime"], stat["metricsId"], "metrics" in stat) == (
        collected,
        f"atlas_metrics_{collected}@default",
        False,
    )
    assert stat["timeToLiveMillis"] == 336 * 3_600_000
    assert "general" in full.json()[0]["metrics"]["data"]
    assert (found.status_code, found.json()["guid"]) == (200, stat["guid"])
    assert (missing.status_code, missing.json()["errorCode"]) == (404, "ATLAS-404-00-009")
    assert (text.status_code, text.json()["errorMessage"]) == (
        400,
        "Invalid value x for query parameter collectionTime",
    )


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_metrics_in_time_range", rules=["MHS-03"])
@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_metrics_for_chart_by_type_names", rules=["MHS-04"])
async def test__a_range_and_its_charts_answer_the_metrics_between_two_times(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """The type data of the type names; a missing time, one that is not before the end, or text is refused."""
    collected = await saved(app)
    window = {"startTime": str(collected - 1), "endTime": str(collected), "typeName": ["DataSet", "Asset"]}

    ranged = await client.get(f"{ADMIN}/metricsstats/range", params=window)
    charts = await client.get(f"{ADMIN}/metricsstats/charts", params=window)
    blank = await client.get(f"{ADMIN}/metricsstats/range", params={"startTime": " ", "endTime": "1"})
    backwards = await client.get(f"{ADMIN}/metricsstats/charts", params={"startTime": "2", "endTime": "1"})
    text = await client.get(f"{ADMIN}/metricsstats/range", params={"startTime": "1", "endTime": "1.5"})

    [stat] = ranged.json()
    assert stat["typeData"] == {
        "DataSet": {"Active": 0, "Deleted": 0, "Shell": 0},
        "Asset": {"Active": 0, "Deleted": 0, "Shell": 0},
    }
    assert sorted(charts.json()) == ["Asset", "DataSet"]
    assert [series["key"] for series in charts.json()["DataSet"]] == ["Active", "Deleted", "Shell"]
    assert charts.json()["DataSet"][0]["values"] == [[collected, 0]]
    assert (blank.status_code, blank.json()["errorMessage"]) == (400, "startTime or endTime is null/empty.")
    assert (backwards.status_code, backwards.json()["errorCode"]) == (400, "ATLAS-400-00-01A")
    assert text.status_code == 400


@pytest.mark.covers(
    "aurelius_atlas_server.metrics_scheduler.MetricsScheduler.run",
    "aurelius_atlas_server.metrics_scheduler.MetricsScheduler.save_and_purge",
    "aurelius_atlas_server.metrics_scheduler.MetricsScheduler.start",
    "aurelius_atlas_server.metrics_scheduler.MetricsScheduler.stop",
    rules=["MHS-05"],
)
async def test__the_metrics_are_saved_and_purged_on_the_multiples_of_the_interval() -> None:
    """The first run waits for the next multiple; a failure of either step is only logged."""
    slept: list[float] = []
    calls: list[str] = []
    rounds = asyncio.Event()

    class Service(MetricsService):
        def __init__(self) -> None:
            pass

        async def save_metrics(self, *, store_connected: bool):  # noqa: ANN202 - the parent's
            calls.append(f"save {store_connected}")
            raise RuntimeError

        async def purge_metrics_stats(self):  # noqa: ANN202 - the parent's
            calls.append("purge")
            if len(calls) >= 4:
                rounds.set()
            raise RuntimeError

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        await asyncio.sleep(0)

    async def connected() -> bool:
        return False

    scheduler = MetricsScheduler(Service(), connected, interval_minutes=60, clock=lambda: 3_600 * 5 + 600, sleep=sleep)
    scheduler.start()
    await asyncio.wait_for(rounds.wait(), 1)
    await scheduler.stop()
    await scheduler.stop()

    assert slept[:2] == [3_000, 3_000]
    assert calls[:4] == ["save False", "purge", "save False", "purge"]


@pytest.mark.covers("aurelius_atlas_server.tenant_workers.metrics_schedule", rules=["MHS-05"])
async def test__an_interval_of_zero_stores_no_metrics(app: FastAPI, settings: ServerSettings) -> None:
    """Off at 0, else started on the store's health."""
    async with app.router.lifespan_context(app):
        unscheduled = settings.model_copy(update={"metrics_persist_interval_minutes": 0})
        off = metrics_schedule(unscheduled, app.state.store, app.state.metrics_util, app.state.entity_store)
        on = metrics_schedule(settings, app.state.store, app.state.metrics_util, app.state.entity_store)
        assert off is None
        assert on is not None
        await on.stop()
