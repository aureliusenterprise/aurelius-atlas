import re
import zoneinfo
from typing import cast

import httpx2 as httpx
import pytest
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument, StoredTypedefs
from aurelius_atlas_model.patches import TYPEDEF_PATCH_TYPE, AtlasPatch, PatchStatus
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server.errors import ATLAS_JSON_MEDIA_TYPE
from aurelius_atlas_server.routes.admin import csrf_token, time_zones
from aurelius_atlas_store_es.testing.fake import FakeClient
from elasticsearch import AsyncElasticsearch


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


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_patches", rules=["ENS-10"])
async def test__patches_lists_the_stored_patch_records_by_id(settings: ServerSettings, fake_es: FakeClient) -> None:
    """``getAtlasPatches``: ``{"patches": [...]}`` sorted by id, each as ``AtlasPatch`` writes it (DV-14)."""
    stored = ElasticsearchTypedefDocument(cast("AsyncElasticsearch", fake_es))
    await stored.prepare()
    patches = [
        AtlasPatch(id=patch_id, type=TYPEDEF_PATCH_TYPE, action="SET_SERVICE_TYPE", status=PatchStatus.APPLIED)
        for patch_id in ("TYPEDEF_PATCH_2", "TYPEDEF_PATCH_1")
    ]
    await stored.write(StoredTypedefs(AtlasTypesDef(), patches), None)
    app = create_app(settings)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://aurelius-atlas") as client:
            response = await client.get("/api/atlas/admin/patches")

    assert response.status_code == 200
    assert response.json() == {
        "patches": [
            {
                "id": f"TYPEDEF_PATCH_{n}",
                "type": "TYPEDEF_PATCH",
                "action": "SET_SERVICE_TYPE",
                "status": "APPLIED",
                "createdTime": 0,
                "updatedTime": 0,
            }
            for n in (1, 2)
        ]
    }
