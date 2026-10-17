"""Atlas errors and the body they are answered with (SRV-04, SRV-05), as ``AtlasBaseExceptionMapper`` does."""

import logging
from enum import Enum
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

LOGGER = logging.getLogger(__name__)

ATLAS_JSON_MEDIA_TYPE = "application/json; charset=UTF-8"
"""The media type of Atlas JSON responses (``Servlets.JSON_MEDIA_TYPE``)."""


class AtlasJSONResponse(JSONResponse):
    """A JSON response with the Atlas media type (SRV-05)."""

    media_type = ATLAS_JSON_MEDIA_TYPE


class AtlasErrorCode(Enum):
    """The Atlas error codes the server raises, with their HTTP status and message template (``AtlasErrorCode``)."""

    INTERNAL_ERROR = (500, "ATLAS-500-00-001", "Internal server error {0}")

    def __init__(self, http_status: int, code: str, template: str) -> None:
        self.http_status = http_status
        self.code = code
        self.template = template

    def message(self, *params: object) -> str:
        """Fill the template's ``{0}``, ``{1}``, ... with the parameters, as Java's ``MessageFormat`` does."""
        return self.template.format(*params)


class AtlasError(Exception):
    """An error the Atlas API answers with its own status and body."""

    def __init__(self, code: AtlasErrorCode, *params: object, cause: BaseException | None = None) -> None:
        self.code = code
        self.message = code.message(*params)
        self.cause = cause
        super().__init__(self.message)


async def atlas_error_handler(_request: Request, error: Exception) -> AtlasJSONResponse:
    """Answer an ``AtlasError`` with its status and ``{"errorCode", "errorMessage"[, "errorCause"]}`` (SRV-04)."""
    if not isinstance(error, AtlasError):  # pragma: no cover - registered for AtlasError only
        raise error
    if error.code.http_status >= 500:  # noqa: PLR2004 - server errors are logged, as Atlas does
        LOGGER.error("Atlas error %s: %s", error.code.code, error.message, exc_info=error.cause)
    body: dict[str, Any] = {"errorCode": error.code.code, "errorMessage": error.message}
    if error.cause is not None:
        body["errorCause"] = str(error.cause)
    return AtlasJSONResponse(status_code=error.code.http_status, content=body)
