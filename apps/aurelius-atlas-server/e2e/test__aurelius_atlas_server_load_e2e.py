"""The server under load on the dev store (LOD-01 to LOD-03): concurrent users through reads, searches and writes.

The run is short by default, so CI runs it with the suite; ``AURELIUS_ATLAS_LOAD_USERS``, ``_SECONDS`` and
``_P95_MS`` make it a longer or harder run (``nx e2e aurelius-atlas-server`` with them set). Its report is printed
and recorded as the junit property ``load_report``.

The timed mix rides the raw client: every request is a latency sample, and typed parsing would add CPU the
measurement must not count (DD-813, ECL-01). The run's own seed and clean-up are not timed, so they go through
the typed client (CL-11).
"""

import json
import os
import uuid
from collections.abc import Callable, Sequence
from itertools import batched
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo, EntityOperation
from aurelius_atlas_model.typedef import AtlasEntityDef, AtlasTypesDef
from aurelius_atlas_server_client import AtlasClient
from load import OperationReport, Sample, atlas_mix, drive, percentile, report

USERS = int(os.environ.get("AURELIUS_ATLAS_LOAD_USERS", "8"))
SECONDS = float(os.environ.get("AURELIUS_ATLAS_LOAD_SECONDS", "20"))
P95_MS = float(os.environ.get("AURELIUS_ATLAS_LOAD_P95_MS", "3000"))
"""The budget of every operation's 95th percentile (LOD-03). A write refreshes what it wrote (DD-322), about half a
second at the 95th percentile on the dev store: the budget leaves shared CI runners several times that."""

BATCH = 100
"""The guids per delete and purge request of the clean-up."""


# impact=severe, likelihood=low (the spine under load drifts slowly). Cost
# ceiling (ADR 062): a capacity claim a contended shared runner cannot honour
# (PR 329's flake record) — weekly Scan's dedicated runner is its home.
@pytest.mark.medium
@pytest.mark.covers(
    "load.drive",
    "load.atlas_mix",
    "load.report",
    "load.OperationReport.as_dict",
    "aurelius_atlas_server_client.client.TypesApi.create_typedefs",
    "aurelius_atlas_server_client.client.EntityApi.create_or_update",
    "aurelius_atlas_server_client.client.EntityApi.delete_by_guids",
    "aurelius_atlas_server_client.client.AdminApi.purge",
    "aurelius_atlas_server_client.client.TypesApi.delete_typedef_by_name",
    rules=["LOD-01", "LOD-02", "LOD-03"],
)
async def test__the_server_holds_a_mixed_load(
    client: httpx.AsyncClient, api: AtlasClient, record_property: Callable[[str, object], None]
) -> None:
    """Every request of the run succeeds, and every operation's 95th percentile is within the budget (LOD-03)."""
    type_name = f"e2e_load_{uuid.uuid4().hex}"
    types = AtlasTypesDef(entity_defs=[AtlasEntityDef(name=type_name, super_types=["DataSet"])])
    await api.types.create_typedefs(types)
    created: list[str] = []
    try:
        guids = [await _seed(api, type_name, number) for number in range(USERS)]
        created.extend(guids)

        samples = await drive(client, atlas_mix(type_name, guids, created), users=USERS, seconds=SECONDS)
    finally:
        await _remove(api, type_name, created)

    reports = report(samples)
    record_property("load_report", json.dumps([found.as_dict() for found in reports]))
    print(_table(reports, USERS, SECONDS))  # noqa: T201 - the run's report, on the e2e output

    assert {found.operation for found in reports} == {"read", "basic search", "quick search", "update", "create"}
    assert [found.operation for found in reports if found.failures] == []
    assert [found.operation for found in reports if found.p95 > P95_MS] == []


@pytest.mark.critical
@pytest.mark.covers("load.percentile", "load.report", "load.Sample.ok", rules=["LOD-02"])
def test__the_report_counts_failures_and_takes_nearest_rank_percentiles() -> None:
    """Nearest rank: of 1 to 20 ms, p50 is 10 and p95 is 19; a 409 or no answer is a failure (LOD-02)."""
    reads = [Sample("read", 200, float(millis)) for millis in range(1, 21)]
    read, write = report([*reads, Sample("write", 409, 5.0), Sample("write", 0, 7.0), Sample("write", 201, 1.0)])

    assert (read.count, read.failures, read.p50, read.p95, read.max_millis) == (20, 0, 10.0, 19.0, 20.0)
    assert (write.count, write.failures) == (3, 2)
    assert percentile([], 0.95) == 0.0


async def _seed(api: AtlasClient, type_name: str, number: int) -> str:
    attributes = {"qualifiedName": f"{type_name}-seed-{number}", "name": f"seed {number}"}
    entity = AtlasEntity(type_name=type_name, attributes=attributes)
    created = await api.entity.create_or_update(AtlasEntityWithExtInfo(entity=entity))
    seeded = created.get_first_entity_by_operation(EntityOperation.CREATE)
    assert seeded is not None
    assert seeded.guid is not None
    return seeded.guid


async def _remove(api: AtlasClient, type_name: str, guids: list[str]) -> None:
    """Delete and purge the run's entities, then its type: the shared dev store is left as it was."""
    for batch in batched(guids, BATCH, strict=False):
        await api.entity.delete_by_guids(list(batch))
        await api.admin.purge(list(batch))
    await api.types.delete_typedef_by_name(type_name)


def _table(reports: Sequence[OperationReport], users: int, seconds: float) -> str:
    total = sum(found.count for found in reports)
    lines: list[Any] = [f"load: {users} users, {seconds:g} s, {total} requests, {total / seconds:.1f} per second"]
    lines += [
        f"  {found.operation:<13} {found.count:>6} req {found.failures:>4} failed "
        f"p50 {found.p50:>6.0f} ms  p95 {found.p95:>6.0f} ms  max {found.max_millis:>6.0f} ms"
        for found in reports
    ]
    return "\n".join(lines)
