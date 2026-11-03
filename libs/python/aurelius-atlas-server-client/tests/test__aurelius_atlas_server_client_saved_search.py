"""``SearchApi``'s DSL search and saved searches against the recorder (CSD-01..CSD-06).

The seven 8.4 search routes stay where they are (``test__aurelius_atlas_server_client_search.py``,
CSD-06 — unchanged); this file holds the eight routes 8.12 adds to ``SearchApi``:
``GET /dsl`` and the seven saved-search routes of ``routes/discovery.py`` (CL-02).
The 204-to-``None`` of a missing profile gets its own test — the distinction a
caller can lose silently (CSD-03).
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_model.discovery import QuickSearchParameters, SearchParameters
from aurelius_atlas_model.profile import AtlasUserSavedSearch
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError
from server_recorder import Recorder

G_SEARCH = "00000000-0000-4000-8000-000000000011"
ROOT = "/api/atlas/v2/search"
"""The mounted prefix of the route module, as the server answers it."""

SEARCH_RESULT: dict[str, Any] = {
    "queryType": "BASIC",
    "entities": [{"guid": "g-1", "typeName": "hive_table", "displayText": "t"}],
    "approximateCount": 1,
}
SAVED: dict[str, Any] = {
    "guid": G_SEARCH,
    "ownerName": "analyst",
    "name": "my_tables",
    "searchType": "BASIC",
    "searchParameters": {"query": "table"},
}
"""The saved search record, read and saved answers alike (SVS-01)."""

SUGGESTIONS: dict[str, Any] = {"prefixString": "pi", "suggestions": ["PII", "Pii"]}
ERROR_BODY: dict[str, Any] = {"errorCode": "ATLAS-400-00-06B", "errorMessage": "no such saved search"}


def _client(recorder: Recorder) -> AtlasClient:
    """The client under test on the recording transport (CL-02)."""
    return AtlasClient(httpx.AsyncClient(base_url="https://atlas.test", transport=recorder.transport()), "tok")


def _params(request: httpx.Request) -> dict[str, str]:
    """The request's query parameters."""
    return dict(request.url.params.multi_items())


def _body(request: httpx.Request) -> Any:  # noqa: ANN401 - the JSON body of the request
    """The request's JSON body."""
    return json.loads(request.content)


def _saved_search() -> AtlasUserSavedSearch:
    """A saved search of a basic query, its owner the acting user (DD-309)."""
    return AtlasUserSavedSearch(
        guid=G_SEARCH,
        owner_name="analyst",
        name="my_tables",
        search_parameters=SearchParameters(query="table"),
    )


@pytest.mark.covers("aurelius_atlas_server_client.client.SearchApi.search_using_dsl", rules=["CSD-01"])
async def test__the_dsl_search_sends_no_parameters_by_default(recorder: Recorder) -> None:
    """Limit 0 and offset 0 are the server's defaults: absence carries them; no text parameter is sent empty."""
    recorder.answer(200, SEARCH_RESULT)

    result = await _client(recorder).search.search_using_dsl()

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/dsl"
    assert sent.url.params.multi_items() == []
    assert result.approximate_count == 1


@pytest.mark.covers("aurelius_atlas_server_client.client.SearchApi.search_using_dsl", rules=["CSD-01"])
async def test__the_dsl_search_sends_every_query_parameter(recorder: Recorder) -> None:
    """The query, typeName, classification and page travel as the route's parameters (DSE-01, DSE-02)."""
    recorder.answer(200, SEARCH_RESULT)

    await _client(recorder).search.search_using_dsl(
        query="hive_table where name like 'a'", type_name="hive_table", classification="PII", limit=10, offset=5
    )

    assert _params(recorder.sent()) == {
        "query": "hive_table where name like 'a'",
        "typeName": "hive_table",
        "classification": "PII",
        "limit": "10",
        "offset": "5",
    }


@pytest.mark.covers("aurelius_atlas_server_client.client.SearchApi.search_using_dsl", rules=["CSD-01"])
async def test__the_dsl_search_raises_the_length_answer(recorder: Recorder) -> None:
    """The length checks are the server's: an over-long query is sent unchecked and its 400 raised (CL-04).

    The server's limit is ``MAX_DSL_QUERY_LENGTH`` (4096) — ``INVALID_QUERY_LENGTH``;
    the client pre-validates nothing (CSD-01).
    """
    recorder.answer(400, ERROR_BODY)

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).search.search_using_dsl(query="x" * 10_000)

    assert raised.value.status_code == 400
    assert len(_params(recorder.sent())["query"]) == 10_000


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.add_saved_search",
    "aurelius_atlas_server_client.client.SearchApi.update_saved_search",
    rules=["CSD-02"],
)
async def test__add_and_update_saved_search_send_the_body_and_return_the_answer(recorder: Recorder) -> None:
    """``POST /saved`` and ``PUT /saved``: the model as JSON, the server's saved answer back (SVS-02, SVS-03)."""
    recorder.answer(200, SAVED)
    recorder.answer(200, SAVED)
    client = _client(recorder)

    added = await client.search.add_saved_search(_saved_search())
    updated = await client.search.update_saved_search(_saved_search())

    assert [(request.method, request.url.path) for request in recorder.requests] == [
        ("POST", f"{ROOT}/saved"),
        ("PUT", f"{ROOT}/saved"),
    ]
    for request in recorder.requests:
        assert _body(request) == _saved_search().to_json()
    assert (added.guid, updated.guid) == (G_SEARCH, G_SEARCH)


@pytest.mark.covers("aurelius_atlas_server_client.client.SearchApi.saved_searches", rules=["CSD-03"])
async def test__saved_searches_lists_the_users_searches(recorder: Recorder) -> None:
    """``GET /saved`` of the acting user: no parameter by default (SVS-04)."""
    recorder.answer(200, [SAVED])

    found = await _client(recorder).search.saved_searches()

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/saved"
    assert sent.url.params.multi_items() == []
    assert found is not None
    assert found[0].name == "my_tables"


@pytest.mark.covers("aurelius_atlas_server_client.client.SearchApi.saved_searches", rules=["CSD-03"])
async def test__saved_searches_sends_the_user_parameter_when_given(recorder: Recorder) -> None:
    """A ``user`` travels as the query parameter; the acting user is the server's default."""
    recorder.answer(200, [])

    found = await _client(recorder).search.saved_searches(user="other")

    assert _params(recorder.sent()) == {"user": "other"}
    assert found == []


@pytest.mark.covers("aurelius_atlas_server_client.client.SearchApi.saved_searches", rules=["CSD-03"])
async def test__a_missing_profile_answers_none_not_an_empty_list(recorder: Recorder) -> None:
    """The 204 of "no profile" is ``None``: distinct from the ``[]`` of a profile with no searches (SVS-04)."""
    recorder.answer(204)

    assert await _client(recorder).search.saved_searches() is None


@pytest.mark.covers("aurelius_atlas_server_client.client.SearchApi.saved_search", rules=["CSD-04"])
async def test__saved_search_reads_by_name(recorder: Recorder) -> None:
    """``GET /saved/{name}`` with the optional user parameter (SVS-04)."""
    recorder.answer(200, SAVED)

    found = await _client(recorder).search.saved_search("my_tables", user="other")

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/saved/my_tables"
    assert _params(sent) == {"user": "other"}
    assert found.guid == G_SEARCH


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.saved_search",
    "aurelius_atlas_server_client.client.SearchApi.delete_saved_search",
    rules=["CSD-04"],
)
async def test__the_saved_search_verbs_read_by_name_and_delete_by_guid(recorder: Recorder) -> None:
    """The asymmetry is the server's: the read path is the name, the delete path the GUID (SVS-04, SVS-05)."""
    recorder.answer(200, SAVED)
    recorder.answer(204)
    client = _client(recorder)

    found = await client.search.saved_search("my_tables")
    await client.search.delete_saved_search(G_SEARCH)

    get_request, delete_request = recorder.requests
    assert get_request.url.path == f"{ROOT}/saved/my_tables"
    assert delete_request.method == "DELETE"
    assert delete_request.url.path == f"{ROOT}/saved/{G_SEARCH}"
    assert found.name == "my_tables"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.execute_saved_search_by_name",
    "aurelius_atlas_server_client.client.SearchApi.execute_saved_search_by_guid",
    rules=["CSD-05"],
)
async def test__the_execute_verbs_run_the_saved_search(recorder: Recorder) -> None:
    """``GET /saved/execute/{name}`` and ``GET /saved/execute/guid/{guid}``: answers a search result (SVS-06)."""
    recorder.answer(200, SEARCH_RESULT)
    recorder.answer(200, SEARCH_RESULT)
    client = _client(recorder)

    by_name = await client.search.execute_saved_search_by_name("my_tables", user="other")
    by_guid = await client.search.execute_saved_search_by_guid(G_SEARCH)

    name_request, guid_request = recorder.requests
    assert name_request.url.path == f"{ROOT}/saved/execute/my_tables"
    assert _params(name_request) == {"user": "other"}
    assert guid_request.url.path == f"{ROOT}/saved/execute/guid/{G_SEARCH}"
    assert guid_request.url.params.multi_items() == []
    assert (by_name.approximate_count, by_guid.approximate_count) == (1, 1)


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.search_with_parameters",
    "aurelius_atlas_server_client.client.SearchApi.search_using_basic",
    "aurelius_atlas_server_client.client.SearchApi.search_using_attribute",
    "aurelius_atlas_server_client.client.SearchApi.search_using_full_text",
    "aurelius_atlas_server_client.client.SearchApi.quick_search",
    "aurelius_atlas_server_client.client.SearchApi.quick_search_using_query",
    "aurelius_atlas_server_client.client.SearchApi.get_suggestions",
    rules=["CSD-06"],
)
async def test__the_eight_four_search_routes_answer_where_they_always_did(recorder: Recorder) -> None:
    """CSD-06: the seven 8.4 methods still answer their seven paths, unchanged by 8.12 (CL-13 extended)."""
    for _ in range(6):
        recorder.answer(200, SEARCH_RESULT)
    recorder.answer(200, SUGGESTIONS)
    client = _client(recorder)

    await client.search.search_with_parameters(SearchParameters(type_name="hive_table"))
    await client.search.search_using_basic(query="t")
    await client.search.search_using_attribute(type_name="hive_table", attr_name="name", attr_value_prefix="a")
    await client.search.search_using_full_text("t")
    await client.search.quick_search(QuickSearchParameters(query="t", type_name="hive_table"))
    await client.search.quick_search_using_query(query="t", type_name="hive_table")
    await client.search.get_suggestions(prefix_string="pi")

    assert [(request.method, request.url.path) for request in recorder.requests] == [
        ("POST", f"{ROOT}/basic"),
        ("GET", f"{ROOT}/basic"),
        ("GET", f"{ROOT}/attribute"),
        ("GET", f"{ROOT}/fulltext"),
        ("POST", f"{ROOT}/quick"),
        ("GET", f"{ROOT}/quick"),
        ("GET", f"{ROOT}/suggestions"),
    ]
