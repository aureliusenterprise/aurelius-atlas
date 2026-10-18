"""The patch record and its JSON (``AtlasPatch``, MDL-06)."""

import pytest
from aurelius_atlas_model.patches import TYPEDEF_PATCH_TYPE, AtlasPatch, PatchStatus


@pytest.mark.covers(rules=["MDL-06"])
def test__a_patch_record_reads_and_writes_atlas_json() -> None:
    """Java's names; the times are longs, 0 when unset, and kept; a null user is left out."""
    record = AtlasPatch.model_validate(
        {
            "id": "TYPEDEF_PATCH_0000_001",
            "description": "Add replication attributes",
            "type": TYPEDEF_PATCH_TYPE,
            "action": "ADD_ATTRIBUTE",
            "status": "APPLIED",
            "createdTime": 1700000000000,
        }
    )

    assert record.status is PatchStatus.APPLIED
    assert record.to_json() == {
        "id": "TYPEDEF_PATCH_0000_001",
        "description": "Add replication attributes",
        "type": "TYPEDEF_PATCH",
        "action": "ADD_ATTRIBUTE",
        "createdTime": 1700000000000,
        "updatedTime": 0,
        "status": "APPLIED",
    }
