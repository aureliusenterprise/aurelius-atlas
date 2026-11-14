"""Aurelius's searches by meaning under ``/api/aurelius/v1`` (SBM-01 to SBM-07, DD-440 to DD-443).

They take quick search's parameters and answer as it does, the facets included; Atlas's own endpoints are not
touched (ADR 046). The query is embedded through the embedder the indexer uses; the similar-entities search uses
the entity's stored vector.
"""

from typing import Annotated

from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_model.discovery import AtlasQuickSearchResult, QuickSearchParameters
from aurelius_atlas_model.errors import validate_guid
from aurelius_atlas_model.params import SimilarSearchParams, read_params
from fastapi import APIRouter, Depends, Request

from aurelius_atlas_server.authorization import AtlasPrivilege, authorizer, verify_access
from aurelius_atlas_server.bodies import json_model
from aurelius_atlas_server.embedding import embed_query, query_embedder
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.models import SemanticSearchParameters
from aurelius_atlas_server.openapi import json_response, request_body
from aurelius_atlas_server.routes.entity import READ_ENTITY_GUID, Store

SEARCH_BY_MEANING = APIRouter(prefix="/api/aurelius/v1", tags=["Search by meaning"])

MEANING_BODY = json_model(SemanticSearchParameters)
"""``searchByMeaning``: quick search's parameters and the mode, validated by the model (SBM-01, SBM-04)."""

type MeaningBody = Annotated[SemanticSearchParameters | None, Depends(MEANING_BODY)]

QUICK_SEARCH_RESULT = json_response(AtlasQuickSearchResult, description="The search result, the facets included.")

SEMANTIC_BODY = request_body(
    SemanticSearchParameters,
    description="Quick search parameters and an optional mode, semantic (default) or hybrid. A query is required.",
)


@SEARCH_BY_MEANING.post("/search/semantic", responses=QUICK_SEARCH_RESULT, **SEMANTIC_BODY)
async def search_by_meaning(request: Request, meaning_body: MeaningBody, store: Store) -> AtlasJSONResponse:
    """Quick search by meaning, ``semantic`` or ``hybrid`` (SBM-01 to SBM-04, SBM-06, SBM-07)."""
    parameters = meaning_body or SemanticSearchParameters()
    hybrid = parameters.checked()
    vector = await embed_query(query_embedder(request), str(parameters.query))
    weight = request.app.state.settings.hybrid_vector_weight if hybrid else 1.0
    result = await EntityDiscoveryService(store, authorizer=authorizer(request)).search_by_meaning(
        parameters, vector, hybrid=hybrid, weight=weight
    )
    return AtlasJSONResponse(content=result.to_json())


@SEARCH_BY_MEANING.get("/entity/guid/{guid}/similar", responses=QUICK_SEARCH_RESULT)
async def similar_entities(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """The entities nearest to one entity's embedding, itself left out (SBM-05 to SBM-07).

    Raises:
        AtlasError: ``INSTANCE_GUID_NOT_FOUND`` for an unknown GUID; ``NO_EMBEDDING`` for an entity not yet
            embedded; ``EMBEDDING_OFF`` without embedding.
    """
    validate_guid("guid", guid)
    query_embedder(request)
    found = await store.get(guid)
    if found is None:
        raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
    verify_access(request, AtlasPrivilege.ENTITY_READ, READ_ENTITY_GUID, guid)
    if found.entity.embedding is None:
        raise AtlasError(AtlasErrorCode.NO_EMBEDDING, guid)
    asked = read_params(SimilarSearchParams, request.query_params)
    asked.checked()
    parameters = QuickSearchParameters(
        type_name=asked.type_name,
        exclude_deleted_entities=asked.exclude_deleted_entities,
        offset=asked.offset,
        limit=asked.limit,
    )
    result = await EntityDiscoveryService(store, authorizer=authorizer(request)).search_by_meaning(
        parameters, found.entity.embedding.vector, exclude_guids=frozenset({guid})
    )
    return AtlasJSONResponse(content=result.to_json())
