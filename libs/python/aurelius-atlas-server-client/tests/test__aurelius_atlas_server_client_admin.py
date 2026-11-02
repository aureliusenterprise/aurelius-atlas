"""``AdminApi``'s seven write routes against the recording transport (CLW-01..CLW-06).

The five 8.4 reads stay where they are (``test__aurelius_atlas_server_client_client.py``,
CLW-07 — unchanged); this file holds the 8.11 writes: patches, purge, the export/import
trio, and the task list. The recorder pins method, path, query, and body for every route
of ``routes/admin.py`` (CL-02); the export answers bytes and the import crosses as
multipart (CL-64, DD-310).
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_model.impexp import AtlasExportRequest, AtlasImportRequest
from aurelius_atlas_model.instance import AtlasObjectId
from aurelius_atlas_server_client.client import AtlasClient
from server_recorder import Recorder

G_ONE = "00000000-0000-4000-8000-00000000000f"
G_TWO = "00000000-0000-4000-8000-000000000010"
ROOT = "/api/atlas/admin"
"""The mounted prefix of the route module, as the server answers it."""

PATCH_ANSWER: dict[str, Any] = {"id": "p-1", "type": "TYPEDEF_PATCH", "status": "APPLIED"}
PURGE_ANSWER: dict[str, Any] = {"mutatedEntities": {"PURGE": [{"guid": G_ONE, "typeName": "t"}]}}
IMPORT_ANSWER: dict[str, Any] = {"operationStatus": "SUCCESS", "metrics": {"TOTAL_ENTITIES_PROCESSED": 3}}
TASK_ANSWER: dict[str, Any] = {"guid": G_ONE, "type": "ENTITY_UPDATE", "status": "PENDING"}


def _client(recorder: Recorder) -> AtlasClient:
    """The client under test on the recording transport (CL-02)."""
    return AtlasClient(httpx.AsyncClient(base_url="https://atlas.test", transport=recorder.transport()), "tok")


def _params(request: httpx.Request) -> list[tuple[str, str]]:
    """The request's query parameters, repeats kept."""
    return list(request.url.params.multi_items())


def _body(request: httpx.Request) -> Any:  # noqa: ANN401 - the JSON body of the request
    """The request's JSON body."""
    return json.loads(request.content)


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.patches", rules=["CLW-01"])
async def test__patches_unwraps_the_servers_envelope(recorder: Recorder) -> None:
    """``GET /patches`` answers ``{"patches": [...]}`` (ENS-10): the client returns the list."""
    recorder.answer(200, {"patches": [PATCH_ANSWER]})

    found = await _client(recorder).admin.patches()

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/patches"
    assert found[0].id == "p-1"
    assert found[0].status is not None
    assert found[0].status.value == "APPLIED"


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.purge", rules=["CLW-02"])
async def test__purge_sends_the_json_array_of_guids(recorder: Recorder) -> None:
    """``PUT /purge`` with a JSON array of guid strings, answered by the mutation response (EDL-01..EDL-03)."""
    recorder.answer(200, PURGE_ANSWER)

    response = await _client(recorder).admin.purge([G_ONE])

    sent = recorder.sent()
    assert sent.method == "PUT"
    assert sent.url.path == f"{ROOT}/purge"
    assert _body(sent) == [G_ONE]
    assert response.mutated_entities is not None
    assert [header.guid for headers in response.mutated_entities.values() for header in headers] == [G_ONE]


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.purge", rules=["CLW-02"])
async def test__purge_of_nothing_sends_the_empty_array(recorder: Recorder) -> None:
    """``[]`` travels as ``[]`` (DV-10): a missing body would be the server's BAD_REQUEST, not a no-op."""
    recorder.answer(200, {})

    await _client(recorder).admin.purge([])

    assert _body(recorder.sent()) == []


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.export", rules=["CLW-03"])
async def test__export_returns_the_zip_as_bytes(recorder: Recorder) -> None:
    """``POST /export`` answers ``application/zip`` (EXP-01..EXP-04): bytes and content type, DD-310."""
    zip_bytes = b"PK\x03\x04export"
    recorder.handler = lambda _: httpx.Response(200, content=zip_bytes, headers={"content-type": "application/zip"})
    request = AtlasExportRequest(items_to_export=[AtlasObjectId(guid=G_ONE)])

    content, content_type = await _client(recorder).admin.export(request)

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/export"
    assert _body(sent)["itemsToExport"] == [{"guid": G_ONE}]
    assert content == zip_bytes
    assert content_type == "application/zip"


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.export", rules=["CLW-03"])
async def test__export_without_a_request_sends_no_body(recorder: Recorder) -> None:
    """No request is the empty one the server builds from a missing body (DV-120): no body, no options."""
    recorder.handler = lambda _: httpx.Response(200, content=b"PK\x03\x04", headers={"content-type": "application/zip"})

    await _client(recorder).admin.export()

    assert recorder.sent().content == b""


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.export", rules=["CLW-03"])
async def test__the_omitted_empty_export_comes_back_empty(recorder: Recorder) -> None:
    """The 204 of ``omitZipResponseForEmptyExport`` (EXP-05): ``(b"", "")``, not an error (CLW-03)."""
    recorder.answer(204)

    content, content_type = await _client(recorder).admin.export(
        AtlasExportRequest(options={"omitZipResponseForEmptyExport": True})
    )

    assert (content, content_type) == (b"", "")


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.import_data", rules=["CLW-04"])
async def test__import_data_sends_the_zip_and_the_request_as_form_parts(recorder: Recorder) -> None:
    """``POST /import`` multipart: the ``data`` file part and a plain-text ``request`` part (IMS-01..IMS-05, DD-313)."""
    recorder.answer(200, IMPORT_ANSWER)

    found = await _client(recorder).admin.import_data(
        b"PK\x03\x04export", AtlasImportRequest(options={"startGuid": G_ONE})
    )

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/import"
    assert sent.headers["content-type"].startswith("multipart/form-data")
    await sent.aread()
    text = sent.content.decode()
    assert 'name="data"; filename="export.zip"' in text
    assert 'name="request"' in text  # a form field, not a file: no filename
    assert '"startGuid"' in text
    assert found.operation_status.value == "SUCCESS"


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.import_data", rules=["CLW-04"])
async def test__import_data_without_a_request_sends_only_the_zip(recorder: Recorder) -> None:
    """No request part: the server reads the missing text as ``{}`` (IMS-01)."""
    recorder.answer(200, IMPORT_ANSWER)

    await _client(recorder).admin.import_data(b"PK\x03\x04")

    sent = recorder.sent()
    await sent.aread()
    assert 'name="data"' in sent.content.decode()
    assert 'name="request"' not in sent.content.decode()


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.import_file", rules=["CLW-05"])
async def test__import_file_passes_the_file_name_option_through(recorder: Recorder) -> None:
    """``POST /importfile`` with the request as JSON body (IMS-06, DV-125): the server opens the name (CLW-05)."""
    recorder.answer(200, IMPORT_ANSWER)

    found = await _client(recorder).admin.import_file(AtlasImportRequest(options={"fileName": "export.zip"}))

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/importfile"
    assert _body(sent) == {"options": {"fileName": "export.zip"}}
    assert found.operation_status.value == "SUCCESS"


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.tasks", rules=["CLW-06"])
async def test__tasks_without_guids_asks_for_every_task(recorder: Recorder) -> None:
    """``GET /tasks`` with no parameter: the server's ``get_all`` (TSK-06)."""
    recorder.answer(200, [TASK_ANSWER])

    found = await _client(recorder).admin.tasks()

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/tasks"
    assert sent.url.params.multi_items() == []
    assert found[0].type == "ENTITY_UPDATE"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.AdminApi.tasks",
    "aurelius_atlas_server_client.client.AdminApi.delete_tasks",
    rules=["CLW-06"],
)
async def test__the_task_verbs_send_each_guid_as_a_repeated_parameter(recorder: Recorder) -> None:
    """``?guids=a&guids=b`` on both the GET and the DELETE (TSK-06) — pinned once for the pair."""
    recorder.answer(200, [TASK_ANSWER, TASK_ANSWER])
    recorder.answer(204)
    client = _client(recorder)

    found = await client.admin.tasks([G_ONE, G_TWO])
    await client.admin.delete_tasks([G_ONE, G_TWO])

    get_request, delete_request = recorder.requests
    assert _params(get_request) == [("guids", G_ONE), ("guids", G_TWO)]
    assert len(found) == 2
    assert delete_request.method == "DELETE"
    assert delete_request.url.path == f"{ROOT}/tasks"
    assert _params(delete_request) == [("guids", G_ONE), ("guids", G_TWO)]
