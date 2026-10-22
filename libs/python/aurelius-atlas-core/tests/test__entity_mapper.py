"""``EntityMapper`` (EWR-09 to EWR-12, EWR-17) and ``EntityComparator`` (EWR-08).

Read from ``EntityGraphMapper`` (``mapAttributes``, ``mapAttribute``, ``mapStructValue``, ``mapArrayValue``,
``mapMapValue``, ``mapSoftRefValue``) and ``AtlasEntityComparator`` of Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_comparator import EntityComparator
from aurelius_atlas_core.entity_mapper import EntityMapper
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.testing.entity_samples import sample_entities, sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.instance import AtlasEntity, AtlasObjectId
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry

M = "aurelius_atlas_core.entity_mapper.EntityMapper"
REGISTRY = sample_registry(writes=True)


def resolve(value: Any) -> str:  # noqa: ANN401 - a reference as given
    """References name entities by their GUID, ``-`` GUIDs as ``new``."""
    guid = str(value.guid if isinstance(value, AtlasObjectId) else value["guid"])
    return "new" if guid.startswith("-") else guid


def mapper() -> EntityMapper:
    """A mapper at time 7, with ``-1`` assigned ``new``."""
    return EntityMapper(REGISTRY, resolve=resolve, guid_assignments={"-1": "new"}, now=7, user=None)


def of(name: str, registry: TypeRegistry = REGISTRY) -> EntityType:
    """The entity type named."""
    found = registry.entity_type(name)
    assert found is not None
    return found


def normalized(type_name: str, **attributes: Any) -> AtlasEntity:  # noqa: ANN401 - attribute values
    """An entity normalised by its type, as discovery leaves it."""
    entity = AtlasEntity(type_name=type_name, attributes=attributes)
    of(type_name).get_normalized_value(entity)
    return entity


def by_name(values: dict[str, Any]) -> dict[str, Any]:
    """Stored values by attribute name."""
    return {name.rpartition(".")[2]: value for name, value in values.items()}


@pytest.mark.covers(f"{M}.create", rules=["EWR-09", "EWR-11", "EWR-12"])
def test__a_new_entity_stores_every_attribute_and_records_what_it_references() -> None:
    """Defaults for primitives; references as GUIDs, soft ones as ``typeName:guid``; maps by key."""
    found = mapper()
    entity = normalized(
        "s_table",
        created="2023-11-14T22:13:20.000Z",
        db={"guid": "d", "typeName": "s_database"},
        byName={"x": {"guid": "c1"}},
        spare=[{"guid": "-1", "typeName": "s_column"}, None],
        props={"k": "v"},
        places=[None, {"x": "2"}],
    )

    stored = found.create(entity, of("s_table"), "t")

    assert by_name(stored.attributes) == {
        "created": 1700000000000,
        "db": "d",
        "byName": {"x": "c1"},
        "spare": ["s_column:new"],
        "props": {"k": "v"},
        "places": [{"typeName": "s_place", "attributes": {"x": 2}}],
    }
    assert (stored.create_time, stored.super_type_names) == (7, list(of("s_table").all_super_types))
    assert found.touched == ["d"]


@pytest.mark.covers(f"{M}.update", f"{M}.touch", rules=["EWR-10", "EWR-12", "EWR-17"])
async def test__an_update_changes_what_it_gives_and_the_time_only_when_it_gives_attributes() -> None:
    """Custom attributes alone leave ``updateTime``; a legacy end lands in its attribute; touching sets the time."""
    store = EntityStore(REGISTRY, MemoryEntityDocuments())
    await store.write([EntityChange(entity) for entity in sample_entities(store.registry)])
    table = await store.get("t")
    assert table is not None
    found = mapper()

    custom = found.update(
        AtlasEntity(type_name="s_table", custom_attributes={"k": "v"}), of("s_table"), table.entity, partial=True
    )
    item = AtlasEntity(type_name="w_item", relationship_attributes={"holder": AtlasObjectId(guid="d")})
    held = found.update(item, of("w_item"), table.entity.model_copy(update={"attributes": {}}), partial=False)

    assert (custom.update_time, custom.custom_attributes, custom.attributes) == (
        1000,
        {"k": "v"},
        table.entity.attributes,
    )
    assert (held.update_time, by_name(held.attributes)) == (7, {"holder": "d"})
    assert found.touch(table.entity).update_time == 7


@pytest.mark.covers("aurelius_atlas_core.entity_comparator.EntityComparator.has_difference", rules=["EWR-08"])
async def test__an_update_differs_by_attributes_relationship_attributes_or_custom_attributes() -> None:
    """Equal values and labels alone are no difference; references compare by GUID through the assignments."""
    store = EntityStore(REGISTRY, MemoryEntityDocuments())
    await store.write([EntityChange(entity) for entity in sample_entities(store.registry)])
    table = await store.get("t")
    assert table is not None
    comparator = EntityComparator(EntityRetriever(store), {"-9": "d"})

    async def differs(**fields: Any) -> bool:  # noqa: ANN401 - entity fields
        entity = AtlasEntity(type_name="s_table", **fields)
        of("s_table").get_normalized_value(entity)
        return await comparator.has_difference(entity, of("s_table"), table.entity)

    assert not await differs(attributes={"name": "orders", "db": {"guid": "-9"}, "unknown": 1}, labels=["x"])
    assert await differs(attributes={"name": "other"})
    assert await differs(relationship_attributes={"home": {"guid": "d"}})
    assert not await differs(relationship_attributes={"home": None, "nothing": 1})
    assert await differs(custom_attributes={})
