"""Unit tests for the error contract: the upstream failure and the Atlas-shaped body (LM-05, LM-07)."""

import pytest
from aurelius_atlas_lineage_model.errors import UpstreamError, atlas_error
from aurelius_atlas_lineage_model.globals import ATLAS_ERROR_CODE


@pytest.mark.covers("aurelius_atlas_lineage_model.errors.atlas_error", rules=["LM-07"])
def test__the_error_body_is_the_atlas_shape() -> None:
    """The Atlas error code and message on the given status (DV-22's body, the legacy's code)."""
    response = atlas_error(502, "the lineage service failed")

    assert response.status_code == 502
    body = bytes(response.body).decode()
    assert ATLAS_ERROR_CODE in body
    assert "the lineage service failed" in body


@pytest.mark.covers("aurelius_atlas_lineage_model.errors.atlas_error", rules=["LM-07"])
def test__the_upstream_failure_carries_its_status() -> None:
    """The chain's failure is the message and the status the route answers with (LM-05, LM-07)."""
    error = UpstreamError(400, "the lineage service rejected the request")

    assert error.status_code == 400
    assert str(error) == "the lineage service rejected the request"
