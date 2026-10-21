"""``AtlasEntityType``'s value side and relationship attributes (EVL-03 to EVL-09, EVL-11, DV-13).

Read from ``AtlasEntityType``, ``AtlasEntityUtil.getRelationshipType``, ``TestAtlasEntityType`` and
``TestAtlasEntity`` of Atlas 2.4.0, on ``ModelTestUtil``'s entity with two super types.
"""

from typing import Any

import pytest
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasEntity, AtlasObjectId, AtlasRelatedObjectId, AtlasStruct
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasEntityDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasTypesDef,
    Cardinality,
    RelationshipCategory,
)
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.testing.model_test_util import ENTITY_DEFS, model_registry

M = "aurelius_atlas_typesystem.entity_type.EntityType"


@pytest.fixture(scope="module")
def entity_type() -> EntityType:
    """``ModelTestUtil.getEntityDefWithSuperTypes()``."""
    found = model_registry().entity_type(ENTITY_DEFS[2])
    assert found is not None
    return found


@pytest.fixture(scope="module")
def column_type(table_registry: TypeRegistry) -> EntityType:
    """The column of ``table_registry``."""
    found = table_registry.entity_type("t_column")
    assert found is not None
    return found


@pytest.fixture(scope="module")
def table_registry() -> TypeRegistry:
    """A table and its columns: a column's ``table`` is a composition's child end, so mandatory."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(
            AtlasTypesDef(
                entity_defs=[
                    AtlasEntityDef(name="t_table"),
                    AtlasEntityDef(
                        name="t_column", attribute_defs=[AtlasAttributeDef(name="name", type_name="string")]
                    ),
                ],
                relationship_defs=[
                    AtlasRelationshipDef(
                        name="t_table_columns",
                        relationship_category=RelationshipCategory.COMPOSITION,
                        end_def1=AtlasRelationshipEndDef(
                            type="t_table", name="columns", is_container=True, cardinality=Cardinality.SET
                        ),
                        end_def2=AtlasRelationshipEndDef(type="t_column", name="table", cardinality=Cardinality.SINGLE),
                    )
                ],
            )
        )
    return registry


@pytest.mark.covers(
    f"{M}.create_default_value",
    f"{M}.is_valid_value",
    f"{M}.validate_value",
    f"{M}.populate_default_values",
    f"{M}.normalize_attribute_values",
    rules=["EVL-04", "EVL-05", "EVL-08", "EVL-11"],
)
def test__atlas_s_entity_type_test_holds(entity_type: EntityType) -> None:
    """``testEntityType…``: defaults, invalid attribute values, missing attributes and values that are no entity."""
    default = entity_type.create_default_value()
    bad_int, bad_date = entity_type.create_default_value(), entity_type.create_default_value()
    bad_int.set_attribute("attr-int", "xyz")
    bad_date.set_attribute("attr-date", "xyz")
    bad_map = dict(entity_type.create_default_value().attributes or {}) | {"attr-biginteger": "xyz"}
    valid = [None, default, entity_type.create_default_value().attributes]
    invalid = [bad_int, bad_date, bad_map, AtlasEntity(), {}, 1, set(), [], ()]

    assert (default.type_name, str(default.guid).startswith("-")) == (ENTITY_DEFS[2], True)
    for value in valid:
        messages: list[str] = []
        assert entity_type.is_valid_value(value), value
        assert entity_type.validate_value(value, "testObj", messages), messages
        assert (entity_type.get_normalized_value(value) is None) == (value is None)
    for value in invalid:
        messages = []
        assert not entity_type.is_valid_value(value), value
        assert not entity_type.validate_value(value, "testObj", messages), value
        assert messages, value
        assert entity_type.get_normalized_value(value) is None, value


@pytest.mark.covers(f"{M}.validate_value", f"{M}.validate_value_for_update", rules=["EVL-08"])
def test__a_value_that_is_no_entity_names_its_java_class(entity_type: EntityType) -> None:
    """``<name>: invalid value type '<class>``, the quote unclosed as in Atlas."""
    messages: list[str] = []

    assert not entity_type.validate_value(1, "e", messages)
    assert not entity_type.validate_value_for_update("x", "e", messages)
    assert entity_type.validate_value_for_update(None, "e", messages)
    assert messages == ["e: invalid value type 'java.lang.Integer", "e: invalid value type 'java.lang.String"]


@pytest.mark.covers(f"{M}.validate_value", f"{M}.is_valid_value", rules=["EVL-08"])
def test__a_mandatory_relationship_attribute_must_have_a_valid_reference(column_type: EntityType) -> None:
    """The child end of a composition is mandatory, except for an incomplete entity; its value is an object id."""
    without = AtlasEntity(type_name="t_column", attributes={"name": "c"})
    incomplete = AtlasEntity(type_name="t_column", attributes={"name": "c"}, is_incomplete=True)
    referring = AtlasEntity(type_name="t_column", attributes={"name": "c"})
    referring.set_relationship_attribute("table", {"guid": "g", "typeName": "t_table"})
    bad = AtlasEntity(type_name="t_column", attributes={"name": "c"})
    bad.set_relationship_attribute("table", 5)
    messages: list[str] = []

    assert column_type.is_valid_value(without)
    assert not column_type.validate_value(without, "e", messages)
    assert column_type.validate_value(incomplete, "e", messages)
    assert column_type.validate_value(referring, "e", messages)
    assert not column_type.validate_value(bad, "e", messages)
    assert messages == [
        "e.table: mandatory attribute value missing in type t_column",
        "e.table=5: invalid value for type objectid",
    ]


@pytest.mark.covers(f"{M}.is_valid_value", f"{M}.validate_value", rules=["EVL-08"])
def test__a_map_is_checked_with_its_relationship_attributes_or_without(column_type: EntityType) -> None:
    """A map's relationship attributes are checked; one without them is checked as having none (DV-13)."""
    with_reference = {"typeName": "t_column", "attributes": {"name": "c"}, "relationshipAttributes": {"table": 5}}
    without: dict[str, Any] = {"name": "c"}
    messages: list[str] = []

    assert column_type.is_valid_value(with_reference)
    assert column_type.is_valid_value(without)
    assert column_type.validate_value(without, "m", messages)
    assert not column_type.validate_value(with_reference, "m", messages)
    assert messages == ["m.table=5: invalid value for type objectid"]


@pytest.mark.covers(
    f"{M}.normalize_relationship_attribute_values",
    f"{M}.normalize_attribute_values",
    f"{M}.normalize_attribute_values_for_update",
    f"{M}.get_normalized_value_for_update",
    rules=["EVL-09", "EVL-03"],
)
def test__references_in_relationship_attributes_are_normalised(column_type: EntityType) -> None:
    """A map becomes an object id, or a related object id when it names a relationship type."""
    entity = AtlasEntity(type_name="t_column", attributes={"name": "c"})
    entity.set_relationship_attribute("table", {"guid": "g", "relationshipType": "t_table_columns"})
    updated = AtlasEntity(type_name="t_column", attributes={"name": 1})
    updated.set_relationship_attribute("table", {"guid": "h"})
    as_map: dict[str, Any] = {"name": "c", "table": {"guid": "m"}}

    assert column_type.get_normalized_value(entity) is entity
    assert isinstance(entity.get_relationship_attribute("table"), AtlasRelatedObjectId)
    assert column_type.get_normalized_value_for_update(updated) is updated
    assert updated.get_attribute("name") == "1"
    assert updated.get_relationship_attribute("table") == AtlasObjectId(guid="h")
    column_type.normalize_attribute_values(as_map)
    assert as_map["table"] == AtlasObjectId(guid="m")
    column_type.normalize_relationship_attribute_values(AtlasStruct(type_name="t_column"), for_update=False)
    column_type.normalize_attribute_values_for_update(bare := AtlasEntity(type_name="t_column"))
    assert bare.relationship_attributes is None


@pytest.mark.covers(f"{M}.is_valid_value_for_update", f"{M}.are_equal_values", rules=["EVL-03", "EVL-06"])
def test__updates_skip_relationships_and_equality_goes_through_the_super_types(entity_type: EntityType) -> None:
    """``isValidValueForUpdate`` does not check relationship attributes; equality checks each super type."""
    update = AtlasEntity(type_name=ENTITY_DEFS[2], attributes={"attr-int": "1"})
    changed = entity_type.create_default_value()
    changed.set_attribute("attr-int", 1)

    assert entity_type.is_valid_value_for_update(None)
    assert entity_type.is_valid_value_for_update(update)
    assert not entity_type.is_valid_value_for_update({"attr-int": "x"})
    assert entity_type.are_equal_values(entity_type.create_default_value(), entity_type.create_default_value(), None)
    assert not entity_type.are_equal_values(entity_type.create_default_value(), changed, None)


@pytest.mark.covers(f"{M}.normalize_attribute_values", rules=["EVL-11"])
def test__a_default_entity_survives_json_and_normalising() -> None:
    """``TestAtlasEntity.testEntitySerDe…``: written, read back and normalised, it is equal."""
    registry = model_registry()
    for name in ENTITY_DEFS:
        typed = registry.entity_type(name)
        assert typed is not None
        original = typed.create_default_value()
        read = AtlasEntity.model_validate(codec.loads(codec.dumps(original)))
        typed.normalize_attribute_values(read)
        assert read == original


@pytest.mark.covers(f"{M}.validate_value_for_update", f"{M}.normalize_attribute_values_for_update", rules=["EVL-03"])
def test__an_update_is_validated_and_normalised_through_the_super_types(entity_type: EntityType) -> None:
    """Each super type validates and normalises the update first; missing attributes stay missing."""
    update = AtlasEntity(type_name=ENTITY_DEFS[2], attributes={"attr-int": "2", "attr-date": "x"})
    messages: list[str] = []

    assert not entity_type.validate_value_for_update(update, "u", messages)
    assert set(messages) == {"u.attr-date=x: invalid value for type date"}
    entity_type.normalize_attribute_values_for_update(update)
    assert update.attributes == {"attr-int": 2, "attr-date": None}


@pytest.mark.covers(f"{M}.is_valid_value", f"{M}.normalize_relationship_attribute_values", rules=["EVL-08", "EVL-09"])
def test__a_struct_is_no_entity_and_arrays_of_references_are_normalised(table_registry: TypeRegistry) -> None:
    """A plain struct fails ``validateRelationshipAttributes``; a ``SET`` end holds an array of object ids."""
    column, table = table_registry.entity_type("t_column"), table_registry.entity_type("t_table")
    assert column is not None
    assert table is not None
    entity = AtlasEntity(type_name="t_table")
    entity.set_relationship_attribute("columns", [{"guid": "c1"}, {"guid": "c2"}])

    assert not column.is_valid_value(AtlasStruct(type_name="t_column", attributes={"name": "c"}))
    assert table.validate_value(entity, "t", messages := [])
    assert messages == []
    assert table.get_normalized_value(entity) is entity
    assert entity.get_relationship_attribute("columns") == [AtlasObjectId(guid="c1"), AtlasObjectId(guid="c2")]
