"""``GraphHelper``'s edge lookups, over the relationships an entity lists (REL-12, REL-14, REL-17, DD-065).

A relationship stands for Atlas's edge: it goes out of end 1 and into end 2 (REL-05). An entity's relationships
are those its document lists, in that order (DD-061).
"""

from collections.abc import Iterable
from typing import Any

from aurelius_atlas_model.instance import RelationshipStatus
from aurelius_atlas_model.typedef import (
    CONSTRAINT_PARAM_GROUP,
    CONSTRAINT_TYPE_MUTUAL_EXCLUSION,
    Cardinality,
)
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.edge_direction import EdgeDirection
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.relationship_type import RelationshipType

from aurelius_atlas_core.stored_relationship import StoredRelationship


def parent_side_children(registry: TypeRegistry, entity_type: EntityType) -> dict[str, str]:
    """The type's parent-side attributes and the child attribute each names (RPS-01, DD-755).

    A parent side is a `SET` whose relationship's opposite end is a `SINGLE` child end (HCA-01): the attribute
    adds children, and each child it adds holds exactly one edge of that attribute back. The nine hierarchy
    ends of HCA-01 are its parent sides.
    """
    found: dict[str, str] = {}
    for name, by_relationship in entity_type.relationship_attributes.items():
        attribute = next(iter(by_relationship.values()), None)
        relationship = _relationship_of(registry, attribute)
        if (
            attribute is None
            or relationship is None
            or not isinstance(attribute.attribute_type, ArrayType)
            or _cardinality_of(registry, attribute, entity_type, str(name)) is not Cardinality.SET
        ):
            continue
        opposite = _opposite_end(relationship, attribute)
        if opposite is not None and opposite.cardinality is Cardinality.SINGLE and opposite.name:
            found[str(name)] = str(opposite.name)
    return found


def parent_family(registry: TypeRegistry, candidate_type: EntityType, child_attribute: str) -> dict[str, str]:
    """The candidate's parent family (RPS-01): each child attribute it could hold an edge of, by edge label.

    The family is the `SINGLE` child attribute named and every child attribute of the candidate's type that
    shares its ``mutuallyExclusive`` group (PME-03, the same group PME-07 enforces). Only attributes whose
    opposite end is a `SET` parent end join, which is what makes a group's members name each other's parent.
    """
    child = candidate_type.relationship_attribute(child_attribute)
    relationship = _relationship_of(registry, child)
    opposite = None if child is None else _opposite_end(relationship, child)
    if child is None or relationship is None or opposite is None or opposite.cardinality is not Cardinality.SET:
        return {}
    group = _mutual_group(relationship, child)
    family: dict[str, str] = {}
    for name, by_relationship in candidate_type.relationship_attributes.items():
        attribute = next(iter(by_relationship.values()), None)
        other = None if attribute is None else _opposite_end(_relationship_of(registry, attribute), attribute)
        if attribute is None or other is None or other.cardinality is not Cardinality.SET:
            continue
        if name == child_attribute or (
            group is not None and group == _mutual_group(_relationship_of(registry, attribute), attribute)
        ):
            family[str(attribute.relationship_edge_label)] = str(name)
    return family


def held_parent_edges(
    guid: str, relationships: Iterable[StoredRelationship], family: dict[str, str], parent_guid: str
) -> list[tuple[StoredRelationship, str]]:
    """The active edges of the family that reach a parent other than ``parent_guid`` (RPS-01).

    Answers each held edge with the child attribute it is the edge of, in the order the entity lists them.
    """
    held = []
    for relationship in relationships:
        child_attribute = family.get(str(relationship.label))
        if child_attribute is None or relationship.state is not RelationshipStatus.ACTIVE:
            continue
        if guid in relationship.ends() and other_end(relationship, guid) != parent_guid:
            held.append((relationship, child_attribute))
    return held


def _relationship_of(registry: TypeRegistry, attribute: AtlasAttribute | None) -> RelationshipType | None:
    """The relationship type of the attribute's edge, or None when it names none."""
    if attribute is None or attribute.relationship_name is None:
        return None
    return registry.relationship_type(str(attribute.relationship_name))


def _cardinality_of(
    registry: TypeRegistry, attribute: AtlasAttribute, entity_type: EntityType, name: str
) -> Cardinality | None:
    """The cardinality of the attribute's end: its own when declared, else the end definition's (HCA-01).

    A relationship attribute of an entity type that declares the attribute itself — every m4i parent side does
    — holds its cardinality on its own definition. One the relationship type added has it only on the end.
    """
    if attribute.attribute_def.cardinality is not None:
        return attribute.attribute_def.cardinality
    end = _end_of(_relationship_of(registry, attribute), attribute, entity_type, name)
    return None if end is None else end.cardinality


def _end_of(
    relationship: RelationshipType | None,
    attribute: AtlasAttribute | None,
    entity_type: EntityType | None = None,
    name: str | None = None,
) -> Any:  # noqa: ANN401 - the end definition the attribute sits on, or None
    """The end definition the attribute sits on, or None when the relationship has none for it.

    The owning type and name default to the attribute's own, which is where a relationship-added attribute sits.
    A declared attribute sits on the end of its type and name, not of the attribute the relationship added.
    """
    if relationship is None or attribute is None:
        return None
    owner = entity_type if entity_type is not None else attribute.defined_in
    attribute_name = name if name is not None else attribute.name
    for end in (relationship.relationship_def.end_def1, relationship.relationship_def.end_def2):
        if end is not None and end.type == owner.type_name and end.name == attribute_name:
            return end
    return None


def _opposite_end(relationship: RelationshipType | None, attribute: AtlasAttribute | None) -> Any:  # noqa: ANN401
    """The end definition of the other end, or None for an attribute that names no end or sits on both."""
    if relationship is None or attribute is None:
        return None
    mine = _end_of(relationship, attribute)
    if mine is None:
        return None
    for end in (relationship.relationship_def.end_def1, relationship.relationship_def.end_def2):
        if end is not None and end is not mine:
            return end
    return None


def _mutual_group(relationship: RelationshipType | None, attribute: AtlasAttribute | None) -> str | None:
    """The ``mutuallyExclusive`` group of the attribute's end definition, or None (PME-03)."""
    end = _end_of(relationship, attribute)
    if end is None:
        return None
    for constraint in end.constraints or []:
        if constraint.is_constraint_type(CONSTRAINT_TYPE_MUTUAL_EXCLUSION):
            group = constraint.get_param(CONSTRAINT_PARAM_GROUP)
            return group.strip() if isinstance(group, str) and group.strip() else None
    return None


def parent_end(
    attribute: AtlasAttribute | None,
) -> tuple[str, EdgeDirection] | None:
    """The parent end of a relationship attribute: its edge label and direction (RUL-03, DD-784).

    One owner answers "which end of this attribute's edges is the one the entity holds" for both write
    paths, so a change to the rule is one edit. An attribute with no edge label names no parent end; the
    direction says whether the entity is end 1 (``OUT``) or end 2 (``IN``) of the edge.
    """
    if attribute is None or attribute.relationship_edge_label is None:
        return None
    return str(attribute.relationship_edge_label), attribute.relationship_edge_direction


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
