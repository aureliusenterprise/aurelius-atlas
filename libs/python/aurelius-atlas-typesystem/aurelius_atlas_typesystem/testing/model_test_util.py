"""A port of Atlas's ``ModelTestUtil``: types with an attribute of every built-in, enum, array and map type (EVL-11).

Test infrastructure: like every ``testing`` module, it is outside the traceability check (DD-010).

Atlas draws some attribute types at random; here they rotate through the same lists, so every run tests the same
definitions.
"""

from itertools import cycle

from aurelius_atlas_model.typedef import (
    ATLAS_BUILTIN_TYPES,
    ATLAS_PRIMITIVE_TYPES,
    AtlasAttributeDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasStructDef,
    AtlasTypesDef,
    array_type_name,
    map_type_name,
)

from aurelius_atlas_typesystem.registry import TypeRegistry

PREFIX_ATTRIBUTE_NAME = "attr-"
ENUM_DEF = "testEnumDef-0"
ENUM_DEF_WITH_NO_DEFAULT = "testEnumDef-1"
STRUCT_DEF = "testStructDef-0"
ENTITY_DEFS = ("testEntityDef-0", "testEntityDef-1", "testEntityDef-2")
"""``ENTITY_DEF``, ``ENTITY_DEF_WITH_SUPER_TYPE`` and ``ENTITY_DEF_WITH_SUPER_TYPES``."""
CLASSIFICATION_DEFS = ("testClassificationDef-0", "testClassificationDef-1", "testClassificationDef-2")


def enum_def(name: str, *, has_default: bool) -> AtlasEnumDef:
    """``newEnumDef``: elements ``ELEMENT-0`` to ``ELEMENT-2``; the default, when there is one, the second."""
    elements = [AtlasEnumElementDef(value=f"ELEMENT-{i}", description=f"element-{i}", ordinal=i) for i in range(3)]
    return AtlasEnumDef(name=name, element_defs=elements, default_value="ELEMENT-1" if has_default else None)


def attribute_def(type_name: str) -> AtlasAttributeDef:
    """``getAttributeDef``: a mandatory attribute named after its type."""
    return AtlasAttributeDef(name=PREFIX_ATTRIBUTE_NAME + type_name, type_name=type_name)


def attribute_defs_with_all_built_in_types() -> list[AtlasAttributeDef]:
    """``newAttributeDefsWithAllBuiltInTypes``, its random built-in and primitive types rotated."""
    built_in, primitive = cycle(ATLAS_BUILTIN_TYPES), cycle(ATLAS_PRIMITIVE_TYPES)
    enums = (ENUM_DEF, ENUM_DEF_WITH_NO_DEFAULT)
    names = [*ATLAS_BUILTIN_TYPES, *enums]
    names += [array_type_name(name) for name in (*ATLAS_BUILTIN_TYPES, *enums)]
    names += [map_type_name(key, next(built_in)) for key in (*ATLAS_PRIMITIVE_TYPES, *enums)]
    names += [map_type_name(next(primitive), enum) for enum in enums]
    names += [array_type_name(array_type_name(next(built_in))) for _ in ATLAS_BUILTIN_TYPES]
    names += [array_type_name(enum) for enum in enums]
    names += [array_type_name(map_type_name(key, next(built_in))) for key in (*ATLAS_PRIMITIVE_TYPES, *enums)]
    names += [array_type_name(map_type_name(next(primitive), enum)) for enum in enums]
    names += [map_type_name(key, array_type_name(next(built_in))) for key in ATLAS_PRIMITIVE_TYPES]
    names += [map_type_name(key, map_type_name(key, next(built_in))) for key in ATLAS_PRIMITIVE_TYPES]
    return [attribute_def(name) for name in names]


def _hierarchy[T: AtlasEntityDef | AtlasClassificationDef](kind: type[T], names: tuple[str, ...]) -> list[T]:
    """The type, one with it as super type, one with both; a sub type drops the attributes its supers have."""
    first = kind(name=names[0], attribute_defs=attribute_defs_with_all_built_in_types())
    second = kind(name=names[1], super_types=[names[0]], attribute_defs=[])
    third = kind(name=names[2], super_types=[names[0], names[1]], attribute_defs=[])
    return [first, second, third]


def model_registry(*extra_struct_attributes: AtlasAttributeDef) -> TypeRegistry:
    """A registry with ``ModelTestUtil``'s enums, struct, entity and classification hierarchies.

    ``extra_struct_attributes`` are added to the struct, as ``TestAtlasStructType`` adds its counted arrays.
    """
    registry = TypeRegistry()
    struct_attributes = [*attribute_defs_with_all_built_in_types(), *extra_struct_attributes]
    types_def = AtlasTypesDef(
        enum_defs=[enum_def(ENUM_DEF, has_default=True), enum_def(ENUM_DEF_WITH_NO_DEFAULT, has_default=False)],
        struct_defs=[AtlasStructDef(name=STRUCT_DEF, attribute_defs=struct_attributes)],
        classification_defs=_hierarchy(AtlasClassificationDef, CLASSIFICATION_DEFS),
        entity_defs=_hierarchy(AtlasEntityDef, ENTITY_DEFS),
    )
    with registry.update() as transient:
        transient.add_types(types_def)
    return registry
