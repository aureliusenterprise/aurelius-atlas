"""The App Search API the original webapp searches with: ``/api/as/v1/engines/{engine}/search`` (ASE-01, ASE-02).

Its reverse proxy sends ``<base>/elastic`` to ``atlas-dev``'s ``search.json``; the engine answers from the entity
index (ADR 060, DD-523). Answers and refusals take App Search's shape, not Atlas's (DD-527).
"""

import json

from aurelius_atlas_core.app_search_engine import ENGINE, AppSearchEngine, AppSearchError
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from aurelius_atlas_server.authorization import AtlasPrivilege, is_access_allowed

APP_SEARCH = APIRouter(prefix="/api/as/v1", tags=["App Search"])

UNKNOWN_ENGINE = "Could not find engine."
NOT_READABLE = "The user is not authorized to read entities"
NOT_JSON = "The request body must be valid JSON"


@APP_SEARCH.post("/engines/{engine}/search")
@APP_SEARCH.post("/engines/{engine}/search.json")
async def search(engine: str, request: Request) -> JSONResponse:
    """App Search's search of ``engine``: ``atlas-dev`` only until 14.5 and 14.6 add the quality engines."""
    try:
        if not is_access_allowed(request, AtlasPrivilege.ENTITY_READ):
            raise AppSearchError(403, NOT_READABLE)  # noqa: TRY301 - answered as every refusal
        if engine != ENGINE:
            raise AppSearchError(404, UNKNOWN_ENGINE)  # noqa: TRY301 - answered as every refusal
        raw = await request.body()
        try:
            body = json.loads(raw) if raw.strip() else {}
        except ValueError as error:
            raise AppSearchError(400, NOT_JSON) from error
        answer = await AppSearchEngine(request.app.state.entity_documents).search(body)
    except AppSearchError as refusal:
        return JSONResponse(refusal.to_json(), status_code=refusal.status)
    return JSONResponse(answer)
