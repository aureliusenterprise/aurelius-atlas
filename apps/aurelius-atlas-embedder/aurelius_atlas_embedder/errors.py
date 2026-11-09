"""Refusals in OpenAI's error shape, for the app's own errors and for invalid requests (EMB-05)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aurelius_atlas_embedder.schemas import ErrorBody, ErrorResponse

INVALID_REQUEST = "invalid_request_error"
"""OpenAI's error type for a request it refuses."""


class EmbedderError(Exception):
    """A refusal with its status, as OpenAI words one."""

    def __init__(self, status: int, message: str, *, param: str | None = None, code: str | None = None) -> None:
        """A refusal answered with ``status``."""
        super().__init__(message)
        self.status = status
        self.body = ErrorBody(message=message, type=INVALID_REQUEST, param=param, code=code)


def error_response(status: int, body: ErrorBody) -> JSONResponse:
    """``body`` as the answer with ``status``."""
    return JSONResponse(status_code=status, content=ErrorResponse(error=body).model_dump())


async def _embedder_error(_request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, EmbedderError)  # noqa: S101 - registered for this class only
    return error_response(error.status, error.body)


async def _validation_error(_request: Request, error: Exception) -> JSONResponse:
    """422 for a request that does not validate, naming the first field at fault (EMB-05)."""
    assert isinstance(error, RequestValidationError)  # noqa: S101 - registered for this class only
    first = error.errors()[0] if error.errors() else {}
    location = [str(part) for part in first.get("loc", ()) if part != "body"]
    param = location[0] if location else None
    message = f"{'.'.join(location) or 'body'}: {first.get('msg', 'invalid request')}"
    return error_response(422, ErrorBody(message=message, type=INVALID_REQUEST, param=param))


def install_error_handlers(app: FastAPI) -> None:
    """Answer refusals and invalid requests in OpenAI's error shape (EMB-05)."""
    app.add_exception_handler(EmbedderError, _embedder_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
