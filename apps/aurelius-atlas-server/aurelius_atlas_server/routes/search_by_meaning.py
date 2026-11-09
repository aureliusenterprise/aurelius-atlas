"""Aurelius's searches by meaning under ``/api/aurelius/v1`` (SBM-01 to SBM-07, DD-440 to DD-443).

They take quick search's parameters and answer as it does, the facets included; Atlas's own endpoints are not
touched (ADR 046). The query is embedded through the embedder the indexer uses; the similar-entities search uses
the entity's stored vector.
"""

from typing import Any

import httpx2 as httpx
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_model.discovery import QuickSearchParameters
from fastapi import APIRouter, Request

from aurelius_atlas_server.authorization import AtlasPrivilege, authorizer, verify_access
from aurelius_atlas_server.embedding import EmbeddingClient, EmbeddingError
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.routes.discovery import FILTERS_WITHOUT_TYPE, NEGATIVE_PAGE, validate_query_length
from aurelius_atlas_server.routes.entity import (
    INT_RANGE,
    READ_ENTITY_GUID,
    Body,
    Store,
    first_value,
    flag,
    java_number,
    model_body,
)
from aurelius_atlas_server.routes.types import validate_param_length

SEARCH_BY_MEANING = APIRouter(prefix="/api/aurelius/v1", tags=["Search by meaning"])

MODES = ("semantic", "hybrid")
NO_QUERY = "A search by meaning needs a query"
NO_SORT = "A search by meaning is ordered by meaning: sortBy is not taken"
UNKNOWN_MODE = "mode must be one of semantic, hybrid"


def _embedder(request: Request) -> EmbeddingClient:
    """The embeddings client, or 404 when embedding is off (SBM-06).

    Raises:
        AtlasError: ``EMBEDDING_OFF`` without one.
    """
    embedder: EmbeddingClient | None = request.app.state.embedder
    if embedder is None:
        raise AtlasError(AtlasErrorCode.EMBEDDING_OFF)
    return embedder


async def _query_vector(embedder: EmbeddingClient, query: str) -> list[float]:
    """The query's embedding, as a ``query`` (DD-443).

    Raises:
        AtlasError: ``EMBEDDER_UNAVAILABLE`` when the embedder cannot be reached or answers otherwise (SBM-06).
    """
    try:
        [vector] = await embedder.embed([query], input_type="query")
    except (httpx.HTTPError, EmbeddingError, KeyError, ValueError) as error:
        raise AtlasError(AtlasErrorCode.EMBEDDER_UNAVAILABLE, type(error).__name__, cause=error) from error
    return vector


def validate_search_by_meaning(parameters: QuickSearchParameters, body: dict[str, Any]) -> bool:
    """Quick search's checks of a search by meaning, and its own; whether it is ``hybrid`` (SBM-04).

    Raises:
        AtlasError: ``BAD_REQUEST`` without a query, with filters but no type, a negative page, a ``sortBy`` or
            another ``mode``; ``INVALID_QUERY_LENGTH`` for a query of more than 4,096 characters.
    """
    mode = body.get("mode", "semantic")
    if mode not in MODES:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, UNKNOWN_MODE)
    if not parameters.query or not parameters.query.strip():
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_QUERY)
    validate_query_length(parameters.query)
    if parameters.limit < 0 or parameters.offset < 0:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NEGATIVE_PAGE)
    if not parameters.type_name and parameters.entity_filters is not None:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, FILTERS_WITHOUT_TYPE)
    if parameters.sort_by:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_SORT)
    return mode == "hybrid"


@SEARCH_BY_MEANING.post("/search/semantic")
async def search_by_meaning(request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """Quick search by meaning, ``semantic`` or ``hybrid`` (SBM-01 to SBM-04, SBM-06, SBM-07)."""
    payload = body if isinstance(body, dict) else {}
    parameters = model_body(QuickSearchParameters, payload) or QuickSearchParameters()
    hybrid = validate_search_by_meaning(parameters, payload)
    vector = await _query_vector(_embedder(request), str(parameters.query))
    weight = request.app.state.settings.hybrid_vector_weight if hybrid else 1.0
    result = await EntityDiscoveryService(store, authorizer=authorizer(request)).search_by_meaning(
        parameters, vector, hybrid=hybrid, weight=weight
    )
    return AtlasJSONResponse(content=result.to_json())


@SEARCH_BY_MEANING.get("/entity/guid/{guid}/similar")
async def similar_entities(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """The entities nearest to one entity's embedding, itself left out (SBM-05 to SBM-07).

    Raises:
        AtlasError: ``INSTANCE_GUID_NOT_FOUND`` for an unknown GUID; ``NO_EMBEDDING`` for an entity not yet
            embedded; ``EMBEDDING_OFF`` without embedding.
    """
    validate_param_length("guid", guid)
    _embedder(request)
    found = await store.get(guid)
    if found is None:
        raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
    verify_access(request, AtlasPrivilege.ENTITY_READ, READ_ENTITY_GUID, guid)
    if found.entity.embedding is None:
        raise AtlasError(AtlasErrorCode.NO_EMBEDDING, guid)
    parameters = QuickSearchParameters(
        type_name=first_value(request, "typeName"),
        exclude_deleted_entities=flag(request, "excludeDeletedEntities"),
        offset=java_number(request, "offset", 0, INT_RANGE),
        limit=java_number(request, "limit", 0, INT_RANGE),
    )
    if parameters.limit < 0 or parameters.offset < 0:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NEGATIVE_PAGE)
    result = await EntityDiscoveryService(store, authorizer=authorizer(request)).search_by_meaning(
        parameters, found.entity.embedding.vector, exclude_guids=frozenset({guid})
    )
    return AtlasJSONResponse(content=result.to_json())
