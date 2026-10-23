"""The admin and error shapes of the Atlas metadata API (CL-10, 8.4).

The response bodies the server's ``routes/admin.py`` and its error handler answer,
stated as models so a client can parse them and a test can name them. The typedef
bodies are not restated here — they are ``aurelius-atlas-model``'s (DD-002), reused
whole (CL-10); this module covers only what that library never had: the admin
answers, and the ``{errorCode, errorMessage}`` body of every Atlas error (SRV-04).
"""

from aurelius_atlas_model.typedef import AtlasModel
from pydantic import Field


class AtlasVersion(AtlasModel):
    """The body of ``GET /api/atlas/admin/version`` (ADM-01, DV-03; CL-10).

    The keys are Atlas's, capitalised; the Aurelius server reports its own name
    and description there (DV-03).
    """

    version: str = Field(alias="Version")
    revision: str = Field(alias="Revision")
    name: str = Field(alias="Name")
    description: str = Field(alias="Description")


class AtlasStatus(AtlasModel):
    """The body of ``GET /api/atlas/admin/status`` (ADM-02; CL-10)."""

    status: str = Field(alias="Status")
    """The service state; the only one Aurelius Atlas has is ``ACTIVE``."""


class AtlasSessionInfo(AtlasModel):
    """The body of ``GET /api/atlas/admin/session`` (ADM-05, DV-04; CL-10).

    The ``atlas.*`` UI settings ride along as extras; the typed fields are the
    session's own — no user until 6.1, so ``user_name`` answers ``None``.
    """

    user_name: str | None = None
    groups: list[str] = Field(default_factory=list)
    timezones: list[str] = Field(default_factory=list)
    csrf_token: str | None = Field(alias="_csrfToken", default=None)


class AtlasErrorInfo(AtlasModel):
    """The body every Atlas error is answered with (SRV-04; CL-10).

    ``{errorCode, errorMessage}``, plus ``errorCause`` on the server-side codes.
    The 8.x auxiliary apps reuse the shape with the ``ATLAS-400-00-029`` code.
    """

    error_code: str = Field(alias="errorCode")
    error_message: str = Field(alias="errorMessage")
    error_cause: str | None = Field(alias="errorCause", default=None)
