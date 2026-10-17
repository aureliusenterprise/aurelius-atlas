"""Type hierarchies, relationship and business metadata types (THY-01 to THY-12).

Read from ``AtlasEntityType``, ``AtlasClassificationType``, ``AtlasRelationshipType`` and
``AtlasBusinessMetadataType`` of Apache Atlas 2.4.0 and the tests ``TestAtlasTypeRegistry``
(``testEntityDefValidHierarchy``, ``testEntityDefInvalidHierarchy_Self``, ``…_CircularRef``,
``testRegistryValiditySuperTypesUpdateWithExistingAttribute``) and ``TestAtlasRelationshipType``.
"""

import json
from pathlib import Path

import pytest
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasBaseTypeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasConstraintDef,
    AtlasEntityDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
    AtlasTypesDef,
    Cardinality,
    PropagateTags,
)
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.types import (
    ArrayType,
    BusinessAttribute,
    ClassificationType,
    EdgeDirection,
    EntityType,
    ObjectIdType,
    RelationshipType,
    entity_types_and_all_sub_types,
    validate_relationship_def,
)

FIXTURES = Path(__file__).parent / "fixtures"


def resolve(*typedefs: AtlasBaseTypeDef) -> TypeRegistry:
    """A registry with ``typedefs`` added, resolved and committed."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(list(typedefs))
    return registry


def failure(*typedefs: AtlasBaseTypeDef) -> AtlasError:
    """The error resolving ``typedefs`` raises."""
    with pytest.raises(AtlasError) as raised:
        resolve(*typedefs)
    return raised.value


def entity(
    name: str, *super_types: str, attributes: tuple[AtlasAttributeDef, ...] = (), **options: str
) -> AtlasEntityDef:
    """An entity definition."""
    return AtlasEntityDef(
        name=name, super_types=list(super_types), attribute_defs=list(attributes), options=options or None
    )


def tag(name: str, *super_types: str, entity_types: tuple[str, ...] = ()) -> AtlasClassificationDef:
    """A classification definition."""
    return AtlasClassificationDef(name=name, super_types=list(super_types), entity_types=list(entity_types))


def attr(name: str, type_name: str = "string", **fields: object) -> AtlasAttributeDef:
    """An attribute definition."""
    return AtlasAttributeDef.model_validate({"name": name, "type_name": type_name, **fields})


def entity_type(registry: TypeRegistry, name: str) -> EntityType:
    """The entity type named ``name``."""
    found = registry.entity_type(name)
    assert found is not None
    return found


def relationship_type(registry: TypeRegistry, name: str) -> RelationshipType:
    """The relationship type named ``name``."""
    found = registry.relationship_type(name)
    assert found is not None
    return found


def classification_type(registry: TypeRegistry, name: str) -> ClassificationType:
    """The classification type named ``name``."""
    found = registry.classification_type(name)
    assert found is not None
    return found


@pytest.mark.covers(rules=["THY-01"])
@pytest.mark.parametrize(
    "typedefs",
    [
        (entity("t", "c"), tag("c")),
        (tag("c", "t"), entity("t")),
        (entity("t", "s"), AtlasStructDef(name="s")),
    ],
    ids=["entity-of-classification", "classification-of-entity", "entity-of-struct"],
)
def test__a_super_type_must_be_of_the_same_kind(typedefs: tuple[AtlasBaseTypeDef, ...]) -> None:
    """``INCOMPATIBLE_SUPERTYPE``, with the super type first as Java passes it."""
    error = failure(*typedefs)

    assert error.code is AtlasErrorCode.INCOMPATIBLE_SUPERTYPE
    assert error.message.endswith(": incompatible supertype " + str(typedefs[0].name))


@pytest.mark.covers(rules=["THY-01"])
def test__an_unknown_super_type_is_not_found() -> None:
    """``typeRegistry.getType(superTypeName)`` raises for a name nobody defines."""
    assert failure(entity("t", "missing")).code is AtlasErrorCode.TYPE_NAME_NOT_FOUND


@pytest.mark.covers(rules=["THY-02"])
@pytest.mark.parametrize(
    ("typedefs", "message"),
    [
        ((entity("L0", "L0"),), "L0: invalid supertypes - circular reference back to self [L0]"),
        ((entity("A", "B"), entity("B", "A")), "A: invalid supertypes - circular reference back to self [A, B]"),
        ((tag("T", "T"),), "T: invalid supertypes - circular reference back to self [T]"),
    ],
    ids=["entity-self", "entity-cycle", "classification-self"],
)
def test__a_circular_hierarchy_fails(typedefs: tuple[AtlasBaseTypeDef, ...], message: str) -> None:
    """``testEntityDefInvalidHierarchy_Self`` and ``…_CircularRef``: ``CIRCULAR_REFERENCE`` names the path."""
    error = failure(*typedefs)

    assert error.code is AtlasErrorCode.CIRCULAR_REFERENCE
    assert error.message == message


@pytest.mark.covers(
    "aurelius_atlas_typesystem.types._HierarchyType.is_super_type_of",
    "aurelius_atlas_typesystem.types._HierarchyType.is_sub_type_of",
    rules=["THY-03", "THY-04"],
)
def test__an_entity_hierarchy_is_resolved() -> None:
    """``testEntityDefValidHierarchy``: super and sub types at every depth, and the inherited attributes."""
    registry = resolve(
        entity("L0", attributes=(attr("a0"),)),
        entity("L1", "L0", attributes=(attr("a1"),)),
        entity("L2", "L1", attributes=(attr("a2"),)),
        entity("M1", "L0"),
    )
    l0, l1, l2 = (entity_type(registry, name) for name in ("L0", "L1", "L2"))

    assert l2.all_super_types == ["L0", "L1"]
    assert list(l2.all_attributes) == ["a0", "a1", "a2"]
    assert l0.sub_types == ["L1", "M1"]
    assert l0.all_sub_types == ["L1", "L2", "M1"]
    assert l0.type_and_all_sub_types == ["L0", "L1", "L2", "M1"]
    assert l2.type_and_all_super_types == ["L0", "L1", "L2"]
    assert l0.is_super_type_of(l2)
    assert l2.is_sub_type_of("L0")
    assert not l1.is_super_type_of("L0")
    assert not l1.is_sub_type_of(None)
    inherited = l2.attribute("a0")
    assert inherited is not None
    assert inherited.defined_in is l0


@pytest.mark.covers(rules=["THY-03"])
def test__an_attribute_name_may_not_come_from_two_types() -> None:
    """``testRegistryValiditySuperTypesUpdateWithExistingAttribute``: ``ATTRIBUTE_NAME_ALREADY_EXISTS_…``."""
    error = failure(
        entity("L0", attributes=(attr("attr1"),)), entity("L2", attributes=(attr("attr1"),)), entity("L1", "L0", "L2")
    )

    assert error.code is AtlasErrorCode.ATTRIBUTE_NAME_ALREADY_EXISTS_IN_ANOTHER_PARENT_TYPE
    assert error.message == "Invalid attribute name: L2.attr1. Attribute already exists in another parent type: L0"


@pytest.mark.covers(rules=["THY-03"])
def test__a_super_type_reached_twice_is_no_conflict() -> None:
    """A diamond: ``L0``'s attribute arrives through ``L1`` and ``L2``, owned by ``L0`` both times."""
    registry = resolve(
        entity("L0", attributes=(attr("a"),)), entity("L1", "L0"), entity("L2", "L0"), entity("L3", "L1", "L2")
    )

    assert entity_type(registry, "L3").all_super_types == ["L0", "L1", "L2"]


@pytest.mark.covers(rules=["THY-04"])
def test__sub_types_are_written_to_the_definitions() -> None:
    """Phase 3 sets ``subTypes`` on entity and classification definitions."""
    registry = resolve(entity("L0"), entity("L1", "L0"), tag("T0"), tag("T1", "T0"))

    assert entity_type(registry, "L0").entity_def.sub_types == ["L1"]
    assert entity_type(registry, "L1").entity_def.sub_types == []
    assert classification_type(registry, "T0").classification_def.sub_types == ["T1"]


@pytest.mark.covers(rules=["THY-05"])
def test__system_attributes_are_found_on_every_entity_and_classification() -> None:
    """``getSystemAttribute`` falls back to ``__ENTITY_ROOT`` and ``__CLASSIFICATION_ROOT``, unqualified."""
    registry = resolve(entity("t", attributes=(attr("name"),)), tag("c"))
    guid = entity_type(registry, "t").attribute("__guid")
    status = classification_type(registry, "c").attribute("__entityStatus")

    assert guid is not None
    assert guid.qualified_name == "__guid"
    assert guid.attribute_def.is_unique
    assert status is not None
    assert classification_type(registry, "c").attribute("__guid") is None
    assert not registry.is_registered("__ENTITY_ROOT")


@pytest.mark.covers(rules=["THY-06"])
def test__header_and_minimal_info_attributes() -> None:
    """Unique attributes plus ``name``, ``description``, ``owner``, ``createTime``; ``schemaAttributes`` adds more."""
    registry = resolve(
        entity(
            "t",
            attributes=(
                attr("qualifiedName", is_unique=True),
                attr("name"),
                attr("owner"),
                attr("columns"),
                attr("other"),
            ),
            schemaAttributes='["columns", "missing"]',
        )
    )
    table = entity_type(registry, "t")

    assert list(table.header_attributes) == ["qualifiedName", "name", "owner"]
    assert list(table.min_info_attributes) == ["qualifiedName", "name", "owner", "columns"]


@pytest.mark.covers(rules=["THY-06"])
def test__the_display_text_attribute_is_own_else_inherited() -> None:
    """Own option when the attribute exists, else a direct super type's, else any super type's."""
    registry = resolve(
        entity("A", attributes=(attr("label"),), displayTextAttribute="label"),
        entity("B", "A"),
        entity("C", "B"),
        entity("D", "A", attributes=(attr("title"),), displayTextAttribute="title"),
        entity("E", displayTextAttribute="missing"),
    )

    assert [entity_type(registry, name).display_text_attribute for name in "ABCDE"] == [
        "label",
        "label",
        "label",
        "title",
        None,
    ]


@pytest.mark.covers(rules=["THY-06"])
def test__internal_types_and_owned_references() -> None:
    """``__internal`` among the super types makes a type internal; ``ownedRef`` attributes are listed."""
    registry = resolve(
        entity("__internal"),
        entity("hidden", "__internal"),
        entity("part"),
        entity("whole", attributes=(attr("parts", "array<part>", constraints=[AtlasConstraintDef(type="ownedRef")]),)),
    )

    assert entity_type(registry, "hidden").is_internal
    assert not entity_type(registry, "part").is_internal
    assert [attribute.name for attribute in entity_type(registry, "whole").owned_ref_attributes] == ["parts"]


@pytest.mark.covers(
    "aurelius_atlas_typesystem.types.ClassificationType.can_apply_to_entity_type",
    "aurelius_atlas_typesystem.types.entity_types_and_all_sub_types",
    rules=["THY-07"],
)
def test__a_classification_applies_to_its_entity_types_and_their_sub_types() -> None:
    """``getEntityTypesAndAllSubTypes``; no restriction anywhere means every entity type."""
    registry = resolve(
        entity("A"), entity("B", "A"), entity("C"), tag("onA", entity_types=("A",)), tag("free"), tag("child", "onA")
    )
    on_a, free, child = (classification_type(registry, name) for name in ("onA", "free", "child"))

    assert on_a.entity_types == ["A", "B"]
    assert on_a.can_apply_to_entity_type(entity_type(registry, "B"))
    assert not on_a.can_apply_to_entity_type(entity_type(registry, "C"))
    assert free.entity_types == []
    assert free.can_apply_to_entity_type(entity_type(registry, "C"))
    assert child.entity_types == ["A", "B"]
    assert entity_types_and_all_sub_types(["A", "C"], registry) == ["A", "B", "C"]


@pytest.mark.covers(rules=["THY-07"])
@pytest.mark.parametrize(
    ("child", "code"),
    [
        (tag("child", "onA", "onC"), AtlasErrorCode.CLASSIFICATIONDEF_PARENTS_ENTITYTYPES_DISJOINT),
        (tag("child", "onA", entity_types=("C",)), AtlasErrorCode.CLASSIFICATIONDEF_ENTITYTYPES_NOT_PARENTS_SUBSET),
        (tag("child", entity_types=("missing",)), AtlasErrorCode.TYPE_NAME_NOT_FOUND),
    ],
    ids=["disjoint-parents", "not-a-subset", "unknown-entity-type"],
)
def test__a_classification_must_honour_its_parents_entity_types(
    child: AtlasClassificationDef, code: AtlasErrorCode
) -> None:
    """Phase 3 of ``AtlasClassificationType``."""
    error = failure(entity("A"), entity("C"), tag("onA", entity_types=("A",)), tag("onC", entity_types=("C",)), child)

    assert error.code is code


@pytest.mark.covers(rules=["THY-07"])
def test__own_entity_types_inside_the_parents_are_kept() -> None:
    """A child may narrow its parents' entity types."""
    registry = resolve(
        entity("A"), entity("B", "A"), tag("onA", entity_types=("A",)), tag("child", "onA", entity_types=("B",))
    )

    assert classification_type(registry, "child").entity_types == ["B"]


def end(type_name: str | None, name: str | None, **fields: object) -> AtlasRelationshipEndDef:
    """A relationship end."""
    return AtlasRelationshipEndDef.model_validate({"type": type_name, "name": name, **fields})


def relationship(
    name: str, end1: AtlasRelationshipEndDef | None, end2: AtlasRelationshipEndDef | None, **fields: object
) -> AtlasRelationshipDef:
    """A relationship definition."""
    return AtlasRelationshipDef.model_validate({"name": name, "end_def1": end1, "end_def2": end2, **fields})


@pytest.mark.covers(rules=["THY-08"])
@pytest.mark.parametrize(
    ("typedef", "code", "message"),
    [
        (
            relationship("r", None, end("t", "b")),
            AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE,
            "Mandatory field endDef1.type has empty/null value",
        ),
        (
            relationship("r", end("t", "a"), end("", "b")),
            AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE,
            "Mandatory field endDef2.type has empty/null value",
        ),
        (
            relationship("r", end("s", "a"), end("t", "b")),
            AtlasErrorCode.RELATIONSHIPDEF_INVALID_END_TYPE,
            "relationshipDef r has invalid end type s",
        ),
        (
            relationship("r", end("t", None), end("t", "b")),
            AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE,
            "Mandatory field endDef1.name has empty/null value",
        ),
        (
            relationship("r", end("t", "a"), end("t", "")),
            AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE,
            "Mandatory field endDef2.name has empty/null value",
        ),
    ],
    ids=["no-end1", "blank-end2-type", "struct-end", "no-end1-name", "blank-end2-name"],
)
def test__relationship_ends_need_an_entity_type_and_a_name(
    typedef: AtlasRelationshipDef, code: AtlasErrorCode, message: str
) -> None:
    """``AtlasRelationshipType.resolveReferences``."""
    error = failure(entity("t"), AtlasStructDef(name="s"), typedef)

    assert (error.code, error.message) == (code, message)


@pytest.mark.covers("aurelius_atlas_typesystem.types.validate_relationship_def", rules=["THY-08"])
@pytest.mark.parametrize(
    ("category", "end1", "end2", "code"),
    [
        (None, end("t", "a", cardinality="LIST"), end("t", "b"), AtlasErrorCode.RELATIONSHIPDEF_LIST_ON_END),
        (
            "AGGREGATION",
            end("t", "a", isContainer=True),
            end("t", "b", isContainer=True),
            AtlasErrorCode.RELATIONSHIPDEF_DOUBLE_CONTAINERS,
        ),
        (
            "ASSOCIATION",
            end("t", "a", isContainer=True),
            end("t", "b"),
            AtlasErrorCode.RELATIONSHIPDEF_ASSOCIATION_AND_CONTAINER,
        ),
        (
            None,
            end("t", "a", isContainer=True),
            end("t", "b"),
            AtlasErrorCode.RELATIONSHIPDEF_ASSOCIATION_AND_CONTAINER,
        ),
        ("COMPOSITION", end("t", "a"), end("t", "b"), AtlasErrorCode.RELATIONSHIPDEF_COMPOSITION_NO_CONTAINER),
        ("AGGREGATION", end("t", "a"), end("t", "b"), AtlasErrorCode.RELATIONSHIPDEF_AGGREGATION_NO_CONTAINER),
        (
            "COMPOSITION",
            end("t", "a", isContainer=True),
            end("t", "b", cardinality="SET"),
            AtlasErrorCode.RELATIONSHIPDEF_COMPOSITION_MULTIPLE_PARENTS,
        ),
    ],
    ids=[
        "list-end",
        "two-containers",
        "association-container",
        "no-category-container",
        "composition",
        "aggregation",
        "multiple-parents",
    ],
)
def test__relationship_ends_must_fit_the_category(
    category: str | None, end1: AtlasRelationshipEndDef, end2: AtlasRelationshipEndDef, code: AtlasErrorCode
) -> None:
    """``validateAtlasRelationshipDef`` and ``TestAtlasRelationshipType``'s invalid cases."""
    typedef = relationship("r", end1, end2, relationship_category=category)
    with pytest.raises(AtlasError) as raised:
        validate_relationship_def(typedef)

    assert raised.value.code is code
    assert failure(entity("t"), typedef).code is code


@pytest.mark.covers("aurelius_atlas_typesystem.types.EntityType.relationship_attribute", rules=["THY-09", "THY-10"])
def test__a_relationship_adds_attributes_to_its_ends() -> None:
    """New attributes hold the other end's type; a composition's container owns, its child must refer back."""
    registry = resolve(
        entity("table"),
        entity("column"),
        relationship(
            "table_columns",
            end("table", "columns", cardinality="SET", isContainer=True),
            end("column", "table"),
            relationship_category="COMPOSITION",
        ),
    )
    table, column = entity_type(registry, "table"), entity_type(registry, "column")
    columns = table.relationship_attribute("columns", "table_columns")
    back = column.relationship_attribute("table")

    assert relationship_type(registry, "table_columns").relationship_label == "r:table_columns"
    assert columns is not None
    assert back is not None
    assert (columns.attribute_def.type_name, columns.attribute_def.is_optional, columns.is_owned_ref) == (
        "array<column>",
        True,
        True,
    )
    assert isinstance(columns.attribute_type, ArrayType)
    assert columns.attribute_type.cardinality is Cardinality.SET
    assert (back.attribute_def.type_name, back.attribute_def.is_optional, back.is_owned_ref) == ("table", False, False)
    assert isinstance(back.attribute_type, ObjectIdType)
    assert (columns.relationship_name, columns.relationship_edge_label) == ("table_columns", "r:table_columns")
    assert (columns.relationship_edge_direction, back.relationship_edge_direction) == (
        EdgeDirection.OUT,
        EdgeDirection.IN,
    )
    assert [attribute.name for attribute in table.owned_ref_attributes] == ["columns"]
    assert table.relationship_attribute("missing") is None


@pytest.mark.covers(rules=["THY-09", "THY-10"])
def test__a_legacy_end_reuses_the_attribute_and_labels_the_edge() -> None:
    """A legacy end's existing attribute is reused; the label is ``__Type.attribute``; directions flip."""
    registry = resolve(
        entity("process", attributes=(attr("outputs", "array<dataset>"),)),
        entity("dataset"),
        relationship(
            "process_outputs",
            end("process", "outputs", cardinality="SET", isLegacyAttribute=True),
            end("dataset", "outputFrom", cardinality="SET"),
        ),
        relationship("dataset_owner", end("dataset", "owner"), end("process", "owned", isLegacyAttribute=True)),
        relationship(
            "both_legacy", end("dataset", "x", isLegacyAttribute=True), end("process", "y", isLegacyAttribute=True)
        ),
    )
    process, dataset = entity_type(registry, "process"), entity_type(registry, "dataset")
    outputs = process.relationship_attribute("outputs")
    output_from = dataset.relationship_attribute("outputFrom")
    owner = dataset.relationship_attribute("owner")
    owned = process.relationship_attribute("owned")
    x, y = dataset.relationship_attribute("x"), process.relationship_attribute("y")

    assert relationship_type(registry, "process_outputs").relationship_label == "__process.outputs"
    assert outputs is not None
    assert outputs is process.all_attributes["outputs"]
    assert outputs.is_legacy_attribute
    assert output_from is not None
    assert not output_from.is_legacy_attribute
    assert (outputs.relationship_edge_direction, output_from.relationship_edge_direction) == (
        EdgeDirection.OUT,
        EdgeDirection.IN,
    )
    assert owner is not None
    assert owned is not None
    assert (owner.relationship_edge_direction, owned.relationship_edge_direction) == (
        EdgeDirection.IN,
        EdgeDirection.OUT,
    )
    assert relationship_type(registry, "both_legacy").relationship_label is None
    assert x is not None
    assert y is not None
    assert (x.relationship_edge_label, y.relationship_edge_label) == ("__dataset.x", "__process.y")
    assert (x.relationship_edge_direction, y.relationship_edge_direction) == (EdgeDirection.OUT, EdgeDirection.OUT)


@pytest.mark.covers(rules=["THY-10"])
def test__a_relationship_from_a_type_to_itself_points_both_ways() -> None:
    """Both ends with the same type and name: one attribute, direction ``BOTH``."""
    registry = resolve(
        entity("term"),
        relationship(
            "term_synonyms", end("term", "synonyms", cardinality="SET"), end("term", "synonyms", cardinality="SET")
        ),
    )
    synonyms = entity_type(registry, "term").relationship_attribute("synonyms")

    assert synonyms is not None
    assert synonyms.relationship_edge_direction is EdgeDirection.BOTH


@pytest.mark.covers(rules=["THY-11"])
def test__relationship_attributes_are_inherited_and_written_back() -> None:
    """Sub types inherit; ``relationshipAttributeDefs`` carries the relationship's name and legacy flag."""
    registry = resolve(
        entity("asset", appendRelationshipsOnPartialUpdate='["tags"]'),
        entity("table", "asset"),
        entity("label"),
        relationship("asset_tags", end("asset", "tags", cardinality="SET"), end("label", "assets", cardinality="SET")),
    )
    table = entity_type(registry, "table")
    asset_def = entity_type(registry, "asset").entity_def

    assert table.relationship_attribute("tags", "asset_tags") is not None
    assert [
        (item.name, item.relationship_type_name, item.is_legacy_attribute)
        for item in asset_def.relationship_attribute_defs or []
    ] == [("tags", "asset_tags", False)]
    assert (asset_def.relationship_attribute_defs or [])[0].is_append_on_partial_update()
    assert table.entity_def.relationship_attribute_defs is not None
    assert not table.entity_def.relationship_attribute_defs[0].is_append_on_partial_update()
    assert (
        entity_type(registry, "label").entity_def.to_json()["relationshipAttributeDefs"][0]["typeName"]
        == "array<asset>"
    )


@pytest.mark.covers(rules=["THY-11"])
@pytest.mark.parametrize(
    ("propagation", "edges_on_1", "edges_on_2"),
    [
        (PropagateTags.NONE, [], []),
        (PropagateTags.ONE_TO_TWO, ["r:r"], []),
        (PropagateTags.TWO_TO_ONE, [], ["r:r"]),
        (PropagateTags.BOTH, ["r:r"], ["r:r"]),
        (None, [], []),
    ],
)
def test__tag_propagation_edges_follow_propagate_tags(
    propagation: PropagateTags | None, edges_on_1: list[str], edges_on_2: list[str]
) -> None:
    """``addRelationshipAttribute``: the label is an edge of the type that classifications propagate from."""
    registry = resolve(
        entity("one"),
        entity("two"),
        entity("sub", "one"),
        relationship("r", end("one", "b"), end("two", "a"), propagate_tags=propagation),
    )

    assert entity_type(registry, "one").tag_propagation_edges == edges_on_1
    assert entity_type(registry, "two").tag_propagation_edges == edges_on_2
    assert entity_type(registry, "sub").tag_propagation_edges == edges_on_1


@pytest.mark.covers(
    "aurelius_atlas_typesystem.types.EntityType.business_attribute",
    "aurelius_atlas_typesystem.types.AtlasAttribute.option_set",
    "aurelius_atlas_typesystem.types.AtlasAttribute.option_int",
    "aurelius_atlas_typesystem.types.AtlasAttribute.option_string",
    rules=["THY-12"],
)
def test__business_attributes_apply_to_their_entity_types_and_sub_types() -> None:
    """``AtlasBusinessMetadataType``: applicable entity types, ``bm.attribute`` lookup, ``businessAttributeDefs``."""
    registry = resolve(
        entity("table"),
        entity("view", "table"),
        entity("other"),
        AtlasBusinessMetadataDef(
            name="bm",
            attribute_defs=[
                attr(
                    "owner",
                    options={"applicableEntityTypes": '["table"]', "maxStrLength": "50", "validPattern": "[a-z]+"},
                ),
                attr("rank", "int", options={"applicableEntityTypes": '["table"]'}),
                attr("ref", "table"),
            ],
        ),
    )
    view = entity_type(registry, "view")
    owner = view.business_attribute("bm", "owner")

    assert isinstance(owner, BusinessAttribute)
    assert (owner.max_string_length, owner.valid_pattern) == (50, "[a-z]+")
    assert [type_.type_name for type_ in owner.applicable_entity_types] == ["table"]
    assert view.attribute("bm.rank") is view.business_attribute("bm", "rank")
    assert view.attribute("bm") is None
    assert entity_type(registry, "other").business_attribute("bm", "owner") is None
    business_defs = entity_type(registry, "table").entity_def.business_attribute_defs
    assert business_defs is not None
    assert [item.name for item in business_defs["bm"]] == ["owner", "rank"]


@pytest.mark.covers(rules=["THY-12"])
@pytest.mark.parametrize(
    ("attribute", "code"),
    [
        (attr("s", "s"), AtlasErrorCode.BUSINESS_METADATA_DEF_ATTRIBUTE_TYPE_INVALID),
        (attr("s", "array<s>"), AtlasErrorCode.BUSINESS_METADATA_DEF_ATTRIBUTE_TYPE_INVALID),
        (attr("n", options={"maxStrLength": " "}), AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE),
        (attr("n", "array<string>"), AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE),
        (attr("n", "int", options={"applicableEntityTypes": '["missing"]'}), AtlasErrorCode.TYPE_NAME_NOT_FOUND),
    ],
    ids=["struct", "array-of-struct", "no-max-length", "string-array", "unknown-entity-type"],
)
def test__business_attributes_are_checked(attribute: AtlasAttributeDef, code: AtlasErrorCode) -> None:
    """The checks of ``AtlasBusinessMetadataType.resolveReferences``."""
    error = failure(AtlasStructDef(name="s"), AtlasBusinessMetadataDef(name="bm", attribute_defs=[attribute]))

    assert error.code is code
    if code is AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE:
        assert error.message == "Mandatory field n.options.maxStrLength has empty/null value"


@pytest.mark.covers(rules=["THY-12"])
def test__malformed_applicable_entity_types_apply_nowhere() -> None:
    """``AtlasType.fromJson`` returns null for malformed JSON, so the attribute applies to no entity type."""
    registry = resolve(
        entity("t"),
        AtlasBusinessMetadataDef(
            name="bm", attribute_defs=[attr("n", "int", options={"applicableEntityTypes": "not json"})]
        ),
    )

    assert entity_type(registry, "t").business_attributes == {}


@pytest.mark.covers(rules=["THY-04", "THY-11", "THY-12"])
def test__atlas_base_and_glossary_models_resolve() -> None:
    """Atlas's own ``addons/models`` files resolve in full, with Atlas's well-known hierarchy."""
    registry = TypeRegistry()
    with registry.update() as transient:
        for name in ("0010-base_model.json", "0011-glossary_model.json"):
            transient.add_types(AtlasTypesDef.model_validate(json.loads((FIXTURES / name).read_text())))
    dataset, process = entity_type(registry, "DataSet"), entity_type(registry, "Process")

    assert dataset.all_super_types == ["Referenceable", "Asset"]
    assert "Asset" in entity_type(registry, "Referenceable").sub_types
    assert process.relationship_attribute("inputs", "dataset_process_inputs") is not None
    assert process.relationship_attribute("meanings", "AtlasGlossarySemanticAssignment") is not None
    assert list(dataset.header_attributes) == ["qualifiedName", "name", "description", "owner"]
    assert dataset.entity_def.to_json()["subTypes"] == ["Path"]
