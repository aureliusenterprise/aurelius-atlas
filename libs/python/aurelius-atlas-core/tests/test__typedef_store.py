"""The typedef store on an in-memory document (TDS-01 to TDS-12).

Read from ``AtlasTypeDefGraphStore`` and the def stores of Apache Atlas 2.4.0 and its test
``AtlasTypeDefGraphStoreTest`` (``testCreateDuplicateType``, ``testDeleteTypeWithReferences``, …).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore, is_valid_name, never_in_use, rectify, referenced_type_names
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
    AtlasRelationshipEndDef,
    AtlasStructDef,
    AtlasTypesDef,
    Cardinality,
    RelationshipCategory,
    TypeCategory,
)
from aurelius_atlas_typesystem.registry import TypeRegistry

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


@pytest.fixture
def document() -> MemoryTypedefDocument:
    """An empty in-memory document."""
    return MemoryTypedefDocument()


@pytest.fixture
async def store(document: MemoryTypedefDocument) -> TypedefStore:
    """A loaded store on ``document``, with a fixed clock."""
    store = TypedefStore(TypeRegistry(), document, now=lambda: NOW)
    await store.load()
    return store


def attr(name: str, type_name: str = "string", **fields: object) -> AtlasAttributeDef:
    """An attribute definition."""
    return AtlasAttributeDef.model_validate({"name": name, "type_name": type_name, **fields})


def types(*typedefs: AtlasEnumDef | AtlasStructDef) -> AtlasTypesDef:
    """An ``AtlasTypesDef`` with ``typedefs`` in the lists of their kinds."""
    by_kind: dict[str, list[object]] = {}
    field = {
        TypeCategory.ENUM: "enum_defs",
        TypeCategory.STRUCT: "struct_defs",
        TypeCategory.CLASSIFICATION: "classification_defs",
        TypeCategory.ENTITY: "entity_defs",
        TypeCategory.RELATIONSHIP: "relationship_defs",
        TypeCategory.BUSINESS_METADATA: "business_metadata_defs",
    }
    for typedef in typedefs:
        by_kind.setdefault(field[typedef.category], []).append(typedef)
    return AtlasTypesDef.model_validate(by_kind)


def enum(name: str, *values: str) -> AtlasEnumDef:
    """An enum with ``values`` as ordinals 1, 2, …."""
    return AtlasEnumDef(
        name=name, element_defs=[AtlasEnumElementDef(value=v, ordinal=i) for i, v in enumerate(values, 1)]
    )


async def failure(coroutine: object) -> AtlasError:
    """The ``AtlasError`` an awaited store call raises."""
    with pytest.raises(AtlasError) as raised:
        await coroutine  # type: ignore[misc]
    return raised.value


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_store.TypedefStore.load",
    "aurelius_atlas_core.typedef_store.TypedefStore.create_types_def",
    rules=["TDS-01", "TDS-10", "TDS-12"],
)
async def test__created_types_are_stored_once_and_reach_the_registry(
    store: TypedefStore, document: MemoryTypedefDocument
) -> None:
    """``createTypesDef``: one write for the whole request; the registry commits after it."""
    created = await store.create_types_def(
        types(enum("colour", "RED"), AtlasEntityDef(name="paint", attribute_defs=[attr("colour", "colour")]))
    )

    assert [typedef.name for typedef in created.enum_defs or []] == ["colour"]
    assert [typedef.name for typedef in created.entity_defs or []] == ["paint"]
    assert document.writes == 1
    assert document.prepared
    assert store.registry.entity_type("paint") is not None


@pytest.mark.covers(rules=["TDS-01"])
async def test__an_unknown_type_name_is_a_bad_request(store: TypedefStore, document: MemoryTypedefDocument) -> None:
    """``tryTypeCreation`` maps ``TYPE_NAME_NOT_FOUND`` to ``BAD_REQUEST`` with the same message."""
    error = await failure(
        store.create_types_def(types(AtlasEntityDef(name="t", attribute_defs=[attr("a", "missing")])))
    )

    assert (error.code, error.message) == (AtlasErrorCode.BAD_REQUEST, "Given typename missing was invalid")
    assert document.writes == 0
    assert store.registry.entity_type("t") is None


@pytest.mark.covers("aurelius_atlas_core.typedef_store.is_valid_name", rules=["TDS-02"])
@pytest.mark.parametrize(
    ("name", "valid"),
    [
        ("hive_table", True),
        ("A b_1", True),
        ("__internal", True),
        ("1abc", False),
        ("a-b", False),
        ("_x", False),
        (None, False),
    ],
)
def test__type_names_follow_atlas_pattern(name: str | None, valid: bool) -> None:  # noqa: FBT001
    """``NAME_REGEX`` and ``INTERNAL_NAME_REGEX`` of ``AtlasAbstractDefStoreV2``."""
    assert is_valid_name(name) is valid


@pytest.mark.covers(rules=["TDS-02"])
async def test__names_must_be_valid_new_and_of_one_kind(store: TypedefStore) -> None:
    """``TYPE_NAME_INVALID_FORMAT``, ``TYPE_ALREADY_EXISTS`` (409) and ``TYPE_MATCH_FAILED`` with the legacy kind."""
    await store.create_types_def(types(AtlasEntityDef(name="t")))

    invalid = await failure(store.create_types_def(types(AtlasEntityDef(name="bad-name"))))
    exists = await failure(store.create_types_def(types(AtlasEntityDef(name="t"))))
    mismatch = await failure(
        store.create_types_def(types(AtlasStructDef(name="x", attribute_defs=[attr("a")]), AtlasEntityDef(name="x")))
    )

    assert invalid.code is AtlasErrorCode.TYPE_NAME_INVALID_FORMAT
    assert invalid.message.startswith("bad-name: invalid name for ENTITY.  Names must consist of a letter")
    assert invalid.message.endswith("space, or _ characters")
    assert (exists.code, exists.code.http_status, exists.message) == (
        AtlasErrorCode.TYPE_ALREADY_EXISTS,
        409,
        "Given type t already exists",
    )
    assert (mismatch.code, mismatch.message) == (AtlasErrorCode.TYPE_MATCH_FAILED, "Given type x doesnt match {1}")


@pytest.mark.covers(rules=["TDS-02"])
async def test__a_business_metadata_attribute_needs_a_valid_name(store: TypedefStore) -> None:
    """``ATTRIBUTE_NAME_INVALID_CHARS`` from ``AtlasBusinessMetadataDefStoreV2.validateType``."""
    error = await failure(
        store.create_types_def(types(AtlasBusinessMetadataDef(name="bm", attribute_defs=[attr("bad name!", "int")])))
    )

    assert error.code is AtlasErrorCode.ATTRIBUTE_NAME_INVALID_CHARS


@pytest.mark.covers(rules=["TDS-03"])
async def test__a_created_definition_gets_its_audit_fields(store: TypedefStore) -> None:
    """``createTypeVertex``: type version, version, GUID, times; the description defaults to the name."""
    created = await store.create_types_def(
        types(AtlasEntityDef(name="t"), AtlasEntityDef(name="u", guid="g-u", type_version="2.0", description="given"))
    )
    t, u = created.entity_defs or []

    assert (t.type_version, t.version, t.create_time, t.update_time, t.description) == ("1.0", 1, NOW, NOW, "t")
    assert t.guid is not None
    assert len(t.guid) == 36
    assert (u.guid, u.type_version, u.description) == ("g-u", "2.0", "given")
    assert (t.created_by, t.updated_by) == (None, None)


@pytest.mark.covers(rules=["TDS-04"])
@pytest.mark.parametrize(
    ("typedef", "code", "message"),
    [
        (AtlasStructDef(name="s"), AtlasErrorCode.BAD_REQUEST, "Missing attributes for structdef"),
        (
            AtlasEnumDef(name="e"),
            AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE,
            "Mandatory field e.values has empty/null value",
        ),
        (
            AtlasEnumDef(name="e", element_defs=[AtlasEnumElementDef(value="A")]),
            AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE,
            "Mandatory field e.elementValue has empty/null value",
        ),
    ],
    ids=["struct-without-attributes", "enum-without-elements", "element-without-ordinal"],
)
async def test__structs_need_attributes_and_enums_elements(
    store: TypedefStore, typedef: AtlasStructDef | AtlasEnumDef, code: AtlasErrorCode, message: str
) -> None:
    """``AtlasStructDefStoreV2.create`` and ``AtlasEnumDefStoreV2.toVertex``."""
    error = await failure(store.create_types_def(types(typedef)))

    assert (error.code, error.message) == (code, message)


@pytest.mark.covers("aurelius_atlas_core.typedef_store.referenced_type_names", rules=["TDS-04"])
def test__referenced_type_names_look_inside_arrays_and_maps() -> None:
    """``AtlasTypeUtil.getReferencedTypeNames``."""
    assert referenced_type_names("map<string,array<table>>") == ["string", "table"]
    assert referenced_type_names("column") == ["column"]
    assert referenced_type_names(None) == []


@pytest.mark.covers(rules=["TDS-05"])
async def test__attributes_are_stored_in_atlas_form(store: TypedefStore) -> None:
    """``toJsonFromAttribute`` then ``toAttributeDefFromJson``: multiplicity decides counts and cardinality."""
    created = await store.create_types_def(
        types(
            AtlasEntityDef(name="part"),
            AtlasEntityDef(
                name="t",
                attribute_defs=[
                    attr("optional", is_optional=True),
                    attr("required", is_optional=False),
                    attr("tags", "array<string>", cardinality="SET", is_optional=True),
                    attr(
                        "bounded",
                        "array<string>",
                        cardinality="LIST",
                        is_optional=False,
                        values_min_count=2,
                        values_max_count=5,
                    ),
                    attr(
                        "parts",
                        "array<part>",
                        cardinality="SET",
                        constraints=[AtlasConstraintDef(type="ownedRef"), AtlasConstraintDef(type="custom")],
                    ),
                    attr(
                        "weighted",
                        is_optional=True,
                        options={"k": "v"},
                        search_weight=7,
                        display_name="W",
                        default_value="d",
                    ),
                ],
            ),
        )
    )
    stored = {a.name: a for a in (created.entity_defs or [])[1].attribute_defs}

    assert (
        stored["optional"].is_optional,
        stored["optional"].values_min_count,
        stored["optional"].values_max_count,
    ) == (True, 0, 1)
    assert (stored["required"].values_min_count, stored["required"].values_max_count) == (1, 1)
    assert (stored["tags"].cardinality, stored["tags"].values_max_count) == ("SET", 2147483647)
    assert (stored["bounded"].cardinality, stored["bounded"].values_min_count, stored["bounded"].values_max_count) == (
        "LIST",
        2,
        5,
    )
    assert [c.type for c in stored["parts"].constraints or []] == ["ownedRef"]
    weighted = stored["weighted"]
    assert (weighted.options, weighted.search_weight, weighted.display_name, weighted.default_value) == (
        {"k": "v"},
        7,
        "W",
        "d",
    )


@pytest.mark.covers(rules=["TDS-06"])
async def test__a_stored_relationship_gets_atlas_defaults(store: TypedefStore) -> None:
    """``setVertexPropertiesFromRelationshipDef``: category ``ASSOCIATION``, ``propagateTags`` ``NONE``."""
    created = await store.create_types_def(
        types(
            AtlasEntityDef(name="a"),
            AtlasRelationshipDef(
                name="r",
                relationship_label="label",
                end_def1=AtlasRelationshipEndDef(type="a", name="x"),
                end_def2=AtlasRelationshipEndDef(type="a", name="y"),
            ),
        )
    )
    relationship = (created.relationship_defs or [])[0]

    assert (relationship.relationship_category, relationship.propagate_tags, relationship.relationship_label) == (
        "ASSOCIATION",
        "NONE",
        "label",
    )


@pytest.mark.covers("aurelius_atlas_core.typedef_store.TypedefStore.update_types_def", rules=["TDS-07"])
async def test__an_update_keeps_name_and_creation_and_bumps_the_version(store: TypedefStore) -> None:
    """``updateTypeVertex`` keeps blank fields; ``markVertexUpdated`` bumps the version."""
    created = await store.create_types_def(
        types(AtlasEntityDef(name="t", description="first", service_type="svc", attribute_defs=[attr("a")]))
    )
    guid = (created.entity_defs or [])[0].guid
    later = datetime(2026, 10, 19, tzinfo=UTC)
    store._now = lambda: later  # noqa: SLF001 - the clock of this test

    updated = await store.update_types_def(
        types(AtlasEntityDef(name="t", description=" ", attribute_defs=[attr("a"), attr("b", is_optional=True)]))
    )
    t = (updated.entity_defs or [])[0]

    assert (t.guid, t.description, t.service_type, t.version) == (guid, "first", "svc", 2)
    assert (t.create_time, t.update_time) == (NOW, later)
    assert [a.name for a in t.attribute_defs] == ["a", "b"]


@pytest.mark.covers(rules=["TDS-07"])
async def test__an_update_of_an_unknown_type_fails(store: TypedefStore) -> None:
    """The def store answers 404; a type name the resolution cannot find becomes ``BAD_REQUEST``."""
    by_name = await failure(store.update_types_def(types(AtlasEntityDef(name="missing"))))
    by_guid = await failure(store.update_types_def(types(AtlasEntityDef(name="missing", guid="g-x"))))

    assert (by_name.code, by_name.code.http_status) == (AtlasErrorCode.TYPE_NAME_NOT_FOUND, 404)
    assert by_guid.code is AtlasErrorCode.TYPE_GUID_NOT_FOUND
    bad_attribute = await failure(
        store.update_types_def(types(AtlasEntityDef(name="missing", attribute_defs=[attr("a", "nothing")])))
    )
    assert bad_attribute.code is AtlasErrorCode.BAD_REQUEST


@pytest.mark.covers(rules=["TDS-08"])
@pytest.mark.parametrize(
    ("update", "code"),
    [
        (AtlasEntityDef(name="t", attribute_defs=[]), AtlasErrorCode.ATTRIBUTE_DELETION_NOT_SUPPORTED),
        (
            AtlasEntityDef(name="t", attribute_defs=[AtlasAttributeDef(name="a", type_name="int")]),
            AtlasErrorCode.BAD_REQUEST,
        ),
        (
            AtlasEntityDef(name="t", attribute_defs=[attr("a"), attr("b", is_optional=False)]),
            AtlasErrorCode.CANNOT_ADD_MANDATORY_ATTRIBUTE,
        ),
        (
            AtlasEntityDef(name="t", attribute_defs=[attr("a")], super_types=[]),
            AtlasErrorCode.SUPERTYPE_REMOVAL_NOT_SUPPORTED,
        ),
    ],
    ids=["remove-attribute", "retype-attribute", "add-mandatory", "remove-super-type"],
)
async def test__an_update_may_not_take_away(store: TypedefStore, update: AtlasEntityDef, code: AtlasErrorCode) -> None:
    """``updateVertexPreUpdate`` and ``createSuperTypeEdges``."""
    await store.create_types_def(
        types(AtlasEntityDef(name="base"), AtlasEntityDef(name="t", super_types=["base"], attribute_defs=[attr("a")]))
    )
    if code is not AtlasErrorCode.SUPERTYPE_REMOVAL_NOT_SUPPORTED:
        update.super_types = ["base"]

    assert (await failure(store.update_types_def(types(update)))).code is code


@pytest.mark.covers(rules=["TDS-08"])
async def test__a_relationship_keeps_its_category_and_ends(store: TypedefStore) -> None:
    """``preUpdateCheck``, with Java's text of the ends."""
    end1, end2 = AtlasRelationshipEndDef(type="a", name="x"), AtlasRelationshipEndDef(type="a", name="y")
    await store.create_types_def(
        types(AtlasEntityDef(name="a"), AtlasRelationshipDef(name="r", end_def1=end1, end_def2=end2))
    )

    category = await failure(
        store.update_types_def(
            types(
                AtlasRelationshipDef(
                    name="r",
                    relationship_category=RelationshipCategory.AGGREGATION,
                    end_def1=end1.model_copy(update={"is_container": True}),
                    end_def2=end2,
                )
            )
        )
    )
    ends = await failure(
        store.update_types_def(
            types(
                AtlasRelationshipDef(
                    name="r",
                    relationship_category=RelationshipCategory.ASSOCIATION,
                    end_def1=AtlasRelationshipEndDef(type="a", name="z"),
                    end_def2=end2,
                )
            )
        )
    )

    assert category.code is AtlasErrorCode.RELATIONSHIPDEF_INVALID_CATEGORY_UPDATE
    assert (
        category.message
        == "invalid  update for relationship r: new relationshipDef category AGGREGATION, existing relationshipDef "
        "category ASSOCIATION"
    )
    assert ends.code is AtlasErrorCode.RELATIONSHIPDEF_INVALID_END1_UPDATE
    assert ends.message == (
        "invalid update for relationshipDef r: new end1 AtlasRelationshipEndDef{type='a', name==>'z', "
        "description==>'null', isContainer==>'false', cardinality==>'SINGLE', isLegacyAttribute==>'false'}, "
        "existing end1 AtlasRelationshipEndDef{type='a', name==>'x', description==>'null', isContainer==>'false', "
        "cardinality==>'SINGLE', isLegacyAttribute==>'false'}"
    )


@pytest.mark.covers(rules=["TDS-08"])
async def test__classification_entity_types_and_business_metadata_applicability_may_only_grow(
    store: TypedefStore,
) -> None:
    """``createEntityTypeEdges`` and ``AtlasBusinessMetadataDefStoreV2.updateVertexPreUpdate``."""
    applies = {"applicableEntityTypes": '["a", "b"]', "maxStrLength": "10"}
    await store.create_types_def(
        types(
            AtlasEntityDef(name="a"),
            AtlasEntityDef(name="b"),
            AtlasClassificationDef(name="c", entity_types=["a", "b"]),
            AtlasBusinessMetadataDef(name="bm", attribute_defs=[attr("n", options=applies)]),
        )
    )

    fewer = await failure(store.update_types_def(types(AtlasClassificationDef(name="c", entity_types=["a"]))))
    unknown = await failure(
        store.update_types_def(types(AtlasClassificationDef(name="c", entity_types=["a", "b", "zzz"])))
    )
    narrowed = await failure(
        store.update_types_def(
            types(
                AtlasBusinessMetadataDef(
                    name="bm",
                    attribute_defs=[attr("n", options={"applicableEntityTypes": '["a"]', "maxStrLength": "10"})],
                )
            )
        )
    )
    cleared = await store.update_types_def(types(AtlasClassificationDef(name="c", entity_types=[])))

    assert fewer.code is AtlasErrorCode.ENTITYTYPE_REMOVAL_NOT_SUPPORTED
    assert unknown.code is AtlasErrorCode.BAD_REQUEST
    assert narrowed.code is AtlasErrorCode.APPLICABLE_ENTITY_TYPES_DELETION_NOT_SUPPORTED
    assert (cleared.classification_defs or [])[0].entity_types == []


@pytest.mark.covers(rules=["TDS-08"])
async def test__a_classification_needs_stored_entity_types(store: TypedefStore) -> None:
    """``CLASSIFICATIONDEF_INVALID_ENTITYTYPES`` when an entity type exists only as another kind."""
    error = await failure(
        store.create_types_def(
            types(
                AtlasStructDef(name="s", attribute_defs=[attr("a")]),
                AtlasClassificationDef(name="c", entity_types=["s"]),
            )
        )
    )

    assert error.code in {AtlasErrorCode.CLASSIFICATIONDEF_INVALID_ENTITYTYPES, AtlasErrorCode.BAD_REQUEST}


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_store.TypedefStore.delete_types_def",
    "aurelius_atlas_core.typedef_store.TypedefStore.delete_type_by_name",
    rules=["TDS-09"],
)
async def test__a_referred_type_may_not_be_deleted(store: TypedefStore) -> None:
    """``deleteTypeVertex`` and ``TYPE_HAS_RELATIONSHIPS``; deleting the referrer with it is allowed."""
    await store.create_types_def(
        types(
            enum("colour", "RED"),
            AtlasEntityDef(name="paint", attribute_defs=[attr("colour", "colour")]),
            AtlasEntityDef(name="can"),
            AtlasRelationshipDef(
                name="r",
                end_def1=AtlasRelationshipEndDef(type="can", name="paints", cardinality=Cardinality.SET),
                end_def2=AtlasRelationshipEndDef(type="paint", name="can"),
            ),
        )
    )

    referred = await failure(store.delete_type_by_name("colour"))
    related = await failure(store.delete_type_by_name("can"))
    await store.delete_types_def(
        types(AtlasEntityDef(name="can"), AtlasEntityDef(name="paint"), AtlasRelationshipDef(name="r"))
    )
    await store.delete_type_by_name("colour")

    assert (referred.code, referred.code.http_status, referred.message) == (
        AtlasErrorCode.TYPE_HAS_REFERENCES,
        409,
        "Given type colour has references",
    )
    assert (related.code, related.message) == (
        AtlasErrorCode.TYPE_HAS_RELATIONSHIPS,
        "Given type can has associated relationshipDefs",
    )
    assert store.registry.typedef_names(TypeCategory.ENTITY) == []
    assert store.registry.typedef_names(TypeCategory.ENUM) == []


@pytest.mark.covers("aurelius_atlas_core.typedef_store.never_in_use", rules=["TDS-09"])
async def test__a_type_in_use_may_not_be_deleted(document: MemoryTypedefDocument) -> None:
    """``typeHasInstanceVertex`` through the ``TypeUsage`` callback (DD-030); by default nothing is in use."""

    async def used(type_name: str) -> bool:
        return type_name == "t"

    store = TypedefStore(TypeRegistry(), document, usage=used)
    await store.load()
    await store.create_types_def(types(AtlasEntityDef(name="t")))

    assert (await failure(store.delete_type_by_name("t"))).code is AtlasErrorCode.TYPE_HAS_REFERENCES
    assert not await never_in_use("t")


@pytest.mark.covers("aurelius_atlas_core.typedef_store.TypedefStore.delete_type_by_name", rules=["TDS-09"])
@pytest.mark.parametrize(
    ("name", "code"),
    [
        (" ", AtlasErrorCode.TYPE_NAME_INVALID),
        ("missing", AtlasErrorCode.TYPE_NAME_NOT_FOUND),
        ("string", AtlasErrorCode.SYSTEM_TYPE),
    ],
)
async def test__deleting_by_name_needs_a_defined_type(store: TypedefStore, name: str, code: AtlasErrorCode) -> None:
    """``deleteTypeByName`` and ``getTypeDefFromTypeWithNoAuthz``."""
    assert (await failure(store.delete_type_by_name(name))).code is code


@pytest.mark.covers(rules=["TDS-09"])
async def test__deleting_an_unknown_definition_fails(store: TypedefStore) -> None:
    """``preDeleteByName`` and ``preDeleteByGuid``."""
    by_name = await failure(store.delete_types_def(types(AtlasStructDef(name="missing"))))
    by_guid = await failure(store.delete_types_def(types(AtlasEnumDef(name="missing", guid="g-1"))))

    assert (by_name.code, by_guid.code) == (AtlasErrorCode.TYPE_NAME_NOT_FOUND, AtlasErrorCode.TYPE_GUID_NOT_FOUND)


@pytest.mark.covers(rules=["TDS-10"])
async def test__a_failed_write_commits_nothing(store: TypedefStore, document: MemoryTypedefDocument) -> None:
    """The registry commits only after the document was written."""
    document.fail_next_write = OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        await store.create_types_def(types(AtlasEntityDef(name="t")))

    assert store.registry.entity_type("t") is None
    assert document.json is None


@pytest.mark.covers(rules=["TDS-11"])
async def test__a_conflict_is_retried_once_on_the_new_definitions(
    store: TypedefStore, document: MemoryTypedefDocument
) -> None:
    """DD-029: reload, apply again, write; a second conflict gives up."""
    other = TypedefStore(TypeRegistry(), document)
    await other.load()
    await other.create_types_def(types(AtlasEntityDef(name="fromOther")))
    document.conflicts = 1

    await store.create_types_def(types(AtlasEntityDef(name="mine")))
    document.conflicts = 2
    error = await failure(store.create_types_def(types(AtlasEntityDef(name="later"))))

    assert sorted(store.registry.typedef_names(TypeCategory.ENTITY)) == ["fromOther", "mine"]
    assert (error.code, error.code.http_status) == (AtlasErrorCode.FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK, 500)


@pytest.mark.covers("aurelius_atlas_core.typedef_store.rectify", rules=["TDS-12"])
def test__loading_repairs_duplicates_and_owned_references_to_no_entity() -> None:
    """``rectifyTypeErrorsIfAny``: the first definition with a name stays; a bad ``ownedRef`` goes."""
    owned = [AtlasConstraintDef(type="ownedRef")]
    repaired = rectify(
        types(
            AtlasEntityDef(
                name="t",
                description="first",
                attribute_defs=[attr("ok", "array<t>", constraints=owned), attr("bad", "string", constraints=owned)],
            ),
            AtlasEntityDef(name="t", description="second"),
        )
    )
    (entity,) = repaired.entity_defs or []

    assert entity.description == "first"
    assert [a.constraints for a in entity.attribute_defs] == [owned, None]


@pytest.mark.covers("aurelius_atlas_core.typedef_store.TypedefStore.load", rules=["TDS-12"])
async def test__loading_reads_what_another_store_stored(document: MemoryTypedefDocument) -> None:
    """``init``: a new process sees every stored definition; with nothing stored, only the built-in types."""
    empty = TypedefStore(TypeRegistry(), document)
    await empty.load()
    await empty.create_types_def(
        AtlasTypesDef.model_validate(json.loads((FIXTURES / "0010-base_model.json").read_text()))
    )

    fresh = TypedefStore(TypeRegistry(), document)
    await fresh.load()

    assert TypeRegistry().typedef_names(TypeCategory.ENTITY) == []
    assert len(fresh.registry.typedef_names(TypeCategory.ENTITY)) == 15
    dataset = fresh.registry.entity_type("DataSet")
    assert dataset is not None
    assert dataset.all_super_types == ["Referenceable", "Asset"]


@pytest.mark.covers("aurelius_atlas_core.typedef_store.TypedefStore.refresh", rules=["TDS-13"])
async def test__a_reader_reloads_after_the_refresh_interval(document: MemoryTypedefDocument) -> None:
    """DD-029: the stored version is checked at most every interval; a change is reloaded."""
    tick = [0.0]
    reader = TypedefStore(TypeRegistry(), document, refresh_seconds=5.0, clock=lambda: tick[0])
    writer = TypedefStore(TypeRegistry(), document)
    await reader.load()
    await writer.load()
    await writer.create_types_def(types(AtlasEntityDef(name="t")))

    assert not await reader.refresh()
    tick[0] = 6.0
    assert await reader.refresh()
    assert reader.registry.entity_type("t") is not None
    assert not await reader.refresh(force=True)


@pytest.mark.covers(rules=["TDS-01", "TDS-07"])
async def test__other_resolution_errors_pass_through(store: TypedefStore) -> None:
    """Only not-found errors become ``BAD_REQUEST``; a circular hierarchy stays ``CIRCULAR_REFERENCE``."""
    created = await failure(store.create_types_def(types(AtlasEntityDef(name="a", super_types=["a"]))))
    await store.create_types_def(types(AtlasEntityDef(name="b")))
    updated = await failure(store.update_types_def(types(AtlasEntityDef(name="b", super_types=["b"]))))

    assert created.code is AtlasErrorCode.CIRCULAR_REFERENCE
    assert updated.code is AtlasErrorCode.CIRCULAR_REFERENCE


@pytest.mark.covers(rules=["TDS-07"])
async def test__structs_and_enums_are_updated_and_deleted(store: TypedefStore) -> None:
    """Enum elements are replaced on update; a struct is found, updated and deleted like any kind."""
    await store.create_types_def(types(enum("e", "A"), AtlasStructDef(name="s", attribute_defs=[attr("a")])))

    updated = await store.update_types_def(
        types(enum("e", "A", "B"), AtlasStructDef(name="s", attribute_defs=[attr("a"), attr("b", is_optional=True)]))
    )
    await store.delete_type_by_name("s")

    assert [e.value for e in (updated.enum_defs or [])[0].element_defs] == ["A", "B"]
    assert [a.name for a in (updated.struct_defs or [])[0].attribute_defs] == ["a", "b"]
    assert store.registry.struct_type("s") is None


@pytest.mark.covers(rules=["TDS-08"])
async def test__an_added_legacy_relationship_end_is_not_stored_as_an_attribute(store: TypedefStore) -> None:
    """``updateVertexPreUpdate`` skips a new attribute that a relationship's legacy end provides."""
    await store.create_types_def(
        types(
            AtlasEntityDef(name="a"),
            AtlasEntityDef(name="b"),
            AtlasRelationshipDef(
                name="r",
                end_def1=AtlasRelationshipEndDef(type="a", name="bs", is_legacy_attribute=True),
                end_def2=AtlasRelationshipEndDef(type="b", name="a"),
            ),
        )
    )

    updated = await store.update_types_def(types(AtlasEntityDef(name="a", attribute_defs=[attr("bs", "b")])))

    assert (updated.entity_defs or [])[0].attribute_defs == []


@pytest.mark.covers(rules=["TDS-08"])
async def test__a_relationship_may_not_be_renamed(store: TypedefStore) -> None:
    """``RELATIONSHIPDEF_INVALID_NAME_UPDATE``; Java passes the existing name as the new one, and the reverse."""
    end1, end2 = AtlasRelationshipEndDef(type="a", name="x"), AtlasRelationshipEndDef(type="a", name="y")
    created = await store.create_types_def(
        types(AtlasEntityDef(name="a"), AtlasRelationshipDef(name="r", end_def1=end1, end_def2=end2))
    )
    guid = (created.relationship_defs or [])[0].guid

    error = await failure(
        store.update_types_def(types(AtlasRelationshipDef(name="other", guid=guid, end_def1=end1, end_def2=end2)))
    )

    assert (error.code, error.message) == (
        AtlasErrorCode.RELATIONSHIPDEF_INVALID_NAME_UPDATE,
        f"invalid relationshipDef rename for relationship guid {guid}: new name r, existing name other",
    )


@pytest.mark.covers(rules=["TDS-08"])
@pytest.mark.parametrize("option", [None, " ", "not json", '{"a": 1}'])
async def test__applicable_entity_types_that_are_not_a_list_are_none(store: TypedefStore, option: str | None) -> None:
    """``AtlasType.fromJson`` gives null for a blank, malformed or non-list option: nothing to keep."""
    options = {"maxStrLength": "5"} | ({} if option is None else {"applicableEntityTypes": option})
    await store.create_types_def(
        types(AtlasBusinessMetadataDef(name="bm", attribute_defs=[attr("n", options=options)]))
    )

    updated = await store.update_types_def(
        types(AtlasBusinessMetadataDef(name="bm", attribute_defs=[attr("n", options={"maxStrLength": "5"})]))
    )

    assert [a.name for a in (updated.business_metadata_defs or [])[0].attribute_defs] == ["n"]


@pytest.mark.covers(rules=["TDS-09"])
async def test__an_entity_type_a_classification_applies_to_is_referred(store: TypedefStore) -> None:
    """The classification's entity-type edge is a reference."""
    await store.create_types_def(types(AtlasEntityDef(name="t"), AtlasClassificationDef(name="c", entity_types=["t"])))

    assert (await failure(store.delete_type_by_name("t"))).code is AtlasErrorCode.TYPE_HAS_REFERENCES
