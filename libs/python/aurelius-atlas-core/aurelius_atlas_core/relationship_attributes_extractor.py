"""``RelationshipAttributesExtractor``: what an exported entity reaches through its relationship attributes (EXP-04).

A related entity is lineage when its type names ``Process`` among its own super types. A relationship goes outward
from the entity when the entity's type is the relationship type's end 1, inward otherwise.
"""

from typing import TYPE_CHECKING

from aurelius_atlas_model.instance import AtlasEntity, AtlasRelatedObjectId
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.entities_extractor import TraversalDirection

if TYPE_CHECKING:
    from aurelius_atlas_core.export_service import ExportContext

PROCESS = "Process"


class RelationshipAttributesExtractor:
    """``RelationshipAttributesExtractor`` with the types of ``registry``."""

    def __init__(self, registry: TypeRegistry) -> None:
        self._registry = registry

    async def full_fetch(self, entity: AtlasEntity, context: ExportContext) -> None:
        """``fullFetch``: every related entity, lineage left out when skipped."""
        for related in _related_object_ids(entity):
            is_lineage = self._is_lineage(related.type_name)
            if context.skip_lineage and is_lineage:
                continue
            context.add_to_be_processed(is_lineage, str(related.guid), TraversalDirection.BOTH)

    async def connected_fetch(self, entity: AtlasEntity, context: ExportContext) -> None:
        """``connectedFetch``: out and in from an entity not reached yet, else the way it was reached, lineage out."""
        direction = context.guid_direction.get(str(entity.guid))
        if direction is None or direction is TraversalDirection.UNKNOWN:
            self._add_to_be_processed(entity, context, [TraversalDirection.OUTWARD, TraversalDirection.INWARD])
        else:
            outward = self._is_lineage(entity.type_name)
            self._add_to_be_processed(entity, context, [TraversalDirection.OUTWARD if outward else direction])

    def _add_to_be_processed(
        self, entity: AtlasEntity, context: ExportContext, directions: list[TraversalDirection]
    ) -> None:
        """``addToBeProcessed``: the related entities in each direction; a lineage entity's the other way."""
        is_lineage_entity = self._is_lineage(entity.type_name)
        related_ids = _related_object_ids(entity)
        for direction in directions:
            for related in related_ids:
                guid = str(related.guid)
                current = context.guid_direction.get(guid)
                is_lineage = self._is_lineage(related.type_name)
                edge = self._edge_direction(related, str(entity.type_name))
                if context.skip_lineage and is_lineage:
                    continue
                if (direction is not edge) != is_lineage_entity:
                    continue
                if current is None:
                    context.add_to_be_processed(is_lineage, guid, direction)
                elif current is TraversalDirection.OUTWARD and direction is TraversalDirection.INWARD:
                    context.guids_processed.discard(guid)
                    context.add_to_be_processed(is_lineage, guid, direction)

    def _edge_direction(self, related: AtlasRelatedObjectId, type_name: str) -> TraversalDirection:
        """``getRelationshipEdgeDirection``: outward when the entity's type is the relationship type's end 1."""
        relationship_type = self._registry.relationship_type(related.relationship_type)
        end1 = None if relationship_type is None else relationship_type.relationship_def.end_def1
        outward = end1 is not None and end1.type == type_name
        return TraversalDirection.OUTWARD if outward else TraversalDirection.INWARD

    def _is_lineage(self, type_name: str | None) -> bool:
        """``isLineageType``: the type names ``Process`` among its own super types."""
        entity_type = self._registry.entity_type(type_name)
        return entity_type is not None and PROCESS in (entity_type.entity_def.super_types or [])


def _related_object_ids(entity: AtlasEntity) -> list[AtlasRelatedObjectId]:
    """``getRelatedObjectIds``: each related object id of the entity's relationship attributes, in order."""
    found: list[AtlasRelatedObjectId] = []
    for value in (entity.relationship_attributes or {}).values():
        if isinstance(value, AtlasRelatedObjectId):
            found.append(value)
        elif isinstance(value, list):
            found += [item for item in value if isinstance(item, AtlasRelatedObjectId)]
    return found
