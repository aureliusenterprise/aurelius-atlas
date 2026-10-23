"""The LineageModelClient against the recording transport (CL-01..CL-05, CL-30; DD-115, DD-116).

Every call answers from the externally provided httpx client the test hands in —
its transport is a recorder, no socket opens (CL-02); each test names the methods
it exercises (ADR 049) and the rules it enforces.
"""

from typing import cast

import httpx
import pytest
from aurelius_atlas_lineage_model_client.client import LineageModelClient, LineageModelClientError
from aurelius_atlas_lineage_model_client.models import Direction, LineageModelResponse
from lm_recorder import Recorder

ANSWER = {"model": '{"ar3_model": {}}', "metadata": [{"id": "e-1", "data": {}}]}
ERROR_BODY = {"errorCode": "ATLAS-400-00-029", "errorMessage": "invalid lineage request"}


def _client(recorder: Recorder) -> LineageModelClient:
    """The client under test: an externally built httpx client on the recorder (CL-02, CL-01)."""
    return LineageModelClient(
        httpx.AsyncClient(base_url="https://lineage-model.test", transport=recorder.transport()), "tok"
    )


@pytest.mark.covers(
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.get",
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.with_token",
    rules=["CL-30", "CL-03", "CL-02"],
)
async def test__with_token_shares_the_pool_and_speaks_with_the_new_token(
    recorder: Recorder, tracked_client_http: httpx.AsyncClient
) -> None:
    """The wrapper asks with the caller's token on the owner's connection pool (CL-03)."""
    owner = LineageModelClient(tracked_client_http, "service-token")
    recorder.answer(200, ANSWER)

    answer = await owner.with_token("browser-token").get("e-1")

    assert answer is not None
    assert answer.model == '{"ar3_model": {}}'
    assert recorder.sent().headers["authorization"] == "Bearer browser-token"
    await tracked_client_http.aclose()


@pytest.mark.covers(
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.get",
    rules=["CL-30", "CL-03"],
)
async def test__an_empty_token_travels_unauthenticated(recorder: Recorder) -> None:
    """An empty token source is the unauthenticated call: no authorization header, no malformed bearer (CL-03)."""
    recorder.answer(200, ANSWER)
    http = httpx.AsyncClient(base_url="https://lineage-model.test", transport=recorder.transport())
    client = LineageModelClient(http, "")

    await client.get("e-1")

    assert "authorization" not in recorder.sent().headers
    await http.aclose()


@pytest.mark.covers(
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.get",
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.with_token",
    rules=["CL-02"],
)
async def test__the_pool_is_the_builders_to_close(recorder: Recorder) -> None:
    """The client has no close: it serves until its builder closes the pool (CL-02, DD-116)."""
    http = httpx.AsyncClient(base_url="https://lineage-model.test", transport=recorder.transport())
    client = LineageModelClient(http, "tok")
    borrowed = client.with_token("caller-token")
    recorder.answer(200, ANSWER)
    recorder.answer(200, ANSWER)

    await client.get("e-1")  # the pool is open for the client…
    await borrowed.get("e-1")  # …and for every wrapper of it

    await http.aclose()  # the builder closes — the API client never does
    recorder.answer(200, ANSWER)
    with pytest.raises(RuntimeError):  # httpx's own "client is already closed"
        await client.get("e-1")


@pytest.mark.covers("aurelius_atlas_lineage_model_client.client.LineageModelClient.get", rules=["CL-30", "CL-03"])
async def test__get_asks_the_endpoint_with_the_query(recorder: Recorder) -> None:
    """``GET /?guid=&depth=&direction=`` — the LM-01 query, bearer on it."""
    recorder.answer(200, ANSWER)

    answer = await _client(recorder).get("e-1", depth=5, direction="INPUT")

    sent = recorder.sent()
    assert sent.method == "GET"
    assert dict(sent.url.params) == {"guid": "e-1", "depth": "5", "direction": "INPUT"}
    assert sent.headers["authorization"] == "Bearer tok"
    assert isinstance(answer, LineageModelResponse)


@pytest.mark.covers("aurelius_atlas_lineage_model_client.client.LineageModelClient.get", rules=["CL-30", "CL-04"])
async def test__the_empty_answer_is_none(recorder: Recorder) -> None:
    """A 204 (LM-05/LM-06's no-lineage) is the caller's success path, not an error (CL-04)."""
    recorder.answer(204)

    assert await _client(recorder).get("ghost") is None


@pytest.mark.covers("aurelius_atlas_lineage_model_client.client.LineageModelClient.get", rules=["CL-04"])
async def test__a_rejected_query_raises_with_the_status_and_the_error_body(recorder: Recorder) -> None:
    """The DV-20/DV-21 400, with the Atlas-shaped body in the error (CL-04)."""
    recorder.answer(400, ERROR_BODY)

    with pytest.raises(LineageModelClientError) as raised:
        await _client(recorder).get(
            "e-1", direction=cast("Direction", "SIDEWAYS")
        )  # the DV-20 query, through the client

    assert raised.value.status_code == 400
    assert raised.value.error_code == "ATLAS-400-00-029"
    assert "invalid lineage request" in str(raised.value)


@pytest.mark.covers("aurelius_atlas_lineage_model_client.client.LineageModelClient.get", rules=["CL-04", "CL-05"])
async def test__an_upstream_failure_raises_and_an_unreachable_service_propagates(recorder: Recorder) -> None:
    """The app's 502 (DV-22) starts as a ``LineageModelClientError`` here; a refused socket stays httpx's (CL-05)."""
    recorder.answer(502, ERROR_BODY)
    with pytest.raises(LineageModelClientError) as raised:
        await _client(recorder).get("e-1")
    assert raised.value.status_code == 502

    recorder.handler = lambda _request: (_ for _ in ()).throw(httpx.ConnectError("refused"))
    with pytest.raises(httpx.ConnectError):
        await _client(recorder).get("e-1")
