"""``AtlasTermAssignmentStatus``: how far a glossary term's assignment to an entity got (ENT-09)."""

from enum import StrEnum


class AtlasTermAssignmentStatus(StrEnum):
    """The status of a term assignment, written by its Java name (``glossary.enums.AtlasTermAssignmentStatus``)."""

    DISCOVERED = "DISCOVERED"
    PROPOSED = "PROPOSED"
    IMPORTED = "IMPORTED"
    VALIDATED = "VALIDATED"
    DEPRECATED = "DEPRECATED"
    OBSOLETE = "OBSOLETE"
    OTHER = "OTHER"
