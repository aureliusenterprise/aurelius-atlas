"""The search endpoints of ``DiscoveryREST`` under ``/api/atlas/v2/search`` (SRC-02, FTX-05, QSR-01, SUG-01, DSE-01).

``searchUsingBasic``, ``searchWithParameters``, ``searchUsingAttribute``, ``searchUsingFullText``, both
``quickSearch``, ``getSuggestions``, ``searchUsingDSL`` and the saved searches of the acting user (SVS-01 to
SVS-07).
"""

from typing import Annotated

from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.suggestions_provider import SuggestionsProvider
from aurelius_atlas_model.discovery import (
    AtlasQuickSearchResult,
    AtlasSearchResult,
    AtlasSuggestionsResult,
    FilterCriteria,
    Operator,
    QuickSearchParameters,
    SearchParameters,
)
from aurelius_atlas_model.params import (
    FILTERS_WITHOUT_TYPE,
    NEGATIVE_PAGE,
    AttributeSearchParams,
    BasicSearchParams,
    DslSearchParams,
    FullTextSearchParams,
    QuickQueryParams,
    SavedSearchParams,
    SuggestionsParams,
    read_params,
)
from aurelius_atlas_model.profile import AtlasUserSavedSearch
from fastapi import APIRouter, Depends, Request, Response

from aurelius_atlas_server.authentication import acting_user
from aurelius_atlas_server.authorization import authorizer
from aurelius_atlas_server.bodies import json_model
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.openapi import array_of, json_response, request_body
from aurelius_atlas_server.openapi import no_content as no_content_response
from aurelius_atlas_server.routes.entity import Store
from aurelius_atlas_server.routes.types import validate_param_length

DISCOVERY = APIRouter(prefix="/api/atlas/v2/search", tags=["Discovery"])

QUALIFIED_NAME = "qualifiedName"
NAME = "name"
FILTERS_WITHOUT_TAG = "TagFilters specified without tag name"
SORT_WITHOUT_TYPE = "SortBy specified without Type name"

SEARCH_BODY = json_model(SearchParameters)
"""``searchWithParameters``: the search parameters, validated by their model (SRC-02)."""

QUICK_BODY = json_model(QuickSearchParameters)
"""``quickSearch``: the quick-search parameters, validated by their model (QSR-01)."""

SAVED_BODY = json_model(AtlasUserSavedSearch)
"""``addSavedSearch``/``updateSavedSearch``: the saved search, validated by its model (SVS-02, SVS-03)."""

type SearchBody = Annotated[SearchParameters | None, Depends(SEARCH_BODY)]
type QuickBody = Annotated[QuickSearchParameters | None, Depends(QUICK_BODY)]
type SavedBody = Annotated[AtlasUserSavedSearch | None, Depends(SAVED_BODY)]


def _empty(criteria: FilterCriteria | None) -> bool:
    """``isEmpty``: no filter, or one without an attribute name and criteria."""
    return criteria is None or (not criteria.attribute_name and not criteria.criterion)


def validate_basic_search_parameters(parameters: SearchParameters) -> None:
    """``validateBasicSearchParameters`` (SRC-02).

    Raises:
        AtlasError: ``BAD_REQUEST``, ``INVALID_SEARCH_PARAMS`` or ``INVALID_QUERY_PARAM_LENGTH``.
    """
    if parameters.limit < 0 or parameters.offset < 0:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NEGATIVE_PAGE)
    if not parameters.type_name and not _empty(parameters.entity_filters):
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, FILTERS_WITHOUT_TYPE)
    if not parameters.classification and not _empty(parameters.tag_filters):
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, FILTERS_WITHOUT_TAG)
    if not (parameters.type_name or parameters.classification or parameters.query or parameters.term_name):
        raise AtlasError(AtlasErrorCode.INVALID_SEARCH_PARAMS)
    _validate_lengths(parameters)


def _validate_lengths(parameters: SearchParameters) -> None:
    """``validateSearchParameters``: the names and the query at their lengths, per ``BasicSearchParams`` (FTX-01).

    Raises:
        AtlasError: ``INVALID_QUERY_PARAM_LENGTH`` or ``INVALID_QUERY_LENGTH``.
    """
    BasicSearchParams(
        query=parameters.query,
        type_name=parameters.type_name,
        classification=parameters.classification,
        sort_by=parameters.sort_by,
    ).checked()


def _discovery(request: Request, store: EntityStore) -> EntityDiscoveryService:
    """The discovery service of a request, its saved searches checked as the entity store checks them (AUZ-10)."""
    return EntityDiscoveryService(store, authorizer=authorizer(request))


async def _search(request: Request, store: Store, parameters: SearchParameters) -> AtlasJSONResponse:
    result = await _discovery(request, store).search_with_parameters(parameters)
    return AtlasJSONResponse(content=result.to_json())


@DISCOVERY.post(
    "/basic",
    responses=json_response(AtlasSearchResult, description="The entities the search finds (SRC-02)."),
    **request_body(SearchParameters, required=False, description="The search parameters; no body is an empty search."),
)
async def search_with_parameters(request: Request, search_body: SearchBody, store: Store) -> AtlasJSONResponse:
    """``searchWithParameters``: the entities the body's search finds, validated first (SRC-02, SRC-09)."""
    parameters = search_body or SearchParameters()
    validate_basic_search_parameters(parameters)
    return await _search(request, store, parameters)


@DISCOVERY.get(
    "/basic",
    responses=json_response(AtlasSearchResult, description="The entities the query parameters find (SRC-11)."),
)
async def search_using_basic(request: Request, store: Store) -> AtlasJSONResponse:
    """``searchUsingBasic``: a search of the query parameters, not validated as the body's is (SRC-11)."""
    asked = read_params(BasicSearchParams, request.query_params)
    asked.checked()
    parameters = SearchParameters(
        query=asked.query,
        type_name=asked.type_name,
        classification=asked.classification,
        sort_by=asked.sort_by,
        sort_order=asked.sort_order,
        exclude_deleted_entities=asked.exclude_deleted_entities,
        limit=asked.limit,
        offset=asked.offset,
        marker=asked.marker,
    )
    return await _search(request, store, parameters)


@DISCOVERY.get(
    "/fulltext",
    responses=json_response(
        AtlasSearchResult, description="The entities matching the query, best first, with scores (FTX-05)."
    ),
)
async def search_using_full_text(request: Request, store: Store) -> AtlasJSONResponse:
    """``searchUsingFullText``: the entities matching ``query``, best first, with their scores (FTX-05)."""
    asked = read_params(FullTextSearchParams, request.query_params)
    result = await _discovery(request, store).search_using_full_text(
        asked.checked(),
        exclude_deleted_entities=asked.exclude_deleted_entities,
        limit=asked.limit,
        offset=asked.offset,
    )
    return AtlasJSONResponse(content=result.to_json())


@DISCOVERY.get(
    "/dsl",
    responses=json_response(AtlasSearchResult, description="The entities a DSL query finds (DSE-01)."),
)
async def search_using_dsl(request: Request, store: Store) -> AtlasJSONResponse:
    """``searchUsingDSL``: the entities a DSL query finds, of ``typeName`` and ``classification`` (DSE-01, DSE-02)."""
    asked = read_params(DslSearchParams, request.query_params)
    validate_dsl_search_parameters(asked.query, asked.type_name, asked.classification)
    service = _discovery(request, store)
    result = await service.search_using_dsl_query(
        service.get_dsl_query_using_type_name_classification(asked.query, asked.type_name, asked.classification),
        asked.limit,
        asked.offset,
    )
    return AtlasJSONResponse(content=result.to_json())


def validate_dsl_search_parameters(query: str | None, type_name: str | None, classification: str | None) -> None:
    """``validateDSLSearchParameters``: the names and the query at their lengths, per ``DslSearchParams`` (DSE-01).

    Raises:
        AtlasError: ``INVALID_QUERY_PARAM_LENGTH`` or ``INVALID_QUERY_LENGTH``.
    """
    DslSearchParams(query=query, type_name=type_name, classification=classification).checked()


def validate_quick_search_parameters(parameters: QuickSearchParameters) -> None:
    """The checks of ``quickSearch(QuickSearchParameters)`` and its ``validateSearchParameters`` (QSR-01).

    Raises:
        AtlasError: ``BAD_REQUEST``, ``INVALID_SEARCH_PARAMS``, ``INVALID_QUERY_PARAM_LENGTH`` or
            ``INVALID_QUERY_LENGTH``.
    """
    if parameters.limit < 0 or parameters.offset < 0:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NEGATIVE_PAGE)
    if not parameters.type_name and not _empty(parameters.entity_filters):
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, FILTERS_WITHOUT_TYPE)
    if not parameters.type_name and not parameters.query:
        raise AtlasError(AtlasErrorCode.INVALID_SEARCH_PARAMS)
    if not parameters.type_name and parameters.sort_by:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, SORT_WITHOUT_TYPE)
    _validate_lengths(parameters.search_parameters())


async def _quick(request: Request, store: Store, parameters: QuickSearchParameters) -> AtlasJSONResponse:
    result = await _discovery(request, store).quick_search(parameters)
    return AtlasJSONResponse(content=result.to_json())


@DISCOVERY.get(
    "/quick",
    responses=json_response(
        AtlasQuickSearchResult, description="The entities and the relation count the query quick-finds (QSR-01)."
    ),
)
async def quick_search_using_query(request: Request, store: Store) -> AtlasJSONResponse:
    """``quickSearch`` of query parameters: without sub types, only the query's length checked (QSR-01, QSR-02)."""
    asked = read_params(QuickQueryParams, request.query_params)
    asked.checked()
    parameters = QuickSearchParameters(
        query=asked.query,
        type_name=asked.type_name,
        exclude_deleted_entities=asked.exclude_deleted_entities,
        offset=asked.offset,
        limit=asked.limit,
        sort_by=asked.sort_by,
        sort_order=asked.sort_order,
    )
    return await _quick(request, store, parameters)


@DISCOVERY.post(
    "/quick",
    responses=json_response(
        AtlasQuickSearchResult, description="The entities and the relation count the parameters quick-find (QSR-01)."
    ),
    **request_body(
        QuickSearchParameters, required=False, description="The quick-search parameters; no body is an empty search."
    ),
)
async def quick_search(request: Request, quick_body: QuickBody, store: Store) -> AtlasJSONResponse:
    """``quickSearch`` of ``QuickSearchParameters``, validated first (QSR-01 to QSR-04)."""
    parameters = quick_body or QuickSearchParameters()
    validate_quick_search_parameters(parameters)
    return await _quick(request, store, parameters)


@DISCOVERY.get(
    "/suggestions",
    responses=json_response(
        AtlasSuggestionsResult, description="Terms beginning with the prefix, weighted by field (SUG-01)."
    ),
)
async def get_suggestions(request: Request, store: Store) -> AtlasJSONResponse:
    """``getSuggestions``: terms beginning with ``prefixString``, of ``fieldName`` or the heaviest fields (SUG-01)."""
    asked = read_params(SuggestionsParams, request.query_params)
    result = await SuggestionsProvider(store).suggestions(asked.prefix_string, asked.field_name)
    return AtlasJSONResponse(content=result.to_json())


@DISCOVERY.get(
    "/attribute",
    responses=json_response(AtlasSearchResult, description="Entities whose attribute starts with the prefix (SRC-11)."),
)
async def search_using_attribute(request: Request, store: Store) -> AtlasJSONResponse:
    """``searchUsingAttribute``: entities whose attribute starts with the prefix (SRC-11).

    Raises:
        AtlasError: ``INVALID_PARAMETERS`` without ``attrName`` and ``attrValuePrefix``.
    """
    asked = read_params(AttributeSearchParams, request.query_params)
    asked.checked()
    attr_name = asked.attr_name
    if not attr_name:
        entity_type = None if asked.type_name is None else store.registry.entity_type(asked.type_name)
        attr_name = next(
            (name for name in (QUALIFIED_NAME, NAME) if entity_type is not None and entity_type.attribute(name)),
            QUALIFIED_NAME,
        )
    parameters = SearchParameters(
        type_name=asked.type_name,
        entity_filters=FilterCriteria(
            attribute_name=attr_name, operator=Operator.STARTS_WITH, attribute_value=asked.attr_value_prefix
        ),
        limit=asked.limit,
        offset=asked.offset,
    )
    validate_basic_search_parameters(parameters)
    return await _search(request, store, parameters)


NO_SAVED_SEARCH = "The saved search is missing"


def _saved_search(saved_search: AtlasUserSavedSearch | None) -> AtlasUserSavedSearch:
    """``validateUserSavedSearch``: the body's search, its names and parameters of query-parameter length (SVS-07).

    Raises:
        AtlasError: ``BAD_REQUEST`` without a body (DV-110), ``INVALID_QUERY_PARAM_LENGTH`` or
            ``INVALID_QUERY_LENGTH``.
    """
    if saved_search is None:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_SAVED_SEARCH)
    for name, value in (
        ("name", saved_search.name),
        ("ownerName", saved_search.owner_name),
        ("guid", saved_search.guid),
    ):
        if value is not None:
            validate_param_length(name, value)
    if saved_search.search_parameters is not None:
        _validate_lengths(saved_search.search_parameters)
    return saved_search


def _validate_user(request: Request) -> str | None:
    return read_params(SavedSearchParams, request.query_params).checked()


@DISCOVERY.post(
    "/saved",
    responses=json_response(AtlasUserSavedSearch, description="The saved search, with its GUID and owner (SVS-02)."),
    **request_body(AtlasUserSavedSearch, description="The search to save for the acting user."),
)
async def add_saved_search(request: Request, saved_body: SavedBody, store: Store) -> AtlasJSONResponse:
    """``addSavedSearch``: the body's search, saved for the acting user (SVS-02)."""
    found = await _discovery(request, store).add_saved_search(acting_user(request), _saved_search(saved_body))
    return AtlasJSONResponse(content=found.to_json())


@DISCOVERY.put(
    "/saved",
    responses=json_response(AtlasUserSavedSearch, description="The updated saved search (SVS-03)."),
    **request_body(AtlasUserSavedSearch, description="The saved search to update, by its GUID."),
)
async def update_saved_search(request: Request, saved_body: SavedBody, store: Store) -> AtlasJSONResponse:
    """``updateSavedSearch``: the acting user's search of the body's GUID (SVS-03)."""
    found = await _discovery(request, store).update_saved_search(acting_user(request), _saved_search(saved_body))
    return AtlasJSONResponse(content=found.to_json())


@DISCOVERY.get(
    "/saved",
    responses={
        **json_response(array_of(AtlasUserSavedSearch), description="The user's saved searches (SVS-04)."),
        204: {"description": "The user has no saved searches."},
    },
)
async def get_saved_searches(request: Request, store: Store) -> Response:
    """``getSavedSearches``: the acting user's searches, nothing (204) without a profile (SVS-04)."""
    found = await _discovery(request, store).get_saved_searches(acting_user(request), _validate_user(request))
    if found is None:
        return Response(status_code=204)
    return AtlasJSONResponse(content=[saved.to_json() for saved in found])


@DISCOVERY.get(
    "/saved/execute/guid/{guid}",
    responses=json_response(AtlasSearchResult, description="The result of running the saved search (SVS-06)."),
)
async def execute_saved_search_by_guid(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``executeSavedSearchByGuid``: the acting user's search of the GUID, run (SVS-06)."""
    validate_param_length("guid", guid)
    service = _discovery(request, store)
    found = await service.get_saved_search_by_guid(acting_user(request), guid)
    return AtlasJSONResponse(content=(await service.execute_saved_search(found)).to_json())


@DISCOVERY.get(
    "/saved/execute/{name}",
    responses=json_response(AtlasSearchResult, description="The result of running the saved search (SVS-06)."),
)
async def execute_saved_search_by_name(name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``executeSavedSearchByName``: the acting user's search of the name, run (SVS-06)."""
    validate_param_length("name", name)
    service = _discovery(request, store)
    found = await service.get_saved_search_by_name(acting_user(request), _validate_user(request), name)
    return AtlasJSONResponse(content=(await service.execute_saved_search(found)).to_json())


@DISCOVERY.get(
    "/saved/{name}",
    responses=json_response(AtlasUserSavedSearch, description="The user's saved search of the name (SVS-04)."),
)
async def get_saved_search(name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getSavedSearch``: the acting user's search of the name (SVS-04)."""
    validate_param_length("name", name)
    found = await _discovery(request, store).get_saved_search_by_name(
        acting_user(request), _validate_user(request), name
    )
    return AtlasJSONResponse(content=found.to_json())


@DISCOVERY.delete(
    "/saved/{guid}",
    status_code=204,
    responses=no_content_response("The saved search is deleted (SVS-05)."),
)
async def delete_saved_search(guid: str, request: Request, store: Store) -> Response:
    """``deleteSavedSearch``: the acting user's search of the GUID (SVS-05)."""
    validate_param_length("guid", guid)
    await _discovery(request, store).delete_saved_search(acting_user(request), guid)
    return Response(status_code=204)
