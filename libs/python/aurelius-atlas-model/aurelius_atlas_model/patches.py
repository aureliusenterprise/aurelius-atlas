"""Patch records: which patch was applied, and how it ended (``org.apache.atlas.model.patches``, MDL-06)."""

from enum import StrEnum

from pydantic import Field

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
    """The record of one applied typedef patch; the times are epoch milliseconds."""

    id: str | None = Field(default=None, description="The unique id of the patch.")

    description: str | None = Field(default=None, description="A description of the patch.")

    type: str | None = Field(default=None, description="The kind of patch; typedef patches use ``TYPEDEF_PATCH``.")

    action: str | None = Field(default=None, description="The action the patch performs, e.g. ``ADD_ATTRIBUTE``.")

    updated_by: str | None = Field(default=None, description="The user who applied the patch.")

    created_by: str | None = Field(default=None, description="The user who defined the patch.")

    created_time: int = Field(default=0, description="When the patch was defined, in epoch milliseconds.")

    updated_time: int = Field(default=0, description="When the patch was applied, in epoch milliseconds.")

    status: PatchStatus | None = Field(
        default=None,
        description="How the patch ended: UNKNOWN, APPLIED, SKIPPED, or FAILED.",
    )
