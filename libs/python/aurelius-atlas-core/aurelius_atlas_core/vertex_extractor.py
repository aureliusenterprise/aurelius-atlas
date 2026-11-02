"""``VertexExtractor``: the entities an exported entity reaches through its edges (EXP-04, DD-303).

Atlas walks the entity vertex's edges with Gremlin (``bothE``, ``inE``, ``outE``) to the vertices with a GUID, in
any state. Here those edges are the entity's relationships, from end 1 to end 2, and its references, from the
referring entity to the referred one.
"""

from typing import TYPE_CHECKING

from aurelius_atlas_model.instance import AtlasEntity

from aurelius_atlas_core.entities_extractor import TraversalDirection
from aurelius_atlas_core.entity_store import EntityStore

if TYPE_CHECKING:
    from aurelius_atlas_core.export_service import ExportContext

PROCESS = "Process"


class VertexExtractor:
    """``VertexExtractor`` over the entities of ``store``."""

    def __init__(self, store: EntityStore) -> None:
        self._store = store

    async def full_fetch(self, entity: AtlasEntity, context: ExportContext) -> None:
        """``fullFetch``: every entity at the other end of an edge, unless processed; lineage left out when skipped."""
        for guid, is_process in await self._neighbours(str(entity.guid), TraversalDirection.BOTH):
            if context.skip_lineage and is_process:
                continue
            if guid not in context.guids_processed:
                context.add_to_be_processed(is_process, guid, TraversalDirection.BOTH)

    async def connected_fetch(self, entity: AtlasEntity, context: ExportContext) -> None:
        """``connectedFetch``: out and in from an entity not reached yet, else the way it was reached, a process out."""
        direction = context.guid_direction.get(str(entity.guid))
        if direction is None or direction is TraversalDirection.UNKNOWN:
            directions = [TraversalDirection.OUTWARD, TraversalDirection.INWARD]
        else:
            entity_type = self._store.registry.entity_type(entity.type_name)
            is_process = entity_type is not None and PROCESS in entity_type.all_super_types
            directions = [TraversalDirection.OUTWARD if is_process else direction]
        for direction in directions:
            for guid, is_process in await self._neighbours(str(entity.guid), direction):
                if context.skip_lineage and is_process:
                    continue
                current = context.guid_direction.get(guid)
                if current is None:
                    context.add_to_be_processed(is_process, guid, direction)
                elif current is TraversalDirection.OUTWARD and direction is TraversalDirection.INWARD:
                    context.guids_processed.discard(guid)
                    context.add_to_be_processed(is_process, guid, direction)

    async def _neighbours(self, guid: str, direction: TraversalDirection) -> list[tuple[str, bool]]:
        """The entities at the other end of the entity's edges this way, once each, and whether each is a process."""
        found = await self._store.get(guid)
        if found is None:
            return []
        outward = direction in {TraversalDirection.OUTWARD, TraversalDirection.BOTH}
        inward = direction in {TraversalDirection.INWARD, TraversalDirection.BOTH}
        guids: list[str] = []
        relationships = await self._store.get_relationships(found.entity.relationship_guids or [])
        for relationship in relationships.values():
            stored = relationship.relationship
            if outward and stored.end1_guid == guid:
                guids.append(stored.end2_guid)
            if inward and stored.end2_guid == guid:
                guids.append(stored.end1_guid)
        if outward:
            guids += found.entity.references or []
        if inward:
            guids += [referring.entity.guid for referring in await self._store.referring([guid])]
        ends = await self._store.get_many(list(dict.fromkeys(guids)))
        return [(end, PROCESS in ends[end].entity.super_type_names) for end in dict.fromkeys(guids) if end in ends]
