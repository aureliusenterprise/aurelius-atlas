"""The rule vocabulary endpoints under ``/api/aurelius/v1/quality`` (QRE-01 to QRE-05, DD-473/474).

The editor (7.27) renders its rule form from these answers: the kinds resource is the engine's
vocabulary (12.1's ``KINDS``), and the validate call is the engine's own parser over a stored-rule
shape. Neither route touches the store (QRE-04): the vocabulary is the deployed engine's, not the
catalogue's, and a rule saves through entity write REST (EWR) as before.
"""

from typing import Any

from aurelius_atlas_quality import (
    CASTABLE_TYPES,
    KINDS,
    THRESHOLD_MAX,
    THRESHOLD_MIN,
    QualityRuleError,
    rule_from_atlas_attributes,
)
from fastapi import APIRouter

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.routes.entity import Body

QUALITY = APIRouter(prefix="/api/aurelius/v1/quality", tags=["Quality"])

NOT_AN_OBJECT = "The rule to validate must be a JSON object"
"""The 400 text of a validate body that holds no rule (QRE-03): only a non-object is a bad request."""


@QUALITY.get("/kinds")
async def quality_kinds() -> AtlasJSONResponse:
    """The closed rule vocabulary of the deployed engine (QRE-01, DD-473).

    One entry per check kind sorted by name, with its dimension, its required and optional
    parameters, and its reason line, beside the castable types and the threshold bounds. The
    answer is a render of ``KINDS``, never a table written a second time.
    """
    kinds = [
        {
            "name": kind.value,
            "dimension": spec.dimension.value,
            "required": sorted(spec.required),
            "optional": sorted(spec.optional),
            "reason": spec.reason,
        }
        for kind, spec in sorted(KINDS.items(), key=lambda item: item[0].value)
    ]
    return AtlasJSONResponse(
        content={
            "kinds": kinds,
            "castableTypes": sorted(CASTABLE_TYPES),
            "thresholdMin": THRESHOLD_MIN,
            "thresholdMax": THRESHOLD_MAX,
        }
    )


@QUALITY.post("/rules/validate")
async def validate_quality_rule(body: Body) -> AtlasJSONResponse:
    """A stored-rule shape through the engine's parser (QRE-02/03, DD-474).

    A rule the vocabulary reads answers ``{valid, kind, dimension}``; one it cannot read answers
    ``{valid, reason}`` with the engine's own text. Both are 200: an unreadable rule is the
    product of this endpoint, not a rejected request. No entity is read and nothing is stored.

    Raises:
        AtlasError: ``BAD_REQUEST`` when the body is not a JSON object (QRE-03).
    """
    if not isinstance(body, dict):
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NOT_AN_OBJECT)
    attributes: dict[str, Any] = body
    try:
        rule = rule_from_atlas_attributes(attributes)
    except QualityRuleError as error:
        return AtlasJSONResponse(content={"valid": False, "reason": str(error)})
    return AtlasJSONResponse(content={"valid": True, "kind": rule.kind.value, "dimension": rule.dimension.value})
