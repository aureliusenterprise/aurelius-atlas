"""``ViewApi``'s three doors against the recording transport (CLV-01..CLV-04).

The view family's doors of ``routes/view_search.py`` and ``routes/view_entity.py``
(16.2, 16.3): the search door, the read door, and the mutation door. The recorder
pins method, path, query, and body for every route (CL-02); the view and card
answers are ``aurelius-atlas-model``'s models, reused whole (DD-309), and the
search shapes the client library's own ``aurelius.py`` (DD-562).
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_server_client.aurelius import ViewSearchRequest
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError, ViewVersionConflictError
from server_recorder import Recorder

G_ONE = "00000000-0000-4000-8000-00000000000f"
G_TWO = "00000000-0000-4000-8000-00000000000e"
ROOT = "/api/aurelius/v1"
"""The mounted prefix of the two view route modules."""

VIEW: dict[str, Any] = {
    "guid": G_ONE,
    "typeName": "Asset",
    "name": "the asset",
    "displayText": "the asset",
    "updateTime": 1_700_000_000_000,
    "labels": ["edited"],
    "stale": False,
    "attributes": {"name": "the asset", "qualifiedName": "a.q"},
    "sections": [{"attribute": "childDataset", "entities": [{"guid": G_TWO, "name": "a child"}]}],
}
"""The live view of one entity, as the doors answer it (AVS-04, AVR-08)."""


def _client(recorder: Recorder) -> AtlasClient:
    """The client under test on the recording transport (CL-02)."""
    return AtlasClient(httpx.AsyncClient(base_url="https://atlas.test", transport=recorder.transport()), "tok")


def _body(request: httpx.Request) -> Any:  # noqa: ANN401 - the JSON body of the request
    """The request's JSON body."""
    return json.loads(request.content)


@pytest.mark.covers("aurelius_atlas_server_client.client.ViewApi.search", rules=["CLV-04"])
async def test__the_search_door_sends_the_request_and_answers_cards(recorder: Recorder) -> None:
    """``POST /search``: the door's request document in, the door's answer out as models (AVR-08)."""
    recorder.answer(200, {"cards": [VIEW], "facets": {"typeName": [{"value": "Asset", "count": 1}]}, "total": 1})

    answer = await _client(recorder).view.search(
        ViewSearchRequest(query="asset", filters={"typeName": ["Asset"]}, facets=["typeName"], limit=5)
    )

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/search"
    body = _body(sent)
    assert body["query"] == "asset"
    assert body["filters"] == {"typeName": ["Asset"]}
    assert body["facets"] == ["typeName"]
    assert body["limit"] == 5
    assert answer.total == 1
    assert answer.cards[0].guid == G_ONE
    assert answer.cards[0].name == "the asset"
    assert answer.facets["typeName"] == [{"value": "Asset", "count": 1}]


@pytest.mark.covers("aurelius_atlas_server_client.client.ViewApi.search", rules=["CLV-04"])
async def test__the_search_door_sends_no_body_for_everything(recorder: Recorder) -> None:
    """No request is the empty body the door reads as "everything" (ASE-04): no bytes on the wire."""
    recorder.answer(200, {"cards": [], "facets": {}, "total": 0})

    answer = await _client(recorder).view.search()

    assert recorder.sent().content == b""
    assert answer.total == 0
    assert answer.cards == []


@pytest.mark.covers("aurelius_atlas_server_client.client.ViewApi.read", rules=["CLV-01"])
async def test__the_read_door_answers_the_live_view(recorder: Recorder) -> None:
    """``GET /entity/guid/{guid}``: the entity's live view, parsed into ``EntityView`` (AVR-10)."""
    recorder.answer(200, VIEW)

    view = await _client(recorder).view.read(G_ONE)

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/entity/guid/{G_ONE}"
    assert view.guid == G_ONE
    assert view.name == "the asset"
    assert view.attributes["qualifiedName"] == "a.q"
    assert view.sections[0].attribute == "childDataset"
    assert view.sections[0].entities[0].guid == G_TWO


@pytest.mark.covers("aurelius_atlas_server_client.client.ViewApi.read", rules=["CLV-01", "CL-04"])
async def test__the_read_door_raises_the_atlas_404_of_a_guid_of_none(recorder: Recorder) -> None:
    """A GUID with no entity is the Atlas 404, raised with its error body like every refusal (AVR-10)."""
    recorder.answer(404, {"errorCode": "ATLAS-404-00-005", "errorMessage": f"entity with guid={G_ONE} not found"})

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).view.read(G_ONE)

    assert raised.value.status_code == 404
    assert raised.value.info is not None
    assert raised.value.info.error_code == "ATLAS-404-00-005"
    assert not isinstance(raised.value, ViewVersionConflictError)


@pytest.mark.covers("aurelius_atlas_server_client.client.ViewApi.save", rules=["CLV-02"])
async def test__the_mutation_door_sends_the_view_and_answers_the_saved_one(recorder: Recorder) -> None:
    """``POST /entity``: the dict the caller edited rides whole, the answer is the new live view (AVW-07)."""
    recorder.answer(200, VIEW)
    edited = {**VIEW, "attributes": {**VIEW["attributes"], "name": "renamed"}}

    saved = await _client(recorder).view.save(edited)

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/entity"
    assert "unsafeReparent" not in sent.url.params
    body = _body(sent)
    assert body["attributes"]["name"] == "renamed"
    assert body["guid"] == G_ONE
    assert saved.name == "the asset"


@pytest.mark.covers("aurelius_atlas_server_client.client.ViewApi.save", rules=["CLV-02"])
async def test__the_mutation_door_sends_the_reparent_opt_in_only_when_set(recorder: Recorder) -> None:
    """``unsafeReparent=true`` rides the query string only when the caller asks (RPS-05)."""
    recorder.answer(200, VIEW)

    await _client(recorder).view.save(VIEW, unsafe_reparent=True)

    assert recorder.sent().url.params["unsafeReparent"] == "true"


@pytest.mark.covers("aurelius_atlas_server_client.client.ViewApi.save", rules=["CLV-03", "AVW-04"])
async def test__a_stale_save_raises_the_conflict_with_the_stored_view(recorder: Recorder) -> None:
    """The door's 409: its code beside the stored view, parsed — an AtlasClientError all the same (DD-591)."""
    recorder.answer(409, {"errorCode": "ENTITY_VERSION_CONFLICT", "view": VIEW})

    with pytest.raises(ViewVersionConflictError) as raised:
        await _client(recorder).view.save(VIEW)

    error = raised.value
    assert isinstance(error, AtlasClientError)
    assert error.status_code == 409
    assert error.info is None  # the door's conflict body carries no errorMessage
    assert error.view.update_time is not None
    assert error.view.update_time.timestamp() * 1000 == 1_700_000_000_000
    assert error.view.name == "the asset"
    assert error.view.stale is False


@pytest.mark.covers("aurelius_atlas_server_client.client.ViewApi.save", rules=["CLV-03", "CL-04"])
async def test__another_409_stays_the_base_error(recorder: Recorder) -> None:
    """A 409 without the door's view — any other route's conflict — keeps CL-04's plain shape."""
    recorder.answer(409, {"errorCode": "ATLAS-409-00-002", "errorMessage": "type is referenced"})

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).view.save(VIEW)

    assert not isinstance(raised.value, ViewVersionConflictError)
    assert raised.value.info is not None
    assert raised.value.info.error_code == "ATLAS-409-00-002"


@pytest.mark.covers("aurelius_atlas_server_client.client.ViewApi.save", rules=["CLV-03"])
async def test__a_conflict_answer_that_is_not_json_stays_the_base_error(recorder: Recorder) -> None:
    """A 409 whose bytes are not JSON raises CL-04's error with no info, never a parse crash."""
    recorder.answer(409, text="gateway timeout")

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).view.save(VIEW)

    assert not isinstance(raised.value, ViewVersionConflictError)
    assert raised.value.info is None
