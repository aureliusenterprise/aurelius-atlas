"""The search endpoints through the client library, against the container (CL-13).

The typed twin of the search scenarios: the same server, the same dev CA, the
bodies parsed into ``aurelius-atlas-model``'s contract models (CL-10) — the
client is proven against the real routes, not only the fake transport.
"""

from typing import Any

import pytest
from aurelius_atlas_model.discovery import QuickSearchParameters, SearchParameters
from aurelius_atlas_server_client import AtlasClient, AtlasClientError


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.search_with_parameters",
    "aurelius_atlas_server_client.client.SearchApi.search_using_basic",
    rules=["CL-13", "SRC-02", "SRC-11"],
)
async def test__the_basic_searches_answer_over_tls(api: AtlasClient) -> None:
    """``POST /search/basic`` with a type, ``GET /search/basic`` with a query (SRC-02, SRC-11)."""
    by_type = await api.search.search_with_parameters(
        SearchParameters(type_name="Asset", limit=5, exclude_deleted_entities=True)
    )
    assert by_type.query_type == "BASIC"
    assert by_type.approximate_count >= 0

    by_query = await api.search.search_using_basic(query="*", type_name="Asset", limit=5)
    assert by_query.query_type == "BASIC"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.search_using_full_text",
    rules=["CL-13", "FTX-05"],
)
async def test__the_fulltext_search_answers_with_scores(api: AtlasClient) -> None:
    """``GET /search/fulltext``: the FULL_TEXT answer shape, headers and scores (FTX-05)."""
    result = await api.search.search_using_full_text("table", limit=5)

    assert result.query_type == "FULL_TEXT"
    assert result.full_text_result is None or all(found.score is not None for found in result.full_text_result)


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.quick_search",
    "aurelius_atlas_server_client.client.SearchApi.quick_search_using_query",
    rules=["CL-13", "QSR-01", "QSR-02", "QSR-03"],
)
async def test__the_quick_searches_answer_with_facets(api: AtlasClient) -> None:
    """``POST /search/quick`` and ``GET /search/quick``: results plus ``aggregationMetrics`` (QSR-02, QSR-03)."""
    posted = await api.search.quick_search(QuickSearchParameters(query="*", type_name="Asset", limit=5))
    assert posted.search_results is not None
    metrics: dict[str, list[Any]] = posted.aggregation_metrics or {}
    assert "__typeName" in metrics
    assert "__state" in metrics

    fetched = await api.search.quick_search_using_query(query="*", type_name="Asset", limit=5)
    assert fetched.search_results is not None


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.get_suggestions",
    rules=["CL-13", "SUG-01"],
)
async def test__the_suggestions_answer_through_the_client(api: AtlasClient) -> None:
    """``GET /search/suggestions``: the prefix echoes back, terms are a list (SUG-01)."""
    result = await api.search.get_suggestions("ass")

    assert result.prefix_string == "ass"
    assert result.suggestions is None or len(result.suggestions) <= 5


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.SearchApi.quick_search",
    "aurelius_atlas_server_client.client.SearchApi.search_with_parameters",
    rules=["CL-13", "QSR-01", "CL-04"],
)
async def test__the_server_s_validation_reaches_the_caller(api: AtlasClient) -> None:
    """``sortBy`` without typeName (QSR-01) and an empty search (SRC-02) raise with the error body (CL-04)."""
    with pytest.raises(AtlasClientError) as raised:
        await api.search.quick_search(QuickSearchParameters(query="*", sort_by="name"))
    assert raised.value.status_code == 400
    assert raised.value.info is not None
    assert raised.value.info.error_code == "ATLAS-400-00-029"  # BAD_REQUEST: sortBy without typeName (QSR-01)

    with pytest.raises(AtlasClientError) as raised:
        await api.search.search_with_parameters(SearchParameters())
    assert raised.value.status_code == 400
    assert raised.value.info is not None
    assert raised.value.info.error_code == "ATLAS-400-00-047"  # INVALID_SEARCH_PARAMS (SRC-02)
