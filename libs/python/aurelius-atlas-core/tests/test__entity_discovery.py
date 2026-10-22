"""``EntityDiscovery`` (EWR-03 to EWR-07): walking a request and resolving its references.

Read from ``AtlasEntityGraphDiscoveryV2``, ``IDBasedEntityResolver``, ``UniqAttrBasedEntityResolver``,
``EntityGraphDiscoveryContext`` and ``EntityGraphMapper.validateCustomAttributes``/``validateLabels`` of Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_core.entity_discovery import (
    DiscoveryContext,
    EntityDiscovery,
    EntityStream,
    is_valid_guid,
    is_valid_object_id,
    object_id_of,
    process_dynamic_attributes,
    validate_custom_attributes,
    validate_labels,
)
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.testing.entity_samples import sample_entity, sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasEntityExtInfo, AtlasObjectId

D = "aurelius_atlas_core.entity_discovery"


@pytest.fixture
async def store() -> EntityStore:
    """A store of the sample and write types holding database ``d`` (``db@cl``)."""
    store = EntityStore(sample_registry(writes=True), MemoryEntityDocuments())
    await store.write([EntityChange(sample_entity(store.registry, "s_database", "d", {"qualifiedName": "db@cl"}))])
    return store


def stream(*entities: dict[str, object], referred: dict[str, object] | None = None) -> EntityStream:
    """A stream of a bulk request of these entities."""
    request = AtlasEntitiesWithExtInfo.model_validate({"entities": entities, "referredEntities": referred or {}})
    return EntityStream(list(request.entities or []), request)


@pytest.mark.covers(f"{D}.EntityDiscovery.discover", f"{D}.EntityStream.get_by_guid", rules=["EWR-04", "EWR-05"])
async def test__discovery_records_and_resolves_every_reference(store: EntityStore) -> None:
    """GUIDs in walk order; references by unique values apart; stored, local and found-by-values GUIDs."""
    found = stream(
        {
            "typeName": "s_table",
            "guid": "-1",
            "attributes": {
                "db": {"typeName": "s_database", "uniqueAttributes": {"qualifiedName": "db@cl"}},
                "byName": {"a": {"guid": "-2"}},
                "places": [{"x": 1, "at": {"guid": "d"}}],
            },
        },
        referred={"-2": {"typeName": "s_database", "guid": "-2", "attributes": {"qualifiedName": "db@cl"}}},
    )

    context = await EntityDiscovery(store, found).discover()

    assert context.referenced_guids == ["-1", "d", "-2"]
    assert context.referenced_by_unique == [
        AtlasObjectId(type_name="s_database", unique_attributes={"qualifiedName": "db@cl"})
    ]
    assert context.resolved_guids == {"d": "d", "-2": "d"}
    assert context.local_guids == {"-1"}
    assert found.get_by_guid("-2") is not None
    assert found.get_by_guid("-1") is found.entities[0]


@pytest.mark.covers(
    f"{D}.DiscoveryContext.add_resolved_by_unique", f"{D}.DiscoveryContext.resolved_object_id", rules=["EWR-05"]
)
def test__an_object_id_resolves_also_through_a_sub_type() -> None:
    """An object id recorded for ``s_table`` is found when asked for ``s_ref`` with the same values."""
    context = DiscoveryContext()
    values = {"qualifiedName": "t@cl"}

    context.add_resolved_by_unique(AtlasObjectId(type_name="s_table", unique_attributes=values), "t")

    assert context.resolved_object_id(AtlasObjectId(type_name="s_ref", unique_attributes=values), ["s_table"]) == "t"
    assert context.resolved_object_id(AtlasObjectId(type_name="s_ref", unique_attributes=values), []) is None


@pytest.mark.covers(f"{D}.EntityDiscovery.entity_type", f"{D}.EntityDiscovery.validate_and_normalize", rules=["EWR-07"])
async def test__an_entity_is_checked_then_normalised(store: EntityStore) -> None:
    """The GUID, the type, then the type's messages; a valid entity is normalised in place."""
    discovery = EntityDiscovery(store, stream())
    valid = AtlasEntity(type_name="w_item", attributes={"count": "3"})

    discovery.validate_and_normalize(valid, for_update=True)

    assert valid.attributes == {"count": 3}
    assert discovery.entity_type("w_item").type_name == "w_item"
    for entity, code, message in [
        (
            AtlasEntity(guid="", type_name="w_item"),
            AtlasErrorCode.INVALID_OBJECT_ID,
            "ObjectId is not valid invalid guid ",
        ),
        (AtlasEntity(type_name="nope"), AtlasErrorCode.TYPE_NAME_INVALID, "Type ENTITY with name nope does not exist"),
        (
            AtlasEntity(type_name="w_item", attributes={"flag": "x"}),
            AtlasErrorCode.INSTANCE_CRUD_INVALID_PARAMS,
            "Invalid instance creation/updation parameters passed : [w_item.flag=x: invalid value for type boolean]",
        ),
    ]:
        with pytest.raises(AtlasError) as raised:
            discovery.validate_and_normalize(entity, for_update=False)
        assert (raised.value.code, raised.value.message) == (code, message)


@pytest.mark.covers(f"{D}.process_dynamic_attributes", rules=["EWR-03"])
def test__a_dynamic_attribute_is_set_only_when_every_attribute_it_reads_has_a_value() -> None:
    """``item-{qualifiedName}``: set from the qualified name; kept when that is null."""
    item_type = sample_registry(writes=True).entity_type("w_item")
    assert item_type is not None
    named = AtlasEntity(type_name="w_item", attributes={"qualifiedName": "q", "name": "given"})
    unnamed = AtlasEntity(type_name="w_item", attributes={"name": "given"})

    process_dynamic_attributes(named, item_type)
    process_dynamic_attributes(unnamed, item_type)

    assert (named.get_attribute("name"), unnamed.get_attribute("name")) == ("item-q", "given")


@pytest.mark.covers(f"{D}.validate_custom_attributes", f"{D}.validate_labels", rules=["EWR-07"])
def test__custom_attribute_keys_and_labels_are_short_names() -> None:
    """At most 50 characters of letters, digits, ``_``, ``-`` and CJK ideographs; values are not checked."""
    validate_custom_attributes(AtlasEntity(custom_attributes={"a_b-1中": "x" * 600}))
    validate_labels(["a_b-1中", "x" * 50])
    for check, code, message in [
        (
            lambda: validate_custom_attributes(AtlasEntity(custom_attributes={"k" * 51: "v"})),
            AtlasErrorCode.INVALID_CUSTOM_ATTRIBUTE_KEY_LENGTH,
            f"Invalid key: {'k' * 51} in custom attribute, key size should not be greater than 50",
        ),
        (
            lambda: validate_custom_attributes(AtlasEntity(custom_attributes={"a.b": "v"})),
            AtlasErrorCode.INVALID_CUSTOM_ATTRIBUTE_KEY_CHARACTERS,
            "Invalid key: a.b in custom attribute, key should only contain alphanumeric characters, _ or -",
        ),
        (
            lambda: validate_labels(["l" * 51]),
            AtlasErrorCode.INVALID_LABEL_LENGTH,
            f"Invalid label: {'l' * 51}, label size should not be greater than 50",
        ),
    ]:
        with pytest.raises(AtlasError) as raised:
            check()
        assert (raised.value.code, raised.value.message) == (code, message)


@pytest.mark.covers(f"{D}.is_valid_guid", f"{D}.is_valid_object_id", f"{D}.object_id_of", rules=["EWR-04"])
def test__an_object_id_is_valid_with_a_guid_or_with_a_type_and_unique_values() -> None:
    """Assigned and unassigned GUIDs are valid; a map is read as an object id; others are invalid."""
    assert (is_valid_guid("g"), is_valid_guid("-1"), is_valid_guid(""), is_valid_guid(None)) == (
        True,
        True,
        False,
        False,
    )
    assert is_valid_object_id(AtlasObjectId(type_name="t", unique_attributes={"q": 1}))
    assert not is_valid_object_id(AtlasObjectId(type_name="t"))
    assert object_id_of({"guid": "g"}) == AtlasObjectId(guid="g")
    assert object_id_of(None) is None
    with pytest.raises(AtlasError, match="ObjectId is not valid x"):
        object_id_of("x")
    assert EntityStream([], AtlasEntityExtInfo()).get_by_guid("g") is None
