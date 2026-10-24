"""The admin and error shapes of the Atlas metadata API (CL-10, 8.4).

The response bodies the server's ``routes/admin.py`` and its error handler answer,
stated as models so a client can parse them and a test can name them. The typedef
bodies are not restated here — they are ``aurelius-atlas-model``'s (DD-002), reused
whole (CL-10); this module covers only what that library never had: the admin
answers, and the ``{errorCode, errorMessage}`` body of every Atlas error (SRV-04).
"""

from aurelius_atlas_model.typedef import AtlasModel
from pydantic import Field


# ADM-01; DV-03; CL-10. The keys are Atlas's, capitalised; the Aurelius
# server reports its own name and description there (DV-03).
class AtlasVersion(AtlasModel):
    """The body of ``GET /api/atlas/admin/version``."""

    version: str = Field(alias="Version", description="The software version.")

    revision: str = Field(alias="Revision", description="The source revision the software was built from.")

    name: str = Field(alias="Name", description="The software name.")

    description: str = Field(alias="Description", description="A description of the software.")


# ADM-02; CL-10.
class AtlasStatus(AtlasModel):
    """The body of ``GET /api/atlas/admin/status``."""

    status: str = Field(alias="Status", description="The service state; the only state is ``ACTIVE``.")


# ADM-05; DV-04; CL-10. The ``atlas.*`` UI settings ride along as extras;
# the typed fields are the session's own — the server has no authenticated
# user yet, so ``user_name`` answers ``None``.
class AtlasSessionInfo(AtlasModel):
    """The body of ``GET /api/atlas/admin/session``."""

    user_name: str | None = Field(default=None, description="The signed-in user's name, when known.")

    groups: list[str] = Field(default_factory=list, description="The groups of the signed-in user.")

    timezones: list[str] = Field(default_factory=list, description="The timezones the UI offers.")

    csrf_token: str | None = Field(
        alias="_csrfToken",
        default=None,
        description="The CSRF token mutating requests must carry.",
    )


# SRV-04; CL-10. ``{errorCode, errorMessage}``, plus ``errorCause`` on the
# server-side codes. The auxiliary apps reuse the shape with the
# ``ATLAS-400-00-029`` code.
class AtlasErrorInfo(AtlasModel):
    """The body every Atlas error is answered with."""

    error_code: str = Field(alias="errorCode", description="The Atlas error code, e.g. ``ATLAS-400-00-007``.")

    error_message: str = Field(alias="errorMessage", description="The human-readable error message.")

    error_cause: str | None = Field(
        alias="errorCause",
        default=None,
        description="The cause of a server-side error, when there is one.",
    )
