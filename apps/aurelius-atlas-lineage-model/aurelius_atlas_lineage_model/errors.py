"""The app's error contract: the upstream failure and the Atlas-shaped body (LM-05, LM-07)."""

from fastapi.responses import JSONResponse

from aurelius_atlas_lineage_model.globals import ATLAS_ERROR_CODE


class UpstreamError(Exception):
    """An upstream Atlas/data2model failure, with the status to answer (LM-05, LM-07)."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        """The HTTP status the route answers with (404 → 204, 400 → 400, else 502)."""


def atlas_error(status_code: int, message: str) -> JSONResponse:
    """The Atlas-shaped error body on the given status (LM-07)."""
    return JSONResponse(status_code=status_code, content={"errorCode": ATLAS_ERROR_CODE, "errorMessage": message})
