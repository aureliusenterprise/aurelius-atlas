"""The lineage models' JSON (LIN-05, LIN-07), read from ``AtlasLineageInfo`` and ``LineageOnDemandConstraints``."""

import pytest
from aurelius_atlas_model.lineage import (
    AtlasLineageInfo,
    LineageDirection,
    LineageInfoOnDemand,
    LineageOnDemandConstraints,
    LineageRelation,
)


@pytest.mark.covers(rules=["LIN-05", "LIN-07"])
def test__lineage_info_writes_atlas_s_names_and_leaves_out_nulls() -> None:
    """Atlas's camelCase names; no payload unless on demand; the on-demand flags and counts."""
    info = AtlasLineageInfo(
        base_entity_guid="g",
        lineage_direction=LineageDirection.INPUT,
        lineage_depth=2,
        guid_entity_map={},
        relations=[LineageRelation(from_entity_id="a", to_entity_id="b", relationship_id="r")],
        relations_on_demand={"g": LineageInfoOnDemand(has_more_inputs=True, input_relations_count=3)},
    )
    assert info.to_json() == {
        "baseEntityGuid": "g",
        "lineageDirection": "INPUT",
        "lineageDepth": 2,
        "guidEntityMap": {},
        "relations": [{"fromEntityId": "a", "toEntityId": "b", "relationshipId": "r"}],
        "relationsOnDemand": {
            "g": {"hasMoreInputs": True, "hasMoreOutputs": False, "inputRelationsCount": 3, "outputRelationsCount": 0}
        },
    }


@pytest.mark.covers(rules=["LIN-06"])
def test__constraints_read_nulls_as_java_defaults() -> None:
    """A null or missing limit or depth is 0, a missing direction none; unknown fields are ignored."""
    found = LineageOnDemandConstraints.model_validate({"inputRelationsLimit": None, "depth": 4, "other": 1})
    assert (found.direction, found.input_relations_limit, found.output_relations_limit, found.depth) == (None, 0, 0, 4)
