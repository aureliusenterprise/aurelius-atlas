"""``objectid`` (VAL-10, VAL-15).

Read from ``TestAtlasObjectIdType`` of Atlas 2.4.0 and ``AtlasTypeUtil.isAssignedGuid``.
"""

from decimal import Decimal

import pytest
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelatedObjectId, RelationshipStatus
from aurelius_atlas_typesystem.builtin import ObjectIdType
from aurelius_atlas_typesystem.builtin.object_id_type import is_assigned_guid

M = "aurelius_atlas_typesystem.builtin.object_id_type"
UNIQUE = {"name": "testTypeInstance-1"}
VALID = [
    None,
    {"guid": "guid-1234"},
    {"typeName": "testType", "uniqueAttributes": UNIQUE},
    {"guid": "guid-1234", "typeName": "testType", "uniqueAttributes": UNIQUE},
    AtlasObjectId(),
    AtlasObjectId(guid="guid-1234", type_name="testType"),
]
INVALID = [
    {"guid-invalid": "guid-1234"},
    {"typeName": "testType"},
    {"typeName": "testType", "uniqueAttributes": {}},
    {"typeName": "testType", "uniqueAttributes": []},
    {"guid": ""},
    1,
    1.0,
    Decimal(1),
    "1",
    "",
    "12ab",
    True,
]


@pytest.mark.covers(
    f"{M}.ObjectIdType.create_default_value",
    f"{M}.ObjectIdType.is_valid_value",
    f"{M}.ObjectIdType.get_normalized_value",
    rules=["VAL-10", "VAL-15"],
)
def test__object_ids_and_maps_that_identify_an_entity_are_valid() -> None:
    """``testObjectIdType…``: a GUID, or a type name with unique attributes; the default has GUID ``-1``."""
    object_ids = ObjectIdType("hive_table")

    assert object_ids.create_default_value() == AtlasObjectId(guid="-1", type_name="hive_table")
    assert all(object_ids.is_valid_value(value) for value in VALID)
    assert not any(object_ids.is_valid_value(value) for value in INVALID)
    assert all(object_ids.get_normalized_value(value) is None for value in INVALID)
    assert object_ids.get_normalized_value(VALID[4]) is VALID[4]
    assert object_ids.get_normalized_value(VALID[3]) == AtlasObjectId(
        guid="guid-1234", type_name="testType", unique_attributes=UNIQUE
    )


@pytest.mark.covers(f"{M}.ObjectIdType.get_normalized_value", rules=["VAL-10", "VAL-14"])
def test__a_map_with_a_relationship_type_is_a_related_object_id() -> None:
    """``map.containsKey(KEY_RELATIONSHIP_TYPE)``: read by ``AtlasRelatedObjectId(Map)``; a GUID becomes text."""
    normalized = ObjectIdType().get_normalized_value(
        {"guid": 5, "relationshipType": "r", "relationshipStatus": "ACTIVE", "displayText": "ignored"}
    )

    assert isinstance(normalized, AtlasRelatedObjectId)
    assert (normalized.guid, normalized.relationship_type) == ("5", "r")
    assert (normalized.relationship_status, normalized.display_text) == (RelationshipStatus.ACTIVE, None)


@pytest.mark.covers(f"{M}.ObjectIdType.are_equal_values", f"{M}.is_assigned_guid", rules=["VAL-10"])
def test__object_ids_are_equal_by_guid_or_by_unique_attributes() -> None:
    """GUIDs mapped through the assignments; one assigned and one not compare type and unique attributes.

    So two references with only GUIDs, one unassigned, are equal: both have null type and unique attributes.
    """
    object_ids = ObjectIdType()
    by_unique = {"typeName": "t", "uniqueAttributes": UNIQUE}

    assert object_ids.are_equal_values({"guid": "-1"}, {"guid": "real"}, {"-1": "real"})
    assert not object_ids.are_equal_values({"guid": "-1"}, {"guid": "-2"}, None)
    assert not object_ids.are_equal_values({"guid": "a"}, {"guid": "b"}, None)
    assert object_ids.are_equal_values({"guid": "-1"}, {"guid": "real"}, None)
    assert object_ids.are_equal_values({**by_unique, "guid": "-1"}, {**by_unique, "guid": "real"}, None)
    assert not object_ids.are_equal_values({**by_unique, "guid": "-1"}, {"guid": "real", "typeName": "t"}, None)
    assert object_ids.are_equal_values(None, None, None)
    assert not object_ids.are_equal_values(None, {"guid": "g"}, None)
    assert not object_ids.are_equal_values({"guid": "g"}, "g", None)
    assert [is_assigned_guid(guid) for guid in ("g", "-1", "", None)] == [True, False, False, False]
