"""``AtlasEntityHeaders`` (ENT-16), read from ``org.apache.atlas.model.instance.AtlasEntityHeaders`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.instance import AtlasEntityHeaders


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-16"])
def test__headers_are_kept_by_guid() -> None:
    """``guidHeaderMap``: GUID to header."""
    body = {"guidHeaderMap": {"g": {"guid": "g", "status": "ACTIVE", "isIncomplete": False}}}

    assert AtlasEntityHeaders.model_validate(body).to_json() == body
    assert AtlasEntityHeaders().to_json() == {}
