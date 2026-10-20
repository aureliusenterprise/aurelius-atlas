"""``AtlasRelatedObjectId`` (ENT-12).

Read from ``org.apache.atlas.model.instance.AtlasRelatedObjectId`` of Atlas 2.4.0.
"""

from types import SimpleNamespace

import pytest
from aurelius_atlas_model.instance import AtlasRelatedObjectId, AtlasStruct, EntityStatus, RelationshipStatus

M = "aurelius_atlas_model.instance.related_object_id.AtlasRelatedObjectId"


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-12"])
def test__a_related_object_id_reads_and_writes_its_fields() -> None:
    """The object id's fields and the relationship's; also from an object's attributes."""
    body = {
        "guid": "g",
        "typeName": "hive_db",
        "entityStatus": "ACTIVE",
        "displayText": "db",
        "relationshipType": "hive_table_db",
        "relationshipGuid": "r",
        "relationshipStatus": "ACTIVE",
        "relationshipAttributes": {"typeName": "hive_table_db", "attributes": {}},
        "qualifiedName": "db@cm",
    }

    related = AtlasRelatedObjectId.model_validate(body)
    from_object = AtlasRelatedObjectId.model_validate(
        SimpleNamespace(guid="g", relationship_type="t"), from_attributes=True
    )

    assert related.to_json() == body
    assert (from_object.guid, from_object.relationship_type) == ("g", "t")


@pytest.mark.covers(rules=["ENT-12"])
@pytest.mark.parametrize(
    ("body", "relationship_type"),
    [
        ({"relationshipType": "given", "relationshipAttributes": {"typeName": "struct"}}, "struct"),
        ({"relationshipAttributes": {"typeName": "struct"}, "relationshipType": "given"}, "given"),
        ({"relationshipType": "given", "relationshipAttributes": {"attributes": {}}}, "given"),
        ({"relationship_attributes": AtlasStruct(type_name="struct")}, "struct"),
        ({"relationshipAttributes": None}, None),
    ],
    ids=["struct-after", "type-after", "struct-without-type", "by-name", "null"],
)
def test__of_relationship_type_and_attributes_the_later_one_wins(
    body: dict[str, object], relationship_type: str
) -> None:
    """``setRelationshipAttributes`` sets the type from the struct; Jackson calls setters in the body's order."""
    assert AtlasRelatedObjectId.model_validate(body).relationship_type == relationship_type


@pytest.mark.covers(f"{M}.set_relationship_attributes", rules=["ENT-12"])
def test__setting_relationship_attributes_sets_the_type() -> None:
    """A struct with a type name sets the relationship type; one without, or none, keeps it."""
    related = AtlasRelatedObjectId(relationship_type="given")

    related.set_relationship_attributes(AtlasStruct())
    assert related.relationship_type == "given"
    related.set_relationship_attributes(AtlasStruct(type_name="struct"))
    assert related.relationship_type == "struct"
    related.set_relationship_attributes(None)
    assert (related.relationship_type, related.relationship_attributes) == ("struct", None)


@pytest.mark.covers(f"{M}.__eq__", rules=["ENT-11", "ENT-12"])
def test__related_object_ids_compare_the_relationship_too() -> None:
    """``AtlasRelatedObjectId.equals``: the object id's equality and then its own fields."""
    one = AtlasRelatedObjectId(
        guid="g", entity_status=EntityStatus.ACTIVE, relationship_status=RelationshipStatus.ACTIVE
    )
    same = AtlasRelatedObjectId(
        guid="g", entity_status=EntityStatus.ACTIVE, relationship_status=RelationshipStatus.ACTIVE
    )

    assert one == same
    assert one != AtlasRelatedObjectId(guid="g", relationship_status=RelationshipStatus.DELETED)
    assert one != AtlasRelatedObjectId(guid="other", entity_status=EntityStatus.ACTIVE)
