"""The lineage endpoint (LM-01, LM-04..LM-07, LM-12): fetch, flatten, extract, answer verbatim.

The route is the app's one use case and composes it directly, as the example
app's routes compose theirs: it takes the upstream clients and their circuit
breakers from the app state (wired by ``app.py``), guards each upstream call
with pybreaker's documented ``calling()`` seam (LM-11, DD-117), and maps each
failure to the :class:`UpstreamError` of the status the caller gets (LM-05,
LM-07, LM-12) — the root's handlers turn it into the Atlas-shaped answer.
"""

from typing import Annotated
from uuid import UUID

from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_data2model_client.client import Data2ModelClient, Data2ModelClientError
from aurelius_atlas_data2model_client.models import ExtractionRequest, ExtractionResponse, RulesDef
from aurelius_atlas_lineage_model_client.models import DEFAULT_DEPTH
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError
from aurelius_atlas_server_client.lineage import Direction, LineageInfo
from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse
from pybreaker import CircuitBreaker, CircuitBreakerError

from aurelius_atlas_lineage_model.errors import UpstreamError
from aurelius_atlas_lineage_model.globals import (
    BAD_GATEWAY,
    BAD_REQUEST,
    FAST_FAIL_ATLAS,
    FAST_FAIL_D2M,
    LOGGER,
    NO_CONTENT,
    NOT_FOUND,
)
from aurelius_atlas_lineage_model.lineage import LINEAGE_RULES, flatten_relations

LINEAGE = "lineage"
"""The router's tag: the app's one use case."""


def build_router(auth: KeycloakAuth) -> APIRouter:
    """The lineage router, gated by the app's verifier (LM-08, DV-57).

    The upstreams are read from the app state at call time, so the router
    holds none of its own — the composition root wires them (DD-111's seam).
    """
    router = APIRouter(tags=[LINEAGE])

    @router.get("/", dependencies=[auth.require_auth])
    async def lineage_model(
        request: Request,
        guid: UUID,
        depth: Annotated[int, Query(ge=1)] = DEFAULT_DEPTH,
        direction: Direction = "BOTH",
        token: Annotated[str, auth.require_bearer] = "",
    ) -> Response:
        """Flatten the entity's lineage and extract its model (LM-01).

        The token is verified for this app's audience (LM-08, DV-57) and
        forwarded raw to both upstreams (LM-04) — the legacy's design: the
        upstream services accept the browser's own token. An empty graph (no
        lineage, no relations) is the 204 of LM-05/LM-06; failures arrive as
        ``UpstreamError`` for the root's handlers (LM-07, LM-12).
        """
        state = request.app.state
        info = await _fetch(state.atlas, state.atlas_breaker, guid, depth, direction, token)
        if info is None or not info.relations:
            return Response(status_code=NO_CONTENT)
        rows = flatten_relations(info)
        body = ExtractionRequest.model_validate({"data": rows, "rules": RulesDef.model_validate(LINEAGE_RULES)})
        answer = await _extract(state.d2m, state.d2m_breaker, body, token)
        return JSONResponse(content=answer.model_dump(mode="json", by_alias=True))

    return router


async def _fetch(  # noqa: PLR0913, PLR0917 - the guarded call's own parts: client, breaker, query, token
    atlas: AtlasClient, breaker: CircuitBreaker, guid: UUID, depth: int, direction: Direction, token: str
) -> LineageInfo | None:
    """One guarded fetch of the entity's lineage, on the caller's token (LM-04, CL-03).

    The feed's 404 is the empty graph (LM-05): the answer is None, not a
    failure — the route turns it into the 204. The open circuit (LM-12) and
    the other failures arrive as ``UpstreamError``, in the status to answer.
    The ``calling()`` generator seam is pybreaker's async-safe form (DD-117).
    """
    try:
        with breaker.calling():
            return await atlas.with_token(token).get_lineage(guid, depth=depth, direction=direction)
    except CircuitBreakerError as error:
        raise UpstreamError(BAD_GATEWAY, FAST_FAIL_ATLAS) from error
    except AtlasClientError as error:
        if error.status_code == NOT_FOUND:
            LOGGER.info("No lineage for guid %s", guid)
            return None
        if error.status_code == BAD_REQUEST:
            raise UpstreamError(BAD_REQUEST, "the lineage service rejected the request") from error
        raise UpstreamError(BAD_GATEWAY, "the lineage service failed") from error


async def _extract(
    d2m: Data2ModelClient, breaker: CircuitBreaker, body: ExtractionRequest, token: str
) -> ExtractionResponse:
    """One guarded extraction of the model, on the caller's token (LM-04, CL-03)."""
    try:
        with breaker.calling():
            return await d2m.with_token(token).extract(body)
    except CircuitBreakerError as error:
        raise UpstreamError(BAD_GATEWAY, FAST_FAIL_D2M) from error
    except Data2ModelClientError as error:
        raise UpstreamError(BAD_GATEWAY, "the model extraction failed") from error
