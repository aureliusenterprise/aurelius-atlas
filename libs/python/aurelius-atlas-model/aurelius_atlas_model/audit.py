"""``EntityAuditEventV2``: one change of an entity, as ``v2/entity/{guid}/audit`` answers it (AUD-01).

Ported from Apache Atlas 2.4.0 ``org.apache.atlas.model.audit.EntityAuditEventV2``.
"""

from enum import StrEnum
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance.entity import AtlasEntity
from aurelius_atlas_model.instance.entity_header import AtlasEntityHeader


class EntityAuditActionV2(StrEnum):
    """``EntityAuditActionV2``: what an event records."""

    ENTITY_CREATE = "ENTITY_CREATE"
    ENTITY_UPDATE = "ENTITY_UPDATE"
    ENTITY_DELETE = "ENTITY_DELETE"
    ENTITY_IMPORT_CREATE = "ENTITY_IMPORT_CREATE"
    ENTITY_IMPORT_UPDATE = "ENTITY_IMPORT_UPDATE"
    ENTITY_IMPORT_DELETE = "ENTITY_IMPORT_DELETE"
    CLASSIFICATION_ADD = "CLASSIFICATION_ADD"
    CLASSIFICATION_DELETE = "CLASSIFICATION_DELETE"
    CLASSIFICATION_UPDATE = "CLASSIFICATION_UPDATE"
    PROPAGATED_CLASSIFICATION_ADD = "PROPAGATED_CLASSIFICATION_ADD"
    PROPAGATED_CLASSIFICATION_DELETE = "PROPAGATED_CLASSIFICATION_DELETE"
    PROPAGATED_CLASSIFICATION_UPDATE = "PROPAGATED_CLASSIFICATION_UPDATE"
    TERM_ADD = "TERM_ADD"
    TERM_DELETE = "TERM_DELETE"
    LABEL_ADD = "LABEL_ADD"
    LABEL_DELETE = "LABEL_DELETE"
    ENTITY_PURGE = "ENTITY_PURGE"
    BUSINESS_ATTRIBUTE_UPDATE = "BUSINESS_ATTRIBUTE_UPDATE"
    CUSTOM_ATTRIBUTE_UPDATE = "CUSTOM_ATTRIBUTE_UPDATE"

    @classmethod
    def from_string(cls, value: str) -> EntityAuditActionV2:
        """``fromString``: an action's name, or a ``TAG_`` alias of a classification action (AUD-09).

        ``CUSTOM_ATTRIBUTE_UPDATE`` is not read, as Java's switch leaves it out.

        Raises:
            ValueError: No action has the name.
        """
        name = _ALIASES.get(value, value)
        if name == cls.CUSTOM_ATTRIBUTE_UPDATE or name not in cls.__members__:
            message = f"No enum constant org.apache.atlas.model.audit.EntityAuditEventV2.EntityAuditActionV2.{value}"
            raise ValueError(message)
        return cls(name)


_ALIASES = {
    "TAG_ADD": "CLASSIFICATION_ADD",
    "TAG_DELETE": "CLASSIFICATION_DELETE",
    "TAG_UPDATE": "CLASSIFICATION_UPDATE",
}


class EntityAuditType(StrEnum):
    """``EntityAuditType``: the audit format an event was written in."""

    ENTITY_AUDIT_V1 = "ENTITY_AUDIT_V1"
    ENTITY_AUDIT_V2 = "ENTITY_AUDIT_V2"


class EntityAuditEventV2(AtlasModel):
    """An audit event: the entity, when, by whom, what and its details, its key, and the entity's definition."""

    entity_id: str | None = None
    timestamp: int = 0
    user: str | None = None
    action: EntityAuditActionV2 | None = None
    details: str | None = None
    event_key: str | None = None
    entity: AtlasEntity | None = None
    type: EntityAuditType | None = None

    def to_json(self) -> dict[str, Any]:
        """Every field, nulls included (``JsonSerialize.Inclusion.ALWAYS``); the entity as Atlas writes one."""
        return {
            "entityId": self.entity_id,
            "timestamp": self.timestamp,
            "user": self.user,
            "action": self.action,
            "details": self.details,
            "eventKey": self.event_key,
            "entity": None if self.entity is None else self.entity.to_json(),
            "type": self.type,
        }

    def entity_header(self) -> AtlasEntityHeader | None:
        """``getEntityHeader``: the header in the JSON part of the details, from their first ``{`` (AUD-06)."""
        start = (self.details or "").find("{")
        if start < 0:
            return None
        return AtlasEntityHeader.model_validate(codec.loads((self.details or "")[start:]))
