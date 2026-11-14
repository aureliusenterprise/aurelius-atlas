"""The search door of the view family: ``POST /api/aurelius/v1/search`` (AVR-01..09, AVR-11, AVR-13).

The door opens on every active entity of the request's tenant (DD-586) and answers 16.1 cards, facet
counts and a total (AVR-08). Its refusals are ``VIEW_REFUSED`` in the Aurelius error shape, one message
per problem (AVR-13, SBM-08); without ``ENTITY_READ`` the answer is ``VIEW_FORBIDDEN`` (AVR-01).
"""

from aurelius_atlas_core.view_search import ViewSearchEngine
from fastapi import APIRouter, Request

from aurelius_atlas_server.authorization import AtlasPrivilege, authorizer, is_access_allowed
from aurelius_atlas_server.bodies import Body
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_server.models import ViewSearchAnswer, ViewSearchRequest
from aurelius_atlas_server.openapi import json_response, request_body
from aurelius_atlas_server.tenant_stores import stores

VIEW_SEARCH = APIRouter(prefix="/api/aurelius/v1", tags=["View family"])

VIEW_SEARCH_RESULT = json_response(ViewSearchAnswer, description="The door's answer: cards, facets, and total.")

VIEW_SEARCH_BODY = request_body(ViewSearchRequest, required=False, description="The door's request document.")


@VIEW_SEARCH.post("/search", responses=VIEW_SEARCH_RESULT, **VIEW_SEARCH_BODY)
async def search(request: Request, body: Body) -> dict[str, object]:
    """The view door's search: cards, facet counts and a total over every active entity (AVR-08)."""
    if not is_access_allowed(request, AtlasPrivilege.ENTITY_READ):
        raise AtlasError(AtlasErrorCode.VIEW_FORBIDDEN, authorizer(request).user)
    found = stores(request)
    await found.typedef_store.refresh()  # the cards name attributes through the registry (ERD-10, TSS-06)
    # An empty body asks for everything, as App Search's engine reads one (ASE-04); the door's own
    # refusals answer VIEW_REFUSED through the error handler (AVR-13).
    return await ViewSearchEngine(found.documents, found.registry).search({} if body is None else body)
