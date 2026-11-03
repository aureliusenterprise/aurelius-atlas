"""The admin audit models (ADA-01, ADA-04, ADA-05), as Apache Atlas 2.4.0's ``AtlasAuditEntry`` and
``AuditSearchParameters`` read and write them.
"""  # noqa: D205 - one sentence

import pytest
from aurelius_atlas_model.atlas_audit import AtlasAuditEntry, AuditOperation, AuditSearchParameters
from aurelius_atlas_model.audit import EntityAuditActionV2


@pytest.mark.covers("aurelius_atlas_model.atlas_audit.AuditOperation.to_entity_audit_action_v2", rules=["ADA-05"])
def test__only_a_purge_is_an_entity_audit_action() -> None:
    """``PURGE`` is ``ENTITY_PURGE``; no other operation names an entity action."""
    assert AuditOperation.PURGE.to_entity_audit_action_v2() is EntityAuditActionV2.ENTITY_PURGE
    for operation in AuditOperation:
        if operation is not AuditOperation.PURGE:
            with pytest.raises(ValueError, match=f"Invalid operation for Entity Audit Event V2: {operation.value}"):
                operation.to_entity_audit_action_v2()


@pytest.mark.covers(rules=["ADA-01", "ADA-04"])
def test__an_entry_and_a_search_read_and_write_atlas_json() -> None:
    """Java names, null fields left out, ``resultCount`` always there; a search's nulls read as zero."""
    entry = AtlasAuditEntry.model_validate({"userName": "u", "operation": "PURGE", "startTime": 1, "clientId": "c"})
    search = AuditSearchParameters.model_validate(
        {
            "auditFilters": {"condition": "AND", "criterion": []},
            "limit": None,
            "sortBy": "startTime",
            "sortOrder": "DESCENDING",
        }
    )

    assert entry.to_json() == {
        "guid": "-1",
        "userName": "u",
        "operation": "PURGE",
        "startTime": 1,
        "clientId": "c",
        "resultCount": 0,
    }
    assert (search.limit, search.offset, search.sort_by) == (0, 0, "startTime")
    assert search.to_json()["sortOrder"] == "DESCENDING"
