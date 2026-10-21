"""``AtlasBusinessMetadataType`` and ``AtlasRelationshipType``'s value side (EVL-10).

Read from ``AtlasBusinessMetadataType`` and ``AtlasRelationshipType`` of Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.typedef import (
    AtlasBusinessMetadataDef,
    AtlasEntityDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasTypesDef,
)
from aurelius_atlas_typesystem.business_metadata_type import BusinessMetadataType
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


@pytest.mark.covers(f"{REL}.is_valid_value", f"{REL}.is_valid_value_for_update", f"{REL}.are_equal_values")
def test__relationship_values_wait_for_atlas_relationship() -> None:
    """``AtlasRelationshipType`` checks an ``AtlasRelationship``, which arrives in 3.1."""
    relationship = RelationshipType(
        AtlasRelationshipDef(
            name="r",
            end_def1=AtlasRelationshipEndDef(type="a", name="x"),
            end_def2=AtlasRelationshipEndDef(type="b", name="y"),
        )
    )
    _ = AtlasTypesDef(entity_defs=[AtlasEntityDef(name="a")])

    for call in (
        lambda: relationship.is_valid_value({}),
        lambda: relationship.is_valid_value_for_update({}),
        lambda: relationship.are_equal_values({}, {}, None),
    ):
        with pytest.raises(NotImplementedError, match=r"r: relationship values arrive with AtlasRelationship in 3\.1"):
            call()
