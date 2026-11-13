"""The JSON-array bodies the endpoints read where Java declares no class (DV-10).

Each model owns its shape rule: a body that is none of it fails with the endpoint's own text, as an
``AtlasError`` the server answers with ``BAD_REQUEST``.
"""

import pytest
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.lists import Guids, Labels, RelatedObjectIds

NOT_ARRAYS = ({"a": 1}, ["a", 1], "a", 3, True)


@pytest.mark.covers("aurelius_atlas_model.lists.Labels._json_array_of_labels", rules=["LBL-01"])
def test__labels_reads_an_array_of_strings() -> None:
    """The body of ``setLabels``; any other shape is the endpoint's refusal."""
    assert Labels.model_validate(["a", "b"]).root == ["a", "b"]
    assert Labels.model_validate([]).root == []
    for body in ({"a": 1}, ["a", 1], "a"):
        with pytest.raises(AtlasError) as raised:
            Labels.model_validate(body)
        assert raised.value.code is AtlasErrorCode.BAD_REQUEST
        assert raised.value.message == "Invalid body: a JSON array of labels is expected"


@pytest.mark.covers("aurelius_atlas_model.lists.Guids._json_array_of_guids", rules=["EDL-01"])
def test__guids_reads_an_array_of_strings() -> None:
    """The body of ``purgeByIds``; any other shape is the endpoint's refusal."""
    assert Guids.model_validate(["g1", "g2"]).root == ["g1", "g2"]
    for body in NOT_ARRAYS:
        with pytest.raises(AtlasError) as raised:
            Guids.model_validate(body)
        assert raised.value.message == "Invalid body: a JSON array of GUIDs is expected"


@pytest.mark.covers("aurelius_atlas_model.lists.RelatedObjectIds._json_array_of_related_ids", rules=["GTA-01"])
def test__related_object_ids_reads_an_array_of_ids() -> None:
    """The body of ``assignTermToEntities``; each element stays the endpoint's to validate."""
    found = RelatedObjectIds.model_validate([{"guid": "g", "typeName": "t"}])
    assert found.root[0].guid == "g"
    with pytest.raises(AtlasError) as raised:
        RelatedObjectIds.model_validate({"guid": "g"})
    assert raised.value.message == "Invalid body: a JSON array of related object ids is expected"
