"""``AtlasEntity`` (ENT-04 to ENT-08).

Read from ``org.apache.atlas.model.instance.AtlasEntity`` of Atlas 2.4.0, and the entities Atlas's hive hook
tests send (``addons/hive-bridge/src/test/resources/json``).
"""

from datetime import UTC, datetime

import pytest
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntity,
    AtlasTermAssignmentHeader,
    EntityStatus,
    next_internal_id,
)


@pytest.mark.covers("aurelius_atlas_model.instance.entity.next_internal_id", rules=["ENT-04"])
def test__temporary_guids_are_minus_a_number_and_never_repeat() -> None:
    """``nextInternalId``: ``-`` and a number counted up from the clock."""
    first, second = next_internal_id(), next_internal_id()

    assert first.startswith("-")
    assert first[1:].isdigit()
    assert int(second[1:]) == int(first[1:]) + 1


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-04", "ENT-05"])
def test__an_entity_read_from_nothing_has_init_s_defaults() -> None:
    """The no-argument constructor's ``init()``: a temporary GUID, ``status`` cleared, ``version`` 0."""
    entity = AtlasEntity.model_validate({})

    assert entity.status is None
    assert entity.to_json() == {
        "guid": entity.guid,
        "proxy": False,
        "isIncomplete": False,
        "provenanceType": 0,
        "version": 0,
    }
    assert str(entity.guid).startswith("-")
    assert AtlasEntity().guid != entity.guid


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-04"])
def test__a_field_given_as_null_stays_null() -> None:
    """Jackson calls each setter with the null; the wrapper types keep it."""
    body = {"guid": None, "isProxy": None, "isIncomplete": None, "provenanceType": None, "version": None}

    assert AtlasEntity.model_validate(body).to_json() == {}


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-05"])
def test__is_proxy_is_read_as_is_proxy_and_written_as_proxy() -> None:
    """Jackson names the ``Boolean isProxy()`` getter ``proxy``; the setter ``setIsProxy`` reads ``isProxy``.

    Atlas's own hive hook messages carry ``"proxy": false``, which reading ignores.
    """
    assert AtlasEntity.model_validate({"isProxy": True}).to_json()["proxy"] is True
    assert AtlasEntity.model_validate({"proxy": True}).is_proxy is False


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-05", "ENT-07"])
def test__every_field_is_read_and_written_under_its_java_name() -> None:
    """The getters of ``AtlasEntity``; the sets hold each label and task once."""
    body = {
        "typeName": "hive_table",
        "attributes": {"name": "t"},
        "guid": "g",
        "homeId": "h",
        "isIncomplete": True,
        "provenanceType": 1,
        "status": "ACTIVE",
        "createdBy": "admin",
        "updatedBy": "admin",
        "createTime": 1700000000000,
        "updateTime": 1700000000001,
        "version": 3,
        "relationshipAttributes": {"db": {"guid": "d"}},
        "classifications": [{"typeName": "PII", "entityStatus": "ACTIVE"}],
        "meanings": [{"termGuid": "t", "confidence": 0}],
        "customAttributes": {"k": "v"},
        "businessAttributes": {"bm": {"a": 1}},
        "labels": ["x", "y", "x"],
        "pendingTasks": ["task"],
    }

    written = AtlasEntity.model_validate(body).to_json()

    assert written == {**body, "proxy": False, "labels": ["x", "y"]}


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-06"])
def test__times_are_epoch_milliseconds_read_also_from_iso_strings() -> None:
    """``java.util.Date`` with Jackson's defaults, as TDM-05."""
    entity = AtlasEntity.model_validate({"createTime": 1000, "updateTime": "1970-01-01T00:00:02Z"})

    assert entity.create_time == datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC)
    assert (entity.to_json()["createTime"], entity.to_json()["updateTime"]) == (1000, 2000)


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-07"])
def test__labels_and_pending_tasks_may_be_null_or_empty() -> None:
    """``Set<String>`` fields: null is left out, an empty set is written."""
    entity = AtlasEntity.model_validate({"labels": [], "pendingTasks": None})

    assert entity.to_json()["labels"] == []
    assert "pendingTasks" not in entity.to_json()


@pytest.mark.covers(
    "aurelius_atlas_model.instance.entity.AtlasEntity.has_relationship_attribute",
    "aurelius_atlas_model.instance.entity.AtlasEntity.get_relationship_attribute",
    "aurelius_atlas_model.instance.entity.AtlasEntity.set_relationship_attribute",
    rules=["ENT-08"],
)
def test__relationship_attributes_are_found_and_set_by_name() -> None:
    """``setRelationshipAttribute`` creates the map; ``hasRelationshipAttribute`` counts a null value."""
    entity = AtlasEntity()

    assert (entity.has_relationship_attribute("db"), entity.get_relationship_attribute("db")) == (False, None)
    entity.set_relationship_attribute("db", None)

    assert entity.has_relationship_attribute("db")
    assert entity.relationship_attributes == {"db": None}


@pytest.mark.covers(
    "aurelius_atlas_model.instance.entity.AtlasEntity.get_business_attribute",
    "aurelius_atlas_model.instance.entity.AtlasEntity.set_business_attribute",
    rules=["ENT-08"],
)
def test__business_attributes_are_set_by_business_metadata_and_name() -> None:
    """``setBusinessAttribute`` creates both maps; a missing one reads as None."""
    entity = AtlasEntity()

    assert entity.get_business_attribute("bm", "a") is None
    entity.set_business_attribute("bm", "a", 1)
    entity.set_business_attribute("bm", "b", 2)

    assert entity.business_attributes == {"bm": {"a": 1, "b": 2}}
    assert entity.get_business_attribute("bm", "b") == 2
    assert entity.get_business_attribute("other", "a") is None


@pytest.mark.covers(
    "aurelius_atlas_model.instance.entity.AtlasEntity.add_classifications",
    "aurelius_atlas_model.instance.entity.AtlasEntity.add_meaning",
    rules=["ENT-08"],
)
def test__classifications_and_meanings_are_appended() -> None:
    """``addClassifications`` and ``addMeaning`` create the list, then append."""
    entity = AtlasEntity(status=EntityStatus.ACTIVE)

    entity.add_classifications([AtlasClassification(type_name="a")])
    entity.add_classifications([AtlasClassification(type_name="b")])
    entity.add_meaning(AtlasTermAssignmentHeader(term_guid="t"))

    assert [classification.type_name for classification in entity.classifications or []] == ["a", "b"]
    assert [meaning.term_guid for meaning in entity.meanings or []] == ["t"]
