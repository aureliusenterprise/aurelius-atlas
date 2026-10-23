"""The extraction endpoint (DTM-01): rows and rules in, the ar3 model out.

The route is the app's one use case and composes it directly, as the example
app's routes compose theirs (DD-119's shape): the extraction engine is a pure
module function, so the route calls it and answers its bytes — no
``response_model`` filtering, the body and the answer are the client
library's models (CL-07, CL-50).
"""

from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_data2model_client.models import ExtractionRequest
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from aurelius_atlas_data2model.extract import extract

EXTRACT = "extract"
"""The router's tag: the app's one use case."""


def build_router(auth: KeycloakAuth) -> APIRouter:
    """The extraction router, gated by the app's verifier (DTM-10).

    The gate is the verifier the composition root was built with — the
    router holds none of its own (DD-111's seam, DD-120).
    """
    router = APIRouter(tags=[EXTRACT])

    @router.post("/extract", dependencies=[auth.require_auth])
    def extract_model(body: ExtractionRequest) -> JSONResponse:
        """Rows and rules in, the ar3 model string and metadata out (DTM-01).

        The body and the answer are the client library's models (CL-07, CL-20);
        the answer is serialised from the model so its bytes stay the contract the
        scenarios compare (CL-50).
        """
        return JSONResponse(content=extract(body).model_dump(mode="json", by_alias=True))

    return router
