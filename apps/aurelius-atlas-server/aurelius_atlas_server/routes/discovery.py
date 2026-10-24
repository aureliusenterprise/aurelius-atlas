"""The basic and full-text search endpoints of ``DiscoveryREST`` under ``/api/atlas/v2/search`` (SRC-02, FTX-05).

``searchUsingBasic``, ``searchWithParameters``, ``searchUsingAttribute`` and ``searchUsingFullText``; the other
searches follow in later increments (4.2b, 4.4, 4.5).
"""

from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.free_text import MAX_QUERY_LENGTH
from aurelius_atlas_model.discovery import FilterCriteria, Operator, SearchParameters, SortOrder
from aurelius_atlas_model.errors import java_string
from fastapi import APIRouter, Request

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.routes.entity import (
    INT_RANGE,
    Body,
    Store,
    first_value,
    flag,
    java_number,
    model_body,
    parsed_value,
)
from aurelius_atlas_server.routes.types import validate_param_length

DISCOVERY = APIRouter(prefix="/api/atlas/v2/search", tags=["Discovery"])

QUALIFIED_NAME = "qualifiedName"
NAME = "name"
NEGATIVE_PAGE = "Limit/offset should be non-negative"
FILTERS_WITHOUT_TYPE = "EntityFilters specified without Type name"
FILTERS_WITHOUT_TAG = "TagFilters specified without tag name"
NO_ATTRIBUTE_SEARCH = "attrName : {name}, attrValue: {value} for attribute search."
MAX_FULLTEXT_QUERY_STR_LENGTH = "atlas.graph.fulltext-max-query-str-length"


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
    """``validateSearchParameters``: ``typeName``, ``classification``, ``sortBy`` and ``query`` at most 4,096
    characters (FTX-01).
    """  # noqa: D205 - one sentence
    for name, value in (
        ("typeName", parameters.type_name),
        ("classification", parameters.classification),
        ("sortBy", parameters.sort_by),
    ):
        if value is not None:
            validate_param_length(name, value)
    validate_query_length(parameters.query)


def validate_query_length(query: str | None) -> None:
    """A free-text query of at most ``atlas.graph.fulltext-max-query-str-length`` characters (FTX-01).

    Raises:
        AtlasError: ``INVALID_QUERY_LENGTH``.
    """
    if query and len(query) > MAX_QUERY_LENGTH:
        raise AtlasError(AtlasErrorCode.INVALID_QUERY_LENGTH, MAX_FULLTEXT_QUERY_STR_LENGTH)


async def _search(store: Store, parameters: SearchParameters) -> AtlasJSONResponse:
    result = await EntityDiscoveryService(store).search_with_parameters(parameters)
    return AtlasJSONResponse(content=result.to_json())


@DISCOVERY.post("/basic")
async def search_with_parameters(body: Body, store: Store) -> AtlasJSONResponse:
    """``searchWithParameters``: the entities the body's search finds, validated first (SRC-02, SRC-09)."""
    parameters = model_body(SearchParameters, body) or SearchParameters()
    validate_basic_search_parameters(parameters)
    return await _search(store, parameters)


@DISCOVERY.get("/basic")
async def search_using_basic(request: Request, store: Store) -> AtlasJSONResponse:
    """``searchUsingBasic``: a search of the query parameters, not validated as the body's is (SRC-11)."""
    sort_order = first_value(request, "sortOrder")
    parameters = SearchParameters(
        query=first_value(request, "query"),
        type_name=first_value(request, "typeName"),
        classification=first_value(request, "classification"),
        sort_by=first_value(request, "sortBy"),
        sort_order=None if sort_order is None else parsed_value("sortOrder", sort_order, SortOrder),
        exclude_deleted_entities=flag(request, "excludeDeletedEntities"),
        limit=java_number(request, "limit", 0, INT_RANGE),
        offset=java_number(request, "offset", 0, INT_RANGE),
        marker=first_value(request, "marker"),
    )
    _validate_lengths(parameters)
    return await _search(store, parameters)


@DISCOVERY.get("/fulltext")
async def search_using_full_text(request: Request, store: Store) -> AtlasJSONResponse:
    """``searchUsingFullText``: the entities matching ``query``, best first, with their scores (FTX-05)."""
    query = first_value(request, "query") or ""
    validate_query_length(query)
    result = await EntityDiscoveryService(store).search_using_full_text(
        query,
        exclude_deleted_entities=flag(request, "excludeDeletedEntities"),
        limit=java_number(request, "limit", 0, INT_RANGE),
        offset=java_number(request, "offset", 0, INT_RANGE),
    )
    return AtlasJSONResponse(content=result.to_json())


@DISCOVERY.get("/attribute")
async def search_using_attribute(request: Request, store: Store) -> AtlasJSONResponse:
    """``searchUsingAttribute``: entities whose attribute starts with the prefix (SRC-11).

    Raises:
        AtlasError: ``INVALID_PARAMETERS`` without ``attrName`` and ``attrValuePrefix``.
    """
    attr_name, prefix = first_value(request, "attrName"), first_value(request, "attrValuePrefix")
    type_name = first_value(request, "typeName")
    for name, value in (("attrName", attr_name), ("attrValuePrefix", prefix), ("typeName", type_name)):
        if value is not None:
            validate_param_length(name, value)
    if not attr_name and not prefix:
        message = NO_ATTRIBUTE_SEARCH.format(name=java_string(attr_name), value=java_string(prefix))
        raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, message)
    if not attr_name:
        entity_type = None if type_name is None else store.registry.entity_type(type_name)
        attr_name = next(
            (name for name in (QUALIFIED_NAME, NAME) if entity_type is not None and entity_type.attribute(name)),
            QUALIFIED_NAME,
        )
    parameters = SearchParameters(
        type_name=type_name,
        entity_filters=FilterCriteria(attribute_name=attr_name, operator=Operator.STARTS_WITH, attribute_value=prefix),
        limit=java_number(request, "limit", 0, INT_RANGE),
        offset=java_number(request, "offset", 0, INT_RANGE),
    )
    validate_basic_search_parameters(parameters)
    return await _search(store, parameters)
