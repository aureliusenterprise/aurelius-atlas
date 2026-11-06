"""``POST /api/atlas/admin/audits/ageout`` and the aging schedule (AGE-01 to AGE-03, AGE-05), as Apache Atlas
2.4.0's ``AdminResource#ageoutAuditData`` and ``AtlasAuditReductionService#configureTasks``.
"""  # noqa: D205 - one sentence

import asyncio

import httpx2 as httpx
import pytest
from aurelius_atlas_core.audit_reduction_service import AtlasAuditReductionService, AuditAgingConfig
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_server.app import _audit_aging
from aurelius_atlas_server.audit_aging_scheduler import AuditAgingScheduler
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_typesystem.registry import TypeRegistry
from fake_issuer import FakeIssuer
from fastapi import FastAPI

AGEOUT = "/api/atlas/admin/audits/ageout"


@pytest.mark.covers("aurelius_atlas_server.routes.admin.ageout_audit_data", rules=["AGE-01", "AGE-02", "AGE-03"])
async def test__an_ageout_queues_the_agings_it_asks_for(
    app: FastAPI, client: httpx.AsyncClient, issuer: FakeIssuer, settings: ServerSettings
) -> None:
    """The criteria's agings as pending tasks; none asked for, or aging off, is 204; ``ADMIN_AUDITS`` needed."""
    criteria = {"auditAgingEnabled": True, "defaultAgeoutEnabled": True, "customAgeoutAuditCount": 60}

    found = await client.post(AGEOUT, json=criteria)
    off = await client.post(AGEOUT, json={"defaultAgeoutEnabled": True})
    empty = await client.post(AGEOUT)
    by_config_off = await client.post(AGEOUT, params={"useAuditConfig": "true"})
    app.state.settings = settings.model_copy(update={"audit_aging_enabled": True})
    by_config = await client.post(AGEOUT, params={"useAuditConfig": "TRUE"})
    reader = {"Authorization": f"Bearer {issuer.token('reader', atlas_roles=('atlas-read',))}"}
    refused = await client.post(AGEOUT, json=criteria, headers=reader)
    invalid = await client.post(AGEOUT, json=["x"])
    unknown = await client.post(AGEOUT, json={**criteria, "customAgeoutActionTypes": "NOPE"})

    assert found.status_code == 200
    [task] = found.json()
    assert (task["type"], task["createdBy"], task["status"]) == ("AUDIT_REDUCTION_ENTITY_RETRIEVAL", "admin", "PENDING")
    assert (task["parameters"]["auditAgingType"], task["parameters"]["ttl"]) == ("DEFAULT", 90)
    assert (off.status_code, empty.status_code, by_config_off.status_code) == (204, 204, 204)
    assert [listed["parameters"]["auditAgingType"] for listed in by_config.json()] == ["DEFAULT"]
    assert (refused.status_code, refused.json()["errorMessage"]) == (
        403,
        "reader is not authorized to perform Admin Audits Ageout",
    )
    assert invalid.status_code == 400
    assert unknown.status_code == 500
    assert unknown.json()["errorMessage"].endswith("EntityAuditActionV2.NOPE")


@pytest.mark.covers(
    "aurelius_atlas_server.audit_aging_scheduler.AuditAgingScheduler.run",
    "aurelius_atlas_server.audit_aging_scheduler.AuditAgingScheduler.age_out",
    "aurelius_atlas_server.audit_aging_scheduler.AuditAgingScheduler.start",
    "aurelius_atlas_server.audit_aging_scheduler.AuditAgingScheduler.stop",
    "aurelius_atlas_server.app._audit_aging",
    "aurelius_atlas_server.settings.ServerSettings.audit_aging_config",
    rules=["AGE-05"],
)
async def test__the_configured_aging_runs_after_its_delay_and_then_on_its_frequency(settings: ServerSettings) -> None:
    """At least a minute, then at least a day between rounds; a round that fails is only logged."""
    slept: list[float] = []
    rounds: list[int] = []

    class Aging(AtlasAuditReductionService):
        async def start_by_config(self):  # noqa: ANN202 - the parent's
            rounds.append(1)
            if len(rounds) == 1:
                raise RuntimeError
            return []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        if len(slept) == 3:
            raise asyncio.CancelledError

    store = EntityStore(TypeRegistry(), MemoryEntityDocuments())
    scheduler = AuditAgingScheduler(
        Aging(store, AuditAgingConfig()), frequency_days=0, initial_delay_minutes=0, sleep=sleep
    )
    with pytest.raises(asyncio.CancelledError):
        await scheduler.run()

    assert slept == [60, 86_400, 86_400]
    assert len(rounds) == 2
    assert _audit_aging(settings, store) is None
    enabled = settings.model_copy(update={"audit_aging_enabled": True, "audit_min_count_to_maintain": 9})
    assert enabled.audit_aging_config().min_count_to_maintain == 9
    started = _audit_aging(enabled, store)
    assert started is not None
    await started.stop()
    await started.stop()
