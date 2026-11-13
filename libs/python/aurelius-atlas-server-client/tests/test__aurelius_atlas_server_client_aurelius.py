"""``AureliusApi``'s four routes against the recording transport (CAV-01..CAV-04).

The Aurelius-native endpoints beside the Atlas ones: the two searches by meaning
of ``routes/search_by_meaning.py`` (SBM) and the two rule-vocabulary routes of
``routes/quality.py`` (QRE). The recorder pins method, path, query, and body for
every route (CL-02); the bodies are the client library's own models (DD-562) and
``aurelius-atlas-model``'s quick search result, reused whole (DD-309).
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_server_client.aurelius import SemanticSearchParameters
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError
from server_recorder import Recorder

G_ONE = "00000000-0000-4000-8000-00000000000f"
ROOT = "/api/aurelius/v1"
"""The mounted prefix of the two Aurelius-native route modules."""

QUICK_ANSWER: dict[str, Any] = {"searchResults": {"entities": [{"guid": G_ONE, "typeName": "Table"}]}}
VOCAB_ANSWER: dict[str, Any] = {
    "kinds": [{"name": "not-null", "dimension": "completeness", "required": [], "optional": [], "reason": "is null"}],
    "castableTypes": ["int", "float"],
    "thresholdMin": 0.0,
    "thresholdMax": 1.0,
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


@pytest.mark.covers("aurelius_atlas_server_client.client.AureliusApi.semantic_search", rules=["CAV-02"])
async def test__semantic_search_sends_the_body_with_its_mode(recorder: Recorder) -> None:
    """``POST /search/semantic``: quick search's parameters and the mode, as one body (SBM-01..SBM-04)."""
    recorder.answer(200, QUICK_ANSWER)

    found = await _client(recorder).aurelius.semantic_search(
        SemanticSearchParameters(query="revenue", mode="hybrid", limit=5)
    )

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/search/semantic"
    body = _body(sent)
    assert body["query"] == "revenue"
    assert body["mode"] == "hybrid"
    assert body["limit"] == 5
    assert "sortBy" not in body
    assert found.search_results is not None
    assert found.search_results.entities is not None
    assert found.search_results.entities[0].guid == G_ONE


@pytest.mark.covers("aurelius_atlas_server_client.client.AureliusApi.semantic_search", rules=["CAV-02"])
async def test__semantic_search_sends_no_mode_check_of_its_own(recorder: Recorder) -> None:
    """An unknown mode is the server's BAD_REQUEST, not the client's (CL-12, CAV-02)."""
    recorder.answer(400, {"errorCode": "ATLAS-400-00-001", "errorMessage": "mode must be one of semantic, hybrid"})

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).aurelius.semantic_search(SemanticSearchParameters(query="x", mode="fuzzy"))

    assert raised.value.status_code == 400
    assert raised.value.info is not None
    assert raised.value.info.error_code == "ATLAS-400-00-001"


@pytest.mark.covers("aurelius_atlas_server_client.client.AureliusApi.similar_entities", rules=["CAV-03"])
async def test__similar_entities_sends_the_page_parameters(recorder: Recorder) -> None:
    """``GET /entity/guid/{guid}/similar``: the page parameters as ``_present`` renders them (SBM-05, SBM-07)."""
    recorder.answer(200, QUICK_ANSWER)

    found = await _client(recorder).aurelius.similar_entities(G_ONE, type_name="Table", limit=10)

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/entity/guid/{G_ONE}/similar"
    assert _params(sent) == [("typeName", "Table"), ("limit", "10")]
    assert found.search_results is not None
    assert found.search_results.entities is not None
    assert found.search_results.entities[0].guid == G_ONE


@pytest.mark.covers("aurelius_atlas_server_client.client.AureliusApi.quality_kinds", rules=["CAV-04"])
async def test__quality_kinds_returns_the_vocabulary(recorder: Recorder) -> None:
    """``GET /quality/kinds``: the kinds, castable types and threshold bounds (QRE-01, DD-475)."""
    recorder.answer(200, VOCAB_ANSWER)

    found = await _client(recorder).aurelius.quality_kinds()

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/quality/kinds"
    assert [kind.name for kind in found.kinds] == ["not-null"]
    assert found.castable_types == ["int", "float"]


@pytest.mark.covers("aurelius_atlas_server_client.client.AureliusApi.validate_quality_rule", rules=["CAV-04"])
async def test__validate_quality_rule_sends_the_attributes_and_reads_both_verdicts(recorder: Recorder) -> None:
    """``POST /quality/rules/validate``: the bare attribute object in, the check out — both 200s (QRE-02/03)."""
    recorder.answer(200, {"valid": True, "kind": "not-null", "dimension": "completeness"})
    recorder.answer(200, {"valid": False, "reason": "unknown check kind"})
    client = _client(recorder)

    good = await client.aurelius.validate_quality_rule({"dq.check.kind": "not-null"})
    bad = await client.aurelius.validate_quality_rule({"dq.check.kind": "nonsense"})

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/quality/rules/validate"
    assert _body(sent) == {"dq.check.kind": "not-null"}
    assert good.kind == "not-null"
    assert not bad.valid
    assert bad.reason == "unknown check kind"
