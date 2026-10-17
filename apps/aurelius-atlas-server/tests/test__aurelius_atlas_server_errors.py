import json

import pytest
from aurelius_atlas_server.errors import ATLAS_JSON_MEDIA_TYPE, AtlasError, AtlasErrorCode, atlas_error_handler


@pytest.mark.covers("aurelius_atlas_server.errors.atlas_error_handler", rules=["SRV-04", "SRV-05"])
@pytest.mark.parametrize(
    ("cause", "body"),
    [
        (None, {"errorCode": "ATLAS-500-00-001", "errorMessage": "Internal server error x"}),
        (
            ValueError("disk full"),
            {"errorCode": "ATLAS-500-00-001", "errorMessage": "Internal server error x", "errorCause": "disk full"},
        ),
    ],
)
async def test__error_handler_answers_with_the_atlas_body(cause: Exception | None, body: dict[str, str]) -> None:
    """The status comes from the error code; ``errorCause`` appears only when there is a cause."""
    response = await atlas_error_handler(None, AtlasError(AtlasErrorCode.INTERNAL_ERROR, "x", cause=cause))  # pyright: ignore[reportArgumentType] - the request is not used

    assert response.status_code == 500
    assert response.headers["content-type"] == ATLAS_JSON_MEDIA_TYPE
    assert json.loads(bytes(response.body)) == body
