"""The Data2ModelClient against the recording transport (CL-01..CL-04, CL-21; DD-115, DD-116).

Every call answers from the externally provided httpx client the test hands in —
its transport is a recorder, no socket opens (CL-02); each test names the methods
it exercises (ADR 049) and the rules it enforces.
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_data2model_client.client import Data2ModelClient, Data2ModelClientError
from aurelius_atlas_data2model_client.models import ExtractionRequest, RulesDef
from d2m_recorder import Recorder
from pydantic import ValidationError

ANSWER: dict[str, Any] = {"metadata": [{"id": "n-1", "data": {"created_by": "dataset"}}], "model": '{"ar3_model": {}}'}
ERROR_BODY: dict[str, Any] = {"errorCode": "ATLAS-400-00-029", "errorMessage": "unknown concept type: 'x'"}
REQUEST = ExtractionRequest.model_validate(
    {"data": [{"id": "e-1"}], "rules": {"elements": [{"id": "d", "id_key": "id", "concept_type": "lineage_dataset"}]}}
)


def _client(recorder: Recorder) -> Data2ModelClient:
    """The client under test: an externally built httpx client on the recorder (CL-02, CL-01)."""
    http = httpx.AsyncClient(base_url="https://data2model.test", transport=recorder.transport())
    return Data2ModelClient(http, "tok")


@pytest.mark.covers(
    "aurelius_atlas_data2model_client.client.Data2ModelClient.extract",
    "aurelius_atlas_data2model_client.client.Data2ModelClient.with_token",
    rules=["CL-21", "CL-03", "CL-02"],
)
async def test__with_token_shares_the_pool_and_speaks_with_the_new_token(
    recorder: Recorder, tracked_client_http: httpx.AsyncClient
) -> None:
    """The wrapper posts the caller's token on the owner's connection pool (CL-03, LM-04)."""
    owner = Data2ModelClient(tracked_client_http, "service-token")
    recorder.answer(200, ANSWER)

    answer = await owner.with_token("browser-token").extract(REQUEST)

    assert answer.model == '{"ar3_model": {}}'
    assert recorder.sent().headers["authorization"] == "Bearer browser-token"
    await tracked_client_http.aclose()


@pytest.mark.covers(
    "aurelius_atlas_data2model_client.client.Data2ModelClient.extract",
    rules=["CL-21", "CL-03"],
)
async def test__an_empty_token_travels_unauthenticated(recorder: Recorder) -> None:
    """An empty token source is the unauthenticated call: no authorization header, no malformed bearer (CL-03)."""
    recorder.answer(200, ANSWER)
    http = httpx.AsyncClient(base_url="https://data2model.test", transport=recorder.transport())
    client = Data2ModelClient(http, "")

    await client.extract(REQUEST)

    assert "authorization" not in recorder.sent().headers
    await http.aclose()


@pytest.mark.covers(
    "aurelius_atlas_data2model_client.client.Data2ModelClient.extract",
    "aurelius_atlas_data2model_client.client.Data2ModelClient.with_token",
    rules=["CL-02"],
)
async def test__the_pool_is_the_builders_to_close(recorder: Recorder) -> None:
    """The client has no close: it serves until its builder closes the pool (CL-02, DD-116)."""
    http = httpx.AsyncClient(base_url="https://data2model.test", transport=recorder.transport())
    client = Data2ModelClient(http, "tok")
    borrowed = client.with_token("caller-token")
    recorder.answer(200, ANSWER)
    recorder.answer(200, ANSWER)

    await client.extract(REQUEST)  # the pool is open for the client…
    await borrowed.extract(REQUEST)  # …and for every wrapper of it

    await http.aclose()  # the builder closes — the API client never does
    recorder.answer(200, ANSWER)
    with pytest.raises(RuntimeError):  # httpx's own "client is already closed"
        await client.extract(REQUEST)


@pytest.mark.covers("aurelius_atlas_data2model_client.client.Data2ModelClient.extract", rules=["CL-21"])
async def test__extract_posts_the_request_model_and_parses_the_answer(recorder: Recorder) -> None:
    """``POST /extract``: the model_dump body (legacy wire keys, CL-06), the ``{metadata, model}`` answer (DTM-01)."""
    recorder.answer(200, ANSWER)

    answer = await _client(recorder).extract(REQUEST)

    sent = recorder.sent()
    assert (sent.method, sent.url.path) == ("POST", "/extract")
    assert json.loads(sent.content) == REQUEST.model_dump(mode="json", by_alias=True)
    assert answer.metadata[0].id == "n-1"
    assert RulesDef.model_validate(json.loads(sent.content)["rules"]) == REQUEST.rules


@pytest.mark.covers("aurelius_atlas_data2model_client.client.Data2ModelClient.extract", rules=["CL-04"])
async def test__a_rejected_request_raises_with_the_status_and_the_error_body(recorder: Recorder) -> None:
    """The DTM-11 400, with the Atlas-shaped body in the error (CL-04)."""
    recorder.answer(400, ERROR_BODY)

    with pytest.raises(Data2ModelClientError) as raised:
        await _client(recorder).extract(REQUEST)

    assert raised.value.status_code == 400
    assert raised.value.error_code == "ATLAS-400-00-029"
    assert "unknown concept type" in str(raised.value)


@pytest.mark.covers("aurelius_atlas_data2model_client.client.Data2ModelClient.extract", rules=["CL-04"])
async def test__an_unparsable_error_body_still_carries_the_status(recorder: Recorder) -> None:
    """A 500 of plain text is still a status: the error fields stay None (CL-04)."""
    recorder.answer(500, text="boom")

    with pytest.raises(Data2ModelClientError) as raised:
        await _client(recorder).extract(REQUEST)

    assert (raised.value.status_code, raised.value.error_code, raised.value.error_message) == (500, None, None)


@pytest.mark.covers("aurelius_atlas_data2model_client.client.Data2ModelClient.extract", rules=["CL-05"])
async def test__an_unreachable_service_propagates_httpxs_own_error(recorder: Recorder) -> None:
    """The client maps nothing: a transport failure is ``httpx``'s, the app's job (CL-05, DV-22)."""
    recorder.handler = lambda _request: (_ for _ in ()).throw(httpx.ConnectError("refused"))

    with pytest.raises(httpx.ConnectError):
        await _client(recorder).extract(REQUEST)


# ---------------------------------------------------------------------------
# 8.7 — the failure contract: malformed successes, outage bodies, raising sources
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_data2model_client.client.Data2ModelClient.extract", rules=["CL-08"])
async def test__a_200_with_a_body_of_the_wrong_shape_is_the_contract_failing(recorder: Recorder) -> None:
    """A success that is not the contract: the model rejects the body, pydantic's error travels (CL-08)."""
    recorder.answer(200, {"nope": True})

    with pytest.raises(ValidationError):
        await _client(recorder).extract(REQUEST)


@pytest.mark.covers("aurelius_atlas_data2model_client.client.Data2ModelClient.extract", rules=["CL-08"])
async def test__a_200_of_plain_text_is_the_contract_failing(recorder: Recorder) -> None:
    """A 200 that is not JSON: the client parses through its model and never swallows (CL-08)."""
    recorder.answer(200, text="I am not an extraction body")

    with pytest.raises(ValidationError):
        await _client(recorder).extract(REQUEST)


@pytest.mark.covers("aurelius_atlas_data2model_client.client.Data2ModelClient.extract", rules=["CL-04"])
async def test__a_server_outage_answer_carries_the_status_and_the_fields(recorder: Recorder) -> None:
    """The 5xx with an Atlas body — the shape the 8.2 chain's breakers ride (CL-04)."""
    recorder.answer(502, ERROR_BODY)

    with pytest.raises(Data2ModelClientError) as raised:
        await _client(recorder).extract(REQUEST)

    assert raised.value.status_code == 502
    assert raised.value.error_code == "ATLAS-400-00-029"


@pytest.mark.covers("aurelius_atlas_data2model_client.client.Data2ModelClient.extract", rules=["CL-05"])
async def test__a_timeout_propagates_as_httpxs_own_error(recorder: Recorder) -> None:
    """The pool's timeout is a RequestError too: httpx's own, unmapped (CL-05).

    The MockTransport does not enforce the bound, so the handler raises what
    the bound raises at a real socket.
    """
    timed_out = "read timed out"

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(timed_out)

    recorder.handler = handler

    with pytest.raises(httpx.TimeoutException):
        await _client(recorder).extract(REQUEST)


@pytest.mark.covers("aurelius_atlas_data2model_client.client.Data2ModelClient.extract", rules=["CL-03"])
async def test__a_token_source_that_raises_travels_out_unsent(recorder: Recorder) -> None:
    """A credential fetch that fails is the caller's error, and nothing reaches the wire (CL-03).

    The bearer is read before the request, so a failing source never speaks.
    """
    broken = "the credential store is down"

    def token_source() -> str:
        raise RuntimeError(broken)

    http = httpx.AsyncClient(base_url="https://data2model.test", transport=recorder.transport())
    with pytest.raises(RuntimeError, match="credential store"):
        await Data2ModelClient(http, token_source).extract(REQUEST)
    await http.aclose()

    assert recorder.requests == []  # no bearer, no request
