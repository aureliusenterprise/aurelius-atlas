"""Snapshots of the store's indices: a repository, a schedule, and a restore (SNP-01 to SNP-06, ADR 026).

Elasticsearch's own snapshot lifecycle management takes the snapshots, keeps them for their retention and
deletes them after it, so the schedule runs inside the store whether or not a server is up. This module
registers the repository and the policy, reads how the last runs went, and restores a snapshot into a store.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError

from .errors import StoreError

REPOSITORY = "aurelius-atlas-snapshots"
"""The snapshot repository's name, on every cluster that holds or restores the snapshots."""

POLICY = "aurelius-atlas-snapshots"
"""The snapshot lifecycle policy's id."""

SNAPSHOT_NAME = "<aurelius-atlas-{now/m{yyyy.MM.dd-HH.mm}}>"
"""Each snapshot's name: its minute in UTC; Elasticsearch appends a unique suffix."""

FINISHED_STATES = frozenset({"SUCCESS", "PARTIAL", "FAILED", "INCOMPATIBLE"})
"""The states of a snapshot that is no longer running."""

SNAPSHOT_POLL_SECONDS = 1.0
"""How often ``take_snapshot`` asks whether its snapshot has finished."""

NO_SNAPSHOT_ERROR = "The repository holds no successful snapshot"
STORE_NOT_EMPTY_ERROR = "The store already holds {indices}; restore with replace to delete them first"
SNAPSHOT_FAILED_ERROR = "Snapshot {name} ended {state}"
RESTORE_FAILED_ERROR = "Restoring {name} failed for {failed} of {total} shards"


class SnapshotError(StoreError):
    """A snapshot or a restore did not complete."""


@dataclass(frozen=True)
class SnapshotPolicy:
    """What is snapshotted, where, how often and for how long (SNP-01, SNP-02).

    ``schedule`` is an Elasticsearch cron expression in UTC; ``expire_after`` a time unit such as ``7d``. A
    snapshot past it is deleted, except that the newest ``min_count`` are always kept and never more than
    ``max_count``.
    """

    indices: tuple[str, ...]
    location: str = "aurelius-atlas"
    schedule: str = "0 0 * * * ?"
    expire_after: str = "7d"
    min_count: int = 24
    max_count: int = 200


@dataclass(frozen=True)
class Snapshot:
    """One snapshot in the repository."""

    name: str
    state: str
    started: datetime
    indices: tuple[str, ...]


@dataclass(frozen=True)
class SnapshotStatus:
    """How the policy's last runs went (SNP-03); a time is None when there was no such run."""

    last_success: datetime | None
    last_success_name: str | None
    last_failure: datetime | None
    last_failure_details: str | None

    @property
    def failing(self) -> bool:
        """Whether the last run failed: a failure later than the last success."""
        return self.last_failure is not None and (self.last_success is None or self.last_failure > self.last_success)


def _time(millis: int | None) -> datetime | None:
    return None if millis is None else datetime.fromtimestamp(millis / 1000, tz=UTC)


async def prepare_repository(client: AsyncElasticsearch, location: str) -> None:
    """Register the shared-filesystem repository at ``location``, below the node's ``path.repo`` (SNP-01).

    Registering it again with the same location changes nothing; the node verifies it can write there.
    """
    await client.snapshot.create_repository(
        name=REPOSITORY, repository={"type": "fs", "settings": {"location": location}}
    )


async def prepare_snapshots(client: AsyncElasticsearch, policy: SnapshotPolicy) -> None:
    """Register the repository and put the lifecycle policy that snapshots ``policy.indices`` (SNP-01, SNP-02).

    The snapshots hold the indices with their aliases, not the cluster's global state.
    """
    await prepare_repository(client, policy.location)
    await client.slm.put_lifecycle(
        policy_id=POLICY,
        name=SNAPSHOT_NAME,
        schedule=policy.schedule,
        repository=REPOSITORY,
        config={"indices": list(policy.indices), "include_global_state": False},
        retention={
            "expire_after": policy.expire_after,
            "min_count": policy.min_count,
            "max_count": policy.max_count,
        },
    )


async def snapshot_status(client: AsyncElasticsearch) -> SnapshotStatus:
    """The policy's last success and last failure (SNP-03)."""
    answer = (await client.slm.get_lifecycle(policy_id=POLICY))[POLICY]
    success: dict[str, Any] = answer.get("last_success") or {}
    failure: dict[str, Any] = answer.get("last_failure") or {}
    return SnapshotStatus(
        last_success=_time(success.get("time")),
        last_success_name=success.get("snapshot_name"),
        last_failure=_time(failure.get("time")),
        last_failure_details=failure.get("details"),
    )


async def list_snapshots(client: AsyncElasticsearch) -> list[Snapshot]:
    """The repository's snapshots, oldest first; none when it holds none."""
    try:
        answer = await client.snapshot.get(repository=REPOSITORY, snapshot="_all", sort="start_time")
    except NotFoundError:
        return []
    return [
        Snapshot(
            name=item["snapshot"],
            state=item["state"],
            started=datetime.fromtimestamp(item["start_time_in_millis"] / 1000, tz=UTC),
            indices=tuple(item.get("indices", ())),
        )
        for item in answer["snapshots"]
    ]


async def take_snapshot(
    client: AsyncElasticsearch,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> str:
    """Run the policy now, outside its schedule, and wait for the snapshot to finish; return its name (SNP-04).

    Raises:
        SnapshotError: When the snapshot ends other than ``SUCCESS``.
    """
    name = (await client.slm.execute_lifecycle(policy_id=POLICY))["snapshot_name"]
    while True:
        try:
            [snapshot] = (await client.snapshot.get(repository=REPOSITORY, snapshot=name))["snapshots"]
        except NotFoundError:
            snapshot = {"state": "IN_PROGRESS"}
        if snapshot["state"] in FINISHED_STATES:
            break
        await sleep(SNAPSHOT_POLL_SECONDS)
    if snapshot["state"] != "SUCCESS":
        raise SnapshotError(SNAPSHOT_FAILED_ERROR.format(name=name, state=snapshot["state"]))
    return name


@dataclass(frozen=True)
class RestoreResult:
    """What a restore did: the snapshot, the indices it deleted first and restored, and how long it took."""

    snapshot: str
    deleted: tuple[str, ...]
    restored: tuple[str, ...]
    seconds: float


async def restore(  # noqa: PLR0913 - the restore's choices, each a keyword
    client: AsyncElasticsearch,
    *,
    indices: Sequence[str],
    location: str,
    snapshot: str | None = None,
    replace: bool = False,
    clock: Callable[[], float] = time.monotonic,
) -> RestoreResult:
    """Restore ``indices`` with their aliases from ``snapshot``, by default the newest successful one (SNP-05).

    The repository is registered at ``location`` first, so a clean cluster can restore. A store that already
    holds any of ``indices`` is refused unless ``replace``, which deletes them before the restore; indices of
    the store that the snapshot does not hold are deleted too, so the store comes back as it was.

    Raises:
        SnapshotError: When there is no snapshot to restore, the store is not empty, or a shard fails.
    """
    started = clock()
    await prepare_repository(client, location)
    if snapshot is None:
        successful = [item for item in await list_snapshots(client) if item.state == "SUCCESS"]
        if not successful:
            raise SnapshotError(NO_SNAPSHOT_ERROR)
        snapshot = successful[-1].name
    pattern = ",".join(indices)
    existing = tuple(sorted(await client.indices.get(index=pattern, expand_wildcards="all", ignore_unavailable=True)))
    if existing and not replace:
        raise SnapshotError(STORE_NOT_EMPTY_ERROR.format(indices=", ".join(existing)))
    if existing:
        await client.indices.delete(index=",".join(existing))
    answer = await client.snapshot.restore(
        repository=REPOSITORY,
        snapshot=snapshot,
        indices=pattern,
        include_aliases=True,
        include_global_state=False,
        wait_for_completion=True,
    )
    shards = answer["snapshot"]["shards"]
    if shards["failed"]:
        raise SnapshotError(RESTORE_FAILED_ERROR.format(name=snapshot, failed=shards["failed"], total=shards["total"]))
    return RestoreResult(
        snapshot=snapshot,
        deleted=existing,
        restored=tuple(answer["snapshot"]["indices"]),
        seconds=clock() - started,
    )
