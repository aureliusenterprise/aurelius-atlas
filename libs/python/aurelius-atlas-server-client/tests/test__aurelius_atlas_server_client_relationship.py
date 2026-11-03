"""``RelationshipApi`` against the recording transport (CLR-01..CLR-04).

One test per matrix row of the 8.11 coverage matrix, each naming the client
method it exercises (ADR 056); the recorder pins method, path, query, and body
for every route of ``routes/relationship.py`` (CL-02). The ends of a
relationship are never checked here — the server answers (CLR-03), and the
delete's ``deleteType`` travels only when given (CLR-04, as CLE-04).
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelationship
from aurelius_atlas_server_client.client import AtlasClient
from aurelius_atlas_server_client.models import DeleteType
from server_recorder import Recorder

G_REL = "00000000-0000-4000-8000-00000000000e"
G_ONE = "00000000-0000-4000-8000-00000000000f"
G_TWO = "00000000-0000-4000-8000-000000000010"
ROOT = "/api/atlas/v2/relationship"
"""The mounted prefix of the route module, as the server answers it (CLR-01)."""

RELATIONSHIP: dict[str, Any] = {
    "guid": G_REL,
    "label": "uses",
    "end1": {"guid": G_ONE, "typeName": "sales_table"},
    "end2": {"guid": G_TWO, "typeName": "sales_process"},
}
"""The relationship body, as ``AtlasRelationship.to_json`` writes it (REL-01)."""

REL_ANSWER: dict[str, Any] = {"relationship": RELATIONSHIP}
"""The ``getById`` answer: the ext-info wrapper with only ``relationship`` (REL-03, CLR-02)."""

REL_EXT_ANSWER: dict[str, Any] = {
    **REL_ANSWER,
    "referredEntities": {
        G_ONE: {"guid": G_ONE, "typeName": "sales_table", "displayText": "t"},
        G_TWO: {"guid": G_TWO, "typeName": "sales_process", "displayText": "p"},
    },
}


def _client(recorder: Recorder) -> AtlasClient:
    """The client under test on the recording transport (CL-02)."""
    return AtlasClient(httpx.AsyncClient(base_url="https://atlas.test", transport=recorder.transport()), "tok")


def _params(request: httpx.Request) -> list[tuple[str, str]]:
    """The request's query parameters, repeats kept."""
    return list(request.url.params.multi_items())


def _body(request: httpx.Request) -> Any:  # noqa: ANN401 - the JSON body of the request
    """The request's JSON body."""
    return json.loads(request.content)


def _relationship() -> AtlasRelationship:
    """A relationship between the two ends, its label the type's edge name (DD-309)."""
    return AtlasRelationship(
        guid=G_REL,
        label="uses",
        end1=AtlasObjectId(guid=G_ONE, type_name="sales_table"),
        end2=AtlasObjectId(guid=G_TWO, type_name="sales_process"),
    )


@pytest.mark.covers("aurelius_atlas_server_client.client.RelationshipApi.get", rules=["CLR-01", "CLR-02"])
async def test__get_sends_no_extended_info_by_default(recorder: Recorder) -> None:
    """``GET /guid/{guid}`` with no parameter: the answer holds only ``relationship`` (REL-03, CLR-02)."""
    recorder.answer(200, REL_ANSWER)

    found = await _client(recorder).relationship.get(G_REL)

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/guid/{G_REL}"
    assert sent.url.params.multi_items() == []
    assert found.relationship is not None
    assert found.relationship.label == "uses"
    assert found.referred_entities is None


@pytest.mark.covers("aurelius_atlas_server_client.client.RelationshipApi.get", rules=["CLR-02"])
async def test__get_with_extended_info_sends_the_flag_and_parses_the_ends(recorder: Recorder) -> None:
    """``extendedInfo=true`` asks for the ends' headers (REL-06, CLR-02)."""
    recorder.answer(200, REL_EXT_ANSWER)

    found = await _client(recorder).relationship.get(G_REL, extended_info=True)

    sent = recorder.sent()
    assert dict(_params(sent)) == {"extendedInfo": "true"}
    assert found.referred_entities is not None
    assert found.referred_entities[G_ONE].type_name == "sales_table"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.RelationshipApi.create",
    "aurelius_atlas_server_client.client.RelationshipApi.update",
    rules=["CLR-03"],
)
async def test__create_and_update_send_the_relationship_as_given(recorder: Recorder) -> None:
    """The ends are not checked client-side (REL-04..REL-07): the body travels whole (CLR-03)."""
    recorder.answer(200, RELATIONSHIP)
    recorder.answer(200, RELATIONSHIP)
    client = _client(recorder)

    created = await client.relationship.create(_relationship())
    updated = await client.relationship.update(_relationship())

    assert [(request.method, request.url.path) for request in recorder.requests] == [
        ("POST", ROOT),
        ("PUT", ROOT),
    ]
    for request in recorder.requests:
        body = _body(request)
        assert body["label"] == "uses"
        assert body["end1"] == {"guid": G_ONE, "typeName": "sales_table"}
        assert body["end2"] == {"guid": G_TWO, "typeName": "sales_process"}
    assert (created.label, updated.label) == ("uses", "uses")


@pytest.mark.covers("aurelius_atlas_server_client.client.RelationshipApi.delete", rules=["CLR-04"])
async def test__delete_sends_no_delete_type_by_default(recorder: Recorder) -> None:
    """The server's own delete strategy applies: no parameter, and the 204 returns None (EDL-04, REL-08)."""
    recorder.answer(204)

    await _client(recorder).relationship.delete(G_REL)

    sent = recorder.sent()
    assert sent.method == "DELETE"
    assert sent.url.path == f"{ROOT}/guid/{G_REL}"
    assert sent.url.params.multi_items() == []


@pytest.mark.covers("aurelius_atlas_server_client.client.RelationshipApi.delete", rules=["CLR-04"])
async def test__delete_sends_the_delete_type_the_caller_gives(recorder: Recorder) -> None:
    """``DeleteType.HARD`` travels as ``deleteType=HARD``, as CLE-04."""
    recorder.answer(204)

    await _client(recorder).relationship.delete(G_REL, delete_type=DeleteType.HARD)

    assert dict(_params(recorder.sent())) == {"deleteType": "HARD"}
