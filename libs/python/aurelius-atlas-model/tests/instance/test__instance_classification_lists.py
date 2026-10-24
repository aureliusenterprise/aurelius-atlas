"""``AtlasClassifications`` and ``ClassificationAssociateRequest`` (CLS-01).

Read from ``org.apache.atlas.model.PList``, ``AtlasClassification.AtlasClassifications`` and
``ClassificationAssociateRequest`` of Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.instance import AtlasClassification, AtlasClassifications, ClassificationAssociateRequest


@pytest.mark.covers("aurelius_atlas_model.plist.PList.of", rules=["CLS-01"])
def test__classifications_are_a_whole_page_of_one_list() -> None:
    """``PList(List)``: start 0, page size and total count the length, sort type ``NONE``; nulls are left out."""
    found = AtlasClassifications.of([AtlasClassification(type_name="pii")])

    assert found.to_json() == {
        "list": [{"typeName": "pii", "entityStatus": "ACTIVE"}],
        "startIndex": 0,
        "pageSize": 1,
        "totalCount": 1,
        "sortType": "NONE",
    }
    assert AtlasClassifications().to_json() == {"startIndex": 0, "pageSize": 0, "totalCount": 0}


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["CLS-01"])
def test__an_associate_request_names_entities_by_guid_or_by_unique_attributes() -> None:
    """Its four fields, in Atlas's JSON."""
    body = {
        "classification": {"typeName": "pii", "entityStatus": "ACTIVE"},
        "entityGuids": ["g"],
        "entitiesUniqueAttributes": [{"qualifiedName": "t@cl"}],
        "entityTypeName": "hive_table",
    }

    assert ClassificationAssociateRequest.model_validate(body).to_json() == body
