"""Resolving the types of definitions (TRG-10 to TRG-14, TRG-16).

Read from ``AtlasStructType``, ``AtlasArrayType``, ``AtlasMapType``, ``AtlasEnumType`` and ``AtlasEntityType`` of
Apache Atlas 2.4.0 and the test ``TestAtlasStructType.testInvalidStructDef_MultiValuedAttributeNotArray``.
"""

from typing import Any

import pytest
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasConstraintDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipDef,
    AtlasStructDef,
    Cardinality,
    TypeCategory,
)
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.types import (
    ArrayType,
    AtlasType,
    BuiltInType,
    EntityType,
    EnumType,
    MapType,
    ObjectIdType,
    StructType,
    qualified_attribute_name,
    referenced_entity_type,
)


def resolve(*typedefs: AtlasEnumDef | AtlasStructDef) -> TypeRegistry:
    """A registry with ``typedefs`` added, resolved and committed."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(list(typedefs))
    return registry


def failure(*typedefs: AtlasEnumDef | AtlasStructDef) -> AtlasError:
    """The error resolving ``typedefs`` raises."""
    with pytest.raises(AtlasError) as raised:
        resolve(*typedefs)
    return raised.value


def struct(name: str, *attributes: AtlasAttributeDef) -> AtlasStructDef:
    """A struct definition with ``attributes``."""
    return AtlasStructDef(name=name, attribute_defs=list(attributes))


def entity(name: str, *attributes: AtlasAttributeDef) -> AtlasEntityDef:
    """An entity definition with ``attributes``."""
    return AtlasEntityDef(name=name, attribute_defs=list(attributes))


def struct_type(registry: TypeRegistry, name: str) -> StructType:
    """The struct-like type named ``name``."""
    type_ = registry.get_type(name)
    assert isinstance(type_, StructType)
    return type_


@pytest.mark.covers(
    "aurelius_atlas_typesystem.types.StructType.attribute",
    "aurelius_atlas_typesystem.types.StructType.attribute_type",
    rules=["TRG-10", "TRG-13"],
)
def test__attributes_resolve_their_types() -> None:
    """``resolveReferences`` builds an ``AtlasAttribute`` per definition; lookup is by exact name."""
    registry = resolve(
        AtlasEnumDef(name="colour"),
        struct(
            "paint",
            AtlasAttributeDef(name="colour", type_name="colour"),
            AtlasAttributeDef(name="litres", type_name="int"),
        ),
    )
    paint = struct_type(registry, "paint")

    assert isinstance(paint.attribute_type("colour"), EnumType)
    assert isinstance(paint.attribute_type("litres"), BuiltInType)
    assert paint.attribute("Colour") is None
    assert paint.attribute(None) is None
    assert paint.attribute_type("missing") is None


@pytest.mark.covers(rules=["TRG-10"])
def test__list_and_set_cardinality_need_an_array() -> None:
    """``testInvalidStructDef_MultiValuedAttributeNotArray``: ``INVALID_ATTRIBUTE_TYPE_FOR_CARDINALITY`` (400)."""
    error = failure(struct("s", AtlasAttributeDef(name="tags", type_name="string", cardinality=Cardinality.SET)))

    assert error.code is AtlasErrorCode.INVALID_ATTRIBUTE_TYPE_FOR_CARDINALITY
    assert error.message == "Cardinality of attribute s.tags requires a list or set type"


@pytest.mark.covers(rules=["TRG-10"])
def test__an_array_attribute_takes_the_cardinality_and_counts() -> None:
    """The array type gets ``valuesMinCount``, ``valuesMaxCount`` and the cardinality of its attribute."""
    registry = resolve(
        struct(
            "s",
            AtlasAttributeDef(
                name="tags",
                type_name="array<string>",
                cardinality=Cardinality.SET,
                values_min_count=1,
                values_max_count=3,
            ),
        )
    )
    tags = struct_type(registry, "s").attribute_type("tags")

    assert isinstance(tags, ArrayType)
    assert (tags.cardinality, tags.min_count, tags.max_count) == (Cardinality.SET, 1, 3)


@pytest.mark.covers(rules=["TRG-10"])
@pytest.mark.parametrize("type_name", ["tag", "array<tag>", "map<string,tag>", "meta", "array<meta>"])
def test__classification_and_business_metadata_attributes_are_rejected(type_name: str) -> None:
    """``ATTRIBUTE_TYPE_INVALID`` (400) for the type itself, an array element or a map value."""
    error = failure(
        AtlasClassificationDef(name="tag"),
        AtlasBusinessMetadataDef(name="meta"),
        struct("s", AtlasAttributeDef(name="a", type_name=type_name)),
    )

    assert error.code is AtlasErrorCode.ATTRIBUTE_TYPE_INVALID
    assert error.message == "s.a: invalid attribute type. Attribute cannot be of type classification"


@pytest.mark.covers(rules=["TRG-10"])
def test__a_classification_as_map_key_is_not_checked() -> None:
    """Java checks only an array's element and a map's value."""
    registry = resolve(
        AtlasClassificationDef(name="tag"), struct("s", AtlasAttributeDef(name="a", type_name="map<tag,int>"))
    )

    assert isinstance(struct_type(registry, "s").attribute_type("a"), MapType)


@pytest.mark.covers(
    "aurelius_atlas_typesystem.types.qualified_attribute_name",
    "aurelius_atlas_typesystem.types.AtlasType.type_for_attribute",
    rules=["TRG-11"],
)
def test__attributes_have_qualified_names() -> None:
    """``getQualifiedAttributeName``: ``Type.attribute`` unless the name already contains a dot."""
    registry = resolve(
        struct("s", AtlasAttributeDef(name="a", type_name="int"), AtlasAttributeDef(name="x.y", type_name="int"))
    )
    s = struct_type(registry, "s")

    assert [attribute.qualified_name for attribute in s.all_attributes.values()] == ["s.a", "x.y"]
    assert qualified_attribute_name(AtlasStructDef(name="t"), "b") == "t.b"
    assert registry.get_type("int").type_for_attribute() is registry.get_type("int")


@pytest.mark.covers(
    "aurelius_atlas_typesystem.types.EntityType.type_for_attribute",
    "aurelius_atlas_typesystem.types.ArrayType.type_for_attribute",
    "aurelius_atlas_typesystem.types.MapType.type_for_attribute",
    rules=["TRG-11"],
)
def test__entity_types_are_held_as_object_ids() -> None:
    """``getTypeForAttribute``: an entity becomes ``AtlasObjectIdType``, also inside arrays and maps."""
    registry = resolve(
        entity("table"),
        struct(
            "s",
            AtlasAttributeDef(name="one", type_name="table"),
            AtlasAttributeDef(name="many", type_name="array<table>", cardinality=Cardinality.SET, values_max_count=5),
            AtlasAttributeDef(name="named", type_name="map<string,table>"),
            AtlasAttributeDef(name="plain", type_name="array<int>"),
        ),
    )
    s = struct_type(registry, "s")
    one, many, named, plain = (s.all_attributes[name] for name in ("one", "many", "named", "plain"))

    assert isinstance(one.attribute_type, ObjectIdType)
    assert one.attribute_type.object_type == "table"
    assert isinstance(many.attribute_type, ArrayType)
    assert many.attribute_type.type_name == "array<objectid>"
    assert (many.attribute_type.cardinality, many.attribute_type.max_count) == (Cardinality.LIST, -1)
    assert isinstance(named.attribute_type, MapType)
    assert named.attribute_type.type_name == "map<string,objectid>"
    assert [attribute.is_object_ref for attribute in (one, many, named, plain)] == [True, True, True, False]


@pytest.mark.covers(rules=["TRG-11"])
def test__an_object_id_type_refers_to_asset_by_default() -> None:
    """``new AtlasObjectIdType()`` refers to ``Asset``; the registry's ``objectid`` is one."""
    object_id = TypeRegistry().get_type("objectid")

    assert isinstance(object_id, ObjectIdType)
    assert object_id.object_type == "Asset"
    assert object_id.category is TypeCategory.OBJECT_ID_TYPE


def owned(type_name: str) -> AtlasAttributeDef:
    """An attribute with an ``ownedRef`` constraint."""
    return AtlasAttributeDef(name="parts", type_name=type_name, constraints=[AtlasConstraintDef(type="ownedRef")])


def inverse(type_name: str, params: dict[str, Any] | None) -> AtlasAttributeDef:
    """An attribute with an ``inverseRef`` constraint."""
    return AtlasAttributeDef(
        name="owner", type_name=type_name, constraints=[AtlasConstraintDef(type="inverseRef", params=params)]
    )


@pytest.mark.covers("aurelius_atlas_typesystem.types.referenced_entity_type", rules=["TRG-12"])
def test__owned_and_inverse_references_are_resolved_and_linked() -> None:
    """A valid ``ownedRef`` and its ``inverseRef``: flags, the inverse name and, in phase 2, the inverse attribute."""
    registry = resolve(
        entity("table", owned("array<column>")),
        entity("column", inverse("table", {"attribute": "parts"})),
    )
    table, column = struct_type(registry, "table"), struct_type(registry, "column")
    parts, owner = table.all_attributes["parts"], column.all_attributes["owner"]

    assert parts.is_owned_ref
    assert not owner.is_owned_ref
    assert owner.inverse_ref_attribute_name == "parts"
    assert owner.inverse_ref_attribute is parts
    assert parts.inverse_ref_attribute is None
    assert referenced_entity_type(registry.get_type("array<table>")) is table
    assert referenced_entity_type(registry.get_type("map<string,table>")) is table
    assert referenced_entity_type(registry.get_type("int")) is None


@pytest.mark.covers(rules=["TRG-12"])
def test__an_owned_reference_needs_an_entity_type() -> None:
    """``CONSTRAINT_OWNED_REF_ATTRIBUTE_INVALID_TYPE`` (400)."""
    error = failure(struct("s", owned("array<string>")))

    assert error.code is AtlasErrorCode.CONSTRAINT_OWNED_REF_ATTRIBUTE_INVALID_TYPE
    assert error.message == "s.parts: invalid ownedRef constraint. Attribute array<string> is not an entity type"


@pytest.mark.covers(rules=["TRG-12"])
@pytest.mark.parametrize(
    ("typedefs", "code", "message"),
    [
        (
            [struct("s", inverse("int", {"attribute": "x"}))],
            AtlasErrorCode.CONSTRAINT_INVERSE_REF_ATTRIBUTE_INVALID_TYPE,
            "s.owner: invalid inverseRef constraint. Attribute int is not an entity type",
        ),
        (
            [entity("t"), struct("s", inverse("t", {"attribute": " "}))],
            AtlasErrorCode.CONSTRAINT_MISSING_PARAMS,
            "s.owner : invalid constraint. missing parameter attribute in inverseRef. params={attribute= }",
        ),
        (
            [entity("t"), struct("s", inverse("t", None))],
            AtlasErrorCode.CONSTRAINT_MISSING_PARAMS,
            "s.owner : invalid constraint. missing parameter attribute in inverseRef. params=null",
        ),
        (
            [entity("t"), struct("s", inverse("t", {"attribute": "missing"}))],
            AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_NON_EXISTING,
            "s.owner: invalid inverseRef constraint. Inverse attribute t.missing does not exist",
        ),
        (
            [entity("t", AtlasAttributeDef(name="n", type_name="int")), struct("s", inverse("t", {"attribute": "n"}))],
            AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_INVALID_TYPE,
            "s.owner: invalid inverseRef constraint. Inverse attribute t.n is not an entity type",
        ),
    ],
    ids=["not-entity", "blank-param", "no-params", "missing-inverse", "inverse-not-entity"],
)
def test__an_inverse_reference_is_checked(typedefs: list[AtlasStructDef], code: AtlasErrorCode, message: str) -> None:
    """``resolveConstraints``: each ``inverseRef`` check and its error, all 400."""
    error = failure(*typedefs)

    assert error.code is code
    assert error.code.http_status == 400
    assert error.message == message


@pytest.mark.covers(rules=["TRG-13"])
def test__unique_attributes_are_those_defined_unique() -> None:
    """``getUniqueAttributes``: the attributes whose definition has ``isUnique``."""
    registry = resolve(
        entity(
            "t",
            AtlasAttributeDef(name="qualifiedName", type_name="string", is_unique=True),
            AtlasAttributeDef(name="n", type_name="int"),
        )
    )

    assert list(struct_type(registry, "t").unique_attributes) == ["qualifiedName"]


@pytest.mark.covers(
    "aurelius_atlas_typesystem.types.EnumType.element",
    "aurelius_atlas_typesystem.types.EnumType.element_by_ordinal",
    rules=["TRG-14"],
)
def test__an_enum_type_finds_elements_by_value_and_ordinal() -> None:
    """``getEnumElementDef(String)`` ignores case; ``getEnumElementDef(Number)`` compares ordinals."""
    registry = resolve(
        AtlasEnumDef(
            name="e",
            element_defs=[AtlasEnumElementDef(value="RED", ordinal=1), AtlasEnumElementDef(value="GREEN", ordinal=2)],
        )
    )
    enum = registry.enum_type("e")

    assert enum is not None
    red = enum.element("red")
    assert red is not None
    assert red.ordinal == 1
    green = enum.element_by_ordinal(2)
    assert green is not None
    assert green.value == "GREEN"
    assert enum.element(None) is None
    assert enum.element_by_ordinal(None) is None
    assert enum.element_by_ordinal(9) is None


@pytest.mark.covers(rules=["TRG-14"])
@pytest.mark.parametrize(
    ("enum_def", "default"),
    [
        (
            AtlasEnumDef(
                name="e",
                element_defs=[AtlasEnumElementDef(value="A"), AtlasEnumElementDef(value="B")],
                default_value="B",
            ),
            "B",
        ),
        (AtlasEnumDef(name="e", element_defs=[AtlasEnumElementDef(value="A"), AtlasEnumElementDef(value="B")]), "A"),
        (AtlasEnumDef(name="e"), None),
    ],
    ids=["given", "first-element", "no-elements"],
)
def test__an_enum_default_is_given_or_the_first_element(enum_def: AtlasEnumDef, default: str | None) -> None:
    """The constructor of ``AtlasEnumType``."""
    assert EnumType(enum_def).default_value == default


@pytest.mark.covers("aurelius_atlas_typesystem.types.type_of", rules=["TRG-16"])
@pytest.mark.parametrize(
    "typedef",
    [
        AtlasClassificationDef(name="k", attribute_defs=[AtlasAttributeDef(name="a", type_name="missing")]),
        AtlasEntityDef(name="k", attribute_defs=[AtlasAttributeDef(name="a", type_name="missing")]),
        AtlasRelationshipDef(name="k", attribute_defs=[AtlasAttributeDef(name="a", type_name="missing")]),
        AtlasBusinessMetadataDef(name="k", attribute_defs=[AtlasAttributeDef(name="a", type_name="missing")]),
    ],
    ids=["classification", "entity", "relationship", "business-metadata"],
)
def test__every_kind_resolves_its_own_attributes(typedef: AtlasStructDef) -> None:
    """Each subclass of ``AtlasStructType`` resolves its attributes as a struct does."""
    assert failure(typedef).code is AtlasErrorCode.TYPE_NAME_NOT_FOUND
    fixed = typedef.model_copy(update={"attribute_defs": [AtlasAttributeDef(name="a", type_name="int")]})
    type_: AtlasType = struct_type(resolve(fixed), "k")
    assert isinstance(type_, StructType)
    assert type_.category is typedef.category
    assert isinstance(type_.attribute_type("a"), BuiltInType)
    assert not isinstance(type_, EntityType) or type_.type_for_attribute().type_name == "objectid"
