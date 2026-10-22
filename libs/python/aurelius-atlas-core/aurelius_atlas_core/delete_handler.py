"""``DeleteHandler``: what deleting entities changes, as ``DeleteHandlerV1`` decides it (EDL-03 to EDL-07).

The entities to delete with those they own (``getOwnedVertices``), their new states, and the changes to the
entities referring to them (``deleteVertex``, ``deleteEdgeBetweenVertices``), collected for one write (DD-056).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import EntityStatus, RelationshipStatus
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.edge_direction import EdgeDirection
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.map_type import MapType

from aurelius_atlas_core.entity_documents import VersionedEntity
from aurelius_atlas_core.entity_retriever import SOFT_REFERENCE_SEPARATOR
from aurelius_atlas_core.entity_store import EntityChange, EntityStore, RelationshipChange
from aurelius_atlas_core.graph_helper import collection_elements, edge_for_label
from aurelius_atlas_core.stored_entity import StoredEntity

UNSET_REQUIRED = "Cannot unset required attribute {name} on {guid} edge = {label}"
REMOVE_ARRAY_ELEMENT = "Cannot remove array element from required attribute {name} on {guid} {label}"
REMOVE_MAP_ENTRY = "Cannot remove map entry {name} from required attribute {name} on {guid} {label}"


@dataclass
class Deletion:
    """``RequestContext``'s record of a delete: the entities deleted and changed, in the order reached."""

    deleted: dict[str, VersionedEntity] = field(default_factory=dict)
    updated: dict[str, VersionedEntity] = field(default_factory=dict)
    changes: list[EntityChange] = field(default_factory=list)
    relationship_changes: list[RelationshipChange] = field(default_factory=list)

    def change(self, guid: str) -> int | None:
        """The index of the change of entity ``guid``, or None."""
        return next((index for index, change in enumerate(self.changes) if change.entity.guid == guid), None)


class DeleteHandler:
    """Deletes entities of ``store`` at ``now``; ``soft`` keeps them ``DELETED``, else they are removed."""

    soft = True

    def __init__(self, store: EntityStore, *, now: int, user: str | None, purge: bool = False) -> None:
        self.store = store
        self.now = now
        self.user = user
        self.purge = purge

    def _delete_vertex(self, stored: StoredEntity) -> StoredEntity | None:
        """``_deleteVertex``: the entity's state after the delete, or None when it is removed."""
        raise NotImplementedError  # pragma: no cover - each handler answers

    async def delete_entities(self, candidates: Sequence[VersionedEntity]) -> Deletion:
        """``deleteEntities``: each candidate with what it owns, then those referring to them (EDL-03 to EDL-07).

        Raises:
            AtlasError: ``INTERNAL_ERROR`` when a mandatory reference would lose a deleted entity.
        """
        deletion = Deletion()
        for candidate in candidates:
            if not self._skipped(candidate.entity, deletion):
                await self._owned(candidate, deletion)
        await self._referrers(deletion)
        for found in deletion.deleted.values():
            entity_type = self._entity_type(found.entity)
            after = None if entity_type.is_internal else self._delete_vertex(found.entity)
            deletion.changes.append(EntityChange(after or found.entity, found.version, remove=after is None))
        await self._relationships(deletion)
        return deletion

    async def _relationships(self, deletion: Deletion) -> None:
        """``deleteVertex`` for relationship edges (REL-09).

        A removed entity takes all its relationships with it, and the other ends stop listing them; a soft delete
        marks ``DELETED`` the ``ACTIVE`` ones whose end 2 it deletes, Atlas's incoming edges.
        """
        removed = {change.entity.guid for change in deletion.changes if change.remove}
        listed = [guid for found in deletion.deleted.values() for guid in found.entity.relationship_guids or []]
        relationships = await self.store.get_relationships(listed)
        dropped: dict[str, set[str]] = {}
        for found in relationships.values():
            relationship = found.relationship
            if removed & set(relationship.ends()):
                deletion.relationship_changes.append(RelationshipChange(relationship, found.version, remove=True))
                for end in relationship.ends():
                    dropped.setdefault(end, set()).add(relationship.guid)
            elif (
                relationship.end2_guid in deletion.deleted
                and relationship.state is RelationshipStatus.ACTIVE
                and not self.purge
            ):
                changed = relationship.model_copy(
                    update={"state": RelationshipStatus.DELETED, "update_time": self.now, "updated_by": self.user}
                )
                deletion.relationship_changes.append(RelationshipChange(changed, found.version))
        await self._unlist(deletion, {guid: guids for guid, guids in dropped.items() if guid not in removed})

    async def _unlist(self, deletion: Deletion, dropped: dict[str, set[str]]) -> None:
        """The other ends of removed relationships stop listing them, merged with their other changes."""
        unchanged = await self.store.get_many([guid for guid in dropped if deletion.change(guid) is None])
        for guid, guids in dropped.items():
            index = deletion.change(guid)
            if index is not None:
                change = deletion.changes[index]
                deletion.changes[index] = EntityChange(change.entity.unlisting(guids), change.expected, change.remove)
            elif guid in unchanged:
                deletion.changes.append(EntityChange(unchanged[guid].entity.unlisting(guids), unchanged[guid].version))

    def _skipped(self, stored: StoredEntity, deletion: Deletion) -> bool:
        """``skipVertexForDelete``: deleted by this request, or ``DELETED`` (``ACTIVE`` for a purge) (EDL-03)."""
        skipped_state = EntityStatus.ACTIVE if self.purge else EntityStatus.DELETED
        return stored.guid in deletion.deleted or stored.state is skipped_state

    async def _owned(self, root: VersionedEntity, deletion: Deletion) -> None:
        """``getOwnedVertices``: the entity and those its owned references name, depth first (EDL-05)."""
        stack = [root]
        while stack:
            found = stack.pop()
            if self._skipped(found.entity, deletion):
                continue
            deletion.deleted[found.entity.guid] = found
            entity_type = self._entity_type(found.entity)
            guids = owned_guids(found.entity, entity_type) + await self._owned_through_relationships(
                found.entity, entity_type
            )
            known = await self.store.get_many(guids)
            stack += [known[guid] for guid in guids if guid in known]

    async def _owned_through_relationships(self, stored: StoredEntity, entity_type: EntityType) -> list[str]:
        """``getOwnedVertices`` over relationships: end 2 of each relationship of an owned attribute (REL-19).

        A single attribute's is its ``OUT`` relationship with the label, ``ACTIVE`` else the latest ``DELETED``; an
        array's are all of its relationships. One ``DELETED`` (``ACTIVE`` for a purge) is skipped.
        """
        attributes = [attribute for attribute in entity_type.owned_ref_attributes if attribute.relationship_name]
        if not attributes or not stored.relationship_guids:
            return []
        found = await self.store.get_relationships(stored.relationship_guids)
        relationships = [found[guid].relationship for guid in stored.relationship_guids if guid in found]
        skipped = RelationshipStatus.ACTIVE if self.purge else RelationshipStatus.DELETED
        guids: list[str] = []
        for attribute in attributes:
            if attribute.attribute_type.category is TypeCategory.OBJECT_ID_TYPE:
                edge = edge_for_label(stored.guid, relationships, attribute.relationship_edge_label, EdgeDirection.OUT)
                edges = [] if edge is None else [edge]
            else:
                edges = collection_elements(stored.guid, relationships, attribute)
            guids += [edge.end2_guid for edge in edges if edge.state is not skipped]
        return guids

    async def _referrers(self, deletion: Deletion) -> None:
        """``deleteVertex``: drop or keep each reference to a deleted entity, and change its holder (EDL-07)."""
        deleted = set(deletion.deleted)
        for found in await self.store.referring(list(deleted)):
            holder = found.entity
            if holder.guid in deleted or holder.state is EntityStatus.DELETED:
                continue
            entity_type = self._entity_type(holder)
            attributes = dict(holder.attributes)
            for attribute in entity_type.all_attributes.values():
                if not attribute.attribute_def.is_soft_referenced():
                    self._unset(holder.guid, attribute, attributes, deleted)
            changed = holder.model_copy(update={"attributes": attributes}).touched(now=self.now, user=self.user)
            deletion.updated[holder.guid] = VersionedEntity(changed, found.version)
            deletion.changes.append(EntityChange(changed, found.version))

    def _unset(self, guid: str, attribute: AtlasAttribute, attributes: dict[str, object], deleted: set[str]) -> None:
        """``deleteEdgeBetweenVertices``: a hard delete drops the reference; a mandatory one fails (EDL-07)."""
        name, value = attribute.qualified_name, attributes.get(attribute.qualified_name)
        definition, type_ = attribute.attribute_def, attribute.attribute_type
        problem = {"name": name, "guid": guid, "label": attribute.relationship_edge_label}
        if type_.category is TypeCategory.OBJECT_ID_TYPE and value in deleted:
            if not definition.is_optional:
                raise AtlasError.of_message(AtlasErrorCode.INTERNAL_ERROR, UNSET_REQUIRED.format(**problem))
            if not self.soft:
                attributes.pop(name, None)
        elif isinstance(type_, ArrayType) and isinstance(value, list) and deleted & set(map(str, value)):
            if not definition.is_optional and len(value) <= definition.values_min_count:
                raise AtlasError.of_message(AtlasErrorCode.INTERNAL_ERROR, REMOVE_ARRAY_ELEMENT.format(**problem))
            if not self.soft:
                attributes[name] = [item for item in value if str(item) not in deleted]
        elif isinstance(type_, MapType) and isinstance(value, dict) and deleted & set(map(str, value.values())):
            if not definition.is_optional and len(value) <= definition.values_min_count:
                raise AtlasError.of_message(AtlasErrorCode.INTERNAL_ERROR, REMOVE_MAP_ENTRY.format(**problem))
            if not self.soft:
                attributes[name] = {key: item for key, item in value.items() if str(item) not in deleted}

    def _entity_type(self, stored: StoredEntity) -> EntityType:
        entity_type = self.store.registry.entity_type(stored.type_name)
        if entity_type is None:
            raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, TypeCategory.ENTITY.value, stored.type_name)
        return entity_type


def owned_guids(stored: StoredEntity, entity_type: EntityType) -> list[str]:
    """The GUIDs an entity's owned reference attributes name: single, array or map, soft ones parsed (EDL-05).

    Relationship ends are not attribute values (DD-064); ``DeleteHandler`` follows their relationships (REL-19).
    """
    guids: list[str] = []
    for attribute in entity_type.owned_ref_attributes:
        if attribute.relationship_name is not None:
            continue
        value = stored.attributes.get(attribute.qualified_name)
        items = list(value.values()) if isinstance(value, dict) else value if isinstance(value, list) else [value]
        for item in items:
            if item is None:
                continue
            if attribute.attribute_def.is_soft_referenced():
                parts = [part for part in str(item).split(SOFT_REFERENCE_SEPARATOR) if part]
                if len(parts) > 1:
                    guids.append(parts[1])
            else:
                guids.append(str(item))
    return guids
