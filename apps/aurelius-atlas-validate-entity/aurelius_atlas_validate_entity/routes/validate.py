"""The validation endpoint (VE-01, VE-02): the fixed mock document, for any body.

The route is the app's one use case and composes it directly, as the example
app's routes compose theirs (DD-119's shape). The app is the legacy mock
(DV-14, DD-112): the entity body is never read and the answer is the fixed
document — the mock's whole contract.
"""

from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_validate_entity_client.models import ValidationResponse
from fastapi import APIRouter

from aurelius_atlas_validate_entity.mock import MOCK_VALIDATION

VALIDATE = "validate"
"""The router's tag: the app's one use case."""

VALIDATION = ValidationResponse.model_validate(MOCK_VALIDATION)
"""The mock document as the contract model (CL-40): parsing it at import is the
byte guard between the constant and the browser contract the scenarios compare."""


def build_router(auth: KeycloakAuth) -> APIRouter:
    """The validation router, gated by the app's verifier (VE-03, DV-24).

    The gate is the verifier the composition root was built with — the
    router holds none of its own (DD-112's seam, DD-120).
    """
    router = APIRouter(tags=[VALIDATE])

    @router.post("/", dependencies=[auth.require_auth])
    def validate_entity() -> ValidationResponse:
        """Answer the fixed governance-quality mock for any body (VE-01, VE-02).

        The token is verified for this app's audience (VE-03, DV-24) and nothing is
        forwarded — the legacy's ``requires_auth(transparent=True)`` read the token
        and ignored it; the port keeps that: authentication yes, authorisation by
        the fixed answer. The body is the entity the editor is saving; the mock
        never inspects it, malformed bodies included. The answer is the constant,
        parsed into the client library's contract model (CL-40).
        """
        return VALIDATION

    return router
