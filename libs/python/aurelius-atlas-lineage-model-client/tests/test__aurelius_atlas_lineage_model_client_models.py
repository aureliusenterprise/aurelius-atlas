"""The query and answer shapes of the lineage-model API (CL-30; DD-114).

The app validates its own query with the same constraints this model states —
one contract for caller and server, LM-01's shape.
"""

import pytest
from aurelius_atlas_lineage_model_client.models import (
    DEFAULT_DEPTH,
    MIN_DEPTH,
    LineageModelParams,
    LineageModelResponse,
)
from aurelius_atlas_server_client.lineage import Direction  # noqa: F401 - the shared vocabulary, CL-12/CL-30
from pydantic import ValidationError


@pytest.mark.covers(rules=["CL-30"])
def test__the_defaults_are_the_endpoints_own() -> None:
    """Guid required, depth 3 at least 1, BOTH by default (LM-01)."""
    params = LineageModelParams(guid="e-1")

    assert (params.guid, params.depth, params.direction) == ("e-1", DEFAULT_DEPTH, "BOTH")
    assert DEFAULT_DEPTH == 3
    assert MIN_DEPTH == 1


@pytest.mark.covers(rules=["CL-30"])
def test__a_missing_guid_is_rejected() -> None:
    """The legacy's literal-``None`` crash is DV-21's 400: the contract requires the guid."""
    with pytest.raises(ValidationError):
        LineageModelParams.model_validate({"depth": 2})
    with pytest.raises(ValidationError):
        LineageModelParams.model_validate({"guid": ""})


@pytest.mark.covers(rules=["CL-30"])
def test__a_depth_below_one_is_rejected() -> None:
    """``ge=1`` is the contract the app enforces (LM-01)."""
    with pytest.raises(ValidationError):
        LineageModelParams.model_validate({"guid": "e-1", "depth": 0})


@pytest.mark.covers(rules=["CL-30"])
def test__a_direction_outside_the_vocabulary_is_rejected() -> None:
    """The legacy's ``Enum()`` crash is DV-20's 400 (LM-01)."""
    with pytest.raises(ValidationError):
        LineageModelParams.model_validate({"guid": "e-1", "direction": "SIDEWAYS"})


@pytest.mark.covers(rules=["CL-30"])
def test__an_unknown_query_key_is_rejected() -> None:
    """``extra='forbid'``: the query has exactly the three parameters (LM-01)."""
    with pytest.raises(ValidationError):
        LineageModelParams.model_validate({"guid": "e-1", "page": 1})


@pytest.mark.covers(rules=["CL-30"])
def test__the_response_is_the_data2model_body_forwarded() -> None:
    """``{model, metadata}`` — the model stays a JSON string, the metadata stays open maps (LM-04, DV-15)."""
    response = LineageModelResponse.model_validate(
        {"model": '{"ar3_model": {"@identifier": "x"}}', "metadata": [{"id": "e-in", "data": {}}], "extra": 1}
    )

    assert response.model == '{"ar3_model": {"@identifier": "x"}}'
    assert response.metadata == [{"id": "e-in", "data": {}}]


@pytest.mark.covers(rules=["CL-30"])
def test__the_response_needs_its_model_string() -> None:
    """The answer without a model is not the contract: metadata alone is no document."""
    with pytest.raises(ValidationError):
        LineageModelResponse.model_validate({"metadata": []})
