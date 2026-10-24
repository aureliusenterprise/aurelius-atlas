"""The Atlas ``v2/lineage/{guid}`` body, as the server client owns it (CL-12).

The models moved here from 8.2's app module; these tests are their home now —
the same wire shape ``libs/m4i-atlas-core``'s ``LineageInfo`` states (ADR 055 R4).
"""

from typing import Any
from uuid import UUID

import pytest
from aurelius_atlas_server_client.lineage import Direction, EntityHeaderLite, LineageInfo, LineageRelation

E_IN = UUID("00000000-0000-4000-8000-000000000001")
P_LOAD = UUID("00000000-0000-4000-8000-000000000002")
"""The fixture graph's entities: the fixed UUIDs of 8.2's fixtures (DV-61)."""

BODY: dict[str, Any] = {
    "baseEntityGuid": str(E_IN),
    "lineageDepth": 3,
    "lineageDirection": "BOTH",
    "guidEntityMap": {
        str(E_IN): {"guid": str(E_IN), "typeName": "kafka_topic", "displayText": "Ingest Topic"},
        str(P_LOAD): {"guid": str(P_LOAD), "typeName": "m4i_generic_process", "displayText": "Load Job"},
    },
    "relations": [{"fromEntityId": str(E_IN), "relationshipId": "rel-1", "toEntityId": str(P_LOAD)}],
}


@pytest.mark.covers(rules=["CL-12"])
def test__the_lineage_body_parses_the_camel_case_wire_shape() -> None:
    """``guidEntityMap`` / ``relations`` with the camelCase names, the extra Atlas fields ignored (LM-04)."""
    info = LineageInfo.model_validate(BODY)

    assert info.guid_entity_map[E_IN].type_name == "kafka_topic"
    assert info.guid_entity_map[P_LOAD].display_text == "Load Job"
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
        {"guid": str(E_IN), "typeName": "hive_table", "classifications": [], "status": "ACTIVE"}
    )

    assert header.guid == E_IN
    assert header.type_name == "hive_table"
    assert header.display_text is None


@pytest.mark.covers(rules=["CL-12"])
def test__a_relation_round_trips_the_wire_names() -> None:
    """The snake_case model, the camelCase wire; the endpoint guids travel as UUID strings (LM-02, DV-61)."""
    relation = LineageRelation.model_validate(
        {"fromEntityId": str(E_IN), "relationshipId": "r", "toEntityId": str(P_LOAD)}
    )

    assert relation.model_dump(mode="json", by_alias=True) == {
        "fromEntityId": str(E_IN),
        "relationshipId": "r",
        "toEntityId": str(P_LOAD),
    }


@pytest.mark.covers(rules=["CL-12"])
def test__the_directions_are_the_atlas_vocabulary() -> None:
    """``BOTH``/``INPUT``/``OUTPUT`` — the legacy's ``LineageDirection`` (LM-01); the type is the check."""
    directions: list[Direction] = ["BOTH", "INPUT", "OUTPUT"]

    assert len(directions) == 3
