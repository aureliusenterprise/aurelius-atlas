"""``AtlasStructType``: a struct's attributes, as its definition resolves them (TRG-11, TRG-12, DD-041)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import AtlasEntity, AtlasStruct
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
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.map_type import MapType
from aurelius_atlas_typesystem.values import parse_json

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.entity_type import EntityType
    from aurelius_atlas_typesystem.registry import TypeRegistry

STRUCT_STRING_ERROR = "a string is no struct value: Java's getStructFromValue fails on it"

type StructValue = AtlasStruct | dict[str, Any]
"""A struct value: an ``AtlasStruct`` (or subclass) or a map, as Java's struct types take."""


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

    def create_default_value(self) -> AtlasStruct:
        """A struct of this type with the defaults of its mandatory attributes (EVL-05)."""
        struct = AtlasStruct(type_name=self.struct_def.name)
        self.populate_default_values(struct)
        return struct

    def create_default_value_of(self, value: object) -> Any:  # noqa: ANN401, ARG002 - Java ignores the value
        """``createDefaultValue(Object)``: the default, whatever value is given (EVL-05)."""
        return self.create_default_value()

    def is_valid_value(self, value: object) -> bool:
        """Null, or a struct or map whose own attributes are each valid or optionally absent (EVL-01)."""
        if value is None:
            return True
        attributes = _struct_attributes(value)
        if attributes is None:
            return False
        return all(self._assignable(attributes.get(str(d.name)), d) for d in self.struct_def.attribute_defs)

    def is_valid_value_for_update(self, value: object) -> bool:
        """Null, or a struct or map whose present attributes with a definition are valid for update (EVL-03)."""
        if value is None:
            return True
        attributes = _struct_attributes(value)
        if attributes is None:
            return False
        for name, item in attributes.items():
            attribute_def = self.struct_def.get_attribute(name)
            if item is None or attribute_def is None:
                continue
            attribute = self.all_attributes.get(str(attribute_def.name))
            if attribute is not None and not attribute.attribute_type.is_valid_value_for_update(item):
                return False
        return True

    def get_normalized_value(self, value: object) -> Any:  # noqa: ANN401 - the struct or map itself
        """The struct or map, its attributes normalised, when it is valid; else None (EVL-04)."""
        if value is None or not self.is_valid_value(value):
            return None
        if isinstance(value, AtlasStruct | dict):
            self.normalize_attribute_values(value)
            return value
        return None  # pragma: no cover - a valid value is a struct or a map

    def get_normalized_value_for_update(self, value: object) -> Any:  # noqa: ANN401 - the struct or map itself
        """As ``get_normalized_value``, checked and normalised for update (EVL-03)."""
        if value is None or not self.is_valid_value_for_update(value):
            return None
        if isinstance(value, AtlasStruct | dict):
            self.normalize_attribute_values_for_update(value)
            return value
        return None  # pragma: no cover - a valid value is a struct or a map

    def validate_value(self, value: object, name: str, messages: list[str]) -> bool:
        """Validate each own attribute as ``<name>.<attribute>``; report missing mandatory ones (EVL-02)."""
        if value is None:
            return True
        attributes = _struct_attributes(value)
        if attributes is None:
            messages.append(f"{name}={java_string(value)}: invalid value for type {self.type_name}")
            return False
        valid = True
        for attribute_def in self.struct_def.attribute_defs:
            attribute = self.all_attributes.get(str(attribute_def.name))
            if attribute is None:
                continue  # pragma: no cover - every own attribute definition resolves to an attribute
            field = f"{name}.{attribute_def.name}"
            item = attributes.get(str(attribute_def.name))
            if item is not None:
                valid = attribute.attribute_type.validate_value(item, field, messages) and valid
            elif not attribute_def.is_optional and not _given_elsewhere(value, str(attribute_def.name)):
                valid = False
                messages.append(f"{field}: mandatory attribute value missing in type {self.type_name}")
        return valid

    def validate_value_for_update(self, value: object, name: str, messages: list[str]) -> bool:
        """Validate each present attribute with a type as ``<name>.<attribute>``, for update (EVL-03)."""
        if value is None:
            return True
        attributes = _struct_attributes(value)
        if attributes is None:
            messages.append(f"{name}={java_string(value)}: invalid value for type {self.type_name}")
            return False
        valid = True
        for attribute_name, item in attributes.items():
            attribute = self.all_attributes.get(attribute_name)
            if item is not None and attribute is not None:
                field = f"{name}.{attribute_name}"
                valid = attribute.attribute_type.validate_value_for_update(item, field, messages) and valid
        return valid

    def are_equal_values(self, left: object, right: object, guid_assignments: dict[str, str] | None) -> bool:
        """Both null, or structs of type names equal ignoring case with every attribute equal (EVL-06).

        Raises:
            TypeError: A string, on which Java's ``getStructFromValue`` fails with a ``ClassCastException``.
        """
        if left is None or right is None:
            return left is None and right is None
        first, second = _struct_of(left), _struct_of(right)
        if first is None or second is None:
            return False
        if (first.type_name or "").lower() != (second.type_name or "").lower() or (first.type_name is None) != (
            second.type_name is None
        ):
            return False
        return all(
            attribute.attribute_type.are_equal_values(
                first.get_attribute(str(attribute.name)), second.get_attribute(str(attribute.name)), guid_assignments
            )
            for attribute in self.all_attributes.values()
        )

    def normalize_attribute_values(self, value: StructValue) -> None:
        """Normalise the present own attributes and add the missing mandatory ones (EVL-04).

        A map is normalised at its top level, as Java's ``normalizeAttributeValues(Map)`` does.
        """
        values = value.attributes if isinstance(value, AtlasStruct) else value
        for attribute_def in self.struct_def.attribute_defs:
            attribute_name = str(attribute_def.name)
            if values is not None and attribute_name in values:
                normalized = self._normalized(values[attribute_name], attribute_def)
            elif not attribute_def.is_optional:
                normalized = self._default_of(attribute_def)
            else:
                continue
            if isinstance(value, AtlasStruct):
                value.set_attribute(attribute_name, normalized)
                values = value.attributes
            else:
                value[attribute_name] = normalized

    def normalize_attribute_values_for_update(self, value: StructValue) -> None:
        """Normalise the present own attributes for update; missing ones stay missing (EVL-03)."""
        values = value.attributes if isinstance(value, AtlasStruct) else value
        if values is None:
            return
        for attribute_def in self.struct_def.attribute_defs:
            attribute_name = str(attribute_def.name)
            if attribute_name in values:
                attribute = self.all_attributes.get(attribute_name)
                item = values[attribute_name]
                normalized = (
                    None
                    if attribute is None or item is None
                    else attribute.attribute_type.get_normalized_value_for_update(item)
                )
                values[attribute_name] = normalized

    def populate_default_values(self, struct: AtlasStruct) -> None:
        """Set every mandatory own attribute to its default, replacing its value (EVL-05)."""
        attributes = dict(struct.attributes or {})
        for attribute_def in self.struct_def.attribute_defs:
            if not attribute_def.is_optional:
                attributes[str(attribute_def.name)] = self._default_of(attribute_def)
        struct.attributes = attributes

    def _assignable(self, value: object, attribute_def: AtlasAttributeDef) -> bool:
        """``isAssignableValue``: a valid value, or no value for an optional attribute."""
        if value is None:
            return attribute_def.is_optional
        attribute = self.all_attributes.get(str(attribute_def.name))
        return attribute is None or attribute.attribute_type.is_valid_value(value)

    def _normalized(self, value: object, attribute_def: AtlasAttributeDef) -> Any:  # noqa: ANN401 - a Java value
        """``getNormalizedValue(value, attributeDef)``: a null mandatory attribute gets the type's default."""
        attribute = self.all_attributes.get(str(attribute_def.name))
        if attribute is None:
            return None  # pragma: no cover - every own attribute definition resolves to an attribute
        if value is None:
            return None if attribute_def.is_optional else attribute.attribute_type.create_default_value()
        return attribute.attribute_type.get_normalized_value(value)

    def _default_of(self, attribute_def: AtlasAttributeDef) -> Any:  # noqa: ANN401 - a Java value
        """``createDefaultValue(attributeDef)``: the attribute type's default of its ``defaultValue``."""
        attribute = self.all_attributes.get(str(attribute_def.name))
        return (
            None if attribute is None else attribute.attribute_type.create_default_value_of(attribute_def.default_value)
        )


def struct_attributes(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """``AtlasTypeUtil.toStructAttributes``: a map's ``attributes`` when it has a ``typeName``, else the map."""
    attributes = value.get("attributes")
    return attributes if "typeName" in value and isinstance(attributes, Mapping) else value


def relationship_attributes_of(value: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """``AtlasTypeUtil.toRelationshipAttributes``: a map's ``relationshipAttributes`` when it has a ``typeName``."""
    attributes = value.get("relationshipAttributes")
    return attributes if "typeName" in value and isinstance(attributes, Mapping) else None


def _struct_attributes(value: object) -> Mapping[str, Any] | None:
    """The attribute values of a struct or a map; None for any other value."""
    if isinstance(value, AtlasStruct):
        return value.attributes or {}
    if isinstance(value, Mapping):
        return struct_attributes(value)
    return None


def _given_elsewhere(value: object, attribute_name: str) -> bool:
    """Whether a mandatory attribute without a value is given another way, so no error (EVL-02).

    An entity may have it as a relationship attribute or be incomplete; a map may have it among its relationship
    attributes.
    """
    if isinstance(value, AtlasEntity):
        return value.get_relationship_attribute(attribute_name) is not None or bool(value.is_incomplete)
    if isinstance(value, AtlasStruct):
        return False
    relationship_attributes = relationship_attributes_of(cast("Mapping[str, Any]", value))
    return relationship_attributes is not None and attribute_name in relationship_attributes


def _struct_of(value: object) -> AtlasStruct | None:
    """``getStructFromValue``: a struct, or a map read by Java's map constructor.

    Raises:
        TypeError: A string that is JSON: Java casts the string itself to a map.
    """
    if isinstance(value, AtlasStruct):
        return value
    if isinstance(value, Mapping):
        return AtlasStruct.from_map(cast("Mapping[str, Any]", value))
    if isinstance(value, str):
        if parse_json(value) is None:
            return None
        raise TypeError(STRUCT_STRING_ERROR)
    return None
