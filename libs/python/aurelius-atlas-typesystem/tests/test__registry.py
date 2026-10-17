"""The type registry and its transient copy (TRG-01 to TRG-09).

Read from ``AtlasTypeRegistry`` of Apache Atlas 2.4.0 and its test ``TestAtlasTypeRegistry``
(``testNestedUpdates``, ``testParallelUpdates``, ``testRegistryValidityOnInvalidUpdate``).
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
    AtlasTypesDef,
    Cardinality,
    TypeCategory,
)
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.types import (
    ArrayType,
    BuiltInType,
    BusinessMetadataType,
    ClassificationType,
    EntityType,
    EnumType,
    MapType,
    ObjectIdType,
    RelationshipType,
    StructType,
)

END = AtlasRelationshipEndDef(type="t", name="self")
"""A relationship end on entity type ``t``."""

BUILT_IN = ["boolean", "byte", "short", "int", "long", "float", "double", "biginteger", "bigdecimal", "date", "string"]


def registry_with(*typedefs: AtlasEnumDef | AtlasStructDef) -> TypeRegistry:
    """A registry with ``typedefs`` added and committed."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(list(typedefs))
    return registry


@pytest.mark.covers(
    "aurelius_atlas_typesystem.registry.TypeRegistry.all_type_names",
    "aurelius_atlas_typesystem.registry.TypeRegistry.all_types",
    "aurelius_atlas_typesystem.registry.TypeRegistry.all_service_types",
    "aurelius_atlas_typesystem.registry.TypeRegistry.is_registered",
    rules=["TRG-01", "TRG-04"],
)
def test__a_new_registry_holds_the_built_in_types() -> None:
    """``RegistryData.init()`` registers the eleven primitives and ``objectid``, all ``atlas_core``."""
    registry = TypeRegistry()

    assert sorted(registry.all_type_names()) == sorted([*BUILT_IN, "objectid"])
    for type_ in registry.all_types():
        expected = TypeCategory.OBJECT_ID_TYPE if type_.type_name == "objectid" else TypeCategory.PRIMITIVE
        assert (type_.category, type_.service_type) == (expected, "atlas_core")
    assert registry.all_service_types() == {"atlas_core"}
    assert registry.is_registered("string")
    assert not registry.is_registered("array<string>")


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TypeRegistry.get_type", rules=["TRG-01", "TRG-02"])
def test__registered_names_answer_their_type() -> None:
    """``getType`` returns the cached type for a registered name."""
    registry = TypeRegistry()

    assert isinstance(registry.get_type("int"), BuiltInType)
    assert isinstance(registry.get_type("objectid"), ObjectIdType)
    assert registry.get_type("int") is registry.get_type("int")


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TypeRegistry.get_type", rules=["TRG-02"])
def test__array_and_map_names_are_built_on_demand() -> None:
    """``getType`` builds ``AtlasArrayType`` and ``AtlasMapType``, splitting a map at its first comma."""
    registry = TypeRegistry()
    array = registry.get_type("array<map<string,array<int>>>")

    assert isinstance(array, ArrayType)
    assert (array.cardinality, array.min_count, array.max_count) == (Cardinality.LIST, -1, -1)
    assert isinstance(array.element_type, MapType)
    assert array.element_type.key_type_name == "string"
    assert array.element_type.value_type_name == "array<int>"
    assert isinstance(array.element_type.value_type, ArrayType)
    assert not registry.is_registered("array<map<string,array<int>>>")


@pytest.mark.covers(
    "aurelius_atlas_typesystem.registry.TypeRegistry.get_type",
    "aurelius_atlas_typesystem.registry.TypeRegistry.get_type_by_guid",
    rules=["TRG-03"],
)
@pytest.mark.parametrize("name", ["nothing", "array<nothing>", "map<string,nothing>", "map<nothing>", None])
def test__an_unknown_type_name_fails_with_type_name_not_found(name: str | None) -> None:
    """``TYPE_NAME_NOT_FOUND`` (404) names what was asked for; a map without a value has an empty name."""
    with pytest.raises(AtlasError) as raised:
        TypeRegistry().get_type(name)

    assert raised.value.code is AtlasErrorCode.TYPE_NAME_NOT_FOUND
    assert raised.value.code.http_status == 404


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TypeRegistry.get_type_by_guid", rules=["TRG-03"])
def test__types_are_found_by_guid_and_an_unknown_guid_fails() -> None:
    """``getTypeByGuid`` and ``TYPE_GUID_NOT_FOUND`` (404)."""
    registry = registry_with(AtlasEnumDef(name="colour", guid="g-1"))

    assert registry.get_type_by_guid("g-1").type_name == "colour"
    with pytest.raises(AtlasError) as raised:
        registry.get_type_by_guid("g-2")
    assert raised.value.code is AtlasErrorCode.TYPE_GUID_NOT_FOUND
    assert raised.value.message == "Given type guid g-2 was invalid"


@pytest.mark.covers(
    "aurelius_atlas_typesystem.registry.TypeRegistry.typedef_by_name",
    "aurelius_atlas_typesystem.registry.TypeRegistry.typedef_by_guid",
    "aurelius_atlas_typesystem.registry.TypeRegistry.typedefs",
    "aurelius_atlas_typesystem.registry.TypeRegistry.typedef_names",
    "aurelius_atlas_typesystem.registry.TypeRegistry.types",
    "aurelius_atlas_typesystem.registry.TypeRegistry.enum_type",
    "aurelius_atlas_typesystem.registry.TypeRegistry.struct_type",
    "aurelius_atlas_typesystem.registry.TypeRegistry.classification_type",
    "aurelius_atlas_typesystem.registry.TypeRegistry.entity_type",
    "aurelius_atlas_typesystem.registry.TypeRegistry.relationship_type",
    "aurelius_atlas_typesystem.registry.TypeRegistry.business_metadata_type",
    rules=["TRG-04"],
)
def test__definitions_and_types_are_found_per_kind_and_across_kinds() -> None:
    """The ``get*DefByName``, ``get*DefByGuid``, ``getAll*`` and ``get*TypeByName`` accessors."""
    registry = registry_with(
        AtlasEnumDef(name="e", guid="g-e"),
        AtlasStructDef(name="s"),
        AtlasClassificationDef(name="c"),
        AtlasEntityDef(name="t", service_type="hive"),
        AtlasRelationshipDef(name="r", end_def1=END, end_def2=END),
        AtlasBusinessMetadataDef(name="b"),
    )

    assert isinstance(registry.enum_type("e"), EnumType)
    assert isinstance(registry.struct_type("s"), StructType)
    assert isinstance(registry.classification_type("c"), ClassificationType)
    assert isinstance(registry.entity_type("t"), EntityType)
    assert isinstance(registry.relationship_type("r"), RelationshipType)
    assert isinstance(registry.business_metadata_type("b"), BusinessMetadataType)
    assert registry.entity_type("c") is None
    assert registry.struct_type(None) is None
    entity_def = registry.typedef_by_name("t")
    assert isinstance(entity_def, AtlasEntityDef)
    assert (entity_def.name, entity_def.service_type, entity_def.sub_types) == ("t", "hive", [])
    assert [attribute.name for attribute in entity_def.relationship_attribute_defs or []] == ["self"]
    assert registry.typedef_by_guid("g-e") == AtlasEnumDef(name="e", guid="g-e")
    assert registry.typedef_by_name("missing") is None
    assert registry.typedef_names(TypeCategory.ENTITY) == ["t"]
    assert [typedef.name for typedef in registry.typedefs(TypeCategory.CLASSIFICATION)] == ["c"]
    assert [type_.type_name for type_ in registry.types(TypeCategory.RELATIONSHIP)] == ["r"]
    assert "hive" in registry.all_service_types()


@pytest.mark.covers(
    "aurelius_atlas_typesystem.registry.TypeRegistry.lock_for_update",
    "aurelius_atlas_typesystem.registry.TypeRegistry.release",
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.add_type",
    rules=["TRG-05"],
)
def test__changes_reach_the_registry_only_on_commit() -> None:
    """``testNestedUpdates``: a nested update gets the same copy; nothing is seen before the outer commit."""
    registry = TypeRegistry()
    transient = registry.lock_for_update()
    transient.add_type(AtlasClassificationDef(name="testTag1"))
    assert not registry.is_registered("testTag1")

    nested = registry.lock_for_update()
    assert nested is transient
    nested.add_type(AtlasClassificationDef(name="testTag2"))
    registry.release(nested, commit=True)
    assert not registry.is_registered("testTag2")

    registry.release(transient, commit=True)
    assert registry.is_registered("testTag1")
    assert registry.is_registered("testTag2")


@pytest.mark.covers(
    "aurelius_atlas_typesystem.registry.TypeRegistry.release",
    "aurelius_atlas_typesystem.registry.TypeRegistry.update",
    rules=["TRG-05"],
)
def test__releasing_without_commit_discards_the_changes() -> None:
    """``releaseTypeRegistryForUpdate(ttr, false)``; the context manager discards when its block raises."""
    registry = TypeRegistry()
    transient = registry.lock_for_update()
    transient.add_type(AtlasEnumDef(name="dropped"))
    registry.release(transient, commit=False)

    def fail_inside_update() -> None:
        with registry.update() as failing:
            failing.add_type(AtlasEnumDef(name="also-dropped"))
            raise RuntimeError

    with pytest.raises(RuntimeError):
        fail_inside_update()

    assert not registry.is_registered("dropped")
    assert not registry.is_registered("also-dropped")


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TypeRegistry.release", rules=["TRG-05"])
def test__a_copy_other_than_the_one_handed_out_is_not_committed() -> None:
    """``releaseTypeRegistryForUpdate`` logs and skips the commit for a foreign copy, but releases the lock."""
    registry = TypeRegistry()
    other = TypeRegistry().lock_for_update()
    other.add_type(AtlasEnumDef(name="foreign"))
    registry.lock_for_update()

    registry.release(other, commit=True)

    assert not registry.is_registered("foreign")
    assert registry.lock_for_update(timeout=0) is not other


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TypeRegistry.lock_for_update", rules=["TRG-05"])
def test__waiting_too_long_for_the_lock_fails() -> None:
    """``FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK`` (500) when another thread holds the lock past the timeout."""
    registry = TypeRegistry()
    held = threading.Event()
    done = threading.Event()

    def hold() -> None:
        transient = registry.lock_for_update()
        held.set()
        done.wait(5)
        registry.release(transient, commit=False)

    holder = threading.Thread(target=hold)
    holder.start()
    held.wait(5)
    try:
        with pytest.raises(AtlasError) as raised:
            registry.lock_for_update(timeout=0.05)
    finally:
        done.set()
        holder.join()

    assert raised.value.code is AtlasErrorCode.FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK
    assert raised.value.code.http_status == 500


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TypeRegistry.update", rules=["TRG-05"])
def test__parallel_updates_are_all_kept() -> None:
    """``testParallelUpdates``: three threads add 30 types of four kinds each; every type is registered."""
    registry = TypeRegistry()

    def add_all() -> None:
        for i in range(30):
            for typedef in (
                AtlasEnumDef(name=f"testEnum-{i}"),
                AtlasStructDef(name=f"testStruct-{i}"),
                AtlasClassificationDef(name=f"testTag-{i}"),
                AtlasEntityDef(name=f"testEntity-{i}"),
            ):
                with registry.update() as transient:
                    transient.add_type(typedef)

    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in [pool.submit(add_all) for _ in range(3)]:
            future.result()

    assert len(registry.typedef_names(TypeCategory.ENUM)) == 30
    assert len(registry.typedef_names(TypeCategory.ENTITY)) == 30


@pytest.mark.covers(
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.add_types",
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.copy_of",
    rules=["TRG-06"],
)
def test__adding_registers_by_name_and_guid_and_a_later_definition_replaces() -> None:
    """``TypeDefCache.addType`` puts the definition under its name and, when it has one, its GUID."""
    registry = registry_with(AtlasEnumDef(name="e", guid="g-1"))
    with registry.update() as transient:
        assert transient.typedef_by_name("e") == AtlasEnumDef(name="e", guid="g-1")
        transient.add_types(AtlasTypesDef(enum_defs=[AtlasEnumDef(name="e", description="later")]))

    typedef = registry.typedef_by_name("e")
    assert typedef is not None
    assert typedef.description == "later"
    assert transient.added == [AtlasEnumDef(name="e", description="later")]


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TransientTypeRegistry.add_types", rules=["TRG-06"])
def test__a_definition_may_replace_a_built_in_type() -> None:
    """``TypeCache.addType`` puts by name whatever is there; rejecting it is the store's job (1.4)."""
    registry = registry_with(AtlasStructDef(name="string"))

    assert isinstance(registry.get_type("string"), StructType)


@pytest.mark.covers(
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.update_type",
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.update_type_by_guid",
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.update_type_by_name",
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.update_types",
    rules=["TRG-07"],
)
def test__updating_replaces_by_guid_else_by_name() -> None:
    """``updateTypeWithNoRefResolve`` uses the GUID when it is not blank, else the name, else nothing."""
    registry = registry_with(AtlasEnumDef(name="e", guid="g-1"), AtlasStructDef(name="s"))
    with registry.update() as transient:
        transient.update_type(AtlasEnumDef(name="renamed", guid="g-1"))
        transient.update_type_by_name("s", AtlasStructDef(name="s", description="by name"))
        transient.update_type_by_guid("g-1", AtlasEnumDef(name="renamed", guid="g-1", description="by guid"))
        transient.update_types([AtlasStructDef(description="no target"), AtlasStructDef(name=" ", guid=" ")])
        transient.update_types([AtlasStructDef(name="s", description="by name again")])
        transient.update_types(None)

    assert registry.typedef_by_name("e") is None
    renamed = registry.typedef_by_guid("g-1")
    struct = registry.typedef_by_name("s")
    assert renamed is not None
    assert renamed.description == "by guid"
    assert struct is not None
    assert struct.description == "by name again"
    assert [typedef.description for typedef in transient.updated] == [None, "by name", "by guid", "by name again"]


@pytest.mark.covers(
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.remove_types",
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.remove_type_by_guid",
    "aurelius_atlas_typesystem.registry.TransientTypeRegistry.remove_type_by_name",
    rules=["TRG-08"],
)
def test__removing_drops_the_definition_under_name_and_guid() -> None:
    """``removeTypesDef`` removes by GUID when there is one, else by name; the copy records each removal."""
    registry = registry_with(
        AtlasEnumDef(name="a", guid="g-a"),
        AtlasEnumDef(name="b"),
        AtlasStructDef(name="c", guid="g-c"),
        AtlasStructDef(name="d"),
    )
    with registry.update() as transient:
        transient.remove_types(
            AtlasTypesDef(enum_defs=[AtlasEnumDef(name="ignored", guid="g-a"), AtlasEnumDef(name="b")])
        )
        transient.remove_types(AtlasTypesDef())
        transient.remove_type_by_guid("g-c")
        transient.remove_type_by_name("d")
        transient.remove_type_by_name("missing")
        transient.remove_types(AtlasTypesDef(struct_defs=[AtlasStructDef()]))

    assert registry.typedef_names(TypeCategory.ENUM) == []
    assert registry.typedef_names(TypeCategory.STRUCT) == []
    assert registry.typedef_by_guid("g-a") is None
    with pytest.raises(AtlasError):
        registry.get_type_by_guid("g-c")
    assert [typedef.name for typedef in transient.deleted] == ["ignored", "b", "c", "d", None]


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TransientTypeRegistry.remove_type_by_name", rules=["TRG-08"])
def test__removing_by_name_also_drops_the_guid() -> None:
    """``removeTypeDefByName`` removes the definition's GUID entry too."""
    registry = registry_with(AtlasEnumDef(name="a", guid="g-a"))
    with registry.update() as transient:
        transient.remove_type_by_name("a")

    assert registry.typedef_by_guid("g-a") is None
    with pytest.raises(AtlasError):
        registry.get_type_by_guid("g-a")


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TransientTypeRegistry.add_types", rules=["TRG-09"])
def test__a_failed_resolution_leaves_the_registry_as_it_was() -> None:
    """``testRegistryValidityOnInvalidUpdate``: the failure is raised and nothing is committed."""
    registry = registry_with(AtlasStructDef(name="kept"))

    with pytest.raises(AtlasError) as raised, registry.update() as transient:
        transient.add_types(
            [AtlasStructDef(name="broken", attribute_defs=[AtlasAttributeDef(name="a", type_name="missing")])]
        )

    assert raised.value.code is AtlasErrorCode.TYPE_NAME_NOT_FOUND
    assert raised.value.message == "Given typename missing was invalid"
    assert registry.is_registered("kept")
    assert not registry.is_registered("broken")


@pytest.mark.covers("aurelius_atlas_typesystem.registry.TransientTypeRegistry.add_type", rules=["TRG-09"])
def test__every_change_resolves_every_type_again() -> None:
    """Removing a type that another refers to makes the next resolution fail."""
    registry = registry_with(
        AtlasEnumDef(name="colour"),
        AtlasStructDef(name="paint", attribute_defs=[AtlasAttributeDef(name="colour", type_name="colour")]),
    )

    with pytest.raises(AtlasError), registry.update() as transient:
        transient.remove_type_by_name("colour")
    with registry.update() as transient:
        transient.add_type(None)

    struct = registry.struct_type("paint")
    assert struct is not None
    assert isinstance(struct.attribute_type("colour"), EnumType)
