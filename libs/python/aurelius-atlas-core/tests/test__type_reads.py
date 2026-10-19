"""Reading and searching the registered type definitions (TYR-01 to TYR-08).

Read from ``AtlasTypeDefGraphStore`` (``getByName``, ``getByGuid``, ``get*DefByName``, ``get*DefByGuid``,
``searchTypesDef``), ``FilterUtil``, ``SearchFilter`` and ``TypesREST.getSearchFilter`` of Apache Atlas 2.4.0, and
its test ``TypedefsJerseyResourceIT`` (``testInvalidGets``, ``testListTypesByFilter``).
"""

from collections.abc import Callable, Sequence

import pytest
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.type_search import TypeSearchFilter, search_types_def, type_def_headers
from aurelius_atlas_core.typedef_store import TypedefStore, types_def_of
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasBaseTypeDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasTypeDefHeader,
    Cardinality,
    TypeCategory,
)
from aurelius_atlas_typesystem.registry import TypeRegistry


def entity(name: str, *super_types: str, service_type: str | None = None) -> AtlasEntityDef:
    """An entity definition."""
    return AtlasEntityDef(name=name, super_types=list(super_types), service_type=service_type)


@pytest.fixture
async def store() -> TypedefStore:
    """A store with an enum, a classification, entities in a hierarchy and a relationship between two of them."""
    store = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await store.load()
    await store.create_types_def(
        types_def_of(
            [
                AtlasEnumDef(name="colour", element_defs=[AtlasEnumElementDef(value="RED", ordinal=1)]),
                AtlasClassificationDef(name="pii", service_type="svc"),
                entity("__internal"),
                entity("hidden", "__internal"),
                entity("b_base", service_type="svc"),
                entity("a_child", "b_base"),
                entity("c_grandchild", "a_child", service_type="other"),
                AtlasRelationshipDef(
                    name="child_base",
                    end_def1=AtlasRelationshipEndDef(type="a_child", name="base", cardinality=Cardinality.SINGLE),
                    end_def2=AtlasRelationshipEndDef(type="b_base", name="children", cardinality=Cardinality.SET),
                ),
            ]
        )
    )
    return store


def failure(call: Callable[[], object]) -> AtlasError:
    """The ``AtlasError`` a call raises."""
    with pytest.raises(AtlasError) as raised:
        call()
    return raised.value


@pytest.mark.covers("aurelius_atlas_core.typedef_store.TypedefStore.get_by_name", rules=["TYR-01"])
async def test__a_definition_by_name_carries_what_resolution_adds(store: TypedefStore) -> None:
    """``getByName`` answers the registry's definition: sub types and relationship attributes included."""
    base = store.get_by_name("b_base")

    assert isinstance(base, AtlasEntityDef)
    assert base.sub_types == ["a_child"]
    assert [attribute.name for attribute in base.relationship_attribute_defs or []] == ["children"]
    assert base.business_attribute_defs == {}
    assert store.get_by_name("colour").category is TypeCategory.ENUM


@pytest.mark.covers("aurelius_atlas_core.typedef_store.TypedefStore.get_by_name", rules=["TYR-01"])
@pytest.mark.parametrize(
    ("name", "code", "params"),
    [
        (" ", AtlasErrorCode.TYPE_NAME_INVALID, ("", " ")),
        ("blah", AtlasErrorCode.TYPE_NAME_NOT_FOUND, ("blah",)),
        ("string", AtlasErrorCode.SYSTEM_TYPE, ("PRIMITIVE",)),
        ("objectid", AtlasErrorCode.SYSTEM_TYPE, ("OBJECT_ID_TYPE",)),
        ("array<string>", AtlasErrorCode.SYSTEM_TYPE, ("ARRAY",)),
        ("map<string,int>", AtlasErrorCode.SYSTEM_TYPE, ("MAP",)),
    ],
)
async def test__a_name_without_a_definition_fails(
    store: TypedefStore, name: str, code: AtlasErrorCode, params: tuple[str, ...]
) -> None:
    """Blank, unknown, and built-in, array and map types, which have no definition."""
    error = failure(lambda: store.get_by_name(name))

    assert (error.code, error.params) == (code, params)


@pytest.mark.covers("aurelius_atlas_core.typedef_store.TypedefStore.get_by_guid", rules=["TYR-02"])
async def test__a_definition_by_guid(store: TypedefStore) -> None:
    """``getByGuid``: a blank or unknown GUID is ``TYPE_GUID_NOT_FOUND``."""
    guid = str(store.get_by_name("pii").guid)

    assert store.get_by_guid(guid).name == "pii"
    for missing in (" ", "blah"):
        error = failure(lambda missing=missing: store.get_by_guid(missing))
        assert (error.code, error.params) == (AtlasErrorCode.TYPE_GUID_NOT_FOUND, (missing,))


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_store.TypedefStore.get_def_by_name",
    "aurelius_atlas_core.typedef_store.TypedefStore.get_def_by_guid",
    rules=["TYR-03"],
)
async def test__a_kind_lookup_finds_only_its_kind(store: TypedefStore) -> None:
    """``getEnumDefByName`` of an entity's name is not found, as is any name or GUID no definition has."""
    guid = str(store.get_by_name("colour").guid)

    assert store.get_def_by_name(TypeCategory.ENUM, "colour").name == "colour"
    assert store.get_def_by_guid(TypeCategory.ENUM, guid).name == "colour"
    by_name = failure(lambda: store.get_def_by_name(TypeCategory.ENUM, "b_base"))
    by_guid = failure(lambda: store.get_def_by_guid(TypeCategory.ENTITY, guid))
    unknown = failure(lambda: store.get_def_by_name(TypeCategory.STRUCT, "blah"))

    assert (by_name.code, by_name.params) == (AtlasErrorCode.TYPE_NAME_NOT_FOUND, ("b_base",))
    assert (by_guid.code, by_guid.params) == (AtlasErrorCode.TYPE_GUID_NOT_FOUND, (guid,))
    assert unknown.code is AtlasErrorCode.TYPE_NAME_NOT_FOUND


def names(found: Sequence[AtlasBaseTypeDef] | None) -> list[str]:
    """The names of definitions."""
    return [str(typedef.name) for typedef in found or []]


@pytest.mark.covers("aurelius_atlas_core.type_search.search_types_def", rules=["TYR-05"])
async def test__everything_is_found_without_a_filter_each_kind_sorted_by_name(store: TypedefStore) -> None:
    """``searchTypesDef``: every kind, sorted by name (DD-034); the definitions are the registry's."""
    found = search_types_def(store.registry, TypeSearchFilter())

    assert names(found.entity_defs) == ["__internal", "a_child", "b_base", "c_grandchild", "hidden"]
    assert names(found.enum_defs) == ["colour"]
    assert names(found.classification_defs) == ["pii"]
    assert names(found.relationship_defs) == ["child_base"]
    assert (found.entity_defs or [])[2] is store.registry.typedef_by_name("b_base")


@pytest.mark.covers(
    "aurelius_atlas_core.type_search.TypeSearchFilter.from_query",
    "aurelius_atlas_core.type_search.TypeSearchFilter.matches",
    "aurelius_atlas_core.type_search.TypeSearchFilter.param",
    rules=["TYR-06"],
)
@pytest.mark.parametrize(
    ("query", "entities", "others"),
    [
        ([("type", "class")], ["__internal", "a_child", "b_base", "c_grandchild", "hidden"], []),
        ([("type", "TRAIT")], [], ["pii"]),
        ([("type", "nonsense")], [], []),
        ([("name", "b_base")], ["b_base"], []),
        ([("servicetype", "svc")], ["b_base"], ["pii"]),
        ([("serviceType", "svc")], ["__internal", "a_child", "b_base", "c_grandchild", "hidden"], None),
        ([("supertype", "b_base")], ["a_child", "c_grandchild"], []),
        ([("type", "CLASS"), ("supertype", "b_base"), ("notsupertype", "a_child")], ["a_child"], []),
        ([("notservicetype", "svc"), ("type", "ENTITY")], ["__internal", "a_child", "c_grandchild", "hidden"], []),
        ([("notname", "hidden"), ("type", "ENTITY")], ["__internal", "a_child", "b_base", "c_grandchild"], []),
        ([("name", "b_base"), ("name", "a_child")], ["b_base"], []),
        ([("name", " "), ("type", "ENTITY")], ["__internal", "a_child", "b_base", "c_grandchild", "hidden"], []),
    ],
    ids=[
        "type-class",
        "type-trait",
        "type-unknown",
        "name",
        "servicetype",
        "names-with-case",
        "supertype",
        "not-supertype",
        "not-servicetype",
        "not-name",
        "first-value",
        "blank",
    ],
)
async def test__the_filter_keeps_what_its_parameters_say(
    store: TypedefStore, query: list[tuple[str, str]], entities: list[str], others: list[str] | None
) -> None:
    """``FilterUtil``: all predicates must hold.

    Parameter names are case-sensitive, values of ``type`` are not; a parameter counts with its first value, and a
    blank value filters nothing.
    """
    found = search_types_def(store.registry, TypeSearchFilter.from_query(query))

    assert names(found.entity_defs) == entities
    if others is not None:
        assert names(found.classification_defs) + names(found.enum_defs) == others


@pytest.mark.covers("aurelius_atlas_core.type_search.TypeSearchFilter.from_query", rules=["TYR-07"])
async def test__excluding_internal_types_hides_internal_and_its_sub_types(store: TypedefStore) -> None:
    """``addParamsToHideInternalType``, name and value ignoring case.

    A ``notname`` given too still applies, and the first ``notsupertype`` in the request wins (DV-09).
    """
    hide = TypeSearchFilter.from_query([("type", "ENTITY"), ("EXCLUDEINTERNALTYPESANDREFERENCES", "True")])
    with_notname = TypeSearchFilter.from_query(
        [("excludeInternalTypesAndReferences", "true"), ("notname", "b_base"), ("type", "ENTITY")]
    )
    supertype_first = TypeSearchFilter.from_query(
        [("notsupertype", "a_child"), ("excludeInternalTypesAndReferences", "true"), ("type", "ENTITY")]
    )
    ignored = TypeSearchFilter.from_query([("excludeInternalTypesAndReferences", "false"), ("type", "ENTITY")])

    assert names(search_types_def(store.registry, hide).entity_defs) == ["a_child", "b_base", "c_grandchild"]
    assert names(search_types_def(store.registry, with_notname).entity_defs) == ["a_child", "c_grandchild"]
    assert names(search_types_def(store.registry, supertype_first).entity_defs) == ["a_child", "b_base", "hidden"]
    assert len(search_types_def(store.registry, ignored).entity_defs or []) == 5


@pytest.mark.covers("aurelius_atlas_core.type_search.type_def_headers", rules=["TYR-08"])
async def test__headers_list_the_found_definitions_enums_first(store: TypedefStore) -> None:
    """``toTypeDefHeader``: guid, name, category and service type, enums, then the other kinds in order."""
    found = search_types_def(store.registry, TypeSearchFilter.from_query([("servicetype", "svc")]))

    headers = type_def_headers(found)

    assert [(h.name, h.category, h.service_type) for h in headers] == [
        ("pii", TypeCategory.CLASSIFICATION, "svc"),
        ("b_base", TypeCategory.ENTITY, "svc"),
    ]
    assert headers[0] == AtlasTypeDefHeader.of(store.get_by_name("pii"))
    assert type_def_headers(types_def_of([])) == []


@pytest.mark.covers(rules=["TYR-01"])
async def test__an_attribute_definition_is_found_as_stored(store: TypedefStore) -> None:
    """The registry holds the stored form of 1.4, which is what the lookups answer (TDS-05)."""
    await store.create_types_def(
        types_def_of([AtlasEntityDef(name="t", attribute_defs=[AtlasAttributeDef(name="a", type_name="string")])])
    )

    found = store.get_def_by_name(TypeCategory.ENTITY, "t")

    assert isinstance(found, AtlasEntityDef)
    assert (found.attribute_defs[0].values_min_count, found.attribute_defs[0].values_max_count) == (1, 1)
