"""``AtlasRelationship`` and ``AtlasRelationshipWithExtInfo`` (REL-01).

Read from ``org.apache.atlas.model.instance.AtlasRelationship`` of Apache Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasEntityHeader, AtlasRelationship, AtlasRelationshipWithExtInfo

R = "aurelius_atlas_model.instance.relationship_with_ext_info.AtlasRelationshipWithExtInfo"


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["REL-01"])
def test__a_relationship_reads_and_writes_atlas_json() -> None:
    """Every field round-trips; without them, a temporary GUID, 0 for the numbers, nothing for the rest."""
    body = {
        "typeName": "r",
        "attributes": {"a": 1},
        "guid": "g",
        "homeId": "h",
        "provenanceType": 1,
        "end1": {"guid": "e1", "typeName": "t1"},
        "end2": {"guid": "e2", "typeName": "t2", "uniqueAttributes": {"qualifiedName": "q"}},
        "label": "r:r",
        "propagateTags": "ONE_TO_TWO",
        "status": "DELETED",
        "createdBy": "u",
        "updatedBy": "v",
        "createTime": 1,
        "updateTime": 2,
        "version": 3,
        "propagatedClassifications": [{"typeName": "c", "entityStatus": "ACTIVE"}],
        "blockedPropagatedClassifications": [],
    }
    empty = AtlasRelationship.model_validate({}).to_json()

    assert codec.loads(codec.dumps(AtlasRelationship.model_validate(body).to_json())) == body
    assert str(empty.pop("guid")).startswith("-")
    assert empty == {"provenanceType": 0, "version": 0}


@pytest.mark.covers(
    f"{R}.referred_entities_contains", f"{R}.add_referred_entity", f"{R}.remove_referred_entity", rules=["REL-01"]
)
def test__a_relationship_with_ext_info_holds_the_headers_of_its_ends() -> None:
    """``referredEntities`` by GUID, created when the first is added."""
    found = AtlasRelationshipWithExtInfo(relationship=AtlasRelationship(guid="r"))

    assert not found.referred_entities_contains("a")
    found.add_referred_entity("a", AtlasEntityHeader(guid="a"))

    assert found.referred_entities_contains("a")
    assert found.remove_referred_entity("a") == AtlasEntityHeader(guid="a")
    assert found.remove_referred_entity(None) is None
    assert AtlasRelationshipWithExtInfo().remove_referred_entity("a") is None
