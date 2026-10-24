"""Atlas types: the classes a type definition resolves to, one module per Java class (DD-025, DD-041).

This module re-exports them and makes the unresolved type of a definition (``type_of``).
"""

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    AtlasBaseTypeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasRelationshipDef,
    AtlasStructDef,
)

from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType
from aurelius_atlas_typesystem.attribute import AtlasAttribute, qualified_attribute_name
from aurelius_atlas_typesystem.builtin import BuiltInType, ObjectIdType
from aurelius_atlas_typesystem.business_metadata_type import BusinessAttribute, BusinessMetadataType
from aurelius_atlas_typesystem.classification_type import CLASSIFICATION_ROOT, ClassificationType
from aurelius_atlas_typesystem.edge_direction import EdgeDirection
from aurelius_atlas_typesystem.entity_type import ENTITY_ROOT, EntityType, entity_types_and_all_sub_types
from aurelius_atlas_typesystem.enum_type import EnumType
from aurelius_atlas_typesystem.map_type import MapType
from aurelius_atlas_typesystem.relationship_type import RelationshipType, validate_relationship_def
from aurelius_atlas_typesystem.struct_type import StructType, referenced_entity_type
from aurelius_atlas_typesystem.type_names import (
    CLASSIFICATION_ROOT_NAME,
    ENTITY_HEADER_ATTRIBUTES,
    ENTITY_ROOT_NAME,
    INTERNAL_TYPE_NAME,
    OPTION_APPEND_RELATIONSHIPS_ON_PARTIAL_UPDATE,
    OPTION_SCHEMA_ATTRIBUTES,
)


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


__all__ = [
    "CLASSIFICATION_ROOT",
    "CLASSIFICATION_ROOT_NAME",
    "ENTITY_HEADER_ATTRIBUTES",
    "ENTITY_ROOT",
    "ENTITY_ROOT_NAME",
    "INTERNAL_TYPE_NAME",
    "OPTION_APPEND_RELATIONSHIPS_ON_PARTIAL_UPDATE",
    "OPTION_SCHEMA_ATTRIBUTES",
    "ArrayType",
    "AtlasAttribute",
    "AtlasType",
    "BuiltInType",
    "BusinessAttribute",
    "BusinessMetadataType",
    "ClassificationType",
    "EdgeDirection",
    "EntityType",
    "EnumType",
    "MapType",
    "ObjectIdType",
    "RelationshipType",
    "StructType",
    "entity_types_and_all_sub_types",
    "qualified_attribute_name",
    "referenced_entity_type",
    "type_of",
    "validate_relationship_def",
]
