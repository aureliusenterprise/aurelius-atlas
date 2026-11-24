"""The verdicts door of the view family: ``POST /api/aurelius/v1/rule/verdicts`` (VDR-14, AVS-12, ADR 071).

The door answers one rule's stored governance verdicts (ADR 071): the body names a GUID, the door reads the
verdicts index through the documents contract (ASG-09), and answers AVS-12's rows — never the rule's entity,
never a re-judge (VDR-14). Without ``ENTITY_READ`` the answer is ``VIEW_FORBIDDEN``, as the search and read
doors answer it (AVR-01); the door's refusals are ``VIEW_REFUSED`` in the door's shape (AVR-13).
"""

from aurelius_atlas_core.view_rule import ViewRuleEngine
from fastapi import APIRouter

from aurelius_atlas_server.authorization import AtlasPrivilege, is_access_allowed
from aurelius_atlas_server.bodies import Body
from aurelius_atlas_server.deps import Authorizer, StoreSet
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_server.models import RuleVerdictsAnswer, RuleVerdictsRequest
from aurelius_atlas_server.openapi import json_response, request_body

VIEW_RULE = APIRouter(prefix="/api/aurelius/v1", tags=["View family"])

RULE_VERDICTS_RESULT = json_response(RuleVerdictsAnswer, description="The rule's stored verdict rows.")

RULE_VERDICTS_BODY = request_body(
    RuleVerdictsRequest, required=False, description="The door's request: the rule's GUID (VDR-14)."
)


@VIEW_RULE.post("/rule/verdicts", responses=RULE_VERDICTS_RESULT, **RULE_VERDICTS_BODY)
async def rule_verdicts(body: Body, found: StoreSet, authorized: Authorizer) -> dict[str, object]:
    """The verdicts door: one rule's stored verdicts, read from the verdicts index (VDR-14).

    The door reads its own body: it refuses any shape it cannot answer (AVR-13), and any GUID without
    verdicts — an inactive or deleted rule, an entity, no entity — answers the empty list (VDR-14, ASG-06).
    """
    if not is_access_allowed(authorized, AtlasPrivilege.ENTITY_READ):
        raise AtlasError(AtlasErrorCode.VIEW_FORBIDDEN, authorized.user)
    return await ViewRuleEngine(found.documents).verdicts(body)
