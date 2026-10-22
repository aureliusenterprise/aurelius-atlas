"""``StoredEntity`` (ENS-03, DD-043), after ``EntityGraphMapper.createVertexWithGuid`` and ``GraphHelper``."""

from datetime import UTC, datetime

import pytest
from aurelius_atlas_core.stored_entity import StoredEntity, stored_attributes
from aurelius_atlas_model.instance import AtlasEntity, EntityStatus
from aurelius_atlas_model.typedef import AtlasAttributeDef, AtlasEntityDef, AtlasTypesDef
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry

M = "aurelius_atlas_core.stored_entity"


@pytest.fixture(scope="module")
def table_type() -> EntityType:
    """``table``, a sub type of ``ref`` whose ``qualifiedName`` is unique."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(
            AtlasTypesDef(
                entity_defs=[
                    AtlasEntityDef(
                        name="ref",
                        attribute_defs=[AtlasAttributeDef(name="qualifiedName", type_name="string", is_unique=True)],
                    ),
                    AtlasEntityDef(
                        name="table",
                        super_types=["ref"],
                        attribute_defs=[AtlasAttributeDef(name="size", type_name="int", is_optional=True)],
                    ),
                ]
            )
        )
    found = registry.entity_type("table")
    assert found is not None
    return found


@pytest.mark.covers(f"{M}.StoredEntity.of", f"{M}.stored_attributes", rules=["ENS-03"])
def test__a_new_entity_is_stored_active_with_its_system_properties(table_type: EntityType) -> None:
    """``createVertexWithGuid``: type and super types, ``ACTIVE``, both times now, its own version, qualified names."""
    entity = AtlasEntity(
        type_name="table",
        status=EntityStatus.DELETED,
        version=3,
        labels=["l"],
        custom_attributes={"k": "v"},
        attributes={"qualifiedName": "t@cm", "size": 2, "unknown": 1},
    )

    stored = StoredEntity.of(entity, table_type, guid="g", now=1000, user=None)

    assert stored.to_json() == {
        "guid": "g",
        "typeName": "table",
        "superTypeNames": ["ref"],
        "state": "ACTIVE",
        "createTime": 1000,
        "updateTime": 1000,
        "version": 3,
        "isIncomplete": False,
        "provenanceType": 0,
        "labels": ["l"],
        "customAttributes": {"k": "v"},
        "attributes": {"ref.qualifiedName": "t@cm", "table.size": 2},
    }
    assert stored_attributes({"size": 1, "nope": 2}, table_type) == {"table.size": 1}
    assert StoredEntity.of(AtlasEntity(type_name="table"), table_type, guid="h", now=1, user="u").created_by == "u"


@pytest.mark.covers(f"{M}.StoredEntity.touched", f"{M}.StoredEntity.to_entity", rules=["ENS-03"])
def test__a_stored_entity_reads_back_by_attribute_name(table_type: EntityType) -> None:
    """Times become dates; qualified names become the type's attribute names; an update moves only update time."""
    stored = StoredEntity(
        guid="g", type_name="table", create_time=1000, update_time=1000, attributes={"ref.qualifiedName": "q"}
    )

    touched = stored.touched(now=5000, user="u")
    entity = touched.to_entity(table_type)

    assert (touched.create_time, touched.update_time, touched.updated_by) == (1000, 5000, "u")
    assert entity.attributes == {"qualifiedName": "q"}
    assert (entity.create_time, entity.update_time) == (
        datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC),
        datetime(1970, 1, 1, 0, 0, 5, tzinfo=UTC),
    )
    assert (entity.guid, entity.status, entity.updated_by) == ("g", EntityStatus.ACTIVE, "u")


@pytest.mark.covers(f"{M}.StoredEntity.unique_keys", rules=["ENS-05"])
def test__an_active_entity_holds_its_unique_values(table_type: EntityType) -> None:
    """One key per unique attribute with a value, of the entity's own type; none once it is not ``ACTIVE``."""
    stored = StoredEntity(guid="g", type_name="table", attributes={"ref.qualifiedName": "q"})

    assert [(key.type_name, key.attribute, key.value) for key in stored.unique_keys(table_type)] == [
        ("table", "ref.qualifiedName", "q")
    ]
    assert stored.model_copy(update={"state": EntityStatus.DELETED}).unique_keys(table_type) == []
    assert StoredEntity(guid="h", type_name="table").unique_keys(table_type) == []
