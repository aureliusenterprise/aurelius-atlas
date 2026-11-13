"""The extraction endpoint (DTM-01): rows and rules in, the ar3 model out.

The route is the app's one use case and composes it directly, as the example
app's routes compose theirs (DD-208's shape): the extraction engine is a pure
module function, so the route calls it and answers its bytes — no
``response_model`` filtering, the body and the answer are the client
library's models (CL-07, CL-50).

Since 8.23 the route *declares* both shapes to FastAPI (AUX-06, DD-559): the
body model is FastAPI's own parameter, and ``response_model`` names the answer
for the OpenAPI document only. A route that returns a ``Response`` bypasses
FastAPI's serialization, so the answer's bytes stay the model dump the
scenarios compare (CL-50 holds); the declaration adds the schema, not a filter.
"""

from typing import Any

from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_data2model_client.models import ExtractionRequest, ExtractionResponse
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from aurelius_atlas_data2model.extract import extract

EXTRACT = "extract"
"""The router's tag: the app's one use case."""

EXTRACT_ANSWER: dict[int | str, dict[str, Any]] = {
    200: {"description": "The ar3 model string and its metadata (DTM-01, CL-20)."}
}
"""The OpenAPI answer of ``POST /extract``: the ``ExtractionResponse`` schema, in words."""


def build_router(auth: KeycloakAuth) -> APIRouter:
    """The extraction router, gated by the app's verifier (DTM-10).

    The gate is the verifier the composition root was built with — the
    router holds none of its own (DD-200's seam, DD-209).
    """
    router = APIRouter(tags=[EXTRACT])

    @router.post(
        "/extract",
        response_model=ExtractionResponse,
        responses=EXTRACT_ANSWER,
        dependencies=[auth.require_auth],
    )
    def extract_model(body: ExtractionRequest) -> JSONResponse:
        """Rows and rules in, the ar3 model string and metadata out (DTM-01).

        The body and the answer are the client library's models (CL-07, CL-20);
        the answer is serialised from the model so its bytes stay the contract the
        scenarios compare (CL-50). ``response_model`` documents that answer for
        the OpenAPI surface (AUX-06) and never rewrites the bytes.
        """
        return JSONResponse(content=extract(body).model_dump(mode="json", by_alias=True))

    return router
