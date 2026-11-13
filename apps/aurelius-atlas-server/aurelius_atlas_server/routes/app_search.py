"""The App Search API the original webapp searches with: ``/api/as/v1/engines/{engine}/search`` (ASE-01, ASE-02,
ASQ-01).

Its reverse proxy sends ``<base>/elastic`` to ``atlas-dev``'s ``search.json`` and ``<base>/data_quality`` to
``atlas-dev-quality``'s; the engines answer from the entity index (ADR 060, DD-523, DD-531). Answers and refusals
take App Search's shape, not Atlas's (DD-527).
"""  # noqa: D205 - one sentence

import json

from aurelius_atlas_core.app_search_engine import ENGINES, AppSearchEngine, AppSearchError
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from aurelius_atlas_server.authorization import AtlasPrivilege, is_access_allowed
from aurelius_atlas_server.models import AppSearchAnswer, AppSearchRequest
from aurelius_atlas_server.openapi import json_response, request_body
from aurelius_atlas_server.tenant_stores import stores

APP_SEARCH = APIRouter(prefix="/api/as/v1", tags=["App Search"])

UNKNOWN_ENGINE = "Could not find engine."
NOT_READABLE = "The user is not authorized to read entities"
NOT_JSON = "The request body must be valid JSON"


APP_SEARCH_RESULT = json_response(AppSearchAnswer, description="The App Search answer: meta, results, and facets.")

APP_SEARCH_BODY = request_body(AppSearchRequest, required=False, description="The App Search query document.")


@APP_SEARCH.post("/engines/{engine}/search", responses=APP_SEARCH_RESULT, **APP_SEARCH_BODY)
@APP_SEARCH.post("/engines/{engine}/search.json", responses=APP_SEARCH_RESULT, **APP_SEARCH_BODY)
async def search(engine: str, request: Request) -> JSONResponse:
    """App Search's search of ``engine``: ``atlas-dev`` or ``atlas-dev-quality``, until 14.6 adds the third."""
    try:
        if not is_access_allowed(request, AtlasPrivilege.ENTITY_READ):
            raise AppSearchError(403, NOT_READABLE)  # noqa: TRY301 - answered as every refusal
        if (found := ENGINES.get(engine)) is None:
            raise AppSearchError(404, UNKNOWN_ENGINE)  # noqa: TRY301 - answered as every refusal
        raw = await request.body()
        try:
            body = json.loads(raw) if raw.strip() else {}
        except ValueError as error:
            raise AppSearchError(400, NOT_JSON) from error
        answer = await AppSearchEngine(stores(request).documents, found).search(body)
    except AppSearchError as refusal:
        return JSONResponse(refusal.to_json(), status_code=refusal.status)
    return JSONResponse(answer)
