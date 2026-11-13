"""The shared JSON helpers of ``aurelius_atlas_model.base`` (DD-037)."""

import pytest
from aurelius_atlas_model.base import ATLAS_REQUEST, empty_when_null, null_when_empty
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntity


@pytest.mark.covers("aurelius_atlas_model.base._body_guid", rules=["DV-162"])
def test__a_body_guid_is_checked_only_as_a_request() -> None:
    """A request body must name a GUID as placeholder or UUID text; internal code and answers take any (DV-162)."""
    body = {"guid": "nope", "typeName": "t"}
    assert AtlasEntity.model_validate(body).guid == "nope"
    assert AtlasEntity(guid="nope").to_json()["guid"] == "nope"
    with pytest.raises(AtlasError) as raised:
        AtlasEntity.model_validate(body, context={ATLAS_REQUEST: True})
    assert raised.value.code is AtlasErrorCode.INVALID_OBJECT_ID


@pytest.mark.covers("aurelius_atlas_model.base.empty_when_null", rules=["TDM-06"])
def test__a_null_list_reads_as_empty() -> None:
    """A field Java never leaves null reads null as empty; other values pass unchanged."""
    assert empty_when_null(None) == []
    assert empty_when_null(["a"]) == ["a"]


@pytest.mark.covers("aurelius_atlas_model.base.null_when_empty", rules=["TDM-11"])
def test__an_empty_list_reads_as_null() -> None:
    """A field Java leaves null when empty reads an empty list as null."""
    assert null_when_empty([]) is None
    assert null_when_empty(None) is None
    assert null_when_empty([1]) == [1]
