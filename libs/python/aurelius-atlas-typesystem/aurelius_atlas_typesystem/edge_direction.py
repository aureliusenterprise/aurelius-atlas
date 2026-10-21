"""``AtlasRelationshipEdgeDirection``: which way a relationship attribute's edge points (THY-10)."""

from enum import StrEnum


class EdgeDirection(StrEnum):
    """Which way a relationship attribute's edge points (``AtlasRelationshipEdgeDirection``, THY-10)."""

    IN = "IN"
    OUT = "OUT"
    BOTH = "BOTH"
