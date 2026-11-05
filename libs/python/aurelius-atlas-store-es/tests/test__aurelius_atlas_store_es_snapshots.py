"""Snapshots: the repository, the lifecycle policy, its status, a snapshot on request and a restore (6.4e)."""

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from aurelius_atlas_store_es.snapshots import (
    POLICY,
    REPOSITORY,
    SnapshotError,
    SnapshotPolicy,
    SnapshotStatus,
    list_snapshots,
    prepare_snapshots,
    restore,
    snapshot_status,
    take_snapshot,
)
from aurelius_atlas_store_es.testing.fake import FakeClient, response_meta
from elasticsearch import AsyncElasticsearch, NotFoundError

POLICY_INDICES = ("catalogue-*",)
MISSING = "snapshot_missing_exception"


def es(fake: FakeClient) -> AsyncElasticsearch:
    """The fake where the module expects a client."""
    return cast("AsyncElasticsearch", fake)


async def catalogue(fake: FakeClient) -> None:
    """Two indices of the catalogue, behind their aliases, with a document each, and an index of someone else."""
    for name in ("entities", "audits"):
        await fake.indices.create(index=f"catalogue-{name}-000001", aliases={f"catalogue-{name}": {}})
        await fake.index(index=f"catalogue-{name}", id="d", document={"name": name})
    await fake.indices.create(index="other-000001")


@pytest.mark.covers("aurelius_atlas_store_es.snapshots.prepare_snapshots", rules=["SNP-01", "SNP-02"])
@pytest.mark.covers("aurelius_atlas_store_es.snapshots.prepare_repository", rules=["SNP-01"])
async def test__the_policy_snapshots_the_indices_on_its_schedule_and_keeps_them_for_its_retention() -> None:
    """A shared-filesystem repository, and a policy of the indices with their aliases and without global state."""
    fake = FakeClient()

    await prepare_snapshots(es(fake), SnapshotPolicy(indices=POLICY_INDICES, location="here"))

    assert fake.repositories[REPOSITORY] == {"type": "fs", "settings": {"location": "here"}}
    assert fake.policies[POLICY]["policy"] == {
        "name": "<aurelius-atlas-{now/m{yyyy.MM.dd-HH.mm}}>",
        "schedule": "0 0 * * * ?",
        "repository": REPOSITORY,
        "config": {"indices": ["catalogue-*"], "include_global_state": False},
        "retention": {"expire_after": "7d", "min_count": 24, "max_count": 200},
    }


@pytest.mark.covers("aurelius_atlas_store_es.snapshots.snapshot_status", rules=["SNP-03"])
@pytest.mark.covers("aurelius_atlas_store_es.snapshots.SnapshotStatus.failing", rules=["SNP-03"])
async def test__the_status_names_the_last_success_and_the_last_failure() -> None:
    """Before any run there is neither; a failure after the last success is failing, a success after it is not."""
    fake = FakeClient()
    await catalogue(fake)
    await prepare_snapshots(es(fake), SnapshotPolicy(indices=POLICY_INDICES))
    at = datetime.fromtimestamp(fake.now_millis / 1000, tz=UTC)

    assert await snapshot_status(es(fake)) == SnapshotStatus(None, None, None, None)

    await take_snapshot(es(fake))
    fake.now_millis += 1000
    fake.snapshot_error = "repository is full"
    await fake.slm.execute_lifecycle(policy_id=POLICY)
    failing = await snapshot_status(es(fake))

    assert (failing.last_success, failing.last_success_name) == (at, "snapshot-1")
    assert failing.last_failure_details == "repository is full"
    assert failing.failing
    assert not SnapshotStatus(failing.last_failure, "later", at, "earlier").failing


@pytest.mark.covers("aurelius_atlas_store_es.snapshots.take_snapshot", rules=["SNP-04"])
@pytest.mark.covers("aurelius_atlas_store_es.snapshots.list_snapshots")
async def test__a_snapshot_on_request_waits_until_it_has_finished() -> None:
    """The policy runs now; the snapshot holds the policy's indices; the repository lists it."""
    fake = FakeClient()
    await catalogue(fake)

    assert await list_snapshots(es(fake)) == []

    await prepare_snapshots(es(fake), SnapshotPolicy(indices=POLICY_INDICES))
    name = await take_snapshot(es(fake))
    [listed] = await list_snapshots(es(fake))

    assert (listed.name, listed.state) == (name, "SUCCESS")
    assert listed.indices == ("catalogue-audits-000001", "catalogue-entities-000001")


@pytest.mark.covers("aurelius_atlas_store_es.snapshots.take_snapshot", rules=["SNP-04"])
async def test__a_snapshot_still_running_is_waited_for_and_a_failed_one_raises() -> None:
    """The snapshot is polled until it has finished, missing at first; only ``SUCCESS`` counts."""
    fake = FakeClient()
    await catalogue(fake)
    await prepare_snapshots(es(fake), SnapshotPolicy(indices=POLICY_INDICES))
    states = iter([None, "IN_PROGRESS", "FAILED"])
    sleeps: list[float] = []

    async def get(**_: object) -> dict[str, Any]:
        state = next(states)
        if state is None:
            raise NotFoundError(MISSING, response_meta(404), {})
        return {"snapshots": [{"state": state}]}

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)

    fake.snapshot.get = get
    with pytest.raises(SnapshotError, match="ended FAILED"):
        await take_snapshot(es(fake), sleep=sleep)
    assert sleeps == [1.0, 1.0]


@pytest.mark.covers("aurelius_atlas_store_es.snapshots.restore", rules=["SNP-05"])
async def test__a_restore_brings_back_the_newest_snapshot_into_an_empty_store() -> None:
    """The repository registered on the clean store; the indices back with their aliases and documents."""
    taken = FakeClient()
    await catalogue(taken)
    await prepare_snapshots(es(taken), SnapshotPolicy(indices=POLICY_INDICES, location="shared"))
    await take_snapshot(es(taken))
    await taken.index(index="catalogue-entities", id="later", document={"name": "later"})
    await take_snapshot(es(taken))
    clean = FakeClient()
    clean.repositories, clean.snapshots = {}, taken.snapshots
    ticks = iter([10.0, 12.5])

    result = await restore(es(clean), indices=POLICY_INDICES, location="shared", clock=lambda: next(ticks))

    assert clean.repositories[REPOSITORY]["settings"] == {"location": "shared"}
    assert result.snapshot == "snapshot-2"
    assert result.restored == ("catalogue-audits-000001", "catalogue-entities-000001")
    assert (result.deleted, result.seconds) == ((), 2.5)
    assert clean.aliases == {
        "catalogue-entities": "catalogue-entities-000001",
        "catalogue-audits": "catalogue-audits-000001",
    }
    assert (await clean.get(index="catalogue-entities", id="later"))["_source"] == {"name": "later"}


@pytest.mark.covers("aurelius_atlas_store_es.snapshots.restore", rules=["SNP-05"])
async def test__a_restore_into_a_store_that_holds_the_indices_needs_replace() -> None:
    """Refused by default; with replace, the store's indices are deleted, newer ones too, and the snapshot's back."""
    fake = FakeClient()
    await catalogue(fake)
    await prepare_snapshots(es(fake), SnapshotPolicy(indices=POLICY_INDICES))
    first = await take_snapshot(es(fake))
    await fake.index(index="catalogue-entities", id="lost", document={"name": "lost"})
    await fake.indices.create(index="catalogue-new-000001", aliases={"catalogue-new": {}})

    with pytest.raises(SnapshotError, match="already holds catalogue-audits-000001"):
        await restore(es(fake), indices=POLICY_INDICES, location="aurelius-atlas", snapshot=first)
    result = await restore(es(fake), indices=POLICY_INDICES, location="aurelius-atlas", snapshot=first, replace=True)

    assert result.deleted == ("catalogue-audits-000001", "catalogue-entities-000001", "catalogue-new-000001")
    assert "catalogue-new" not in fake.aliases
    assert "other-000001" in fake.documents
    assert "lost" not in fake.documents["catalogue-entities-000001"]


async def test__a_restore_needs_a_successful_snapshot_and_every_shard() -> None:
    """An empty repository has nothing to restore; a failed shard fails the restore."""
    fake = FakeClient()

    with pytest.raises(SnapshotError, match="no successful snapshot"):
        await restore(es(fake), indices=POLICY_INDICES, location="aurelius-atlas")

    await catalogue(fake)
    await prepare_snapshots(es(fake), SnapshotPolicy(indices=POLICY_INDICES))
    name = await take_snapshot(es(fake))

    async def partly(**_: object) -> dict[str, Any]:
        return {"snapshot": {"indices": [], "shards": {"total": 2, "failed": 1}}}

    fake.snapshot.restore = partly
    with pytest.raises(SnapshotError, match="failed for 1 of 2 shards"):
        await restore(es(fake), indices=POLICY_INDICES, location="aurelius-atlas", snapshot=name, replace=True)
