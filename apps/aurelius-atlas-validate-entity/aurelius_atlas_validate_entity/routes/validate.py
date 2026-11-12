"""The validation endpoint (VEV-01/02, VE-03): the draft's attributes in, the live verdicts out.

The route is the app's one use case and composes it directly, as the example
app's routes compose theirs (DD-208's shape). Since 12.7 the body is read (VEV-01):
the draft entity's ``attributes`` are what the governance rules run over. The
verdicts come from :class:`~aurelius_atlas_validate_entity.verdicts.VerdictEngine`
wired by the composition root; a draft the app cannot read is
:class:`~aurelius_atlas_validate_entity.errors.DraftRejected` and a catalogue
failure is its :class:`~aurelius_atlas_validate_entity.errors.UpstreamError`,
each answered by the root's handlers (VEV-01/06).

The caller's token verifies at the gate (VE-03, unchanged) and is never forwarded
— the app reads the rules as its own service identity (VEV-04, DD-499).
"""

from typing import Annotated, Any

from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_validate_entity_client.models import ValidationResponse
from fastapi import APIRouter, Body, Request

from aurelius_atlas_validate_entity.errors import DraftRejectedError
from aurelius_atlas_validate_entity.globals import LOGGER

VALIDATE = "validate"
"""The router's tag: the app's one use case."""

BAD_DRAFT = "the validation body must be an entity object with an attributes object"
"""The VEV-01 rejection line: what the app can read is the draft's attributes."""


def build_router(auth: KeycloakAuth) -> APIRouter:
    """The validation router, gated by the app's verifier (VE-03, DV-75).

    The gate is the verifier the composition root was built with — the
    router holds none of its own (DD-201's seam, DD-209).
    """
    router = APIRouter(tags=[VALIDATE])

    @router.post("/", dependencies=[auth.require_auth])
    async def validate_entity(
        request: Request,
        body: Annotated[Any, Body()],  # noqa: ANN401 - any JSON value
    ) -> ValidationResponse:
        """`POST /`: the draft entity in, the governance verdicts out (VEV-01/02).

        The token is verified for this app's audience (VE-03, DV-75); the rules
        read runs as the app's own identity, never the caller's (VEV-04). The
        body must be a JSON object whose ``attributes`` is a JSON object —
        anything else is the 400 of VEV-01, in the Atlas error body (DV-79's
        posture: the legacy Flask 500 is not ported). The rest of the body is
        ignored: a verdict reads attributes, not relationships.
        """
        if not isinstance(body, dict) or not isinstance(body.get("attributes"), dict):
            LOGGER.info("Rejected draft: %s", BAD_DRAFT)
            raise DraftRejectedError(BAD_DRAFT)
        engine = request.app.state.engine
        return await engine.evaluate_draft(body["attributes"])

    return router
