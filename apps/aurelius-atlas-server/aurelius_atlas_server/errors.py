"""The body Atlas errors are answered with (SRV-04, SRV-05), as ``AtlasBaseExceptionMapper`` does.

The errors themselves live in ``aurelius_atlas_model.errors`` (DD-023) and are re-exported here.
"""

import logging
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from fastapi import Request
from fastapi.responses import JSONResponse

__all__ = ["ATLAS_JSON_MEDIA_TYPE", "AtlasError", "AtlasErrorCode", "AtlasJSONResponse", "atlas_error_handler"]

LOGGER = logging.getLogger(__name__)

ATLAS_JSON_MEDIA_TYPE = "application/json; charset=UTF-8"
"""The media type of Atlas JSON responses (``Servlets.JSON_MEDIA_TYPE``)."""


class AtlasJSONResponse(JSONResponse):
    """A JSON response with the Atlas media type (SRV-05), written by Atlas's JSON codec (VAL-01, DD-039)."""

    media_type = ATLAS_JSON_MEDIA_TYPE

    def render(self, content: Any) -> bytes:  # noqa: ANN401 - any JSON value
        """Decimals keep their digits and dates are epoch milliseconds, as Jackson writes them."""
        return codec.dumps(content)


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
