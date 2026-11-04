"""``GET /api/atlas/admin/metrics`` (MET-01 to MET-04), as Apache Atlas 2.4.0's ``AdminResource#getMetrics``."""

import httpx2 as httpx
import pytest
from aurelius_atlas_store_es.testing.fake import FakeClient
from fake_issuer import FakeIssuer

METRICS = "/api/atlas/admin/metrics"


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_metrics", rules=["MET-01", "MET-03"])
@pytest.mark.covers("aurelius_atlas_server.app._start", rules=["MET-03"])
async def test__the_metrics_answer_the_catalogues_counts_and_the_servers_stats(
    client: httpx.AsyncClient, fake_es: FakeClient, issuer: FakeIssuer
) -> None:
    """The four groups; the server started and became active as it started; a store not healthy is not connected."""
    found = await client.get(METRICS)
    fake_es.cluster_status = "red"
    unhealthy = await client.get(METRICS)
    reader = {"Authorization": f"Bearer {issuer.token('reader', atlas_roles=('atlas-read',))}"}
    as_reader = await client.get(METRICS, headers=reader)

    assert found.status_code == 200
    data = found.json()["data"]
    assert sorted(data) == ["entity", "general", "system", "tag"]
    stats = data["general"]["stats"]
    assert stats["Server:startTimeStamp"] > 0
    assert stats["Server:activeTimeStamp"] >= stats["Server:startTimeStamp"]
    assert (stats["Server:statusBackendStore"], stats["Server:statusIndexStore"]) == ("connected", "connected")
    assert data["general"]["typeCount"] > 0
    assert sorted(data["system"]) == ["memory", "os", "runtime"]
    unhealthy_stats = unhealthy.json()["data"]["general"]["stats"]
    assert unhealthy_stats["Server:statusBackendStore"] == "not-connected"
    assert as_reader.status_code == 200
