"""Atlas types: what a type definition becomes once its references are resolved (DD-025).

Ported from ``org.apache.atlas.type`` of Apache Atlas 2.4.0, the definition side only: the value side
(validation, normalisation, defaults) arrives with entities in 2.1. A type resolves against a registry in
three phases, as Java's ``resolveReferences``, ``resolveReferencesPhase2`` and ``resolveReferencesPhase3``.
"""

import json
from enum import StrEnum
from typing import TYPE_CHECKING

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.typedef import (
    ATLAS_TYPE_ASSET,
    ATLAS_TYPE_DATE,
    ATLAS_TYPE_INT,
    ATLAS_TYPE_OBJECT_ID,
    ATLAS_TYPE_STRING,
    ATTR_MAX_STRING_LENGTH,
    ATTR_OPTION_APPLICABLE_ENTITY_TYPES,
    ATTR_VALID_PATTERN,
    ATTRDEF_OPTION_APPEND_ON_PARTIAL_UPDATE,
    CONSTRAINT_PARAM_ATTRIBUTE,
    CONSTRAINT_TYPE_INVERSE_REF,
    CONSTRAINT_TYPE_OWNED_REF,
    COUNT_NOT_SET,
    OPTION_DISPLAY_TEXT_ATTRIBUTE,
    SERVICE_TYPE_ATLAS_CORE,
    AtlasAttributeDef,
    AtlasBaseTypeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasConstraintDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipAttributeDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
    Cardinality,
    PropagateTags,
    RelationshipCategory,
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


class EdgeDirection(StrEnum):
    """Which way a relationship attribute's edge points (``AtlasRelationshipEdgeDirection``, THY-10)."""

    IN = "IN"
    OUT = "OUT"
    BOTH = "BOTH"


class AtlasAttribute:
    """A resolved attribute of a struct-like type (``AtlasStructType.AtlasAttribute``)."""

    def __init__(
        self,
        defined_in: StructType,
        attribute_def: AtlasAttributeDef,
        attribute_type: AtlasType,
        relationship_name: str | None = None,
        relationship_label: str | None = None,
    ) -> None:
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
        self.relationship_name = relationship_name
        self.relationship_edge_label = relationship_label or f"__{self.qualified_name}"
        self.relationship_edge_direction = EdgeDirection.OUT
        self.is_legacy_attribute = False

    def option_set(self, name: str) -> list[str] | None:
        """Option ``name`` read as a JSON array of names, or None when blank or not an array (``getOptionSet``)."""
        value = _parsed_json(self.attribute_def.get_option(name))
        return list(dict.fromkeys(str(item) for item in value)) if isinstance(value, list) else None

    def option_int(self, name: str) -> int | None:
        """Option ``name`` as an integer, or None when blank (``getOptionInt``)."""
        value = self.attribute_def.get_option(name)
        return None if value is None or not value.strip() else int(value)

    def option_string(self, name: str) -> str | None:
        """Option ``name``, or None when blank (``getOptionString``)."""
        value = self.attribute_def.get_option(name)
        return None if value is None or not value.strip() else value


def _parsed_json(value: str | None) -> object:
    """``AtlasType.fromJson``: None for a blank or malformed value."""
    if value is None or not value.strip():
        return None
    try:
        return json.loads(value)
    except ValueError:
        return None


def qualified_attribute_name(struct_def: AtlasStructDef, attribute_name: str) -> str:
    """``Type.attribute``, or the name itself when it contains a dot or belongs to a root type (TRG-11, THY-05)."""
    if struct_def.name in {ENTITY_ROOT_NAME, CLASSIFICATION_ROOT_NAME} or "." in attribute_name:
        return attribute_name
    return f"{struct_def.name}.{attribute_name}"


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


ENTITY_ROOT_NAME = "__ENTITY_ROOT"
CLASSIFICATION_ROOT_NAME = "__CLASSIFICATION_ROOT"
INTERNAL_TYPE_NAME = "__internal"
ENTITY_HEADER_ATTRIBUTES = ("name", "description", "owner", "createTime")
OPTION_SCHEMA_ATTRIBUTES = "schemaAttributes"
OPTION_APPEND_RELATIONSHIPS_ON_PARTIAL_UPDATE = "appendRelationshipsOnPartialUpdate"


class _HierarchyType(StructType):
    """What entity and classification types share: super and sub types, inherited attributes (THY-01 to THY-04)."""

    def __init__(self, struct_def: AtlasStructDef) -> None:
        super().__init__(struct_def)
        self.super_types: list[_HierarchyType] = []
        self.all_super_types: list[str] = []
        self.sub_types: list[str] = []
        self.all_sub_types: list[str] = []
        self.type_and_all_sub_types: list[str] = []
        self.type_and_all_super_types: list[str] = []

    def _declared_super_types(self) -> list[str]:
        raise NotImplementedError  # pragma: no cover - every kind overrides it

    def _same_kind(self, registry: TypeRegistry, name: str) -> _HierarchyType | None:
        raise NotImplementedError  # pragma: no cover - every kind overrides it

    def is_super_type_of(self, other: StructType | str | None) -> bool:
        """Whether ``other`` is among this type's sub types, at any depth (THY-04)."""
        return _name_of(other) in self.all_sub_types

    def is_sub_type_of(self, other: StructType | str | None) -> bool:
        """Whether ``other`` is among this type's super types, at any depth (THY-04)."""
        return _name_of(other) in self.all_super_types

    def _resolve_references(self, registry: TypeRegistry) -> None:
        super()._resolve_references(registry)
        all_super_types: dict[str, None] = {}
        all_attributes: dict[str, AtlasAttribute] = {}
        self._collect_hierarchy(registry, all_super_types, all_attributes, {}, [])
        supers: list[_HierarchyType] = []
        for name in self._declared_super_types():
            super_type = registry.get_type(name)
            if not isinstance(super_type, type(self)):
                raise AtlasError(AtlasErrorCode.INCOMPATIBLE_SUPERTYPE, name, self.type_name)
            supers.append(super_type)
        self.super_types = supers
        self.all_super_types = list(all_super_types)
        self.all_attributes = all_attributes
        self.unique_attributes = {
            name: attribute for name, attribute in all_attributes.items() if attribute.attribute_def.is_unique
        }
        self.sub_types = []
        self.all_sub_types = []
        self.type_and_all_sub_types = [str(self.type_name)]
        self.type_and_all_super_types = [*self.all_super_types, str(self.type_name)]

    def _collect_hierarchy(
        self,
        registry: TypeRegistry,
        all_super_types: dict[str, None],
        all_attributes: dict[str, AtlasAttribute],
        owners: dict[str, str],
        visited: list[str],
    ) -> None:
        """``collectTypeHierarchyInfo``: super types first, depth first, then this type's own attributes."""
        name = str(self.struct_def.name)
        if name in visited:
            raise AtlasError(AtlasErrorCode.CIRCULAR_REFERENCE, name, visited)
        declared = self._declared_super_types()
        if declared:
            visited.append(name)
            for super_name in declared:
                super_type = self._same_kind(registry, super_name)
                if super_type is not None:
                    super_type._collect_hierarchy(registry, all_super_types, all_attributes, owners, visited)  # noqa: SLF001
            visited.remove(name)
            all_super_types.update(dict.fromkeys(declared))
        for attribute_def in self.struct_def.attribute_defs:
            attribute_name = str(attribute_def.name)
            attribute_type = registry.get_type(attribute_def.type_name)
            if owners.get(attribute_name, name) != name:
                raise AtlasError(
                    AtlasErrorCode.ATTRIBUTE_NAME_ALREADY_EXISTS_IN_ANOTHER_PARENT_TYPE,
                    name,
                    attribute_name,
                    owners[attribute_name],
                )
            all_attributes[attribute_name] = AtlasAttribute(self, attribute_def, attribute_type)
            owners[attribute_name] = name

    def _resolve_references_phase2(self, registry: TypeRegistry) -> None:
        super()._resolve_references_phase2(registry)
        for super_type in self.super_types:
            super_type.sub_types = _with(super_type.sub_types, str(self.type_name))
        for super_name in self.all_super_types:
            super_type = self._same_kind(registry, super_name)
            if super_type is not None:
                super_type.all_sub_types = _with(super_type.all_sub_types, str(self.type_name))
                super_type.type_and_all_sub_types = _with(super_type.type_and_all_sub_types, str(self.type_name))


def _name_of(other: StructType | str | None) -> str | None:
    return other.type_name if isinstance(other, StructType) else other


def _with(names: list[str], name: str) -> list[str]:
    return names if name in names else [*names, name]


class ClassificationType(_HierarchyType):
    """A classification type: its hierarchy and the entity types it applies to (THY-01 to THY-05, THY-07)."""

    def __init__(self, classification_def: AtlasClassificationDef) -> None:
        super().__init__(classification_def)
        self.classification_def = classification_def
        self.entity_types: list[str] = []

    def _declared_super_types(self) -> list[str]:
        return self.classification_def.super_types

    def _same_kind(self, registry: TypeRegistry, name: str) -> _HierarchyType | None:
        return registry.classification_type(name)

    def _system_attribute(self, name: str) -> AtlasAttribute | None:
        return CLASSIFICATION_ROOT.all_attributes.get(name)

    def can_apply_to_entity_type(self, entity_type: EntityType) -> bool:
        """Whether the classification may be applied to ``entity_type`` (THY-07)."""
        return not self.entity_types or entity_type.type_name in self.entity_types

    def _resolve_references(self, registry: TypeRegistry) -> None:
        super()._resolve_references(registry)
        self.entity_types = []

    def _resolve_references_phase3(self, registry: TypeRegistry) -> None:
        super()._resolve_references_phase3(registry)
        allowed_by_supers: list[str] | None = None
        own = self.classification_def.entity_types
        for super_name in self.all_super_types:
            super_def = registry.typedef_by_name(super_name)
            names = super_def.entity_types if isinstance(super_def, AtlasClassificationDef) else []
            if not names:
                continue
            expanded = entity_types_and_all_sub_types(names, registry)
            allowed_by_supers = (
                expanded if allowed_by_supers is None else [name for name in allowed_by_supers if name in expanded]
            )
            if not allowed_by_supers:
                break
        if allowed_by_supers is None:
            self.entity_types = entity_types_and_all_sub_types(own, registry)
        elif not allowed_by_supers:
            raise AtlasError(AtlasErrorCode.CLASSIFICATIONDEF_PARENTS_ENTITYTYPES_DISJOINT, self.type_name)
        elif not own:
            self.entity_types = allowed_by_supers
        else:
            self.entity_types = entity_types_and_all_sub_types(own, registry)
            if not set(self.entity_types) <= set(allowed_by_supers):
                raise AtlasError(AtlasErrorCode.CLASSIFICATIONDEF_ENTITYTYPES_NOT_PARENTS_SUBSET, self.type_name, own)
        self.classification_def.sub_types = list(self.sub_types)


def entity_types_and_all_sub_types(names: list[str], registry: TypeRegistry) -> list[str]:
    """The entity types named and all their sub types (``getEntityTypesAndAllSubTypes``, THY-07).

    Raises:
        AtlasError: ``TYPE_NAME_NOT_FOUND`` for a name that is not an entity type.
    """
    found: dict[str, None] = {}
    for name in names:
        entity_type = registry.entity_type(name)
        if entity_type is None:
            raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, name)
        found.update(dict.fromkeys(entity_type.type_and_all_sub_types))
    return list(found)


class EntityType(_HierarchyType):
    """An entity type: its hierarchy, relationship and business attributes (THY-01 to THY-06, THY-10 to THY-12)."""

    def __init__(self, entity_def: AtlasEntityDef) -> None:
        super().__init__(entity_def)
        self.entity_def = entity_def
        self.relationship_attributes: dict[str, dict[str, AtlasAttribute]] = {}
        self.business_attributes: dict[str, dict[str, BusinessAttribute]] = {}
        self.owned_ref_attributes: list[AtlasAttribute] = []
        self.header_attributes: dict[str, AtlasAttribute] = {}
        self.min_info_attributes: dict[str, AtlasAttribute] = {}
        self.tag_propagation_edges: list[str | None] = []
        self.display_text_attribute = entity_def.get_option(OPTION_DISPLAY_TEXT_ATTRIBUTE)
        self.is_internal = False

    def _declared_super_types(self) -> list[str]:
        return self.entity_def.super_types

    def _same_kind(self, registry: TypeRegistry, name: str) -> _HierarchyType | None:
        return registry.entity_type(name)

    def type_for_attribute(self) -> AtlasType:
        """An attribute holds an entity as ``objectid`` of this entity type (TRG-11)."""
        return ObjectIdType(self.type_name)

    def _system_attribute(self, name: str) -> AtlasAttribute | None:
        return ENTITY_ROOT.all_attributes.get(name)

    def _business_attribute(self, name: str) -> AtlasAttribute | None:
        metadata, separator, attribute = name.partition(".")
        return self.business_attribute(metadata, attribute) if separator else None

    def business_attribute(self, metadata_name: str, attribute_name: str) -> BusinessAttribute | None:
        """The attribute ``attribute_name`` of business metadata ``metadata_name`` on this type (THY-12)."""
        return self.business_attributes.get(metadata_name, {}).get(attribute_name)

    def relationship_attribute(self, name: str, relationship_type: str | None = None) -> AtlasAttribute | None:
        """The relationship attribute ``name`` of ``relationship_type``, else of the first relationship (THY-10)."""
        attributes = self.relationship_attributes.get(name)
        if not attributes:
            return None
        if relationship_type is not None and relationship_type in attributes:
            return attributes[relationship_type]
        return next(iter(attributes.values()))

    def _resolve_references(self, registry: TypeRegistry) -> None:
        super()._resolve_references(registry)
        self.relationship_attributes = {}
        self.business_attributes = {}
        self.tag_propagation_edges = []
        self.is_internal = False
        self.header_attributes = dict(self.unique_attributes)
        for name in ENTITY_HEADER_ATTRIBUTES:
            if (attribute := self.attribute(name)) is not None:
                self.header_attributes[name] = attribute
        self.min_info_attributes = dict(self.header_attributes)
        schema_attributes = _parsed_json(self.entity_def.get_option(OPTION_SCHEMA_ATTRIBUTES))
        for name in schema_attributes if isinstance(schema_attributes, list) else []:
            if (attribute := self.attribute(str(name))) is not None:
                self.min_info_attributes[str(name)] = attribute
        self.display_text_attribute = self._valid_attribute_name(
            self.entity_def.get_option(OPTION_DISPLAY_TEXT_ATTRIBUTE)
        )
        for super_type in self.super_types if self.display_text_attribute is None else []:
            option = super_type.struct_def.get_option(OPTION_DISPLAY_TEXT_ATTRIBUTE)
            if option is not None and (valid := self._valid_attribute_name(option)) is not None:
                self.display_text_attribute = valid
                break

    def _valid_attribute_name(self, name: str | None) -> str | None:
        return name if name is not None and self.attribute(name) is not None else None

    def _add_relationship_attribute(
        self, name: str, attribute: AtlasAttribute, relationship_type: RelationshipType
    ) -> None:
        """``addRelationshipAttribute``: register it and the tag-propagation edge it may add (THY-10, THY-11)."""
        self.relationship_attributes.setdefault(name, {})[str(relationship_type.type_name)] = attribute
        propagation = relationship_type.relationship_def.propagate_tags or PropagateTags.NONE
        end1, end2 = relationship_type.end1_type, relationship_type.end2_type
        propagates = (
            propagation is PropagateTags.BOTH
            or (propagation is PropagateTags.ONE_TO_TWO and end1 is not None and end1.type_name == self.type_name)
            or (propagation is PropagateTags.TWO_TO_ONE and end2 is not None and end2.type_name == self.type_name)
        )
        if propagates and relationship_type.relationship_label not in self.tag_propagation_edges:
            self.tag_propagation_edges.append(relationship_type.relationship_label)

    def _add_business_attribute(self, attribute: BusinessAttribute) -> None:
        self.business_attributes.setdefault(str(attribute.defined_in.type_name), {})[str(attribute.name)] = attribute

    def _resolve_references_phase3(self, registry: TypeRegistry) -> None:
        super()._resolve_references_phase3(registry)
        for super_name in self.all_super_types:
            if super_name == INTERNAL_TYPE_NAME:
                self.is_internal = True
            super_type = registry.entity_type(super_name)
            if super_type is not None:
                self._inherit_from(super_type)
        self.owned_ref_attributes = [attribute for attribute in self.all_attributes.values() if attribute.is_owned_ref]
        self.owned_ref_attributes += [
            attribute
            for by_relationship in self.relationship_attributes.values()
            for attribute in by_relationship.values()
            if attribute.is_owned_ref
        ]
        self._write_back()
        if self.display_text_attribute is None:
            for super_name in self.all_super_types:
                super_type = registry.entity_type(super_name)
                if super_type is not None and super_type.display_text_attribute is not None:
                    self.display_text_attribute = super_type.display_text_attribute
                    break

    def _inherit_from(self, super_type: EntityType) -> None:
        """Take a super type's relationship, business attributes and tag-propagation edges (THY-11, THY-12)."""
        for name, by_relationship in super_type.relationship_attributes.items():
            mine = self.relationship_attributes.setdefault(name, {})
            for relationship, attribute in by_relationship.items():
                mine.setdefault(relationship, attribute)
        for metadata, attributes in super_type.business_attributes.items():
            self.business_attributes.setdefault(metadata, {}).update(attributes)
        for edge in super_type.tag_propagation_edges:
            if edge not in self.tag_propagation_edges:
                self.tag_propagation_edges.append(edge)

    def _write_back(self) -> None:
        """Write the derived fields into the definition, as Java's phase 3 does (THY-04, THY-11, THY-12)."""
        append = _parsed_json(self.entity_def.get_option(OPTION_APPEND_RELATIONSHIPS_ON_PARTIAL_UPDATE))
        appended = {str(name) for name in append} if isinstance(append, list) else set()
        relationship_defs: list[AtlasRelationshipAttributeDef] = []
        for by_relationship in self.relationship_attributes.values():
            for relationship, attribute in by_relationship.items():
                relationship_def = AtlasRelationshipAttributeDef.model_validate(
                    {
                        **attribute.attribute_def.model_dump(),
                        "relationship_type_name": relationship,
                        "is_legacy_attribute": attribute.is_legacy_attribute,
                    }
                )
                if relationship_def.name in appended:
                    relationship_def.set_option(ATTRDEF_OPTION_APPEND_ON_PARTIAL_UPDATE, "true")
                relationship_defs.append(relationship_def)
        self.entity_def.sub_types = list(self.sub_types)
        self.entity_def.relationship_attribute_defs = relationship_defs
        self.entity_def.business_attribute_defs = {
            metadata: [attribute.attribute_def for attribute in attributes.values()]
            for metadata, attributes in self.business_attributes.items()
        }


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


class BusinessAttribute(AtlasAttribute):
    """A business metadata attribute and the entity types it applies to (``AtlasBusinessAttribute``, THY-12)."""

    def __init__(
        self,
        attribute: AtlasAttribute,
        applicable_entity_types: list[EntityType],
        max_string_length: int = 0,
        valid_pattern: str | None = None,
    ) -> None:
        self.__dict__.update(attribute.__dict__)
        self.applicable_entity_types = applicable_entity_types
        self.max_string_length = max_string_length
        self.valid_pattern = valid_pattern


class BusinessMetadataType(StructType):
    """A business metadata type: its attributes and the entity types they apply to (THY-12)."""

    def __init__(self, business_metadata_def: AtlasBusinessMetadataDef) -> None:
        super().__init__(business_metadata_def)
        self.business_metadata_def = business_metadata_def

    def _resolve_references(self, registry: TypeRegistry) -> None:
        super()._resolve_references(registry)
        business_attributes: dict[str, AtlasAttribute] = {}
        for name, attribute in self.all_attributes.items():
            held = _contained(attribute.attribute_type)
            if isinstance(held, StructType):
                raise AtlasError(AtlasErrorCode.BUSINESS_METADATA_DEF_ATTRIBUTE_TYPE_INVALID, self.type_name, name)
            applicable: list[EntityType] = []
            for entity_name in attribute.option_set(ATTR_OPTION_APPLICABLE_ENTITY_TYPES) or []:
                entity_type = registry.entity_type(entity_name)
                if entity_type is None:
                    raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, entity_name)
                applicable.append(entity_type)
            if isinstance(held, BuiltInType) and held.type_name == ATLAS_TYPE_STRING:
                max_length = attribute.option_int(ATTR_MAX_STRING_LENGTH)
                if max_length is None:
                    raise AtlasError(
                        AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE,
                        attribute.attribute_def.name,
                        f"options.{ATTR_MAX_STRING_LENGTH}",
                    )
                business_attributes[name] = BusinessAttribute(
                    attribute, applicable, max_length, attribute.option_string(ATTR_VALID_PATTERN)
                )
            else:
                business_attributes[name] = BusinessAttribute(attribute, applicable)
        self.all_attributes = business_attributes

    def _resolve_references_phase2(self, registry: TypeRegistry) -> None:
        super()._resolve_references_phase2(registry)
        for attribute in self.all_attributes.values():
            if isinstance(attribute, BusinessAttribute):
                for entity_type in attribute.applicable_entity_types:
                    entity_type._add_business_attribute(attribute)  # noqa: SLF001


def _root_entity_def() -> AtlasEntityDef:
    """``AtlasRootEntityType.getRootEntityDef``: the system attributes of every entity (THY-05)."""
    unique = {"__guid", "__historicalGuids"}
    attributes = [
        ("__timestamp", ATLAS_TYPE_DATE),
        ("__modificationTimestamp", ATLAS_TYPE_DATE),
        ("__modifiedBy", ATLAS_TYPE_STRING),
        ("__createdBy", ATLAS_TYPE_STRING),
        ("__state", ATLAS_TYPE_STRING),
        ("__guid", ATLAS_TYPE_STRING),
        ("__historicalGuids", ATLAS_TYPE_STRING),
        ("__typeName", ATLAS_TYPE_STRING),
        ("__classificationsText", ATLAS_TYPE_STRING),
        ("__classificationNames", ATLAS_TYPE_STRING),
        ("__propagatedClassificationNames", ATLAS_TYPE_STRING),
        ("__isIncomplete", ATLAS_TYPE_INT),
        ("__labels", ATLAS_TYPE_STRING),
        ("__customAttributes", ATLAS_TYPE_STRING),
        ("__pendingTasks", ATLAS_TYPE_STRING),
    ]
    return AtlasEntityDef(
        name=ENTITY_ROOT_NAME,
        description="Root entity for system attributes",
        type_version="1.0",
        attribute_defs=[
            AtlasAttributeDef(name=name, type_name=type_name, is_unique=name in unique, is_indexable=True)
            for name, type_name in attributes
        ],
    )


def _root_classification_def() -> AtlasClassificationDef:
    """``initRootClassificationType``: the system attributes of every classification (THY-05)."""
    attributes = [
        ("__typeName", ATLAS_TYPE_STRING),
        ("__timestamp", ATLAS_TYPE_DATE),
        ("__modificationTimestamp", ATLAS_TYPE_DATE),
        ("__modifiedBy", ATLAS_TYPE_STRING),
        ("__createdBy", ATLAS_TYPE_STRING),
        ("__entityStatus", ATLAS_TYPE_STRING),
    ]
    return AtlasClassificationDef(
        name=CLASSIFICATION_ROOT_NAME,
        description="Root classification for system attributes",
        type_version="1.0",
        attribute_defs=[
            AtlasAttributeDef(name=name, type_name=type_name, is_indexable=True) for name, type_name in attributes
        ],
    )


ENTITY_ROOT = EntityType(_root_entity_def())
"""``__ENTITY_ROOT``; not registered, resolved by every registry (THY-05)."""

CLASSIFICATION_ROOT = ClassificationType(_root_classification_def())
"""``__CLASSIFICATION_ROOT``; not registered, resolved by every registry (THY-05)."""


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
