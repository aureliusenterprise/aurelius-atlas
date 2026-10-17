import re
import zoneinfo

import httpx
import pytest
from aurelius_atlas_server.errors import ATLAS_JSON_MEDIA_TYPE
from aurelius_atlas_server.routes.admin import csrf_token, time_zones
from aurelius_atlas_store_es.testing.fake import FakeClient


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_readiness", rules=["ADM-04", "SRV-04", "SRV-05"])
async def test__readiness_fails_while_the_store_is_unhealthy(client: httpx.AsyncClient, fake_es: FakeClient) -> None:
    """A red cluster makes readiness answer 500 with the Atlas error body; liveness and status stay up."""
    fake_es.cluster_status = "red"

    readiness = await client.get("/api/atlas/admin/readiness")
    liveness = await client.get("/api/atlas/admin/liveness")
    status = await client.get("/api/atlas/admin/status")

    assert readiness.status_code == 500
    assert readiness.headers["content-type"] == ATLAS_JSON_MEDIA_TYPE
    assert readiness.json() == {
        "errorCode": "ATLAS-500-00-001",
        "errorMessage": "Internal server error Service not ready to accept client requests",
    }
    assert liveness.status_code == 200
    assert status.json() == {"Status": "ACTIVE"}


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.get_session", "aurelius_atlas_server.routes.admin.csrf_token", rules=["ADM-05"]
)
async def test__session_gives_a_new_token_of_letters_and_digits(client: httpx.AsyncClient) -> None:
    """The CSRF token has 20 letters and digits and differs between sessions."""
    first = (await client.get("/api/atlas/admin/session")).json()["_csrfToken"]
    second = (await client.get("/api/atlas/admin/session")).json()["_csrfToken"]

    assert re.fullmatch(r"[A-Za-z0-9]{20}", first)
    assert first != second
    assert re.fullmatch(r"[A-Za-z0-9]{20}", csrf_token())


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.get_session", "aurelius_atlas_server.routes.admin.time_zones", rules=["ADM-05"]
)
async def test__session_lists_the_iana_time_zones(client: httpx.AsyncClient) -> None:
    """The time zones are the IANA ids, sorted (DV-05)."""
    zones = (await client.get("/api/atlas/admin/session")).json()["timezones"]

    assert zones == sorted(zoneinfo.available_timezones())
    assert {"UTC", "Europe/Amsterdam", "America/New_York"} <= set(zones)
    assert time_zones() == zones
