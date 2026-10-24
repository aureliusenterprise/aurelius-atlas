"""``EntityMutations.EntityOperation``: what a write did to an entity (ENT-09)."""

from enum import StrEnum


class EntityOperation(StrEnum):
    """The kinds of entity mutation a response reports (``EntityMutations.EntityOperation``)."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    PARTIAL_UPDATE = "PARTIAL_UPDATE"
    DELETE = "DELETE"
    PURGE = "PURGE"
