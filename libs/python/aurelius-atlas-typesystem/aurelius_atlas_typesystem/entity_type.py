"""``AtlasEntityType``: an entity, its hierarchy, relationship and business attributes (THY-09 to THY-12)."""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntity, AtlasStruct
from aurelius_atlas_model.typedef import (
    ATLAS_TYPE_DATE,
    ATLAS_TYPE_INT,
    ATLAS_TYPE_STRING,
    ATTRDEF_OPTION_APPEND_ON_PARTIAL_UPDATE,
    OPTION_DISPLAY_TEXT_ATTRIBUTE,
    AtlasAttributeDef,
    AtlasEntityDef,
    AtlasRelationshipAttributeDef,
    PropagateTags,
    TypeCategory,
)

from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.builtin import ObjectIdType

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.hierarchy_type import HierarchyType
from aurelius_atlas_typesystem.struct_type import StructValue, relationship_attributes_of
from aurelius_atlas_typesystem.type_names import (
    ENTITY_HEADER_ATTRIBUTES,
    ENTITY_ROOT_NAME,
    INTERNAL_TYPE_NAME,
    OPTION_APPEND_RELATIONSHIPS_ON_PARTIAL_UPDATE,
    OPTION_SCHEMA_ATTRIBUTES,
)
from aurelius_atlas_typesystem.values import java_class_name, parse_json, relationship_type_of

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.business_metadata_type import BusinessAttribute
    from aurelius_atlas_typesystem.relationship_type import RelationshipType


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


class EntityType(HierarchyType):
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

    def _same_kind(self, registry: TypeRegistry, name: str) -> HierarchyType | None:
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
        schema_attributes = _option_json(self.entity_def.get_option(OPTION_SCHEMA_ATTRIBUTES))
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
        append = _option_json(self.entity_def.get_option(OPTION_APPEND_RELATIONSHIPS_ON_PARTIAL_UPDATE))
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

    def _entity_supers(self) -> list[EntityType]:
        return [super_type for super_type in self.super_types if isinstance(super_type, EntityType)]

    def create_default_value(self) -> AtlasEntity:
        """An entity of this type, with a temporary GUID and its mandatory attributes' defaults (EVL-05)."""
        entity = AtlasEntity(type_name=self.entity_def.name)
        self.populate_default_values(entity)
        return entity

    def is_valid_value(self, value: object) -> bool:
        """Valid for each super type, for its own attributes and its relationship attributes (EVL-08)."""
        if value is None:
            return True
        if not all(super_type.is_valid_value(value) for super_type in self._entity_supers()):
            return False
        return super().is_valid_value(value) and self._relationship_values_valid(value)

    def is_valid_value_for_update(self, value: object) -> bool:
        """Valid for update for each super type and its own attributes; relationship attributes are not checked."""
        if value is None:
            return True
        if not all(super_type.is_valid_value_for_update(value) for super_type in self._entity_supers()):
            return False
        return super().is_valid_value_for_update(value)

    def validate_value(self, value: object, name: str, messages: list[str]) -> bool:
        """Validate for each super type, the own attributes, then the relationship attributes (EVL-08)."""
        if value is None:
            return True
        if not isinstance(value, AtlasEntity | Mapping):
            messages.append(f"{name}: invalid value type '{java_class_name(value)}")
            return False
        valid = True
        for super_type in self._entity_supers():
            valid = super_type.validate_value(value, name, messages) and valid
        own = super().validate_value(value, name, messages)
        return own and self._validate_relationship_values(value, name, messages) and valid

    def validate_value_for_update(self, value: object, name: str, messages: list[str]) -> bool:
        """Validate for update for each super type and the own attributes (EVL-03, EVL-08)."""
        if value is None:
            return True
        if not isinstance(value, AtlasEntity | Mapping):
            messages.append(f"{name}: invalid value type '{java_class_name(value)}")
            return False
        valid = True
        for super_type in self._entity_supers():
            valid = super_type.validate_value_for_update(value, name, messages) and valid
        return super().validate_value_for_update(value, name, messages) and valid

    def are_equal_values(self, left: object, right: object, guid_assignments: dict[str, str] | None) -> bool:
        """Equal for each super type and for this type (EVL-06)."""
        return all(
            super_type.are_equal_values(left, right, guid_assignments) for super_type in self._entity_supers()
        ) and super().are_equal_values(left, right, guid_assignments)

    def normalize_attribute_values(self, value: StructValue) -> None:
        """Normalise for each super type, the own attributes, then the relationship attributes (EVL-09)."""
        for super_type in self._entity_supers():
            super_type.normalize_attribute_values(value)
        super().normalize_attribute_values(value)
        self.normalize_relationship_attribute_values(value, for_update=False)

    def normalize_attribute_values_for_update(self, value: StructValue) -> None:
        """As ``normalize_attribute_values``, for update (EVL-03, EVL-09)."""
        for super_type in self._entity_supers():
            super_type.normalize_attribute_values_for_update(value)
        super().normalize_attribute_values_for_update(value)
        self.normalize_relationship_attribute_values(value, for_update=True)

    def populate_default_values(self, struct: AtlasStruct) -> None:
        """Defaults for each super type's mandatory attributes, then this type's (EVL-05)."""
        for super_type in self._entity_supers():
            super_type.populate_default_values(struct)
        super().populate_default_values(struct)

    def normalize_relationship_attribute_values(self, value: StructValue, *, for_update: bool) -> None:
        """Normalise the value of each relationship attribute that holds object ids or entities (EVL-09).

        An entity's ``relationshipAttributes``; a map at its top level, as Java's map overload does.
        """
        for attribute_name in self.relationship_attributes:
            if isinstance(value, AtlasEntity):
                if not value.has_relationship_attribute(attribute_name):
                    continue
                item = value.get_relationship_attribute(attribute_name)
            elif isinstance(value, AtlasStruct) or attribute_name not in value:
                continue
            else:
                item = value[attribute_name]
            attribute = self.relationship_attribute(attribute_name, relationship_type_of(item))
            if attribute is None or not _holds_references(attribute.attribute_type):  # pragma: no cover
                continue  # every relationship attribute holds references; Java checks anyway
            held = attribute.attribute_type
            normalized = held.get_normalized_value_for_update(item) if for_update else held.get_normalized_value(item)
            if isinstance(value, AtlasEntity):
                value.set_relationship_attribute(attribute_name, normalized)
            else:
                value[attribute_name] = normalized

    def _relationship_values(self, value: object) -> Mapping[str, Any] | None:
        """The relationship attribute values of an entity or a map (empty for a map without them, DV-13)."""
        if isinstance(value, AtlasEntity):
            return value.relationship_attributes or {}
        if isinstance(value, Mapping):
            return relationship_attributes_of(cast("Mapping[str, Any]", value)) or {}
        return None

    def _relationship_values_valid(self, value: object) -> bool:
        """``validateRelationshipAttributes(Object)``: each relationship attribute's value is assignable (EVL-08)."""
        if not self.relationship_attributes:
            return True
        values = self._relationship_values(value)
        if values is None:
            return False
        for attribute_name in self.relationship_attributes:
            item = values.get(attribute_name)
            attribute = self.relationship_attribute(attribute_name, relationship_type_of(item))
            if (
                item is not None
                and attribute is not None
                and not _holds_references(attribute.attribute_type)
                and not attribute.attribute_type.is_valid_value(item)
            ):  # pragma: no cover - every relationship attribute holds references; Java checks anyway
                return False
        return True

    def _validate_relationship_values(self, value: object, name: str, messages: list[str]) -> bool:
        """``validateRelationshipAttributes(Object, String, List)``: missing mandatory ones and references (EVL-08)."""
        if not self.relationship_attributes:
            return True
        values = self._relationship_values(value) or {}
        valid = True
        for attribute_name in self.relationship_attributes:
            item = values.get(attribute_name)
            attribute = self.relationship_attribute(attribute_name, relationship_type_of(item))
            if attribute is None:
                continue  # pragma: no cover - every name has an attribute
            field = f"{name}.{attribute_name}"
            if isinstance(value, AtlasEntity) and not attribute.attribute_def.is_optional and item is None:
                if value.is_incomplete:
                    continue
                valid = False
                messages.append(f"{field}: mandatory attribute value missing in type {self.type_name}")
            if item is not None and _holds_references(attribute.attribute_type):
                valid = attribute.attribute_type.validate_value(item, field, messages) and valid
        return valid


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


ENTITY_ROOT = EntityType(_root_entity_def())
"""``__ENTITY_ROOT``; not registered, resolved by every registry (THY-05)."""


def _option_json(value: str | None) -> object:
    """``AtlasType.fromJson`` of an option: None for a missing, blank or malformed value."""
    return None if value is None or not value.strip() else parse_json(value)


def _holds_references(type_: AtlasType) -> bool:
    """``isValidRelationshipType``: an object id or entity type, or an array of one."""
    if isinstance(type_, ArrayType):
        type_ = resolved(type_.element_type)
    return type_.category in (TypeCategory.OBJECT_ID_TYPE, TypeCategory.ENTITY)
