"""``AtlasBusinessMetadataType`` and ``AtlasRelationshipType``'s value side (EVL-10, REL-02).

Read from ``AtlasBusinessMetadataType`` and ``AtlasRelationshipType`` of Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelationship
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasBusinessMetadataDef,
    AtlasEntityDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasTypesDef,
)
from aurelius_atlas_typesystem.business_metadata_type import BusinessMetadataType
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.relationship_type import RelationshipType

BM = "aurelius_atlas_typesystem.business_metadata_type.BusinessMetadataType"
REL = "aurelius_atlas_typesystem.relationship_type.RelationshipType"


@pytest.mark.covers(
    f"{BM}.is_valid_value", f"{BM}.create_default_value", f"{BM}.get_normalized_value", rules=["EVL-10"]
)
def test__business_metadata_has_no_instances() -> None:
    """Every value is valid; the default and every normalised value are null."""
    metadata = BusinessMetadataType(AtlasBusinessMetadataDef(name="bm"))

    assert metadata.is_valid_value({"anything": 1})
    assert metadata.create_default_value() is None
    assert metadata.get_normalized_value({"a": 1}) is None


def relationship_type() -> RelationshipType:
    """``r`` between ``a`` (and its sub type ``a2``) and ``b``, with an ``int`` attribute ``n``."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(
            AtlasTypesDef(
                entity_defs=[
                    AtlasEntityDef(name="a"),
                    AtlasEntityDef(name="a2", super_types=["a"]),
                    AtlasEntityDef(name="b"),
                ],
                relationship_defs=[
                    AtlasRelationshipDef(
                        name="r",
                        end_def1=AtlasRelationshipEndDef(type="a", name="x"),
                        end_def2=AtlasRelationshipEndDef(type="b", name="y"),
                        attribute_defs=[AtlasAttributeDef(name="n", type_name="int", is_optional=True)],
                    )
                ],
            )
        )
    found = registry.get_type("r")
    assert isinstance(found, RelationshipType)
    return found


def relationship(end1: dict[str, str], end2: dict[str, str], **attributes: object) -> AtlasRelationship:
    """A relationship of ``r`` between the ends."""
    return AtlasRelationship.model_validate({"typeName": "r", "end1": end1, "end2": end2, "attributes": attributes})


@pytest.mark.covers(f"{REL}.is_valid_value", f"{REL}.is_valid_value_for_update", rules=["REL-02"])
def test__a_relationship_is_valid_with_typed_ends_of_its_types_or_with_both_guids() -> None:
    """End types of the type or a sub type with valid attributes; untyped ends need GUIDs; maps are invalid."""
    found = relationship_type()

    assert found.is_valid_value(None)
    assert found.is_valid_value(relationship({"typeName": "a2"}, {"typeName": "b"}, n=1))
    assert not found.is_valid_value(relationship({"typeName": "a2"}, {"typeName": "b"}, n="x"))
    assert not found.is_valid_value(relationship({"typeName": "b"}, {"typeName": "a"}))
    assert found.is_valid_value_for_update(relationship({"guid": "g1"}, {"guid": "g2"}))
    assert not found.is_valid_value(relationship({"guid": "g1"}, {"typeName": "b"}))
    assert not found.is_valid_value(AtlasRelationship(type_name="r", end1=AtlasObjectId(guid="g")))
    assert not found.is_valid_value({"typeName": "r"})


@pytest.mark.covers(f"{REL}.are_equal_values", rules=["REL-02"])
def test__relationships_are_equal_by_attributes_guid_ends_label_propagation_and_status() -> None:
    """A map is read as a relationship; anything else is never equal."""
    found = relationship_type()
    first = relationship({"guid": "g1"}, {"guid": "g2"}, n=1).model_copy(update={"guid": "r1", "label": "l"})

    assert found.are_equal_values(None, None, None)
    assert not found.are_equal_values(first, None, None)
    assert found.are_equal_values(first, first.to_json(), None)
    assert not found.are_equal_values(first, first.model_copy(update={"label": "m"}), None)
    assert not found.are_equal_values(first, relationship({"guid": "g1"}, {"guid": "g2"}, n=2), None)
    assert not found.are_equal_values(first, "x", None)
    assert not found.are_equal_values(first, {"status": "nope"}, None)
