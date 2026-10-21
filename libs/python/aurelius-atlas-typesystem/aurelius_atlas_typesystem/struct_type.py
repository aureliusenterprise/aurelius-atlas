"""``AtlasStructType``: a struct's attributes, as its definition resolves them (TRG-11, TRG-12, DD-041)."""

from typing import TYPE_CHECKING, cast

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.typedef import (
    CONSTRAINT_PARAM_ATTRIBUTE,
    CONSTRAINT_TYPE_INVERSE_REF,
    CONSTRAINT_TYPE_OWNED_REF,
    AtlasAttributeDef,
    AtlasStructDef,
    Cardinality,
    TypeCategory,
)

from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.map_type import MapType

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_typesystem.attribute import AtlasAttribute

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.entity_type import EntityType


def contained_type(type_: AtlasType) -> AtlasType:
    """The element of an array or the value of a map; the type itself otherwise."""
    if isinstance(type_, ArrayType):
        return resolved(type_.element_type)
    if isinstance(type_, MapType):
        return resolved(type_.value_type)
    return type_


def referenced_entity_type(type_: AtlasType) -> EntityType | None:
    """The entity type a type, an array of it or a map to it refers to, or None (TRG-12)."""
    if isinstance(type_, ArrayType):
        type_ = resolved(type_.element_type)
    if isinstance(type_, MapType):
        type_ = resolved(type_.value_type)
    return cast("EntityType", type_) if type_.category is TypeCategory.ENTITY else None


class StructType(AtlasType):
    """A struct type, and the base of every type with attributes (``AtlasStructType``, TRG-10 to TRG-13)."""

    def __init__(self, struct_def: AtlasStructDef) -> None:
        super().__init__(struct_def.name, struct_def.category, struct_def.service_type)
        self.struct_def = struct_def
        self.all_attributes: dict[str, AtlasAttribute] = {}
        self.unique_attributes: dict[str, AtlasAttribute] = {}

    def attribute(self, name: str | None) -> AtlasAttribute | None:
        """The attribute named exactly ``name``, then the system and business attribute, or None (TRG-13, THY-05)."""
        if name is None:
            return None
        return self.all_attributes.get(name) or self._system_attribute(name) or self._business_attribute(name)

    def _system_attribute(self, name: str) -> AtlasAttribute | None:  # noqa: ARG002 - structs have none
        return None

    def _business_attribute(self, name: str) -> AtlasAttribute | None:  # noqa: ARG002 - structs have none
        return None

    def attribute_type(self, name: str | None) -> AtlasType | None:
        """The type of the attribute named ``name``, or None (TRG-13)."""
        attribute = self.attribute(name)
        return None if attribute is None else attribute.attribute_type

    def _resolve_references(self, registry: TypeRegistry) -> None:
        attributes: dict[str, AtlasAttribute] = {}
        for attribute_def in self.struct_def.attribute_defs:
            attribute_type = registry.get_type(attribute_def.type_name)
            attribute = AtlasAttribute(self, attribute_def, attribute_type)
            if attribute_def.cardinality in {Cardinality.LIST, Cardinality.SET}:
                if not isinstance(attribute_type, ArrayType):
                    raise AtlasError(
                        AtlasErrorCode.INVALID_ATTRIBUTE_TYPE_FOR_CARDINALITY, self.type_name, attribute_def.name
                    )
                attribute_type.min_count = attribute_def.values_min_count
                attribute_type.max_count = attribute_def.values_max_count
                attribute_type.cardinality = attribute_def.cardinality or Cardinality.LIST
            if contained_type(attribute_type).category in (TypeCategory.CLASSIFICATION, TypeCategory.BUSINESS_METADATA):
                raise AtlasError(AtlasErrorCode.ATTRIBUTE_TYPE_INVALID, self.type_name, attribute_def.name)
            attributes[str(attribute_def.name)] = attribute
        self._resolve_constraints(registry)
        self.all_attributes = attributes
        self.unique_attributes = {
            name: attribute for name, attribute in attributes.items() if attribute.attribute_def.is_unique
        }

    def _resolve_constraints(self, registry: TypeRegistry) -> None:
        for attribute_def in self.struct_def.attribute_defs:
            for constraint in attribute_def.constraints or []:
                if constraint.is_constraint_type(CONSTRAINT_TYPE_OWNED_REF):
                    if referenced_entity_type(registry.get_type(attribute_def.type_name)) is None:
                        raise AtlasError(
                            AtlasErrorCode.CONSTRAINT_OWNED_REF_ATTRIBUTE_INVALID_TYPE,
                            self.type_name,
                            attribute_def.name,
                            CONSTRAINT_TYPE_OWNED_REF,
                            attribute_def.type_name,
                        )
                elif constraint.is_constraint_type(CONSTRAINT_TYPE_INVERSE_REF):
                    self._check_inverse_ref(registry, attribute_def, constraint.params)

    def _check_inverse_ref(
        self, registry: TypeRegistry, attribute_def: AtlasAttributeDef, params: dict[str, object] | None
    ) -> None:
        entity_type = referenced_entity_type(registry.get_type(attribute_def.type_name))
        if entity_type is None:
            raise AtlasError(
                AtlasErrorCode.CONSTRAINT_INVERSE_REF_ATTRIBUTE_INVALID_TYPE,
                self.type_name,
                attribute_def.name,
                CONSTRAINT_TYPE_INVERSE_REF,
                attribute_def.type_name,
            )
        inverse_name = (params or {}).get(CONSTRAINT_PARAM_ATTRIBUTE)
        if inverse_name is None or not str(inverse_name).strip():
            raise AtlasError(
                AtlasErrorCode.CONSTRAINT_MISSING_PARAMS,
                self.type_name,
                attribute_def.name,
                CONSTRAINT_PARAM_ATTRIBUTE,
                CONSTRAINT_TYPE_INVERSE_REF,
                java_string(params),
            )
        inverse_def = entity_type.struct_def.get_attribute(str(inverse_name))
        if inverse_def is None:
            raise AtlasError(
                AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_NON_EXISTING,
                self.type_name,
                attribute_def.name,
                CONSTRAINT_TYPE_INVERSE_REF,
                entity_type.type_name,
                inverse_name,
            )
        if referenced_entity_type(registry.get_type(inverse_def.type_name)) is None:
            raise AtlasError(
                AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_INVALID_TYPE,
                self.type_name,
                attribute_def.name,
                CONSTRAINT_TYPE_INVERSE_REF,
                entity_type.type_name,
                inverse_name,
            )

    def _resolve_references_phase2(self, registry: TypeRegistry) -> None:
        for attribute in self.all_attributes.values():
            if attribute.inverse_ref_attribute_name is None:
                continue
            entity_type = referenced_entity_type(registry.get_type(attribute.attribute_def.type_name))
            if entity_type is not None:
                attribute.inverse_ref_attribute = entity_type.attribute(attribute.inverse_ref_attribute_name)
