"""The helpers the Java typedef classes offer (TDM-16 to TDM-19).

Read from Apache Atlas 2.4.0's typedef classes and their tests ``TestAtlasStructDef``, ``TestAtlasEnumDef``,
``TestAtlasClassificationDef`` and ``TestAtlasEntityDef`` (``testHasAttribute``, ``testAddAttribute``,
``testRemoveAttribute``, ``testAddSuperType``, …).
"""

import pytest
from aurelius_atlas_model.typedef import (
    ATLAS_BUILTIN_TYPES,
    ATLAS_PRIMITIVE_TYPES,
    ATLAS_RELATIONSHIP_ATTRIBUTE_TYPES,
    AtlasAttributeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasConstraintDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipDef,
    AtlasStructDef,
    AtlasTypeDefHeader,
    AtlasTypesDef,
    TypeCategory,
    array_type_name,
    find_attribute,
    map_type_name,
)


@pytest.fixture
def struct() -> AtlasStructDef:
    """A struct with attributes ``a`` and ``b``."""
    return AtlasStructDef(
        name="s", attribute_defs=[AtlasAttributeDef(name="a", type_name="int"), AtlasAttributeDef(name="b")]
    )


@pytest.mark.covers(
    "aurelius_atlas_model.typedef.AtlasStructDef.get_attribute",
    "aurelius_atlas_model.typedef.AtlasStructDef.has_attribute",
    "aurelius_atlas_model.typedef.find_attribute",
    rules=["TDM-16"],
)
def test__attributes_are_found_by_name_without_case(struct: AtlasStructDef) -> None:
    """``getAttribute`` and ``hasAttribute`` use ``StringUtils.equalsIgnoreCase``."""
    attribute = struct.get_attribute("A")

    assert attribute is not None
    assert attribute.type_name == "int"
    assert struct.has_attribute("B")
    assert not struct.has_attribute("c")
    assert struct.get_attribute(None) is None
    assert find_attribute(struct.attribute_defs, "b") is struct.attribute_defs[1]


@pytest.mark.covers("aurelius_atlas_model.typedef.AtlasStructDef.add_attribute", rules=["TDM-16"])
def test__adding_an_attribute_replaces_one_with_the_same_name_and_appends(struct: AtlasStructDef) -> None:
    """``addAttribute`` copies the others, drops the same-named one and appends the new one."""
    struct.add_attribute(AtlasAttributeDef(name="A", type_name="string"))

    assert [(attribute.name, attribute.type_name) for attribute in struct.attribute_defs] == [
        ("b", None),
        ("A", "string"),
    ]


@pytest.mark.covers("aurelius_atlas_model.typedef.AtlasStructDef.remove_attribute", rules=["TDM-16"])
def test__removing_an_attribute_matches_its_name_without_case(struct: AtlasStructDef) -> None:
    """``removeAttribute`` keeps every attribute with another name; an unknown name changes nothing."""
    struct.remove_attribute("A")
    struct.remove_attribute("missing")

    assert [attribute.name for attribute in struct.attribute_defs] == ["b"]


@pytest.mark.covers(
    "aurelius_atlas_model.typedef.AtlasEnumDef.get_element",
    "aurelius_atlas_model.typedef.AtlasEnumDef.has_element",
    "aurelius_atlas_model.typedef.AtlasEnumDef.add_element",
    "aurelius_atlas_model.typedef.AtlasEnumDef.remove_element",
    rules=["TDM-16"],
)
def test__enum_elements_are_found_replaced_and_removed_by_value_without_case() -> None:
    """``getElement``, ``hasElement``, ``addElement`` and ``removeElement`` of ``AtlasEnumDef``."""
    enum = AtlasEnumDef(
        name="e", element_defs=[AtlasEnumElementDef(value="RED", ordinal=1), AtlasEnumElementDef(value="GREEN")]
    )

    element = enum.get_element("red")
    assert element is not None
    assert element.ordinal == 1
    assert enum.has_element("Green")
    assert not enum.has_element("blue")

    enum.add_element(AtlasEnumElementDef(value="Red", ordinal=9))
    assert [(element.value, element.ordinal) for element in enum.element_defs] == [("GREEN", None), ("Red", 9)]

    enum.remove_element("green")
    assert [element.value for element in enum.element_defs] == ["Red"]


@pytest.mark.covers(
    "aurelius_atlas_model.typedef.AtlasClassificationDef.has_super_type",
    "aurelius_atlas_model.typedef.AtlasClassificationDef.add_super_type",
    "aurelius_atlas_model.typedef.AtlasClassificationDef.remove_super_type",
    "aurelius_atlas_model.typedef.AtlasClassificationDef.has_entity_type",
    "aurelius_atlas_model.typedef.AtlasClassificationDef.add_entity_type",
    "aurelius_atlas_model.typedef.AtlasClassificationDef.remove_entity_type",
    rules=["TDM-16"],
)
def test__classification_super_and_entity_types_match_exactly() -> None:
    """``Set.contains`` compares exactly; adding a present name changes nothing."""
    classification = AtlasClassificationDef(name="c", super_types=["PII"])

    classification.add_super_type("PII")
    classification.add_super_type("Sensitive")
    classification.add_entity_type("table")
    assert classification.has_super_type("Sensitive")
    assert not classification.has_super_type("pii")
    assert classification.has_entity_type("table")
    assert classification.super_types == ["PII", "Sensitive"]

    classification.remove_super_type("PII")
    classification.remove_entity_type("table")
    classification.remove_entity_type("missing")
    assert classification.super_types == ["Sensitive"]
    assert classification.entity_types == []


@pytest.mark.covers(
    "aurelius_atlas_model.typedef.AtlasEntityDef.has_super_type",
    "aurelius_atlas_model.typedef.AtlasEntityDef.add_super_type",
    "aurelius_atlas_model.typedef.AtlasEntityDef.remove_super_type",
    rules=["TDM-16"],
)
def test__entity_super_types_match_exactly() -> None:
    """``hasSuperType``, ``addSuperType`` and ``removeSuperType`` of ``AtlasEntityDef``."""
    entity = AtlasEntityDef(name="t")

    entity.add_super_type("DataSet")
    entity.add_super_type("DataSet")
    assert entity.super_types == ["DataSet"]
    assert entity.has_super_type("DataSet")
    assert not entity.has_super_type("dataset")

    entity.remove_super_type("DataSet")
    assert entity.super_types == []


@pytest.mark.covers(
    "aurelius_atlas_model.typedef.AtlasBaseTypeDef.get_option",
    "aurelius_atlas_model.typedef.AtlasBaseTypeDef.set_option",
    "aurelius_atlas_model.typedef.AtlasAttributeDef.get_option",
    "aurelius_atlas_model.typedef.AtlasAttributeDef.set_option",
    rules=["TDM-16"],
)
def test__options_are_read_and_set_by_exact_key() -> None:
    """``getOption`` returns null without options; ``setOption`` creates the map on first use."""
    typedef = AtlasBusinessMetadataDef(name="bm")
    attribute = AtlasAttributeDef(name="a")

    assert typedef.get_option("x") is None
    assert attribute.get_option("x") is None
    typedef.set_option("x", "1")
    attribute.set_option("maxStrLength", "50")

    assert typedef.get_option("x") == "1"
    assert typedef.get_option("X") is None
    assert attribute.options == {"maxStrLength": "50"}


@pytest.mark.covers(
    "aurelius_atlas_model.typedef.AtlasAttributeDef.is_soft_referenced",
    "aurelius_atlas_model.typedef.AtlasAttributeDef.is_append_on_partial_update",
    rules=["TDM-16"],
)
@pytest.mark.parametrize(("value", "expected"), [(None, False), ("true", True), ("TRUE", True), ("yes", False)])
def test__soft_reference_and_append_options_are_true_only_for_true(value: str | None, expected: bool) -> None:  # noqa: FBT001
    """``Boolean.valueOf`` is true for ``true`` in any case, false for anything else."""
    attribute = AtlasAttributeDef(name="a")
    if value is not None:
        attribute.set_option("isSoftReference", value)
        attribute.set_option("isAppendOnPartialUpdate", value)

    assert attribute.is_soft_referenced() is expected
    assert attribute.is_append_on_partial_update() is expected


@pytest.mark.covers(
    "aurelius_atlas_model.typedef.AtlasConstraintDef.is_constraint_type",
    "aurelius_atlas_model.typedef.AtlasConstraintDef.get_param",
    "aurelius_atlas_model.typedef.AtlasAttributeDef.add_constraint",
    rules=["TDM-16"],
)
def test__constraints_are_matched_by_type_without_case_and_read_by_parameter() -> None:
    """``isConstraintType`` uses ``equalsIgnoreCase``; ``getParam`` is null without parameters."""
    attribute = AtlasAttributeDef(name="columns")
    attribute.add_constraint(AtlasConstraintDef(type="inverseRef", params={"attribute": "table"}))
    attribute.add_constraint(AtlasConstraintDef(type="ownedRef"))

    inverse, owned = attribute.constraints or []
    assert inverse.is_constraint_type("INVERSEREF")
    assert not inverse.is_constraint_type(None)
    assert inverse.get_param("attribute") == "table"
    assert owned.get_param("attribute") is None


@pytest.mark.covers(
    "aurelius_atlas_model.typedef.AtlasTypesDef.is_empty",
    "aurelius_atlas_model.typedef.AtlasTypesDef.has_enum_def",
    "aurelius_atlas_model.typedef.AtlasTypesDef.has_struct_def",
    "aurelius_atlas_model.typedef.AtlasTypesDef.has_classification_def",
    "aurelius_atlas_model.typedef.AtlasTypesDef.has_entity_def",
    "aurelius_atlas_model.typedef.AtlasTypesDef.has_relationship_def",
    "aurelius_atlas_model.typedef.AtlasTypesDef.has_business_metadata_def",
    rules=["TDM-17"],
)
def test__a_types_def_tells_whether_it_is_empty_and_what_it_holds() -> None:
    """``isEmpty`` and the ``has*Def`` methods of ``AtlasTypesDef``; names compare exactly."""
    assert AtlasTypesDef().is_empty()
    assert AtlasTypesDef(enum_defs=None, entity_defs=None).is_empty()

    types = AtlasTypesDef(
        enum_defs=[AtlasEnumDef(name="e")],
        struct_defs=[AtlasStructDef(name="s")],
        classification_defs=[AtlasClassificationDef(name="c")],
        entity_defs=[AtlasEntityDef(name="t")],
        relationship_defs=[AtlasRelationshipDef(name="r")],
        business_metadata_defs=[AtlasBusinessMetadataDef(name="b")],
    )

    assert not types.is_empty()
    assert types.has_enum_def("e")
    assert types.has_struct_def("s")
    assert types.has_classification_def("c")
    assert types.has_entity_def("t")
    assert types.has_relationship_def("r")
    assert types.has_business_metadata_def("b")
    assert not types.has_entity_def("T")
    assert not AtlasTypesDef(entity_defs=None).has_entity_def("t")


@pytest.mark.covers("aurelius_atlas_model.typedef.AtlasTypeDefHeader.of", rules=["TDM-18"])
def test__a_header_carries_the_identity_of_its_type_definition() -> None:
    """``new AtlasTypeDefHeader(AtlasBaseTypeDef)``: guid, name, category and service type."""
    header = AtlasTypeDefHeader.of(AtlasClassificationDef(guid="g-1", name="PII", service_type="atlas_core"))

    assert header == AtlasTypeDefHeader(
        guid="g-1", name="PII", category=TypeCategory.CLASSIFICATION, service_type="atlas_core"
    )
    assert header.to_json() == {"guid": "g-1", "name": "PII", "serviceType": "atlas_core", "category": "CLASSIFICATION"}


@pytest.mark.covers(
    "aurelius_atlas_model.typedef.array_type_name", "aurelius_atlas_model.typedef.map_type_name", rules=["TDM-19"]
)
def test__collection_type_names_are_built_as_atlas_builds_them() -> None:
    """``getArrayTypeName`` and ``getMapTypeName``: no spaces, a comma between key and value."""
    assert array_type_name("string") == "array<string>"
    assert map_type_name("string", array_type_name("int")) == "map<string,array<int>>"


@pytest.mark.covers(rules=["TDM-19"])
def test__the_built_in_type_names_are_atlas() -> None:
    """``ATLAS_PRIMITIVE_TYPES``, ``ATLAS_RELATIONSHIP_ATTRIBUTE_TYPES`` and ``ATLAS_BUILTIN_TYPES``."""
    primitives = ("boolean", "byte", "short", "int", "long", "float", "double", "biginteger", "bigdecimal", "string")

    assert primitives == ATLAS_PRIMITIVE_TYPES
    assert (*primitives, "date") == ATLAS_RELATIONSHIP_ATTRIBUTE_TYPES
    assert (*primitives, "date", "objectid") == ATLAS_BUILTIN_TYPES
