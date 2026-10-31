"""``BulkImportResponse`` and ``ImportInfo`` (GIM-02), as Atlas 2.4.0 writes them."""

import pytest
from aurelius_atlas_model.bulk_import import BulkImportResponse, ImportInfo, ImportStatus

B = "aurelius_atlas_model.bulk_import"


@pytest.mark.covers(f"{B}.BulkImportResponse.to_json", f"{B}.ImportInfo.to_json", rules=["GIM-02"])
def test__the_response_leaves_out_empty_lists_and_row_numbers() -> None:
    """``@AtlasJSON`` ``NON_EMPTY`` lists; ``ImportInfo`` with nulls and without its row number."""
    failed = ImportInfo(parent_object_name="g", import_status=ImportStatus.FAILED, remarks="r", row_number=3)
    created = ImportInfo(parent_object_name="g", child_object_name="t", import_status=ImportStatus.SUCCESS)
    assert BulkImportResponse(failed_import_info_list=[failed], success_import_info_list=[created]).to_json() == {
        "failedImportInfoList": [
            {"parentObjectName": "g", "childObjectName": None, "importStatus": "FAILED", "remarks": "r"}
        ],
        "successImportInfoList": [
            {"parentObjectName": "g", "childObjectName": "t", "importStatus": "SUCCESS", "remarks": ""}
        ],
    }
    assert BulkImportResponse().to_json() == {}
    assert ImportInfo().to_json() == {
        "parentObjectName": None,
        "childObjectName": None,
        "importStatus": None,
        "remarks": "",
    }
