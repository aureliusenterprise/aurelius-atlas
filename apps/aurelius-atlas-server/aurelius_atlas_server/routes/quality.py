"""The rule vocabulary endpoints under ``/api/aurelius/v1/quality`` (QRE-01 to QRE-05, DD-475/476).

The editor (7.27) renders its rule form from these answers: the kinds resource is the engine's
vocabulary (12.1's ``KINDS``), and the validate call is the engine's own parser over a stored-rule
shape. Neither route touches the store (QRE-04): the vocabulary is the deployed engine's, not the
catalogue's, and a rule saves through entity write REST (EWR) as before.
"""

from typing import Annotated, Any

from aurelius_atlas_model.maps import AttributeValues
from aurelius_atlas_quality import (
    CASTABLE_TYPES,
    KINDS,
    THRESHOLD_MAX,
    THRESHOLD_MIN,
    QualityRuleError,
    rule_from_atlas_attributes,
)
from fastapi import APIRouter, Depends

from aurelius_atlas_server.bodies import json_root
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.models import QualityKind, QualityRuleCheck, QualityVocabulary
from aurelius_atlas_server.openapi import json_response, request_body

QUALITY = APIRouter(prefix="/api/aurelius/v1/quality", tags=["Quality"])

NOT_AN_OBJECT = "The rule to validate must be a JSON object"
"""The 400 text of a validate body that holds no rule (QRE-03): only a non-object is a bad request."""

RULE_BODY = json_root(AttributeValues)
"""``validateQualityRule``: the stored-rule attributes, a JSON object of them (QRE-02, QRE-03)."""

type RuleBody = Annotated[dict[str, Any] | None, Depends(RULE_BODY)]


KINDS_RESPONSE = json_response(
    QualityVocabulary, description="The vocabulary: kinds, castableTypes, thresholdMin, thresholdMax."
)


@QUALITY.get("/kinds", responses=KINDS_RESPONSE)
async def quality_kinds() -> AtlasJSONResponse:
    """The closed rule vocabulary of the deployed engine (QRE-01, DD-475).

    One entry per check kind sorted by name, with its dimension, its required and optional
    parameters, and its reason line, beside the castable types and the threshold bounds. The
    answer is a render of ``KINDS``, never a table written a second time.
    """
    vocabulary = QualityVocabulary(
        kinds=[
            QualityKind(
                name=kind.value,
                dimension=spec.dimension.value,
                required=sorted(spec.required),
                optional=sorted(spec.optional),
                reason=spec.reason,
            )
            for kind, spec in sorted(KINDS.items(), key=lambda item: item[0].value)
        ],
        castable_types=sorted(CASTABLE_TYPES),
        threshold_min=THRESHOLD_MIN,
        threshold_max=THRESHOLD_MAX,
    )
    return AtlasJSONResponse(content=vocabulary.to_json())


VALIDATE_RESPONSE = json_response(
    QualityRuleCheck, description="{valid, kind, dimension} for a readable rule, {valid: false, reason} otherwise."
)

VALIDATE_BODY = request_body(AttributeValues, description="The stored-rule attributes to validate.")


@QUALITY.post("/rules/validate", responses=VALIDATE_RESPONSE, **VALIDATE_BODY)
async def validate_quality_rule(attributes: RuleBody) -> AtlasJSONResponse:
    """A stored-rule shape through the engine's parser (QRE-02/03, DD-476).

    A rule the vocabulary reads answers ``{valid, kind, dimension}``; one it cannot read answers
    ``{valid, reason}`` with the engine's own text. Both are 200: an unreadable rule is the
    product of this endpoint, not a rejected request. No entity is read and nothing is stored.

    Raises:
        AtlasError: ``BAD_REQUEST`` when the body is not a JSON object (QRE-03).
    """
    if attributes is None:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NOT_AN_OBJECT)
    try:
        rule = rule_from_atlas_attributes(attributes)
    except QualityRuleError as error:
        return AtlasJSONResponse(content=QualityRuleCheck(valid=False, reason=str(error)).to_json())
    check = QualityRuleCheck(valid=True, kind=rule.kind.value, dimension=rule.dimension.value)
    return AtlasJSONResponse(content=check.to_json())
