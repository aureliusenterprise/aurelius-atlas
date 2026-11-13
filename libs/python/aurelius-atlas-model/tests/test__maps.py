"""The JSON map bodies the endpoints read where Java declares no class (DV-10).

Each is the request as it arrives, checked by its own model; these tests pin the shape each model lets
through and the endpoint's refusal text for any other body.
"""

import pytest
from aurelius_atlas_model.errors import AtlasError
from aurelius_atlas_model.maps import AttributeValues, BusinessAttributesMap, JsonValue


@pytest.mark.covers(rules=["EWR-15"])
def test__a_json_value_reads_any_json() -> None:
    """``partialUpdateEntityAttrByGuid``'s new value: Java's plain ``Object``, so anything is read."""
    for value in (None, 3, "s", True, [1, 2], {"a": None}):
        assert JsonValue.model_validate(value).root == value


@pytest.mark.covers(
    "aurelius_atlas_model.maps.AttributeValues._json_object", rules=["GTM-04", "GCT-04", "GLS-04", "BMD-01", "BMD-03"]
)
def test__attribute_values_read_an_object_of_anything() -> None:
    """The glossary ``/partial`` and business metadata bodies: names to values of any kind."""
    found = AttributeValues.model_validate({"name": "n", "count": 3, "tags": ["a"], "removed": None})

    assert found.root == {"name": "n", "count": 3, "tags": ["a"], "removed": None}
    assert found.model_dump() == found.root


@pytest.mark.covers("aurelius_atlas_model.maps.AttributeValues._json_object", rules=["BMD-01"])
def test__attribute_values_refuse_any_other_body() -> None:
    """A body that is no JSON object is the endpoint's ``BAD_REQUEST`` (DV-10)."""
    for body in (["a"], "a", 3, None):
        with pytest.raises(AtlasError) as raised:
            AttributeValues.model_validate(body)
        assert raised.value.message == "Invalid body: a JSON object of attribute values is expected"


@pytest.mark.covers(
    "aurelius_atlas_model.maps.BusinessAttributesMap._json_object_of_value_maps", rules=["BMD-01", "BMD-05"]
)
def test__a_business_metadata_map_keeps_a_null_value() -> None:
    """A name given null removes that metadata's attributes, so the null must survive the read."""
    found = BusinessAttributesMap.model_validate({"term": {"owner": "ann"}, "tag": None})

    assert found.root == {"term": {"owner": "ann"}, "tag": None}


@pytest.mark.covers("aurelius_atlas_model.maps.BusinessAttributesMap._json_object_of_value_maps", rules=["BMD-01"])
def test__a_business_metadata_map_refuses_any_other_body() -> None:
    """A list, or a value that is neither a map nor null, is the endpoint's ``BAD_REQUEST`` (DV-10)."""
    for body in (["a"], {"bm_a": 1}, "a"):
        with pytest.raises(AtlasError) as raised:
            BusinessAttributesMap.model_validate(body)
        assert raised.value.message == (
            "Invalid body: a JSON object of attribute values by business metadata is expected"
        )
