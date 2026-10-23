"""The Atlas ``v2/lineage/{guid}`` body, as the server client owns it (CL-12).

The models moved here from 8.2's app module; these tests are their home now —
the same wire shape ``libs/m4i-atlas-core``'s ``LineageInfo`` states (ADR 055 R4).
"""

from typing import Any

import pytest
from aurelius_atlas_server_client.lineage import Direction, EntityHeaderLite, LineageInfo, LineageRelation

BODY: dict[str, Any] = {
    "baseEntityGuid": "e-in",
    "lineageDepth": 3,
    "lineageDirection": "BOTH",
    "guidEntityMap": {
        "e-in": {"guid": "e-in", "typeName": "kafka_topic", "displayText": "Ingest Topic"},
        "p-load": {"guid": "p-load", "typeName": "m4i_generic_process", "displayText": "Load Job"},
    },
    "relations": [{"fromEntityId": "e-in", "relationshipId": "rel-1", "toEntityId": "p-load"}],
}


@pytest.mark.covers(rules=["CL-12"])
def test__the_lineage_body_parses_the_camel_case_wire_shape() -> None:
    """``guidEntityMap`` / ``relations`` with the camelCase names, the extra Atlas fields ignored (LM-04)."""
    info = LineageInfo.model_validate(BODY)

    assert info.guid_entity_map["e-in"].type_name == "kafka_topic"
    assert info.guid_entity_map["p-load"].display_text == "Load Job"
    assert info.relations[0].relationship_id == "rel-1"


@pytest.mark.covers(rules=["CL-12"])
def test__the_empty_lineage_body_is_valid() -> None:
    """The defaults of an answer with neither map nor relations: empty, not absent."""
    info = LineageInfo.model_validate({})

    assert info.guid_entity_map == {}
    assert info.relations == []


@pytest.mark.covers(rules=["CL-12"])
def test__an_entity_header_tolerates_the_atlas_fields_the_rows_never_use() -> None:
    """Classifications, labels, statuses: extra fields are ignored (LM-02)."""
    header = EntityHeaderLite.model_validate(
        {"guid": "e-1", "typeName": "hive_table", "classifications": [], "status": "ACTIVE"}
    )

    assert header.guid == "e-1"
    assert header.type_name == "hive_table"
    assert header.display_text is None


@pytest.mark.covers(rules=["CL-12"])
def test__a_relation_round_trips_the_wire_names() -> None:
    """The snake_case model, the camelCase wire (LM-02)."""
    relation = LineageRelation.model_validate({"fromEntityId": "a", "relationshipId": "r", "toEntityId": "b"})

    assert relation.model_dump(by_alias=True) == {"fromEntityId": "a", "relationshipId": "r", "toEntityId": "b"}


@pytest.mark.covers(rules=["CL-12"])
def test__the_directions_are_the_atlas_vocabulary() -> None:
    """``BOTH``/``INPUT``/``OUTPUT`` — the legacy's ``LineageDirection`` (LM-01); the type is the check."""
    directions: list[Direction] = ["BOTH", "INPUT", "OUTPUT"]

    assert len(directions) == 3
