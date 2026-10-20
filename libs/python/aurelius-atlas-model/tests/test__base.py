"""The shared JSON helpers of ``aurelius_atlas_model.base`` (DD-037)."""

import pytest
from aurelius_atlas_model.base import empty_when_null, null_when_empty


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
