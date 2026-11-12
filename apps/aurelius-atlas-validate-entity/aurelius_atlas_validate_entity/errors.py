"""The app's error contract: the catalogue failure and the Atlas-shaped body (VEV-01, VEV-06)."""

from fastapi.responses import JSONResponse

from aurelius_atlas_validate_entity.globals import ATLAS_ERROR_CODE


class UpstreamError(Exception):
    """A catalogue failure the caller is answered for, with the status to answer (VEV-06).

    The mint refusal, the open circuit, and a failed rule read all arrive here;
    the root's handler turns each into the 502 answer (DV-80's sibling).
    """

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        """The HTTP status the route answers with: the 502 of VEV-06."""


class DraftRejectedError(Exception):
    """A draft the app will not read (VEV-01): the handler answers it 400.

    The legacy Flask service crashed on such a body — a 500; the port states
    the 400 of DV-79's posture, in the Atlas error body.
    """


def atlas_error(status_code: int, message: str) -> JSONResponse:
    """The Atlas-shaped error body on the given status (VEV-01/06, DV-72's posture)."""
    return JSONResponse(status_code=status_code, content={"errorCode": ATLAS_ERROR_CODE, "errorMessage": message})
