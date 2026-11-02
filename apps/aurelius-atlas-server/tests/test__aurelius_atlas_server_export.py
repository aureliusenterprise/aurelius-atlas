"""``POST /api/atlas/admin/export`` (EXP-01, EXP-02, EXP-06), as Apache Atlas 2.4.0's ``AdminResource#export``."""

import io
import json
import zipfile

import httpx2 as httpx
import pytest
from fake_issuer import FakeIssuer
from fastapi import FastAPI

EXPORT = "/api/atlas/admin/export"
TYPES = {
    "entityDefs": [
        {
            "name": "t_exp",
            "superTypes": [],
            "attributeDefs": [{"name": "qualifiedName", "typeName": "string", "isUnique": True, "isOptional": False}],
        }
    ]
}


async def entity(client: httpx.AsyncClient) -> str:
    """The GUID of a new ``t_exp`` ``q``."""
    assert (await client.post("/api/atlas/v2/types/typedefs", json=TYPES)).status_code == 200
    body = {"entity": {"typeName": "t_exp", "attributes": {"qualifiedName": "q"}}}
    return str((await client.post("/api/atlas/v2/entity", json=body)).json()["mutatedEntities"]["CREATE"][0]["guid"])


@pytest.mark.covers("aurelius_atlas_server.routes.admin.export", rules=["EXP-01", "EXP-06"])
async def test__an_export_answers_a_zip_of_the_entities(client: httpx.AsyncClient) -> None:
    """A ZIP of the entity, the order, the types and the result; an empty one, or none when asked."""
    guid = await entity(client)
    item = {"typeName": "t_exp", "uniqueAttributes": {"qualifiedName": "q"}}

    found = await client.post(EXPORT, json={"itemsToExport": [item]})
    empty = await client.post(EXPORT, json={"itemsToExport": [{"guid": "missing"}]})
    omitted = await client.post(
        EXPORT, json={"itemsToExport": [{"guid": "missing"}], "options": {"omitZipResponseForEmptyExport": "true"}}
    )

    assert found.status_code == 200
    assert found.headers["content-type"] == "application/zip"
    assert found.headers["content-disposition"] == "attachment; filename=AtlasExportResult"
    with zipfile.ZipFile(io.BytesIO(found.content)) as archive:
        assert sorted(archive.namelist()) == sorted(
            [f"{guid}.json", "atlas-export-order.json", "atlas-typesdef.json", "atlas-export-info.json"]
        )
        info = json.loads(archive.read("atlas-export-info.json"))
    assert (info["userName"], info["operationStatus"], info["sourceClusterName"]) == ("admin", "SUCCESS", "default")
    assert empty.status_code == 200
    assert (omitted.status_code, omitted.content) == (204, b"")


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.export", "aurelius_atlas_server.routes.admin._export_request", rules=["EXP-01"]
)
async def test__an_export_needs_the_admin_role_the_lock_and_a_request(
    app: FastAPI, client: httpx.AsyncClient, issuer: FakeIssuer
) -> None:
    """``export`` needs ``ADMIN_EXPORT``; another export or import running is 409 unless lineage is skipped."""
    reader = {"Authorization": f"Bearer {issuer.token('reader', atlas_roles=('atlas-read', 'atlas-write'))}"}
    refused = await client.post(EXPORT, json={}, headers=reader)
    assert (refused.status_code, refused.json()["errorMessage"]) == (403, "reader is not authorized to perform export")
    assert (await client.post(EXPORT, json=["a"])).status_code == 400
    assert (await client.post(EXPORT)).status_code == 200

    lock = app.state.import_export_lock
    await lock.acquire()
    try:
        busy = await client.post(EXPORT, json={"itemsToExport": []})
        skipping = await client.post(EXPORT, json={"options": {"skipLineage": False}})
    finally:
        lock.release()
    assert (busy.status_code, busy.json()["errorCode"]) == (409, "ATLAS-500-00-006")
    assert skipping.status_code == 200
