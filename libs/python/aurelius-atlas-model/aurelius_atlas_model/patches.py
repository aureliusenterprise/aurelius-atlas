"""Patch records: which patch was applied, and how it ended (``org.apache.atlas.model.patches``, MDL-06)."""

from enum import StrEnum

from aurelius_atlas_model.base import AtlasModel

TYPEDEF_PATCH_TYPE = "TYPEDEF_PATCH"
"""The ``type`` of a typedef patch's record (``AtlasTypeDefStoreInitializer.TYPEDEF_PATCH_TYPE``)."""


class PatchStatus(StrEnum):
    """How a patch ended (``AtlasPatch.PatchStatus``)."""

    UNKNOWN = "UNKNOWN"
    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class AtlasPatch(AtlasModel):
    """The record of one patch (``AtlasPatch``); the times are epoch milliseconds."""

    id: str | None = None
    description: str | None = None
    type: str | None = None
    action: str | None = None
    updated_by: str | None = None
    created_by: str | None = None
    created_time: int = 0
    updated_time: int = 0
    status: PatchStatus | None = None
