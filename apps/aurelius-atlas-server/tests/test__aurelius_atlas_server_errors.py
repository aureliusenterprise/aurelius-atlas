import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from aurelius_atlas_server.errors import (
    ATLAS_JSON_MEDIA_TYPE,
    AtlasError,
    AtlasErrorCode,
    AtlasJSONResponse,
    atlas_error_handler,
)


@pytest.mark.covers("aurelius_atlas_server.errors.atlas_error_handler", rules=["SRV-04", "SRV-05", "SRV-07"])
@pytest.mark.parametrize(
    ("cause", "body"),
    [
        (None, {"errorCode": "ATLAS-500-00-001", "errorMessage": "Internal server error x"}),
        # A 5xx answer is opaque: the cause's text is logged, never echoed (SRV-07, DD-235, DV-85).
        (ValueError("disk full"), {"errorCode": "ATLAS-500-00-001", "errorMessage": "Internal server error x"}),
    ],
)
async def test__error_handler_answers_with_the_atlas_body(cause: Exception | None, body: dict[str, str]) -> None:
    """The status comes from the error code; a 5xx body has no cause, and no span means no requestId."""
    response = await atlas_error_handler(
        None,  # pyright: ignore[reportArgumentType] - the request is not used
        AtlasError(AtlasErrorCode.INTERNAL_ERROR, "x", cause=cause),
    )

    assert response.status_code == 500
    assert response.headers["content-type"] == ATLAS_JSON_MEDIA_TYPE
    assert json.loads(bytes(response.body)) == body


@pytest.mark.covers("aurelius_atlas_server.errors.atlas_error_handler", rules=["SRV-04", "SRV-07"])
async def test__client_errors_echo_the_cause_as_atlas_does() -> None:
    """A 4xx cause is the request's own defect: Atlas echoes it, Aurelius keeps the field (SRV-04)."""
    response = await atlas_error_handler(
        None,  # pyright: ignore[reportArgumentType] - the request is not used
        AtlasError(AtlasErrorCode.INVALID_PARAMETERS, "name", cause=ValueError("name is required")),
    )

    assert response.status_code == 400
    assert json.loads(bytes(response.body)) == {
        "errorCode": "ATLAS-400-00-01A",
        "errorMessage": "invalid parameters: name",
        "errorCause": "name is required",
    }


@pytest.mark.covers("aurelius_atlas_server.errors.AtlasJSONResponse.render", rules=["VAL-01"])
def test__responses_are_written_by_atlas_s_json_codec() -> None:
    """Decimals keep their digits and dates are epoch milliseconds, as Jackson writes them (DD-039)."""
    response = AtlasJSONResponse(content={"size": Decimal("1.10"), "at": datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC)})

    assert bytes(response.body) == b'{"size":1.10,"at":1000}'
    assert response.headers["content-type"] == ATLAS_JSON_MEDIA_TYPE
