"""The validation endpoint (VEV-01/02, VE-03): the draft's attributes in, the live verdicts out.

The route is the app's one use case and composes it directly, as the example
app's routes compose theirs (DD-208's shape). Since 12.7 the body is read (VEV-01):
the draft entity's ``attributes`` are what the governance rules run over. Since
8.23 the body parses as :class:`~aurelius_atlas_validate_entity.models.DraftEntity`
(AUX-06, DD-558): the shape rule moved from the handler's ``isinstance`` check into
the model, so the OpenAPI document names what the handler consumes and a draft the
app cannot read is refused at parse time. The 400 of VEV-01 is unchanged: the
root's ``RequestValidationError`` handler answers a parse failure in the Atlas
error body (DV-79's posture).
The verdicts come from :class:`~aurelius_atlas_validate_entity.verdicts.VerdictEngine`
wired by the composition root; a catalogue failure is its
:class:`~aurelius_atlas_validate_entity.errors.UpstreamError`, answered by the
root's handlers (VEV-06).

The caller's token verifies at the gate (VE-03, unchanged) and is never forwarded
— the app reads the rules as its own service identity (VEV-04, DD-499).
"""

from typing import Any

from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_validate_entity_client.models import ValidationResponse
from fastapi import APIRouter, Request

from aurelius_atlas_validate_entity.models import DraftEntity

VALIDATE = "validate"
"""The router's tag: the app's one use case."""

VALIDATE_ANSWER: dict[int | str, dict[str, Any]] = {
    200: {"description": "The verdicts of the ACTIVE rules, and the unread ones (VEV-02/03)."},
    400: {"description": "A draft the app will not read: the Atlas error body (VEV-01, DV-79)."},
}
"""The OpenAPI answers of ``POST /``: the verdicts, and the 400 the parse failure becomes.

FastAPI's automatic 422 leaves the document in ``app.py``: the app answers the 400 of VEV-01
where FastAPI would promise a validation answer (AUX-06).
"""


def build_router(auth: KeycloakAuth) -> APIRouter:
    """The validation router, gated by the app's verifier (VE-03, DV-75).

    The gate is the verifier the composition root was built with — the
    router holds none of its own (DD-201's seam, DD-209).
    """
    router = APIRouter(tags=[VALIDATE])

    @router.post("/", response_model=ValidationResponse, responses=VALIDATE_ANSWER, dependencies=[auth.require_auth])
    async def validate_entity(request: Request, body: DraftEntity) -> ValidationResponse:
        """`POST /`: the draft entity in, the governance verdicts out (VEV-01/02).

        The token is verified for this app's audience (VE-03, DV-75); the rules
        read runs as the app's own identity, never the caller's (VEV-04). The
        model of the body requires an entity object whose ``attributes`` is a JSON
        object — anything else is the 400 of VEV-01, in the Atlas error body. The
        rest of the body is ignored: a verdict reads attributes, not relationships.
        """
        engine = request.app.state.engine
        return await engine.evaluate_draft(body.attributes)

    return router
