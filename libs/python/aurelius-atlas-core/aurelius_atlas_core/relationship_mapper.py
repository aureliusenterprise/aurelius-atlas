"""``RelationshipMapper``: an entity's relationship attributes onto relationships (REL-11 to REL-16, DD-066).

The relationship side of ``EntityGraphMapper``: ``mapRelationshipAttributes`` with
``mapObjectIdValueUsingRelationship``, ``updateRelationship``, ``mapArrayValue``, ``addInverseReference`` and
``deleteEdgeReference``, in memory. The writer writes what it changed, and the ends' new lists, with the request's
entities.
"""

from collections.abc import Callable, Mapping
from typing import Any

from aurelius_atlas_model.instance import (
    AtlasEntity,
    AtlasRelatedObjectId,
    AtlasRelationship,
    EntityOperation,
    RelationshipStatus,
)
from aurelius_atlas_model.typedef import Cardinality, TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.edge_direction import EdgeDirection
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.struct_type import struct_attributes
from aurelius_atlas_typesystem.values import java_distinct, relationship_type_of

from aurelius_atlas_core.entity_documents import DocumentVersion, VersionedEntity
from aurelius_atlas_core.entity_store import EntityStore, RelationshipChange
from aurelius_atlas_core.graph_helper import (
    collection_elements,
    edge_for_label,
    referenced_end,
    relationship_type_name,
)
from aurelius_atlas_core.relationship_store import (
    created_relationship,
    relationship_edge_label,
    validate_relationship,
)
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship

type Resolve = Callable[[Any], str]
"""The GUID of the entity a reference value names; raises ``INVALID_OBJECT_ID`` when it names none."""


class RelationshipMapper:
    """Maps the relationship attributes of one request's entities at ``now``, as ``user`` (DD-066).

    ``known`` holds the entities the request read, and gains those the mapper reads; ``created`` the entities it
    creates. Entities a relationship change makes updated are added to ``touched``; ``hard`` deletes replaced
    relationships rather than marking them ``DELETED`` (REL-15).
    """

    def __init__(  # noqa: PLR0913 - the request's context, as ``EntityMutationContext`` and ``RequestContext``
        self,
        store: EntityStore,
        *,
        resolve: Resolve,
        known: dict[str, VersionedEntity],
        created: Mapping[str, StoredEntity],
        now: int,
        user: str | None,
        hard: bool,
        touched: list[str],
    ) -> None:
        self._store = store
        self._resolve = resolve
        self._known = known
        self._created = created
        self._now = now
        self._user = user
        self._hard = hard
        self._touched = touched
        self._relationships: dict[str, StoredRelationship] = {}
        self._versions: dict[str, DocumentVersion] = {}
        self._changed: dict[str, None] = {}
        self._new: set[str] = set()
        self._removed: set[str] = set()
        self._listed: dict[str, list[str]] = {}

    def relationship_changes(self) -> list[RelationshipChange]:
        """The relationships created, changed and removed, in the order first changed."""
        changes = []
        for guid in self._changed:
            if guid in self._new and guid in self._removed:
                continue
            changes.append(
                RelationshipChange(self._relationships[guid], self._versions.get(guid), remove=guid in self._removed)
            )
        return changes

    def listings(self) -> dict[str, list[str]]:
        """The entities whose lists of relationships changed, and their new lists (DD-061)."""
        return dict(self._listed)

    async def map(self, entity: AtlasEntity, entity_type: EntityType, guid: str, operation: EntityOperation) -> None:
        """``mapRelationshipAttributes``: every relationship attribute on create, the given ones else (REL-11)."""
        if not entity.relationship_attributes:
            return
        for name in entity_type.relationship_attributes:
            if operation is not EntityOperation.CREATE and not entity.has_relationship_attribute(name):
                continue
            value = entity.get_relationship_attribute(name)
            attribute = entity_type.relationship_attribute(name, relationship_type_of(value))
            if attribute is None or (operation is EntityOperation.CREATE and value is None):
                continue
            if attribute.attribute_type.category is TypeCategory.OBJECT_ID_TYPE:
                await self._single(attribute, value, guid)
            elif isinstance(attribute.attribute_type, ArrayType):
                await self._array(entity_type, attribute, value, guid, operation)

    async def _single(self, attribute: AtlasAttribute, value: object, guid: str) -> None:
        """``mapToVertexByTypeCategory`` for a reference: REL-12."""
        direction = attribute.relationship_edge_direction
        relationship_guid = _relationship_guid(value)
        if relationship_guid:
            current = await self._relationship(relationship_guid)
        else:
            current = edge_for_label(
                guid, await self._of(guid), attribute.relationship_edge_label, attribute.relationship_edge_direction
            )
        new = None
        target = None
        if value is not None:
            target = self._resolve(value)
            new = await self._map_object_id(attribute, value, guid, target, current)
            if attribute.inverse_ref_attribute is not None:
                await self._inverse(attribute.inverse_ref_attribute, new, _relationship_attributes(value))
        if current is None and new is not None:
            self._touch(new.end1_guid if direction is EdgeDirection.IN else new.end2_guid)
        if current is not None and (new is None or new.guid != current.guid):
            if target is not None:
                self._touch(target)
            await self._delete_reference(current, attribute, guid, direction)

    async def _array(
        self,
        entity_type: EntityType,
        attribute: AtlasAttribute,
        value: object,
        guid: str,
        operation: EntityOperation,
    ) -> None:
        """``mapArrayValue`` of references: REL-14."""
        current = collection_elements(guid, await self._of(guid), attribute)
        appending = (
            operation is EntityOperation.PARTIAL_UPDATE
            and attribute.attribute_def.is_append_on_partial_update()
            and bool(current)
        )
        items = list(value) if isinstance(value, list | tuple | set) else []
        if attribute.attribute_def.cardinality is Cardinality.SET:
            items = java_distinct(items)
        mapped: list[str] = []
        for index, item in enumerate(items):
            existing = None if appending or index >= len(current) else current[index]
            new = await self._map_object_id(attribute, item, guid, self._resolve(item), existing)
            if attribute.inverse_ref_attribute is not None:
                await self._inverse(attribute.inverse_ref_attribute, new, None)  # Java passes the whole array
            mapped.append(new.guid)
        kept: list[str] = []
        for relationship in current:
            if relationship.guid in mapped:
                continue
            if (
                appending
                or _appends_relationships(entity_type, str(attribute.name))
                or not await self._delete_reference(
                    relationship, attribute, guid, attribute.relationship_edge_direction
                )
            ):
                kept.append(relationship.guid)
        for index, relationship_guid in enumerate(dict.fromkeys(kept + mapped)):
            relationship = self._relationships[relationship_guid]
            if relationship.state is RelationshipStatus.ACTIVE and relationship.index != index:
                self._put(relationship.model_copy(update={"index": index}))

    async def _map_object_id(
        self,
        attribute: AtlasAttribute,
        value: object,
        guid: str,
        target: str,
        current: StoredRelationship | None,
    ) -> StoredRelationship:
        """``mapObjectIdValueUsingRelationship``: update the current relationship, else get or create one."""
        attributes = _relationship_attributes(value)
        direction = attribute.relationship_edge_direction
        if current is not None:
            return await self._update_relationship(current, guid, target, direction, attributes)
        if direction is EdgeDirection.IN:
            new, created = await self._get_or_create(target, guid, str(attribute.relationship_name), attributes)
        else:
            new, created = await self._get_or_create(guid, target, str(attribute.relationship_name), attributes)
        if created:
            self._touch(target)
        return new

    async def _update_relationship(
        self,
        current: StoredRelationship,
        guid: str,
        target: str,
        direction: EdgeDirection,
        attributes: Mapping[str, Any] | None,
    ) -> StoredRelationship:
        """``updateRelationship``: the current relationship when it reaches ``target``, else one that does."""
        if direction is EdgeDirection.IN:
            reached = current.end1_guid
        elif direction is EdgeDirection.OUT:
            reached = current.end2_guid
        else:
            reached = current.end1_guid if current.end2_guid == guid else current.end2_guid
        if reached == target:
            return current
        if direction is EdgeDirection.IN:
            new, _ = await self._get_or_create(target, current.end2_guid, current.type_name, attributes)
        elif direction is EdgeDirection.OUT:
            new, _ = await self._get_or_create(current.end1_guid, target, current.type_name, attributes)
        else:
            new, _ = await self._get_or_create(target, guid, current.type_name, attributes)
        self._touch(target)
        return new

    async def _get_or_create(
        self, end1: str, end2: str, type_name: str, attributes: Mapping[str, Any] | None
    ) -> tuple[StoredRelationship, bool]:
        """``getOrCreate``: an ``ACTIVE`` relationship from ``end1`` to ``end2`` with the label, else a new one.

        Answers it and whether it was created (REL-13).
        """
        from_entity, to_entity = await self._entity(end1), await self._entity(end2)
        relationship = AtlasRelationship(
            type_name=type_name, attributes=None if attributes is None else dict(attributes)
        )
        relationship_type = self._store.registry.relationship_type(type_name)
        if relationship_type is not None:
            label = relationship_edge_label(relationship_type, from_entity, to_entity)
            both = set(await self._listing(end2))
            for found in await self._of(end1):
                if (
                    found.guid in both
                    and (found.end1_guid, found.end2_guid, found.label) == (end1, end2, label)
                    and found.state is RelationshipStatus.ACTIVE
                ):
                    return found, False
        relationship_type = validate_relationship(self._store.registry, from_entity, to_entity, relationship)
        stored = created_relationship(
            relationship_type,
            from_entity,
            to_entity,
            relationship,
            guid=self._store.new_guid(),
            now=self._now,
            user=self._user,
        )
        self._new.add(stored.guid)
        self._put(stored)
        for end in dict.fromkeys((end1, end2)):
            self._listed[end] = [*await self._listing(end), stored.guid]
        return stored, True

    async def _inverse(
        self, inverse: AtlasAttribute, relationship: StoredRelationship, attributes: Mapping[str, Any] | None
    ) -> None:
        """``addInverseReference``: end 2's inverse attribute gets a relationship back to end 1 (REL-16, DV-32)."""
        inverse_type = inverse.defined_in
        name = str(inverse.name)
        if not isinstance(inverse_type, EntityType) or name not in inverse_type.relationship_attributes:
            return
        guid, other = relationship.end2_guid, relationship.end1_guid
        listed = await self._of(guid)
        inverse_edge = edge_for_label(guid, listed, inverse.relationship_edge_label, EdgeDirection.OUT)
        type_name = str(relationship_type_name(guid, listed, inverse_type, name))
        new, created = await self._get_or_create(guid, other, type_name, attributes)
        updated = True
        if inverse.attribute_type.category is TypeCategory.OBJECT_ID_TYPE and inverse_edge is not None:
            if inverse_edge.guid == new.guid:
                updated = False
            else:
                await self._delete_reference(inverse_edge, inverse, guid, EdgeDirection.OUT)
        elif isinstance(inverse.attribute_type, ArrayType):
            updated = created
        if updated:
            self._touch(guid)

    async def _delete_reference(
        self, relationship: StoredRelationship, attribute: AtlasAttribute, guid: str, direction: EdgeDirection
    ) -> bool:
        """``deleteEdgeReference``: delete a relationship an update replaced or dropped (REL-15).

        Answers whether it was removed. An owned entity is not deleted with it until 3.2 (DV-31).
        """
        relationship = self._relationships.get(relationship.guid, relationship)
        if attribute.is_owned_ref:
            await self._delete(relationship)
            return self._hard
        if not self._hard and relationship.state is RelationshipStatus.DELETED:
            return False
        await self._delete(relationship)
        self._touch(referenced_end(relationship, direction, guid))
        return self._hard

    async def _delete(self, relationship: StoredRelationship) -> None:
        """``deleteEdge``: mark it ``DELETED``, or remove it and drop it from its ends' lists."""
        if not self._hard:
            if relationship.state is not RelationshipStatus.DELETED:
                self._put(
                    relationship.model_copy(
                        update={"state": RelationshipStatus.DELETED, "update_time": self._now, "updated_by": self._user}
                    )
                )
            return
        self._removed.add(relationship.guid)
        self._changed[relationship.guid] = None
        for end in relationship.ends():
            self._listed[end] = [guid for guid in await self._listing(end) if guid != relationship.guid]

    def _touch(self, guid: str) -> None:
        """``recordEntityUpdate``: the entity becomes updated by this request (EWR-12)."""
        if guid not in self._touched:
            self._touched.append(guid)

    def _put(self, relationship: StoredRelationship) -> None:
        self._relationships[relationship.guid] = relationship
        self._changed[relationship.guid] = None

    async def _entity(self, guid: str) -> StoredEntity:
        """An entity the request creates, read or reads now."""
        if guid in self._created:
            return self._created[guid]
        if guid not in self._known:
            found = await self._store.get(guid)
            if found is None:  # pragma: no cover - references are resolved to stored or created entities
                raise KeyError(guid)
            self._known[guid] = found
        return self._known[guid].entity

    async def _listing(self, guid: str) -> list[str]:
        """The relationships entity ``guid`` lists, as this request changed them."""
        if guid not in self._listed:
            await self._entity(guid)
        return self._listed_now(guid)

    def _listed_now(self, guid: str) -> list[str]:
        if guid in self._listed:
            return self._listed[guid]
        stored = self._created.get(guid) or (self._known[guid].entity if guid in self._known else None)
        return list(stored.relationship_guids or []) if stored is not None else []

    async def _of(self, guid: str) -> list[StoredRelationship]:
        """Entity ``guid``'s relationships, as this request changed them, in the order it lists them."""
        listed = await self._listing(guid)
        await self._read([found for found in listed if found not in self._relationships])
        return [self._relationships[found] for found in listed if found in self._relationships]

    async def _relationship(self, guid: str) -> StoredRelationship | None:
        """The relationship with ``guid``, unless unknown or removed by this request."""
        if guid not in self._relationships:
            await self._read([guid])
        return None if guid in self._removed else self._relationships.get(guid)

    async def _read(self, guids: list[str]) -> None:
        if guids:
            for guid, found in (await self._store.get_relationships(guids)).items():
                self._relationships[guid] = found.relationship
                self._versions[guid] = found.version


def _appends_relationships(entity_type: EntityType, name: str) -> bool:
    """``getAppendOptionForRelationship``: the type's relationship attribute ``name`` appends (REL-14)."""
    return any(
        definition.name == name and definition.is_append_on_partial_update()
        for definition in entity_type.entity_def.relationship_attribute_defs or []
    )


def _relationship_guid(value: object) -> str | None:
    """``getRelationshipGuid``: a related object id's relationship GUID, or a map's."""
    if isinstance(value, AtlasRelatedObjectId):
        return value.relationship_guid
    if isinstance(value, Mapping):
        found = value.get("relationshipGuid")
        return None if found is None else str(found)
    return None


def _relationship_attributes(value: object) -> Mapping[str, Any] | None:
    """``getRelationshipAttributes``: a related object id's relationship attributes, or a map's."""
    if isinstance(value, AtlasRelatedObjectId):
        struct = value.relationship_attributes
        return None if struct is None else struct.attributes
    if isinstance(value, Mapping):
        struct = value.get("relationshipAttributes")
        if isinstance(struct, Mapping):
            return struct_attributes(struct)
    return None
