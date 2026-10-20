"""``AtlasRelationship.Status``: the life-cycle state of a relationship (ENT-09)."""

from enum import StrEnum


class RelationshipStatus(StrEnum):
    """Whether a relationship is active or soft-deleted (``AtlasRelationship.Status``)."""

    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
