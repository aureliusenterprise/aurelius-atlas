"""The SearchApi against the recording transport (CL-13; the routes of ``routes/discovery.py``).

Every call answers from the externally provided httpx client the test hands in —
its transport is a recorder, no socket opens (CL-02); each test names the methods
it exercises (ADR 049) and the rules it enforces.
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_model.discovery import (
    AtlasAggregationEntry,
    QuickSearchParameters,
    SearchParameters,
    SortOrder,
)
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError
from pydantic import ValidationError
from server_recorder import Recorder

SEARCH_RESULT: dict[str, Any] = {
    "queryType": "BASIC",
    "entities": [{"guid": "g-1", "typeName": "hive_table", "displayText": "t"}],
    "approximateCount": 1,
}
QUICK_RESULT: dict[str, Any] = {
    "searchResults": {"queryType": "BASIC", "entities": [], "approximateCount": 2},
    "aggregationMetrics": {"__typeName": [{"name": "hive_table", "count": 2}]},
}
SUGGESTIONS: dict[str, Any] = {"prefixString": "pi", "suggestions": ["PII", "Pii"]}
ERROR_BODY: dict[str, Any] = {"errorCode": "ATLAS-400-00-006", "errorMessage": "no type name"}


def _client(recorder: Recorder, token: str = "tok") -> AtlasClient:  # noqa: S107 - a fixed fake credential, not a secret
    """The client under test: an externally built httpx client on the recorder (CL-02, CL-01)."""
    return AtlasClient(httpx.AsyncClient(base_url="https://atlas.test", transport=recorder.transport()), token)


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.search_with_parameters",
    rules=["CL-13", "CL-10", "CL-03"],
)
async def test__the_basic_post_search_sends_the_parameters_as_body(recorder: Recorder) -> None:
    """``POST /search/basic``: the body is ``SearchParameters.to_json()``, the answer is parsed (SRC-02)."""
    recorder.answer(200, SEARCH_RESULT)
    parameters = SearchParameters(type_name="hive_table", limit=10, include_sub_types=True)

    result = await _client(recorder).search.search_with_parameters(parameters)

    assert result.query_type == "BASIC"
    assert result.entities is not None
    assert result.entities[0].guid == "g-1"
    assert result.approximate_count == 1
    sent = recorder.sent()
    assert (sent.method, sent.url.path) == ("POST", "/api/atlas/v2/search/basic")
    assert json.loads(sent.content) == parameters.to_json()
    assert sent.headers["authorization"] == "Bearer tok"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.search_using_basic",
    "aurelius_atlas_server_client.client._present",
    rules=["CL-13"],
)
async def test__the_basic_get_search_carries_its_query_parameters(recorder: Recorder) -> None:
    """``GET /search/basic``: the given parameters travel, the Java defaults (0, false) and None do not (SRC-11)."""
    recorder.answer(200, SEARCH_RESULT)

    await _client(recorder).search.search_using_basic(
        query="table",
        type_name="Asset",
        exclude_deleted_entities=True,
        limit=20,
        sort_order=SortOrder.DESCENDING,
    )

    sent = recorder.sent()
    assert (sent.method, sent.url.path) == ("GET", "/api/atlas/v2/search/basic")
    assert dict(sent.url.params) == {
        "query": "table",
        "typeName": "Asset",
        "excludeDeletedEntities": "true",
        "limit": "20",
        "sortOrder": "DESCENDING",
    }


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.search_using_attribute",
    rules=["CL-13"],
)
async def test__the_attribute_search_sends_the_prefix_criteria(recorder: Recorder) -> None:
    """``GET /search/attribute``: attrName, attrValuePrefix and typeName (SRC-11)."""
    recorder.answer(200, SEARCH_RESULT)

    result = await _client(recorder).search.search_using_attribute(
        type_name="hive_table", attr_name="qualifiedName", attr_value_prefix="staging.", limit=5
    )

    assert result.entities is not None
    assert dict(recorder.sent().url.params) == {
        "typeName": "hive_table",
        "attrName": "qualifiedName",
        "attrValuePrefix": "staging.",
        "limit": "5",
    }


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.search_using_full_text",
    rules=["CL-13"],
)
async def test__the_fulltext_search_sends_the_query_and_page(recorder: Recorder) -> None:
    """``GET /search/fulltext``: query, excludeDeletedEntities, limit (FTX-05)."""
    recorder.answer(200, {"queryType": "FULL_TEXT", "fullTextResult": [{"entity": {"guid": "g"}, "score": 9.5}]})

    result = await _client(recorder).search.search_using_full_text("sales", exclude_deleted_entities=True, limit=7)

    assert result.query_type == "FULL_TEXT"
    assert result.full_text_result is not None
    assert result.full_text_result[0].score == 9.5
    assert dict(recorder.sent().url.params) == {"query": "sales", "excludeDeletedEntities": "true", "limit": "7"}


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.quick_search",
    rules=["CL-13", "CL-10"],
)
async def test__the_quick_post_search_answers_with_results_and_facets(recorder: Recorder) -> None:
    """``POST /search/quick``: the body is ``QuickSearchParameters.to_json()``, facets are parsed (QSR-01, QSR-03)."""
    recorder.answer(200, QUICK_RESULT)
    parameters = QuickSearchParameters(query="tab", type_name="Asset")

    result = await _client(recorder).search.quick_search(parameters)

    assert result.search_results is not None
    assert result.search_results.approximate_count == 2
    metrics = result.aggregation_metrics or {}
    assert metrics["__typeName"] == [AtlasAggregationEntry(name="hive_table", count=2)]
    sent = recorder.sent()
    assert (sent.method, sent.url.path) == ("POST", "/api/atlas/v2/search/quick")
    assert json.loads(sent.content) == parameters.to_json()


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.quick_search_using_query",
    rules=["CL-13"],
)
async def test__the_quick_get_search_carries_its_query_parameters(recorder: Recorder) -> None:
    """``GET /search/quick``: the query and typeName travel; the route checks only their length (QSR-01)."""
    recorder.answer(200, QUICK_RESULT)

    result = await _client(recorder).search.quick_search_using_query(query="tab", type_name="Asset", offset=10)

    assert result.search_results is not None
    assert dict(recorder.sent().url.params) == {"query": "tab", "typeName": "Asset", "offset": "10"}


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.get_suggestions",
    rules=["CL-13"],
)
async def test__the_suggestions_call_sends_the_prefix_and_field(recorder: Recorder) -> None:
    """``GET /search/suggestions``: prefixString and the optional fieldName (SUG-01, SUG-02)."""
    recorder.answer(200, SUGGESTIONS)

    result = await _client(recorder).search.get_suggestions("pi", field_name="__typeName")

    assert result.suggestions == ["PII", "Pii"]
    assert result.prefix_string == "pi"
    assert dict(recorder.sent().url.params) == {"prefixString": "pi", "fieldName": "__typeName"}


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.quick_search_using_query",
    rules=["CL-13", "CL-04"],
)
async def test__a_search_error_raises_with_the_status_and_the_atlas_body(recorder: Recorder) -> None:
    """A 400 (sortBy without typeName, QSR-01) raises ``AtlasClientError`` with the server's error body (CL-04)."""
    recorder.answer(400, ERROR_BODY)

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).search.quick_search_using_query(sort_by="name")

    assert raised.value.status_code == 400
    assert raised.value.info is not None
    assert raised.value.info.error_code == "ATLAS-400-00-006"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.search_with_parameters",
    rules=["CL-13", "CL-05"],
)
async def test__an_unreachable_server_propagates_as_httpx_error(recorder: Recorder) -> None:
    """A transport failure is httpx's own error, not an ``AtlasClientError`` — the app maps it (CL-05)."""
    recorder.handler = lambda _request: (_ for _ in ()).throw(httpx.ConnectError("refused"))

    with pytest.raises(httpx.ConnectError):
        await _client(recorder).search.search_with_parameters(SearchParameters(query="*"))


def test__the_parameters_serialise_as_the_server_reads_them() -> None:
    """The bodies are ``aurelius-atlas-model``'s whole (CL-10): camelCase aliases, None keys dropped.

    A body with an unknown key validates leniently, as the server's ``model_body`` reads one (CL-06).
    """
    parameters = SearchParameters.model_validate({"typeName": "Asset", "limit": "5", "unknown": 1})
    payload = parameters.to_json()

    assert (payload["typeName"], payload["limit"]) == ("Asset", 5)
    assert "query" not in payload  # an unset value is no key (exclude_none)
    assert "unknown" not in payload  # an unknown key is ignored, never echoed (CL-06)
    with pytest.raises(ValidationError):
        SearchParameters.model_validate({"limit": "not a number"})
