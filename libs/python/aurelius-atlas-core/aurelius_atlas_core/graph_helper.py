"""``GraphHelper``'s edge lookups, over the relationships an entity lists (REL-12, REL-14, REL-17, DD-065).

A relationship stands for Atlas's edge: it goes out of end 1 and into end 2 (REL-05). An entity's relationships
are those its document lists, in that order (DD-061).
"""

from collections.abc import Iterable

from aurelius_atlas_model.instance import RelationshipStatus
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.edge_direction import EdgeDirection
from aurelius_atlas_typesystem.entity_type import EntityType

from aurelius_atlas_core.stored_relationship import StoredRelationship


def edges_for_label(
    guid: str, relationships: Iterable[StoredRelationship], label: str, direction: EdgeDirection
) -> list[StoredRelationship]:
    """``getEdgesForLabel``: entity ``guid``'s relationships with ``label`` in ``direction``, in any state."""
    found = []
    for relationship in relationships:
        if relationship.label != label:
            continue
        if (
            (direction is EdgeDirection.OUT and relationship.end1_guid == guid)
            or (direction is EdgeDirection.IN and relationship.end2_guid == guid)
            or (direction is EdgeDirection.BOTH and guid in relationship.ends())
        ):
            found.append(relationship)
    return found


def edge_for_label(
    guid: str, relationships: Iterable[StoredRelationship], label: str, direction: EdgeDirection
) -> StoredRelationship | None:
    """``getEdgeForLabel``: the first ``ACTIVE`` one of ``edges_for_label``, else the latest updated ``DELETED``."""
    latest = None
    for relationship in edges_for_label(guid, relationships, label, direction):
        if relationship.state is RelationshipStatus.ACTIVE:
            return relationship
        if latest is None or relationship.update_time >= latest.update_time:
            latest = relationship
    return latest


def collection_elements(
    guid: str, relationships: Iterable[StoredRelationship], attribute: AtlasAttribute
) -> list[StoredRelationship]:
    """``getCollectionElementsUsingRelationship``: the attribute's relationships, an array's by index (DD-065).

    They are sorted by index only when the first has one, as ``sortCollectionElements`` does.
    """
    found = edges_for_label(
        guid, relationships, attribute.relationship_edge_label, attribute.relationship_edge_direction
    )
    if isinstance(attribute.attribute_type, ArrayType) and found and found[0].index is not None:
        found.sort(key=lambda relationship: relationship.index or 0)
    return found


def relationship_type_name(
    guid: str, relationships: Iterable[StoredRelationship], entity_type: EntityType, name: str
) -> str | None:
    """``getRelationshipTypeName``: the relationship type of attribute ``name`` of entity ``guid`` (REL-17).

    The attribute's only one, else that of the first relationship the entity is end 2 of that is one of the
    attribute's, else the attribute's first.
    """
    names = list(entity_type.relationship_attributes.get(name, {}))
    if len(names) < 2:  # noqa: PLR2004 - one relationship type, or none
        return names[0] if names else None
    found = (r.type_name for r in relationships if r.end2_guid == guid and r.type_name in names)
    return next(found, names[0])


def referenced_end(relationship: StoredRelationship, direction: EdgeDirection, guid: str) -> str:
    """``getReferencedEntityVertex``: end 2 for ``OUT``, end 1 for ``IN``, the end that is not ``guid`` for ``BOTH``."""
    if direction is EdgeDirection.OUT:
        return relationship.end2_guid
    if direction is EdgeDirection.IN:
        return relationship.end1_guid
    return relationship.end2_guid if relationship.end1_guid == guid else relationship.end1_guid


def other_end(relationship: StoredRelationship, guid: str) -> str:
    """The end ``mapVertexToObjectId`` reads: end 2, unless that is entity ``guid``."""
    return relationship.end1_guid if relationship.end2_guid == guid else relationship.end2_guid
