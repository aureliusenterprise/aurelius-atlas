"""Atlas types: what a type definition becomes once its references are resolved (DD-025).

Ported from ``org.apache.atlas.type`` of Apache Atlas 2.4.0, the definition side only: the value side
(validation, normalisation, defaults) arrives with entities in 2.1. A type resolves against a registry in
three phases, as Java's ``resolveReferences``, ``resolveReferencesPhase2`` and ``resolveReferencesPhase3``.
"""

from typing import TYPE_CHECKING

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    ATLAS_TYPE_ASSET,
    ATLAS_TYPE_OBJECT_ID,
    CONSTRAINT_PARAM_ATTRIBUTE,
    CONSTRAINT_TYPE_INVERSE_REF,
    CONSTRAINT_TYPE_OWNED_REF,
    COUNT_NOT_SET,
    SERVICE_TYPE_ATLAS_CORE,
    AtlasAttributeDef,
    AtlasBaseTypeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipDef,
    AtlasStructDef,
    Cardinality,
    TypeCategory,
    array_type_name,
    map_type_name,
)

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.registry import TypeRegistry


class AtlasType:
    """A type: its name, category and service type (``AtlasType``)."""

    def __init__(self, type_name: str | None, category: TypeCategory, service_type: str | None) -> None:
        self.type_name = type_name
        self.category = category
        self.service_type = service_type

    def type_for_attribute(self) -> AtlasType:
        """The type an attribute of this type holds; an entity type is held as an ``objectid`` (TRG-11)."""
        return self

    def _resolve_references(self, registry: TypeRegistry) -> None:
        """Phase 1: resolve the names this type refers to."""

    def _resolve_references_phase2(self, registry: TypeRegistry) -> None:
        """Phase 2: link what needs every type's phase 1 done."""

    def _resolve_references_phase3(self, registry: TypeRegistry) -> None:
        """Phase 3: link what needs every type's phase 2 done."""


class BuiltInType(AtlasType):
    """A primitive type such as ``string`` or ``int`` (``AtlasBuiltInTypes``, TRG-01)."""

    def __init__(self, type_name: str) -> None:
        super().__init__(type_name, TypeCategory.PRIMITIVE, SERVICE_TYPE_ATLAS_CORE)


class ObjectIdType(AtlasType):
    """``objectid``: a reference to an entity of ``object_type`` (``AtlasObjectIdType``)."""

    def __init__(self, object_type: str | None = ATLAS_TYPE_ASSET) -> None:
        super().__init__(ATLAS_TYPE_OBJECT_ID, TypeCategory.OBJECT_ID_TYPE, SERVICE_TYPE_ATLAS_CORE)
        self.object_type = object_type


class ArrayType(AtlasType):
    """``array<T>`` with its cardinality and value counts (``AtlasArrayType``, TRG-02)."""

    def __init__(
        self,
        element_type_name: str,
        *,
        element_type: AtlasType | None = None,
        min_count: int = COUNT_NOT_SET,
        max_count: int = COUNT_NOT_SET,
        cardinality: Cardinality = Cardinality.LIST,
    ) -> None:
        super().__init__(array_type_name(element_type_name), TypeCategory.ARRAY, SERVICE_TYPE_ATLAS_CORE)
        self.element_type_name = element_type_name
        self.element_type = element_type
        self.min_count = min_count
        self.max_count = max_count
        self.cardinality = cardinality

    def type_for_attribute(self) -> AtlasType:
        """This array, or a new one over the element's attribute type when that differs (TRG-11)."""
        element = _resolved(self.element_type).type_for_attribute()
        if element is self.element_type:
            return self
        return ArrayType(
            _name(element),
            element_type=element,
            min_count=self.min_count,
            max_count=self.max_count,
            cardinality=self.cardinality,
        )

    def _resolve_references(self, registry: TypeRegistry) -> None:
        self.element_type = registry.get_type(self.element_type_name)


class MapType(AtlasType):
    """``map<K,V>`` (``AtlasMapType``, TRG-02)."""

    def __init__(
        self,
        key_type_name: str,
        value_type_name: str,
        *,
        key_type: AtlasType | None = None,
        value_type: AtlasType | None = None,
    ) -> None:
        super().__init__(map_type_name(key_type_name, value_type_name), TypeCategory.MAP, SERVICE_TYPE_ATLAS_CORE)
        self.key_type_name = key_type_name
        self.value_type_name = value_type_name
        self.key_type = key_type
        self.value_type = value_type

    def type_for_attribute(self) -> AtlasType:
        """This map, or a new one over the key's and value's attribute types when they differ (TRG-11)."""
        key = _resolved(self.key_type).type_for_attribute()
        value = _resolved(self.value_type).type_for_attribute()
        if key is self.key_type and value is self.value_type:
            return self
        return MapType(_name(key), _name(value), key_type=key, value_type=value)

    def _resolve_references(self, registry: TypeRegistry) -> None:
        self.key_type = registry.get_type(self.key_type_name)
        self.value_type = registry.get_type(self.value_type_name)


def _resolved(type_: AtlasType | None) -> AtlasType:
    if type_ is None:  # pragma: no cover - a type is resolved before its attribute type is asked for
        raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, "unresolved type")
    return type_


def _name(type_: AtlasType) -> str:
    return str(type_.type_name)


class EnumType(AtlasType):
    """An enum type: its elements by value and ordinal, and its default (``AtlasEnumType``, TRG-14)."""

    def __init__(self, enum_def: AtlasEnumDef) -> None:
        super().__init__(enum_def.name, enum_def.category, enum_def.service_type)
        self.enum_def = enum_def
        self._elements = {str(element.value).lower(): element for element in enum_def.element_defs}
        first = enum_def.element_defs[0].value if enum_def.element_defs else None
        self.default_value = enum_def.default_value if enum_def.default_value is not None else first

    def element(self, value: str | None) -> AtlasEnumElementDef | None:
        """The element with ``value``, compared without case, or None (TRG-14)."""
        return None if value is None else self._elements.get(value.lower())

    def element_by_ordinal(self, ordinal: int | None) -> AtlasEnumElementDef | None:
        """The element with ``ordinal``, or None (TRG-14)."""
        if ordinal is None:
            return None
        return next((element for element in self._elements.values() if element.ordinal == ordinal), None)


class AtlasAttribute:
    """A resolved attribute of a struct-like type (``AtlasStructType.AtlasAttribute``)."""

    def __init__(self, defined_in: StructType, attribute_def: AtlasAttributeDef, attribute_type: AtlasType) -> None:
        self.defined_in = defined_in
        self.attribute_def = attribute_def
        self.attribute_type = attribute_type.type_for_attribute()
        self.name = attribute_def.name
        self.qualified_name = qualified_attribute_name(defined_in.struct_def, str(attribute_def.name))
        constraints = attribute_def.constraints or []
        self.is_owned_ref = any(constraint.is_constraint_type(CONSTRAINT_TYPE_OWNED_REF) for constraint in constraints)
        self.inverse_ref_attribute_name = next(
            (
                str(param)
                for constraint in constraints
                if constraint.is_constraint_type(CONSTRAINT_TYPE_INVERSE_REF)
                and (param := constraint.get_param(CONSTRAINT_PARAM_ATTRIBUTE)) is not None
            ),
            None,
        )
        self.inverse_ref_attribute: AtlasAttribute | None = None
        self.is_object_ref = _holds_object_ids(self.attribute_type)


def qualified_attribute_name(struct_def: AtlasStructDef, attribute_name: str) -> str:
    """``Type.attribute``, or the name itself when it already contains a dot (TRG-11)."""
    return attribute_name if "." in attribute_name else f"{struct_def.name}.{attribute_name}"


def _holds_object_ids(type_: AtlasType) -> bool:
    if isinstance(type_, ArrayType):
        type_ = _resolved(type_.element_type)
    elif isinstance(type_, MapType):
        type_ = _resolved(type_.value_type)
    return type_.category is TypeCategory.OBJECT_ID_TYPE


def _contained(type_: AtlasType) -> AtlasType:
    """The element of an array or the value of a map; the type itself otherwise."""
    if isinstance(type_, ArrayType):
        return _resolved(type_.element_type)
    if isinstance(type_, MapType):
        return _resolved(type_.value_type)
    return type_


def referenced_entity_type(type_: AtlasType) -> EntityType | None:
    """The entity type a type, an array of it or a map to it refers to, or None (TRG-12)."""
    if isinstance(type_, ArrayType):
        type_ = _resolved(type_.element_type)
    if isinstance(type_, MapType):
        type_ = _resolved(type_.value_type)
    return type_ if isinstance(type_, EntityType) else None


class StructType(AtlasType):
    """A struct type, and the base of every type with attributes (``AtlasStructType``, TRG-10 to TRG-13)."""

    def __init__(self, struct_def: AtlasStructDef) -> None:
        super().__init__(struct_def.name, struct_def.category, struct_def.service_type)
        self.struct_def = struct_def
        self.all_attributes: dict[str, AtlasAttribute] = {}
        self.unique_attributes: dict[str, AtlasAttribute] = {}

    def attribute(self, name: str | None) -> AtlasAttribute | None:
        """The attribute named exactly ``name``, or None (TRG-13)."""
        return None if name is None else self.all_attributes.get(name)

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
            if isinstance(_contained(attribute_type), ClassificationType | BusinessMetadataType):
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
                _java_map(params),
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


def _java_map(params: dict[str, object] | None) -> str:
    """``String.valueOf(Map)``: ``{k=v, k2=v2}``, or ``null``."""
    if params is None:
        return "null"
    return "{" + ", ".join(f"{key}={value}" for key, value in params.items()) + "}"


class ClassificationType(StructType):
    """A classification type; its hierarchy and entity types are resolved in 1.3 (TRG-16)."""

    def __init__(self, classification_def: AtlasClassificationDef) -> None:
        super().__init__(classification_def)
        self.classification_def = classification_def


class EntityType(StructType):
    """An entity type; its hierarchy and relationship attributes are resolved in 1.3 (TRG-16)."""

    def __init__(self, entity_def: AtlasEntityDef) -> None:
        super().__init__(entity_def)
        self.entity_def = entity_def

    def type_for_attribute(self) -> AtlasType:
        """An attribute holds an entity as ``objectid`` of this entity type (TRG-11)."""
        return ObjectIdType(self.type_name)


class RelationshipType(StructType):
    """A relationship type; its ends are resolved in 1.3 (TRG-16)."""

    def __init__(self, relationship_def: AtlasRelationshipDef) -> None:
        super().__init__(relationship_def)
        self.relationship_def = relationship_def


class BusinessMetadataType(StructType):
    """A business metadata type; the entity types it applies to are resolved in 1.3 (TRG-16)."""

    def __init__(self, business_metadata_def: AtlasBusinessMetadataDef) -> None:
        super().__init__(business_metadata_def)
        self.business_metadata_def = business_metadata_def


def type_of(typedef: AtlasBaseTypeDef) -> StructType | EnumType:
    """The unresolved type of a definition, by its exact class (``addTypeWithNoRefResolve``)."""
    match typedef:
        case AtlasEnumDef():
            return EnumType(typedef)
        case AtlasClassificationDef():
            return ClassificationType(typedef)
        case AtlasEntityDef():
            return EntityType(typedef)
        case AtlasRelationshipDef():
            return RelationshipType(typedef)
        case AtlasBusinessMetadataDef():
            return BusinessMetadataType(typedef)
        case AtlasStructDef():
            return StructType(typedef)
        case _:  # pragma: no cover - every concrete typedef class is matched above
            raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, f"unknown type definition {type(typedef).__name__}")
