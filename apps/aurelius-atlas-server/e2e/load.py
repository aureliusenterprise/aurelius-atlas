"""The load driver of the server's load test (LOD-01, LOD-02): concurrent users through a mix of requests.

No load-testing framework: the users are asyncio tasks on one ``httpx`` client, each looping through the mix
until the run's time is up, and every request is a sample of its operation, its status and its duration.
"""

# ruff: noqa: INP001 - a helper module beside the e2e tests, imported by them

import asyncio
import math
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx2 as httpx

Request = Callable[[httpx.AsyncClient, int, int], Awaitable[httpx.Response]]
"""One operation of the mix: sends its request as a user (the second argument) on its turn (the third)."""

ENTITY = "/api/atlas/v2/entity"


@dataclass(frozen=True)
class Sample:
    """One request of a run: its operation, its status (0 when it got no answer) and its duration."""

    operation: str
    status: int
    millis: float

    @property
    def ok(self) -> bool:
        """Whether the server answered with a success (LOD-02)."""
        return 200 <= self.status < 300  # noqa: PLR2004 - the success range


@dataclass(frozen=True)
class OperationReport:
    """The samples of one operation: how many, how many failed, and their durations' percentiles (LOD-02)."""

    operation: str
    count: int
    failures: int
    p50: float
    p95: float
    max_millis: float

    def as_dict(self) -> dict[str, Any]:
        """The report as JSON, its durations in whole milliseconds."""
        return {
            "operation": self.operation,
            "count": self.count,
            "failures": self.failures,
            "p50": round(self.p50),
            "p95": round(self.p95),
            "max": round(self.max_millis),
        }


def percentile(values: Sequence[float], fraction: float) -> float:
    """The nearest-rank percentile: the smallest value at least ``fraction`` of the values reach; 0 for none."""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(math.ceil(fraction * len(ordered)) - 1, 0)]


def report(samples: Sequence[Sample]) -> list[OperationReport]:
    """Each operation's report, by operation name (LOD-02)."""
    by_operation: dict[str, list[Sample]] = {}
    for sample in samples:
        by_operation.setdefault(sample.operation, []).append(sample)
    reports = []
    for operation, found in sorted(by_operation.items()):
        millis = [sample.millis for sample in found]
        failures = sum(not sample.ok for sample in found)
        reports.append(
            OperationReport(
                operation, len(found), failures, percentile(millis, 0.5), percentile(millis, 0.95), max(millis)
            )
        )
    return reports


async def drive(
    client: httpx.AsyncClient,
    mix: Sequence[tuple[str, Request]],
    *,
    users: int,
    seconds: float,
    clock: Callable[[], float] = time.monotonic,
) -> list[Sample]:
    """Run ``users`` users for ``seconds``, each through the mix in turn from its own offset (LOD-01).

    A request the server does not answer is a sample of status 0; the run goes on.
    """
    deadline = clock() + seconds
    samples: list[Sample] = []

    async def user(number: int) -> None:
        turn = number
        while clock() < deadline:
            operation, request = mix[turn % len(mix)]
            start = clock()
            try:
                status = (await request(client, number, turn)).status_code
            except httpx.HTTPError:
                status = 0
            samples.append(Sample(operation, status, (clock() - start) * 1000))
            turn += 1

    async with asyncio.TaskGroup() as group:
        for number in range(users):
            group.create_task(user(number))
    return samples


def atlas_mix(type_name: str, guids: Sequence[str], created: list[str]) -> list[tuple[str, Request]]:
    """The mix of the server's load test (LOD-01): reads, two searches, an update and a create.

    Reads take any of the seeded ``guids``; a user updates only its own seeded entity, so no two users write
    one entity at once; the guids of the entities created are added to ``created``, for the clean-up.
    """

    async def read(client: httpx.AsyncClient, _user: int, turn: int) -> httpx.Response:
        return await client.get(f"{ENTITY}/guid/{guids[turn % len(guids)]}")

    async def basic_search(client: httpx.AsyncClient, _user: int, _turn: int) -> httpx.Response:
        return await client.post("/api/atlas/v2/search/basic", json={"typeName": type_name, "limit": 10})

    async def quick_search(client: httpx.AsyncClient, _user: int, _turn: int) -> httpx.Response:
        params = {"query": "*", "typeName": type_name, "limit": 10}
        return await client.get("/api/atlas/v2/search/quick", params=params)

    async def update(client: httpx.AsyncClient, user: int, turn: int) -> httpx.Response:
        attributes = {"qualifiedName": f"{type_name}-seed-{user}", "name": f"seed {user}", "description": str(turn)}
        return await client.post(ENTITY, json={"entity": {"typeName": type_name, "attributes": attributes}})

    async def create(client: httpx.AsyncClient, user: int, turn: int) -> httpx.Response:
        attributes = {"qualifiedName": f"{type_name}-{user}-{turn}", "name": f"created {user} {turn}"}
        response = await client.post(ENTITY, json={"entity": {"typeName": type_name, "attributes": attributes}})
        if response.is_success:
            created.extend(header["guid"] for header in response.json()["mutatedEntities"]["CREATE"])
        return response

    return [
        ("read", read),
        ("basic search", basic_search),
        ("quick search", quick_search),
        ("update", update),
        ("create", create),
    ]
