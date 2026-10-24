"""The admin and error shapes of the server contract (CL-10; DD-203).

The typedef bodies are ``aurelius-atlas-model``'s, reused whole — there is
nothing to restate here for them (CL-10); these tests cover the shapes that
library never had.
"""

import pytest
from aurelius_atlas_server_client.models import AtlasErrorInfo, AtlasSessionInfo, AtlasStatus, AtlasVersion
from pydantic import ValidationError


@pytest.mark.covers(rules=["CL-10", "CL-06"])
def test__the_version_body_is_atlas_capitalised() -> None:
    """``Version``/``Revision``/``Name``/``Description`` — Atlas's keys (ADM-01, DV-03)."""
    version = AtlasVersion.model_validate(
        {"Version": "4.1.0", "Revision": "abc1234", "Name": "Aurelius Atlas", "Description": "the Python Atlas"}
    )

    assert version.version == "4.1.0"
    assert version.revision == "abc1234"
    assert version.name == "Aurelius Atlas"
    assert version.description == "the Python Atlas"


@pytest.mark.covers(rules=["CL-10"])
def test__the_status_body_names_the_service_state() -> None:
    """``Status`` — ``ACTIVE`` is the only state Aurelius Atlas has (ADM-02)."""
    assert AtlasStatus.model_validate({"Status": "ACTIVE"}).status == "ACTIVE"


@pytest.mark.covers(rules=["CL-10", "CL-06"])
def test__the_session_body_carries_the_settings_and_the_csrf_token() -> None:
    """``userName``/``groups``/``timezones``/``_csrfToken``; the ``atlas.*`` settings ride as extras (ADM-05, DV-04)."""
    session = AtlasSessionInfo.model_validate(
        {
            "userName": "analyst",
            "groups": ["atlas"],
            "timezones": ["UTC"],
            "_csrfToken": "token-1",
            "atlas.cluster": "primary",
        }
    )

    assert session.user_name == "analyst"
    assert session.groups == ["atlas"]
    assert session.timezones == ["UTC"]
    assert session.csrf_token == "token-1"  # noqa: S105 - a fixed fake token in a test, not a secret


@pytest.mark.covers(rules=["CL-10"])
def test__the_session_body_has_no_user_before_6_1() -> None:
    """The empty session is valid: no user, no groups, no token."""
    session = AtlasSessionInfo.model_validate({})

    assert session.user_name is None
    assert session.groups == []
    assert session.csrf_token is None


@pytest.mark.covers(rules=["CL-10"])
def test__the_error_body_is_the_atlas_error_shape() -> None:
    """``{errorCode, errorMessage}`` plus ``errorCause`` on the server-side codes (SRV-04)."""
    info = AtlasErrorInfo.model_validate(
        {"errorCode": "ATLAS-400-00-029", "errorMessage": "bad request", "errorCause": "the cause"}
    )

    assert info.error_code == "ATLAS-400-00-029"
    assert info.error_message == "bad request"
    assert info.error_cause == "the cause"


@pytest.mark.covers(rules=["CL-10"])
def test__a_body_that_is_not_the_error_shape_is_not_an_error() -> None:
    """The client's error parsing leans on this: a body without the code is no error (CL-04)."""
    with pytest.raises(ValidationError):
        AtlasErrorInfo.model_validate({"message": "not the Atlas shape"})
