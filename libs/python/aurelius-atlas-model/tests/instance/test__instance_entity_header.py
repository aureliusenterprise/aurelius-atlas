"""``AtlasEntityHeader`` (ENT-14), read from ``org.apache.atlas.model.instance.AtlasEntityHeader`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntity,
    AtlasEntityHeader,
    AtlasTermAssignmentHeader,
    EntityStatus,
)


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-14"])
def test__a_header_reads_and_writes_its_fields() -> None:
    """The struct's fields and the header's; labels once each."""
    body = {
        "typeName": "hive_table",
        "attributes": {"qualifiedName": "t@cm"},
        "guid": "g",
        "status": "DELETED",
        "displayText": "t",
        "classificationNames": ["PII"],
        "classifications": [{"typeName": "PII", "entityStatus": "ACTIVE"}],
        "meaningNames": ["term"],
        "meanings": [{"termGuid": "t", "confidence": 0}],
        "isIncomplete": True,
        "labels": ["a", "a"],
    }

    assert AtlasEntityHeader.model_validate(body).to_json() == {**body, "labels": ["a"]}


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-14"])
def test__a_header_without_them_is_active_and_complete() -> None:
    """The fields' initial values: ``status`` ``ACTIVE``, ``isIncomplete`` false."""
    assert AtlasEntityHeader.model_validate({}).to_json() == {"status": "ACTIVE", "isIncomplete": False}


@pytest.mark.covers("aurelius_atlas_model.instance.entity_header.AtlasEntityHeader.of", rules=["ENT-14"])
def test__the_header_of_an_entity() -> None:
    """``AtlasEntityHeader(AtlasEntity)``: classification names and labels only when there are any; no meanings."""
    entity = AtlasEntity(
        type_name="t",
        attributes={"a": 1},
        guid="g",
        status=EntityStatus.DELETED,
        is_incomplete=True,
        classifications=[AtlasClassification(type_name="PII")],
        labels=["l"],
        meanings=[AtlasTermAssignmentHeader(term_guid="m")],
    )

    header = AtlasEntityHeader.of(entity)
    bare = AtlasEntityHeader.of(AtlasEntity(guid="b", classifications=[], labels=[]))

    assert (header.type_name, header.attributes, header.guid, header.status) == ("t", {"a": 1}, "g", "DELETED")
    assert (header.classification_names, header.labels, header.is_incomplete) == (["PII"], ["l"], True)
    assert header.meanings is None
    assert (bare.classification_names, bare.labels, bare.classifications, bare.status) == (None, None, [], None)
