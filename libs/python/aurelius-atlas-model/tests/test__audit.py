"""``EntityAuditEventV2`` (AUD-01, AUD-09), read from ``model.audit.EntityAuditEventV2`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2

A = "aurelius_atlas_model.audit"


@pytest.mark.covers(f"{A}.EntityAuditEventV2.to_json", rules=["AUD-01"])
def test__an_event_writes_every_field_nulls_included() -> None:
    """``JsonSerialize.Inclusion.ALWAYS``: a listed event has no entity and no type, and says so."""
    body = {
        "entityId": "g",
        "timestamp": 1000,
        "user": None,
        "action": "ENTITY_CREATE",
        "details": 'Created: {"typeName":"t"}',
        "eventKey": "g:1000:0:1001",
        "entity": None,
        "type": None,
    }

    event = EntityAuditEventV2.model_validate(body)
    with_entity = EntityAuditEventV2.model_validate({**body, "entity": {"typeName": "t", "guid": "g"}})

    assert event.action is EntityAuditActionV2.ENTITY_CREATE
    assert event.to_json() == body
    assert with_entity.to_json()["entity"]["guid"] == "g"


@pytest.mark.covers(f"{A}.EntityAuditEventV2.entity_header", rules=["AUD-06"])
def test__the_header_is_read_from_the_json_part_of_the_details() -> None:
    """From the first ``{``; none without one."""
    purged = EntityAuditEventV2(details='Purged: {"typeName":"t","guid":"g","attributes":{"name":"n"}}')

    header = purged.entity_header()

    assert header is not None
    assert (header.type_name, header.guid, header.attributes) == ("t", "g", {"name": "n"})
    assert EntityAuditEventV2(details="Deleted entity").entity_header() is None
    assert EntityAuditEventV2().entity_header() is None


@pytest.mark.covers(f"{A}.EntityAuditActionV2.from_string", rules=["AUD-09"])
def test__actions_are_read_by_name_or_tag_alias() -> None:
    """``TAG_ADD`` reads as ``CLASSIFICATION_ADD``; ``CUSTOM_ATTRIBUTE_UPDATE`` and unknown names fail."""
    assert EntityAuditActionV2.from_string("ENTITY_PURGE") is EntityAuditActionV2.ENTITY_PURGE
    assert EntityAuditActionV2.from_string("TAG_ADD") is EntityAuditActionV2.CLASSIFICATION_ADD
    assert EntityAuditActionV2.from_string("TAG_UPDATE") is EntityAuditActionV2.CLASSIFICATION_UPDATE
    assert EntityAuditActionV2.from_string("TAG_DELETE") is EntityAuditActionV2.CLASSIFICATION_DELETE
    for name in ("CUSTOM_ATTRIBUTE_UPDATE", "entity_create", "NOPE"):
        with pytest.raises(ValueError, match=name):
            EntityAuditActionV2.from_string(name)
