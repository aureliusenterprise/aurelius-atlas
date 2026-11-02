"""``EntitiesExtractor``: which strategy finds the entities an exported entity reaches, by fetch type (EXP-04).

An item of a type with relationship attributes is followed through them (``RelationshipAttributesExtractor``),
any other through every relationship and reference of its entities (``VertexExtractor``).
"""

from enum import Enum
from typing import TYPE_CHECKING, Protocol

from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_typesystem.entity_type import EntityType

from aurelius_atlas_core.entity_store import EntityStore

if TYPE_CHECKING:
    from aurelius_atlas_core.export_service import ExportContext


class TraversalDirection(Enum):
    """``ExportService.TraversalDirection``: how an entity was reached."""

    UNKNOWN = "UNKNOWN"
    INWARD = "INWARD"
    OUTWARD = "OUTWARD"
    BOTH = "BOTH"


class ExtractStrategy(Protocol):
    """``ExtractStrategy``: the entities an exported entity reaches, queued in the context."""

    async def full_fetch(self, entity: AtlasEntity, context: ExportContext) -> None:
        """Every entity related to it, either way."""
        ...

    async def connected_fetch(self, entity: AtlasEntity, context: ExportContext) -> None:
        """The entities related to it in the direction it was reached in."""
        ...


class EntitiesExtractor:
    """``EntitiesExtractor`` over the entities of ``store``."""

    def __init__(self, store: EntityStore) -> None:
        from aurelius_atlas_core.relationship_attributes_extractor import (  # noqa: PLC0415 - they import this module
            RelationshipAttributesExtractor,
        )
        from aurelius_atlas_core.vertex_extractor import VertexExtractor  # noqa: PLC0415

        self._vertex: ExtractStrategy = VertexExtractor(store)
        self._relationship: ExtractStrategy = RelationshipAttributesExtractor(store.registry)
        self._extractor: ExtractStrategy | None = None

    def set_extractor(self, entity_type: EntityType | None) -> None:
        """``setExtractor``: relationship attributes for a type with any, else every relationship (EXP-04)."""
        uses_relationships = entity_type is not None and bool(entity_type.relationship_attributes)
        self._extractor = self._relationship if uses_relationships else self._vertex

    async def get(self, entity: AtlasEntity, context: ExportContext) -> None:
        """``get``: a connected export follows the direction reached in, any other every relationship (EXP-04)."""
        from aurelius_atlas_core.export_service import ExportFetchType  # noqa: PLC0415 - it imports this module

        extractor = self._extractor or self._vertex
        if context.fetch_type is ExportFetchType.CONNECTED:
            await extractor.connected_fetch(entity, context)
        else:
            await extractor.full_fetch(entity, context)
