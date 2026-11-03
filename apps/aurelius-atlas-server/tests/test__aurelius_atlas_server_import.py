"""``POST /api/atlas/admin/import`` and ``importfile`` (IMS-01, IMS-06), as Apache Atlas 2.4.0's ``AdminResource``."""

import io
import zipfile
from pathlib import Path

import httpx2 as httpx
import pytest
from base_models import base_models
from fake_issuer import FakeIssuer
from fastapi import FastAPI

ADMIN = "/api/atlas/admin"
TYPES = {
    "entityDefs": [
        {
            "name": "t_imp",
            "superTypes": [],
            "attributeDefs": [{"name": "qualifiedName", "typeName": "string", "isUnique": True, "isOptional": False}],
        }
    ]
}


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model: an export or import records its servers and audit entry (REP-02)."""
    return base_models(tmp_path)


async def exported(client: httpx.AsyncClient) -> bytes:
    """The ZIP of an export of a new ``t_imp``."""
    assert (await client.post("/api/atlas/v2/types/typedefs", json=TYPES)).status_code == 200
    body = {"entity": {"typeName": "t_imp", "attributes": {"qualifiedName": "q"}}}
    guid = (await client.post("/api/atlas/v2/entity", json=body)).json()["mutatedEntities"]["CREATE"][0]["guid"]
    return (await client.post(f"{ADMIN}/export", json={"itemsToExport": [{"guid": guid}]})).content


def empty_zip() -> bytes:
    """A ZIP whose export order is empty."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("atlas-export-order.json", "[]")
    return buffer.getvalue()


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.import_data",
    "aurelius_atlas_server.routes.admin._import_request",
    rules=["IMS-01"],
)
async def test__an_upload_is_imported(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """The result of the import; an empty ZIP answers an empty result; ``importData`` needs ``ADMIN_IMPORT``."""
    content = await exported(client)

    found = await client.post(f"{ADMIN}/import", files={"data": ("e.zip", content)}, data={"request": "{}"})
    empty = await client.post(f"{ADMIN}/import", files={"data": ("e.zip", empty_zip())})
    reader = {"Authorization": f"Bearer {issuer.token('reader', atlas_roles=('atlas-read',))}"}
    refused = await client.post(f"{ADMIN}/import", files={"data": ("e.zip", content)}, headers=reader)

    assert found.status_code == 200
    assert (found.json()["operationStatus"], found.json()["userName"]) == ("SUCCESS", "admin")
    assert (empty.status_code, empty.json()["operationStatus"], empty.json()["processedEntities"]) == (200, "FAIL", [])
    assert refused.json()["errorMessage"] == "reader is not authorized to perform importData"


@pytest.mark.covers(
    "aurelius_atlas_server.routes.admin.import_file",
    "aurelius_atlas_server.routes.admin._exclusively",
    rules=["IMS-06"],
)
async def test__a_file_is_imported_from_the_import_folder(
    app: FastAPI, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    """Only with an import folder; another import running refuses an upload."""
    (tmp_path / "e.zip").write_bytes(await exported(client))

    refused = await client.post(f"{ADMIN}/importfile", json={"options": {"fileName": "e.zip"}})
    app.state.settings = app.state.settings.model_copy(update={"import_folder": tmp_path})
    found = await client.post(f"{ADMIN}/importfile", json={"options": {"fileName": "e.zip"}})
    lock = app.state.import_export_lock
    await lock.acquire()
    try:
        busy = await client.post(f"{ADMIN}/import", files={"data": ("e.zip", empty_zip())})
    finally:
        lock.release()

    assert (refused.status_code, refused.json()["errorMessage"]) == (400, "invalid parameters: e.zip: file not found")
    assert found.json()["operationStatus"] == "SUCCESS"
    assert (busy.status_code, busy.json()["errorCode"]) == (409, "ATLAS-500-00-006")
