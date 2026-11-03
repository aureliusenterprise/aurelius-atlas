"""The Atlas ``api/atlas/v2/lineage`` body and its client (CL-12, CL-60..CL-63).

The models moved here from 8.2's app module; these tests are their home now —
the same wire shape ``libs/m4i-atlas-core``'s ``LineageInfo`` states (ADR 055 R4).
The client tests answer the resource API from the recording transport (CL-02),
on the mounted prefix 8.8 fixes (DD-308).
"""

import json
from typing import Any
from uuid import UUID

import httpx2 as httpx
import pytest
from aurelius_atlas_model.lineage import LineageDirection, LineageOnDemandConstraints
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError
from aurelius_atlas_server_client.lineage import Direction, EntityHeaderLite, LineageInfo, LineageRelation
from server_recorder import Recorder

E_IN = UUID("00000000-0000-4000-8000-000000000001")
P_LOAD = UUID("00000000-0000-4000-8000-000000000002")
"""The fixture graph's entities: the fixed UUIDs of 8.2's fixtures (DV-78)."""

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
    """The snake_case model, the camelCase wire; the endpoint guids travel as UUID strings (LM-02, DV-78)."""
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


LINEAGE_ANSWER: dict[str, Any] = {
    "guidEntityMap": {str(E_IN): {"guid": str(E_IN), "typeName": "hive_table", "displayText": "T"}},
    "relations": [],
}
"""The lineage body a client test answers with (CL-12's shape)."""


def _client(recorder: Recorder) -> AtlasClient:
    """The client under test on the recording transport (CL-02)."""
    return AtlasClient(httpx.AsyncClient(base_url="https://atlas.test", transport=recorder.transport()), "tok")


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.LineageApi.get",
    "aurelius_atlas_server_client.client.AtlasClient.__init__",
    rules=["CL-61", "CL-60"],
)
async def test__lineage_get_reads_the_mounted_feed(recorder: Recorder) -> None:
    """``GET api/atlas/v2/lineage/{guid}`` with the depth and direction parameters (CL-61, DD-308)."""
    recorder.answer(200, LINEAGE_ANSWER)

    info = await _client(recorder).lineage.get(E_IN, depth=5, direction="INPUT")

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"/api/atlas/v2/lineage/{E_IN}"
    assert dict(sent.url.params) == {"depth": "5", "direction": "INPUT"}
    assert info.guid_entity_map[E_IN].type_name == "hive_table"


@pytest.mark.covers("aurelius_atlas_server_client.client.AtlasClient.get_lineage", rules=["CL-61"])
async def test__the_get_lineage_alias_speaks_the_fixed_prefix(recorder: Recorder) -> None:
    """The 8.2-era alias answers the mounted path, not the legacy one (CL-61, DD-308)."""
    recorder.answer(200, LINEAGE_ANSWER)

    await _client(recorder).get_lineage(E_IN)

    assert recorder.sent().url.path == f"/api/atlas/v2/lineage/{E_IN}"


@pytest.mark.covers("aurelius_atlas_server_client.client.LineageApi.get_on_demand", rules=["CL-62", "CL-60"])
async def test__get_on_demand_posts_the_constraints_per_guid(recorder: Recorder) -> None:
    """``POST api/atlas/v2/lineage/{guid}`` carries each guid's constraints as the model's JSON (CL-62, DD-309)."""
    recorder.answer(200, LINEAGE_ANSWER)

    await _client(recorder).lineage.get_on_demand(
        E_IN, {str(E_IN): LineageOnDemandConstraints(direction=LineageDirection.INPUT, depth=2)}
    )

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == f"/api/atlas/v2/lineage/{E_IN}"
    body = json.loads(sent.content)
    assert body[str(E_IN)]["depth"] == 2
    assert body[str(E_IN)]["direction"] == "INPUT"


@pytest.mark.covers("aurelius_atlas_server_client.client.LineageApi.get_on_demand", rules=["CL-62"])
async def test__get_on_demand_without_constraints_posts_no_body(recorder: Recorder) -> None:
    """No constraints is no body — the server answers its own defaults (CL-62, LIN-06)."""
    recorder.answer(200, LINEAGE_ANSWER)

    await _client(recorder).lineage.get_on_demand(E_IN)

    assert recorder.sent().content == b""


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.LineageApi.get_by_unique_attributes",
    rules=["CL-63", "CL-60"],
)
async def test__get_by_unique_attributes_renders_the_attr_parameters(recorder: Recorder) -> None:
    """Each attribute travels as ``attr:<name>`` on the uniqueAttribute route (CL-63)."""
    recorder.answer(200, LINEAGE_ANSWER)

    await _client(recorder).lineage.get_by_unique_attributes(
        "hive_table", {"qualifiedName": "t@cluster", "name": "t"}, depth=2
    )

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == "/api/atlas/v2/lineage/uniqueAttribute/type/hive_table"
    assert dict(sent.url.params) == {
        "attr:qualifiedName": "t@cluster",
        "attr:name": "t",
        "depth": "2",
        "direction": "BOTH",
    }


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.LineageApi.get",
    rules=["CL-04"],
)
async def test__a_lineage_error_answer_raises_with_its_status(recorder: Recorder) -> None:
    """A non-2xx from the feed raises ``AtlasClientError`` with the status (CL-04): the caller maps it."""
    recorder.answer(404, {"errorCode": "ATLAS-404-00-011", "errorMessage": "no lineage"})

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).lineage.get(UUID(int=9))

    assert raised.value.status_code == 404
