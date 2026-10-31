"""``BulkImportResponse``: what an import made and what it could not (GIM-02).

Atlas writes the response with ``@AtlasJSON``, its empty lists left out, and each ``ImportInfo`` with Jackson's
defaults: its four properties with getters, nulls included, its row number not at all.
"""

from enum import StrEnum
from typing import Any

from pydantic import Field

from aurelius_atlas_model.base import AtlasModel


class ImportStatus(StrEnum):
    """``BulkImportResponse.ImportStatus``."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ImportInfo(AtlasModel):
    """``ImportInfo``: the glossary and term of a row, its status, remarks and row number."""

    parent_object_name: str | None = None
    child_object_name: str | None = None
    import_status: ImportStatus | None = None
    remarks: str | None = ""
    row_number: int = -1

    def to_json(self) -> dict[str, Any]:
        """The four properties Atlas writes, nulls included."""
        return {
            "parentObjectName": self.parent_object_name,
            "childObjectName": self.child_object_name,
            "importStatus": None if self.import_status is None else self.import_status.value,
            "remarks": self.remarks,
        }


class BulkImportResponse(AtlasModel):
    """``BulkImportResponse``: the rows that failed and those that succeeded."""

    failed_import_info_list: list[ImportInfo] = Field(default_factory=list)
    success_import_info_list: list[ImportInfo] = Field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        """``NON_EMPTY``: each list only when it holds an entry."""
        found: dict[str, Any] = {}
        if self.failed_import_info_list:
            found["failedImportInfoList"] = [info.to_json() for info in self.failed_import_info_list]
        if self.success_import_info_list:
            found["successImportInfoList"] = [info.to_json() for info in self.success_import_info_list]
        return found
