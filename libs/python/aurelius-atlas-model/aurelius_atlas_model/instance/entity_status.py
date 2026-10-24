"""``AtlasEntity.Status``: the life-cycle state of an entity (ENT-09)."""

from enum import StrEnum


class EntityStatus(StrEnum):
    """Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``)."""

    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    PURGED = "PURGED"
