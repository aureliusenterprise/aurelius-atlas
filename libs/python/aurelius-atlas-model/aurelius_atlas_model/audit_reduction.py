"""``AuditReductionCriteria`` and ``AtlasAuditAgingType``: what an aging of the entity audits removes (AGE-01).

Ported from Apache Atlas 2.4.0 ``org.apache.atlas.model.audit.AuditReductionCriteria`` and
``Constants.AtlasAuditAgingType``.
"""

from enum import StrEnum

from pydantic import Field

from aurelius_atlas_model.base import AtlasModel, JavaInt


class AtlasAuditAgingType(StrEnum):
    """``AtlasAuditAgingType``: the default aging of every type, a custom one of some, a sweep of some."""

    DEFAULT = "DEFAULT"
    CUSTOM = "CUSTOM"
    SWEEP = "SWEEP"


AUDIT_AGING_TYPE_KEY = "auditAgingType"
AUDIT_AGING_TTL_KEY = "ttl"
AUDIT_AGING_COUNT_KEY = "auditCount"
AUDIT_AGING_ENTITY_TYPES_KEY = "entityTypes"
AUDIT_AGING_ACTION_TYPES_KEY = "actionTypes"
AUDIT_AGING_EXCLUDE_ENTITY_TYPES_KEY = "excludeEntityTypes"
CREATE_EVENTS_AGEOUT_ALLOWED_KEY = "createEventsAgeoutAllowed"
AUDIT_AGING_SUBTYPES_INCLUDED_KEY = "subTypesIncluded"
"""The parameters of an aging task, as ``Constants`` names them."""


class AuditReductionCriteria(AtlasModel):
    """``AuditReductionCriteria``: the default, custom and sweep agings an ``audits/ageout`` asks for (AGE-01)."""

    audit_aging_enabled: bool = False
    default_ageout_enabled: bool = False
    audit_sweepout_enabled: bool = False
    create_events_ageout_allowed: bool = False
    sub_types_included: bool = True
    ignore_default_ageout_ttl: bool = Field(default=False, alias="ignoreDefaultAgeoutTTL")
    default_ageout_audit_count: JavaInt = 0
    default_ageout_ttl_in_days: JavaInt = Field(default=0, alias="defaultAgeoutTTLInDays")
    custom_ageout_audit_count: JavaInt = 0
    custom_ageout_ttl_in_days: JavaInt = Field(default=0, alias="customAgeoutTTLInDays")
    custom_ageout_entity_types: str | None = None
    custom_ageout_action_types: str | None = None
    sweepout_entity_types: str | None = None
    sweepout_action_types: str | None = None
