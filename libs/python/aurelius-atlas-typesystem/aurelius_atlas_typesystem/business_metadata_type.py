"""``AtlasBusinessMetadataType``: business metadata and the entity types it applies to (THY-12)."""

from typing import TYPE_CHECKING

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    ATLAS_TYPE_STRING,
    ATTR_MAX_STRING_LENGTH,
    ATTR_OPTION_APPLICABLE_ENTITY_TYPES,
    ATTR_VALID_PATTERN,
    AtlasBusinessMetadataDef,
)

from aurelius_atlas_typesystem.builtin import BuiltInType

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.struct_type import StructType, contained_type

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.entity_type import EntityType


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
            held = contained_type(attribute.attribute_type)
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
