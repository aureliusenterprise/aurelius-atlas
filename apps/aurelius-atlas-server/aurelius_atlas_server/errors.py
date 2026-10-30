"""The body Atlas errors are answered with (SRV-04, SRV-05, SRV-07), as ``AtlasBaseExceptionMapper`` does.

The errors themselves live in ``aurelius_atlas_model.errors`` (DD-023) and are re-exported here.
5xx bodies are opaque: the cause is logged, and the trace id rides along for correlation (DD-235, DV-85).
"""

import logging
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from fastapi import Request
from fastapi.responses import JSONResponse
from opentelemetry import trace as otel_trace

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
    """Answer an ``AtlasError`` with its status and ``{"errorCode", "errorMessage"[, "errorCause"]}`` (SRV-04).

    A server error (5xx) keeps Atlas's two-field shape and adds the trace id of the request as
    ``requestId`` (SRV-07, DD-235): the cause's text goes to the log, never to the wire, so a
    wrapped store or transport failure cannot leak internals; the id ties the response to the
    logged stack and the trace. A client error (4xx) echoes the cause as Atlas does (SRV-04) —
    there the cause is the request's own defect, not server internals.
    """
    if not isinstance(error, AtlasError):  # pragma: no cover - registered for AtlasError only
        raise error
    body: dict[str, Any] = {"errorCode": error.code.code, "errorMessage": error.message}
    headers: dict[str, str] = {}
    if error.code.http_status >= 500:  # noqa: PLR2004 - server errors are logged, as Atlas does
        LOGGER.error("Atlas error %s: %s", error.code.code, error.message, exc_info=error.cause)
        trace_id = _trace_id()
        if trace_id is not None:
            body["requestId"] = trace_id
            headers["X-Request-Id"] = trace_id
    elif error.cause is not None:
        body["errorCause"] = str(error.cause)
    return AtlasJSONResponse(status_code=error.code.http_status, content=body, headers=headers)


def _trace_id() -> str | None:
    """The trace id of the current span, 32 hex digits; None without a recording span.

    ``create_app`` instruments the app (``FastAPIInstrumentor``, app.py), so every request —
    in-process tests and the image alike — carries a recording span, and a 5xx answer names
    it (SRV-07). A call outside a span (a bare handler call, no server) answers with no id.
    """
    span = otel_trace.get_current_span()
    context = span.get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else None
