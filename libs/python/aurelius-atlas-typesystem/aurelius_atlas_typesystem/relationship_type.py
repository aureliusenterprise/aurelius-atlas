"""``AtlasRelationshipType``: a relationship between two entity types and the attributes it adds (THY-10, THY-11)."""

from typing import TYPE_CHECKING

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    CONSTRAINT_TYPE_OWNED_REF,
    AtlasAttributeDef,
    AtlasConstraintDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    Cardinality,
    RelationshipCategory,
    array_type_name,
)

from aurelius_atlas_typesystem.array_type import ArrayType

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.edge_direction import EdgeDirection
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.struct_type import StructType

RELATIONSHIP_VALUES_ERROR = "{type}: relationship values arrive with AtlasRelationship in 3.1"


class RelationshipType(StructType):
    """A relationship type: its ends, label and the attributes it adds to them (THY-08 to THY-10)."""

    def __init__(self, relationship_def: AtlasRelationshipDef) -> None:
        super().__init__(relationship_def)
        self.relationship_def = relationship_def
        ends = (relationship_def.end_def1, relationship_def.end_def2)
        self.has_legacy_attribute_end = any(end is not None and end.is_legacy_attribute for end in ends)
        self.relationship_label: str | None = None
        self.end1_type: EntityType | None = None
        self.end2_type: EntityType | None = None

    def is_valid_value(self, value: object) -> bool:
        """Takes an ``AtlasRelationship``, which arrives with relationship instances in 3.1."""
        raise NotImplementedError(RELATIONSHIP_VALUES_ERROR.format(type=self.type_name))

    def is_valid_value_for_update(self, value: object) -> bool:
        """Takes an ``AtlasRelationship``, which arrives with relationship instances in 3.1."""
        raise NotImplementedError(RELATIONSHIP_VALUES_ERROR.format(type=self.type_name))

    def are_equal_values(self, left: object, right: object, guid_assignments: dict[str, str] | None) -> bool:
        """Takes an ``AtlasRelationship``, which arrives with relationship instances in 3.1."""
        raise NotImplementedError(RELATIONSHIP_VALUES_ERROR.format(type=self.type_name))

    def _resolve_references(self, registry: TypeRegistry) -> None:
        super()._resolve_references(registry)
        self.end1_type = self._end_type(registry, "endDef1", self.relationship_def.end_def1)
        self.end2_type = self._end_type(registry, "endDef2", self.relationship_def.end_def2)
        for label, end in (("endDef1", self.relationship_def.end_def1), ("endDef2", self.relationship_def.end_def2)):
            if end is None or not end.name:
                raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE, label, "name")
        validate_relationship_def(self.relationship_def)

    def _end_type(self, registry: TypeRegistry, label: str, end: AtlasRelationshipEndDef | None) -> EntityType:
        if end is None or not end.type:
            raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE, label, "type")
        end_type = registry.get_type(end.type)
        if not isinstance(end_type, EntityType):
            raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_INVALID_END_TYPE, self.type_name, end.type)
        return end_type

    def _resolve_references_phase2(self, registry: TypeRegistry) -> None:
        super()._resolve_references_phase2(registry)
        end1, end2 = _ends(self.relationship_def)
        end1_type, end2_type = _resolved_entity(self.end1_type), _resolved_entity(self.end2_type)
        label = self.relationship_def.relationship_label
        if label is None:
            if not end1.is_legacy_attribute and not end2.is_legacy_attribute:
                label = f"r:{self.type_name}"
            elif end1.is_legacy_attribute and not end2.is_legacy_attribute:
                label = _legacy_edge_label(end1_type, end1.name)
            elif not end1.is_legacy_attribute and end2.is_legacy_attribute:
                label = _legacy_edge_label(end2_type, end2.name)
        self.relationship_label = label
        self._add_to_end(end1, end1_type, str(end2_type.type_name), registry, label)
        self._add_to_end(end2, end2_type, str(end1_type.type_name), registry, label)
        self._set_edge_directions(end1, end2, end1_type, end2_type)

    def _add_to_end(
        self,
        end: AtlasRelationshipEndDef,
        entity_type: EntityType,
        other_type_name: str,
        registry: TypeRegistry,
        label: str | None,
    ) -> None:
        name = str(end.name)
        attribute = entity_type.attribute(name)
        if label is None:
            label = _legacy_edge_label(entity_type, name)
        if attribute is None:
            composition = self.relationship_def.relationship_category is RelationshipCategory.COMPOSITION
            attribute_def = AtlasAttributeDef(
                name=name,
                type_name=array_type_name(other_type_name) if end.cardinality is Cardinality.SET else other_type_name,
                is_optional=not composition or end.is_container,
                cardinality=end.cardinality,
            )
            if composition and end.is_container:
                attribute_def.add_constraint(AtlasConstraintDef(type=CONSTRAINT_TYPE_OWNED_REF))
            attribute_type = registry.get_type(attribute_def.type_name)
            if isinstance(attribute_type, ArrayType):
                attribute_type.cardinality = attribute_def.cardinality or Cardinality.LIST
            attribute = AtlasAttribute(entity_type, attribute_def, attribute_type, str(self.type_name), label)
            attribute.is_legacy_attribute = end.is_legacy_attribute
        else:
            attribute.relationship_name = self.type_name
            attribute.relationship_edge_label = label or attribute.relationship_edge_label
            attribute.is_legacy_attribute = True
        entity_type._add_relationship_attribute(name, attribute, self)  # noqa: SLF001

    def _set_edge_directions(
        self,
        end1: AtlasRelationshipEndDef,
        end2: AtlasRelationshipEndDef,
        end1_type: EntityType,
        end2_type: EntityType,
    ) -> None:
        """``addRelationshipEdgeDirection`` (THY-10)."""
        name = str(self.type_name)
        first = end1_type.relationship_attribute(str(end1.name), name)
        if end1.type == end2.type and end1.name == end2.name:
            if first is not None:
                first.relationship_edge_direction = EdgeDirection.BOTH
            return
        second = end2_type.relationship_attribute(str(end2.name), name)
        direction1, direction2 = EdgeDirection.OUT, EdgeDirection.IN
        if end1.is_legacy_attribute and end2.is_legacy_attribute:
            if self.relationship_def.relationship_label is None:
                direction2 = EdgeDirection.OUT
        elif not end1.is_legacy_attribute and end2.is_legacy_attribute:
            direction1, direction2 = EdgeDirection.IN, EdgeDirection.OUT
        if first is not None:
            first.relationship_edge_direction = direction1
        if second is not None:
            second.relationship_edge_direction = direction2


def _ends(relationship_def: AtlasRelationshipDef) -> tuple[AtlasRelationshipEndDef, AtlasRelationshipEndDef]:
    end1, end2 = relationship_def.end_def1, relationship_def.end_def2
    if end1 is None or end2 is None:  # pragma: no cover - phase 1 checked both ends
        raise AtlasError(AtlasErrorCode.INVALID_VALUE, "relationshipDef ends are null")
    return end1, end2


def _resolved_entity(entity_type: EntityType | None) -> EntityType:
    if entity_type is None:  # pragma: no cover - phase 1 resolved both ends
        raise AtlasError(AtlasErrorCode.INVALID_VALUE, "relationship end type is not resolved")
    return entity_type


def _legacy_edge_label(entity_type: EntityType, attribute_name: str | None) -> str | None:
    """``getLegacyEdgeLabel``: ``__`` and the qualified name of the end's attribute, or None (THY-09)."""
    attribute = entity_type.attribute(attribute_name)
    return None if attribute is None else f"__{attribute.qualified_name}"


def validate_relationship_def(relationship_def: AtlasRelationshipDef) -> None:
    """Check the ends' cardinality and containers against the category (``validateAtlasRelationshipDef``, THY-08).

    Raises:
        AtlasError: The ``RELATIONSHIPDEF_*`` code of the first rule broken.
    """
    end1, end2 = _ends(relationship_def)
    category = relationship_def.relationship_category
    name = relationship_def.name
    if Cardinality.LIST in {end1.cardinality, end2.cardinality}:
        raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_LIST_ON_END, name)
    if end1.is_container and end2.is_container:
        raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_DOUBLE_CONTAINERS, name)
    if end1.is_container or end2.is_container:
        if category in {None, RelationshipCategory.ASSOCIATION}:
            raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_ASSOCIATION_AND_CONTAINER, name)
    elif category is RelationshipCategory.COMPOSITION:
        raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_COMPOSITION_NO_CONTAINER, name)
    elif category is RelationshipCategory.AGGREGATION:
        raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_AGGREGATION_NO_CONTAINER, name)
    if category is RelationshipCategory.COMPOSITION and any(
        end.cardinality is Cardinality.SET and not end.is_container for end in (end1, end2)
    ):
        raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_COMPOSITION_MULTIPLE_PARENTS, name)
