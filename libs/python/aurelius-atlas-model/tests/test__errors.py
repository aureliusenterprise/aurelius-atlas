"""Atlas error codes and messages (TRG-15), copied from ``AtlasErrorCode`` of Apache Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode


@pytest.mark.covers("aurelius_atlas_model.errors.AtlasErrorCode.message", rules=["TRG-15"])
def test__an_error_code_fills_its_template_in_order() -> None:
    """``MessageFormat`` puts the parameters at ``{0}``, ``{1}``, ...; Java prints a null as ``null``."""
    assert AtlasErrorCode.INTERNAL_ERROR.message("boom") == "Internal server error boom"
    assert (
        AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_NON_EXISTING.message("t", "a", "inverseRef", "u", "b")
        == "t.a: invalid inverseRef constraint. Inverse attribute u.b does not exist"
    )
    assert AtlasErrorCode.TYPE_NAME_NOT_FOUND.message(None) == "Given typename null was invalid"


@pytest.mark.covers(rules=["TRG-15"])
@pytest.mark.parametrize(
    ("code", "status", "atlas_code"),
    [
        (AtlasErrorCode.CONSTRAINT_MISSING_PARAMS, 400, "ATLAS-400-00-007"),
        (AtlasErrorCode.INVALID_ATTRIBUTE_TYPE_FOR_CARDINALITY, 400, "ATLAS-400-00-012"),
        (AtlasErrorCode.CONSTRAINT_INVERSE_REF_ATTRIBUTE_INVALID_TYPE, 400, "ATLAS-400-00-01C"),
        (AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_NON_EXISTING, 400, "ATLAS-400-00-01D"),
        (AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_INVALID_TYPE, 400, "ATLAS-400-00-01E"),
        (AtlasErrorCode.CONSTRAINT_OWNED_REF_ATTRIBUTE_INVALID_TYPE, 400, "ATLAS-400-00-01F"),
        (AtlasErrorCode.ATTRIBUTE_TYPE_INVALID, 400, "ATLAS-400-00-081"),
        (AtlasErrorCode.TYPE_NAME_NOT_FOUND, 404, "ATLAS-404-00-001"),
        (AtlasErrorCode.TYPE_GUID_NOT_FOUND, 404, "ATLAS-404-00-002"),
        (AtlasErrorCode.INTERNAL_ERROR, 500, "ATLAS-500-00-001"),
        (AtlasErrorCode.FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK, 500, "ATLAS-500-00-005"),
    ],
)
def test__each_code_has_atlas_status_and_code(code: AtlasErrorCode, status: int, atlas_code: str) -> None:
    """The status and code of every member match ``AtlasErrorCode.java``."""
    assert (code.http_status, code.code) == (status, atlas_code)


@pytest.mark.covers(rules=["TRG-15"])
def test__an_error_keeps_its_code_parameters_message_and_cause() -> None:
    """``AtlasBaseException(errorCode, cause, params...)``."""
    cause = ValueError("disk full")
    error = AtlasError(AtlasErrorCode.TYPE_GUID_NOT_FOUND, "g-1", cause=cause)

    assert error.code is AtlasErrorCode.TYPE_GUID_NOT_FOUND
    assert error.params == ("g-1",)
    assert error.message == str(error) == "Given type guid g-1 was invalid"
    assert error.cause is cause
