"""The store's snapshots: the policy put at start, its runs watched, and the snapshot command (6.4e)."""

import argparse
import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server import snapshots as command
from aurelius_atlas_server.settings import SNAPSHOT_INDICES, StoreAccessSettings
from aurelius_atlas_server.snapshot_watcher import LAST_SUCCESS_GAUGE, SnapshotWatcher
from aurelius_atlas_store_es.snapshots import POLICY, REPOSITORY, SnapshotStatus
from aurelius_atlas_store_es.testing.fake import FakeClient
from opentelemetry.metrics import CallbackOptions
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import Gauge, InMemoryMetricReader

EARLIER = datetime(2026, 11, 4, 10, tzinfo=UTC)
LATER = datetime(2026, 11, 4, 11, tzinfo=UTC)


@pytest.mark.covers("aurelius_atlas_server.settings.ServerSettings.snapshot_policy", rules=["SNP-02"])
def test__snapshots_are_off_and_hourly_for_seven_days_by_default(settings: ServerSettings) -> None:
    """Off unless enabled; when on, every index of the server, every hour, kept seven days."""
    policy = settings.snapshot_policy()

    assert not settings.snapshot_enabled
    assert (policy.indices, policy.location) == (SNAPSHOT_INDICES, "aurelius-atlas")
    assert SNAPSHOT_INDICES == ("aurelius-atlas-*",)
    assert (policy.schedule, policy.expire_after, policy.min_count, policy.max_count) == ("0 0 * * * ?", "7d", 24, 200)


@pytest.mark.covers("aurelius_atlas_server.app._snapshots", rules=["SNP-01", "SNP-03"])
async def test__the_server_puts_the_policy_and_watches_it_when_snapshots_are_enabled(
    settings: ServerSettings, fake_es: FakeClient
) -> None:
    """Disabled, the store gets no repository; enabled, the repository and policy, and a watcher that reads it."""
    disabled = create_app(settings)
    async with disabled.router.lifespan_context(disabled):
        assert fake_es.repositories == {}

    enabled = settings.model_copy(update={"snapshot_enabled": True, "snapshot_schedule": "0 30 * * * ?"})
    app = create_app(enabled)
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0)
        assert fake_es.repositories[REPOSITORY]["settings"] == {"location": "aurelius-atlas"}
        assert fake_es.policies[POLICY]["policy"]["schedule"] == "0 30 * * * ?"
        assert fake_es.policies[POLICY]["policy"]["config"]["indices"] == ["aurelius-atlas-*"]


@pytest.mark.covers(
    "aurelius_atlas_server.snapshot_watcher.SnapshotWatcher.check",
    "aurelius_atlas_server.snapshot_watcher.SnapshotWatcher.run",
    "aurelius_atlas_server.snapshot_watcher.SnapshotWatcher.start",
    "aurelius_atlas_server.snapshot_watcher.SnapshotWatcher.stop",
    rules=["SNP-03"],
)
async def test__the_watcher_checks_at_start_then_every_interval_and_logs_a_failed_run(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failure after the last success is logged as an error; a status it cannot read is logged and forgotten."""
    answers: list[SnapshotStatus | Exception] = [
        SnapshotStatus(EARLIER, "first", None, None),
        SnapshotStatus(EARLIER, "first", LATER, "repository is full"),
        RuntimeError("store down"),
    ]
    slept: list[float] = []
    done = asyncio.Event()

    async def read() -> SnapshotStatus:
        answer = answers.pop(0)
        if not answers:
            done.set()
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        await asyncio.sleep(0)

    watcher = SnapshotWatcher(read, interval_minutes=15, sleep=sleep)
    with caplog.at_level(logging.ERROR, logger="aurelius-atlas-server"):
        watcher.start()
        await asyncio.wait_for(done.wait(), 1)
        await asyncio.sleep(0)
        await watcher.stop()
        await watcher.stop()

    assert slept[:2] == [900, 900]
    assert watcher.status is None
    messages = [record.getMessage() for record in caplog.records]
    assert any("The last snapshot failed" in message and "repository is full" in message for message in messages)
    assert "Reading the snapshot policy failed" in messages


@pytest.mark.covers(
    "aurelius_atlas_server.snapshot_watcher.SnapshotWatcher.register",
    "aurelius_atlas_server.snapshot_watcher.SnapshotWatcher.observe",
    rules=["SNP-03"],
)
async def test__the_gauge_reports_the_last_success_while_the_watcher_runs() -> None:
    """Seconds since the epoch of the last success; nothing before a success or once stopped."""
    status = SnapshotStatus(None, None, None, None)

    async def read() -> SnapshotStatus:
        return status

    reader = InMemoryMetricReader()
    watcher = SnapshotWatcher(read, interval_minutes=15)
    watcher.register(MeterProvider(metric_readers=[reader]).get_meter("test"))

    watcher.start()
    await asyncio.sleep(0)
    assert list(watcher.observe(CallbackOptions())) == []

    status = SnapshotStatus(LATER, "second", EARLIER, "earlier")
    await watcher.check()
    data = reader.get_metrics_data()
    assert data is not None
    [metric] = [m for rm in data.resource_metrics for sm in rm.scope_metrics for m in sm.metrics]
    assert (metric.name, metric.unit) == (LAST_SUCCESS_GAUGE, "s")
    assert isinstance(metric.data, Gauge)
    assert [point.value for point in metric.data.data_points] == [LATER.timestamp()]

    await watcher.stop()
    assert list(watcher.observe(CallbackOptions())) == []


@pytest.fixture
def store_environment(monkeypatch: pytest.MonkeyPatch, ca_file: Path) -> None:
    """The store's settings in the environment, as the server's image and the restore Job set them."""
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_HOSTS", '["https://localhost:9200"]')
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD", "test-password")
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_CA_CERTS", str(ca_file))


async def _catalogue(fake: FakeClient) -> None:
    await fake.indices.create(index="aurelius-atlas-entities-000001", aliases={"aurelius-atlas-entities": {}})
    await fake.index(index="aurelius-atlas-entities", id="e", document={"name": "kept"})
    await fake.slm.put_lifecycle(
        policy_id=POLICY, repository=REPOSITORY, config={"indices": list(SNAPSHOT_INDICES)}, schedule="0 0 * * * ?"
    )
    await fake.snapshot.create_repository(name=REPOSITORY, repository={"type": "fs"})


@pytest.mark.covers("aurelius_atlas_server.snapshots.main", rules=["SNP-04", "SNP-05"])
@pytest.mark.covers("aurelius_atlas_server.snapshots.parser")
@pytest.mark.usefixtures("store_environment")
def test__the_command_takes_lists_and_restores_a_snapshot(
    fake_es: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """``take`` prints the name, ``list`` the snapshots, ``restore --replace`` brings the indices back."""
    asyncio.run(_catalogue(fake_es))

    assert command.main(["take"]) == 0
    assert command.main(["list"]) == 0
    fake_es.documents["aurelius-atlas-entities-000001"].clear()
    assert command.main(["restore", "--replace"]) == 0

    out = capsys.readouterr().out.splitlines()
    assert out[0] == "snapshot-1"
    assert out[1].startswith("snapshot-1\tSUCCESS\t2023-11-14T22:13:20+00:00\t1")
    assert out[2].startswith("Restored snapshot-1: 1 indices in ")
    assert out[2].endswith(" s (1 deleted first)")
    assert "e" in fake_es.documents["aurelius-atlas-entities-000001"]


@pytest.mark.covers("aurelius_atlas_server.snapshots.main", rules=["SNP-05"])
@pytest.mark.covers("aurelius_atlas_server.snapshots.run")
@pytest.mark.usefixtures("store_environment")
def test__a_restore_into_a_store_in_use_is_refused_without_replace(
    fake_es: FakeClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """The command fails with the reason, and the store keeps its indices."""
    asyncio.run(_catalogue(fake_es))
    assert command.main(["take"]) == 0

    assert command.main(["restore", "--snapshot", "snapshot-1"]) == 1

    assert "already holds aurelius-atlas-entities-000001" in capsys.readouterr().err
    assert "aurelius-atlas-entities-000001" in fake_es.documents


@pytest.mark.usefixtures("store_environment")
async def test__the_command_needs_only_the_store_s_settings(fake_es: FakeClient) -> None:
    """No TLS pair or identity provider: the restore Job sets the store's settings alone."""
    settings = StoreAccessSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    lines: list[str] = []
    await _catalogue(fake_es)

    await command.run(argparse.Namespace(command="list"), settings, lines.append)

    assert lines == []
