"""The ValidateEntityClient against the recording transport (CL-01..CL-05, CL-40; DD-115, DD-116).

Every call answers from the externally provided httpx client the test hands in —
its transport is a recorder, no socket opens (CL-02); each test names the methods
it exercises (ADR 049) and the rules it enforces.
"""

import json

import httpx2 as httpx
import pytest
from aurelius_atlas_validate_entity_client.client import ValidateEntityClient, ValidateEntityClientError
from aurelius_atlas_validate_entity_client.models import ValidationResponse
from pydantic import ValidationError
from ve_recorder import Recorder

ANSWER: dict[str, object] = {
    "dataEntity": {"items": [], "isNonCompliant": True},
    "definition": {"items": [], "isNonCompliant": False},
    "domainLead": {"items": [], "isNonCompliant": True},
    "name": {"items": [], "isNonCompliant": False},
}
ERROR_BODY = {"errorCode": "ATLAS-401-00-001", "errorMessage": "no credential"}


def _client(recorder: Recorder) -> ValidateEntityClient:
    """The client under test: an externally built httpx client on the recorder (CL-02, CL-01)."""
    return ValidateEntityClient(
        httpx.AsyncClient(base_url="https://validate-entity.test", transport=recorder.transport()), "tok"
    )


@pytest.mark.covers(
    "aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate",
    "aurelius_atlas_validate_entity_client.client.ValidateEntityClient.with_token",
    rules=["CL-40", "CL-03", "CL-02"],
)
async def test__with_token_shares_the_pool_and_speaks_with_the_new_token(
    recorder: Recorder, tracked_client_http: httpx.AsyncClient
) -> None:
    """The wrapper posts the caller's token on the owner's connection pool (CL-03)."""
    owner = ValidateEntityClient(tracked_client_http, "service-token")
    recorder.answer(200, ANSWER)

    answer = await owner.with_token("browser-token").validate({"guid": "e-1"})

    assert answer.name.is_non_compliant is False
    assert recorder.sent().headers["authorization"] == "Bearer browser-token"
    await tracked_client_http.aclose()


@pytest.mark.covers(
    "aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate",
    rules=["CL-40", "CL-03"],
)
async def test__an_empty_token_travels_unauthenticated(recorder: Recorder) -> None:
    """An empty token source is the unauthenticated call: no authorization header, no malformed bearer (CL-03)."""
    recorder.answer(200, ANSWER)
    http = httpx.AsyncClient(base_url="https://validate-entity.test", transport=recorder.transport())
    client = ValidateEntityClient(http, "")

    await client.validate({"guid": "e-1"})

    assert "authorization" not in recorder.sent().headers
    await http.aclose()


@pytest.mark.covers(
    "aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate",
    "aurelius_atlas_validate_entity_client.client.ValidateEntityClient.with_token",
    rules=["CL-02"],
)
async def test__the_pool_is_the_builders_to_close(recorder: Recorder) -> None:
    """The client has no close: it serves until its builder closes the pool (CL-02, DD-116)."""
    http = httpx.AsyncClient(base_url="https://validate-entity.test", transport=recorder.transport())
    client = ValidateEntityClient(http, "tok")
    borrowed = client.with_token("caller-token")
    recorder.answer(200, ANSWER)
    recorder.answer(200, ANSWER)

    await client.validate({"guid": "e-1"})  # the pool is open for the client…
    await borrowed.validate({"guid": "e-1"})  # …and for every wrapper of it

    await http.aclose()  # the builder closes — the API client never does
    recorder.answer(200, ANSWER)
    with pytest.raises(RuntimeError):  # httpx's own "client is already closed"
        await client.validate({"guid": "e-1"})


@pytest.mark.covers(
    "aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate", rules=["CL-40", "CL-03"]
)
async def test__validate_posts_the_entity_and_parses_the_cards(recorder: Recorder) -> None:
    """``POST /``: the entity as a plain mapping (the mock never reads it, VE-01), the cards parsed (VE-02)."""
    recorder.answer(200, ANSWER)

    answer = await _client(recorder).validate({"guid": "e-1", "typeName": "Dataset"})

    sent = recorder.sent()
    assert (sent.method, sent.url.path) == ("POST", "/")
    assert json.loads(sent.content) == {"guid": "e-1", "typeName": "Dataset"}
    assert sent.headers["authorization"] == "Bearer tok"
    assert isinstance(answer, ValidationResponse)
    assert answer.data_entity.is_non_compliant is True


@pytest.mark.covers("aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate", rules=["CL-04"])
async def test__a_missing_credential_raises_with_the_status_and_the_error_body(recorder: Recorder) -> None:
    """The 401 of VE-03, with the Atlas-shaped body in the error (CL-04)."""
    recorder.answer(401, ERROR_BODY)

    with pytest.raises(ValidateEntityClientError) as raised:
        await _client(recorder).validate({})

    assert raised.value.status_code == 401
    assert raised.value.error_code == "ATLAS-401-00-001"
    assert "no credential" in str(raised.value)


@pytest.mark.covers("aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate", rules=["CL-05"])
async def test__an_unreachable_service_propagates_httpxs_own_error(recorder: Recorder) -> None:
    """The client maps nothing: a transport failure is ``httpx``'s, the app's job (CL-05)."""
    recorder.handler = lambda _request: (_ for _ in ()).throw(httpx.ConnectError("refused"))

    with pytest.raises(httpx.ConnectError):
        await _client(recorder).validate({})


# ---------------------------------------------------------------------------
# 8.7 — the failure contract: malformed successes, outage bodies, raising sources
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate", rules=["CL-08"])
async def test__a_200_with_a_body_of_the_wrong_shape_is_the_contract_failing(recorder: Recorder) -> None:
    """A success that is not the contract: the model rejects the body, pydantic's error travels (CL-08)."""
    recorder.answer(200, {"nope": True})

    with pytest.raises(ValidationError):
        await _client(recorder).validate({})


@pytest.mark.covers("aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate", rules=["CL-08"])
async def test__a_200_of_plain_text_is_the_contract_failing(recorder: Recorder) -> None:
    """A 200 that is not JSON: the client parses through its model and never swallows (CL-08)."""
    recorder.answer(200, text="I am not a validation document")

    with pytest.raises(ValidationError):
        await _client(recorder).validate({})


@pytest.mark.covers("aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate", rules=["CL-04"])
async def test__a_server_outage_answer_carries_the_status_and_the_fields(recorder: Recorder) -> None:
    """The 5xx with an Atlas body — the shape the webapp's alert rides (CL-04)."""
    recorder.answer(502, ERROR_BODY)

    with pytest.raises(ValidateEntityClientError) as raised:
        await _client(recorder).validate({})

    assert raised.value.status_code == 502
    assert raised.value.error_code == "ATLAS-401-00-001"


@pytest.mark.covers("aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate", rules=["CL-05"])
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
        await _client(recorder).validate({})


@pytest.mark.covers("aurelius_atlas_validate_entity_client.client.ValidateEntityClient.validate", rules=["CL-03"])
async def test__a_token_source_that_raises_travels_out_unsent(recorder: Recorder) -> None:
    """A credential fetch that fails is the caller's error, and nothing reaches the wire (CL-03).

    The bearer is read before the request, so a failing source never speaks.
    """
    broken = "the credential store is down"

    def token_source() -> str:
        raise RuntimeError(broken)

    http = httpx.AsyncClient(base_url="https://validate-entity.test", transport=recorder.transport())
    with pytest.raises(RuntimeError, match="credential store"):
        await ValidateEntityClient(http, token_source).validate({})
    await http.aclose()

    assert recorder.requests == []  # no bearer, no request
