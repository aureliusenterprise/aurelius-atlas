"""The lineage endpoints of ``LineageREST`` (LIN-01 to LIN-06), on the fake Elasticsearch.

Read from ``LineageREST`` of Apache Atlas 2.4.0; the traversal itself is tested on ``EntityLineageService`` in
``aurelius-atlas-core``.
"""

import json
from typing import Any

import httpx
import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from fastapi import FastAPI

D = "aurelius_atlas_server.routes.lineage"
LINEAGE = "/api/atlas/v2/lineage"
BASE = {"Referenceable", "Asset", "DataSet", "Process", "dataset_process_inputs", "process_dataset_outputs"}


@pytest.fixture
async def flow(client: httpx.AsyncClient) -> dict[str, str]:
    """Base-model lineage types; ``src`` -> ``load`` -> ``dst``, and the database ``db``; their GUIDs."""
    model = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json").read_text(encoding="utf-8"))
    types = {
        "entityDefs": [
            *[found for found in model["entityDefs"] if found["name"] in BASE],
            {"name": "l_table", "superTypes": ["DataSet"]},
            {"name": "l_process", "superTypes": ["Process"]},
            {"name": "l_db", "superTypes": ["Asset"]},
        ],
        "relationshipDefs": [found for found in model["relationshipDefs"] if found["name"] in BASE],
    }
    created = await client.post("/api/atlas/v2/types/typedefs", json=types)
    assert created.status_code == 200, created.text

    def entity(type_name: str, name: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
        return {
            "typeName": type_name,
            "guid": f"-{name}",
            "attributes": {"qualifiedName": name, "name": name, **attributes},
        }

    table = {"typeName": "l_table", "guid": "-src"}
    answer = await client.post(
        "/api/atlas/v2/entity/bulk",
        json={
            "entities": [
                entity("l_table", "src"),
                entity("l_table", "dst"),
                entity("l_db", "db"),
                entity("l_process", "load", inputs=[table], outputs=[{"typeName": "l_table", "guid": "-dst"}]),
            ]
        },
    )
    assert answer.status_code == 200, answer.text
    return {name: answer.json()["guidAssignments"][f"-{name}"] for name in ("src", "dst", "db", "load")}


async def send(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:  # noqa: ANN401
    """The status and the JSON body."""
    response = await client.request(method, url, **kwargs)
    return response.status_code, response.json()


@pytest.mark.covers(f"{D}.get_lineage_graph", f"{D}.direction_and_depth", rules=["LIN-01", "LIN-05"])
async def test__lineage_by_guid_with_its_defaults(client: httpx.AsyncClient, flow: dict[str, str]) -> None:
    """``BOTH`` and depth 3 by default; the process, both tables, two relations."""
    status, found = await send(client, "GET", f"{LINEAGE}/{flow['dst']}")
    assert (status, found["lineageDirection"], found["lineageDepth"], found["baseEntityGuid"]) == (
        200,
        "BOTH",
        3,
        flow["dst"],
    )
    assert set(found["guidEntityMap"]) == {flow["src"], flow["dst"], flow["load"]}
    assert {(r["fromEntityId"], r["toEntityId"]) for r in found["relations"]} == {
        (flow["src"], flow["load"]),
        (flow["load"], flow["dst"]),
    }
    assert found["relationsOnDemand"] == {}


@pytest.mark.covers(f"{D}.get_lineage_by_unique_attribute", rules=["LIN-01"])
async def test__lineage_by_unique_attribute(client: httpx.AsyncClient, flow: dict[str, str]) -> None:
    """The entity holding the ``attr:`` values; an unknown type or value fails as for entities."""
    url = f"{LINEAGE}/uniqueAttribute/type/l_table"
    status, found = await send(client, "GET", url, params={"attr:qualifiedName": "src", "direction": "OUTPUT"})
    _, unknown_type = await send(
        client, "GET", f"{LINEAGE}/uniqueAttribute/type/nope", params={"attr:qualifiedName": "x"}
    )
    _, unknown_value = await send(client, "GET", url, params={"attr:qualifiedName": "none"})
    assert (status, found["baseEntityGuid"], found["lineageDirection"]) == (200, flow["src"], "OUTPUT")
    assert unknown_type["errorCode"] == "ATLAS-400-00-014"
    assert unknown_value["errorCode"] == "ATLAS-404-00-009"


@pytest.mark.covers(f"{D}.get_lineage_graph", f"{D}.direction_and_depth", rules=["LIN-01", "LIN-02"])
async def test__lineage_fails_as_atlas_answers(client: httpx.AsyncClient, flow: dict[str, str]) -> None:
    """Invalid direction or depth (DV-39), an over-long GUID, an unknown entity, one neither data set nor process."""
    cases = [
        (f"{LINEAGE}/{flow['dst']}", {"direction": "UP"}, 400, "ATLAS-400-00-029"),
        (f"{LINEAGE}/{flow['dst']}", {"depth": "x"}, 400, "ATLAS-400-00-029"),
        (f"{LINEAGE}/{'x' * 4097}", {}, 400, "ATLAS-400-00-057"),
        (f"{LINEAGE}/nope", {}, 404, "ATLAS-404-00-005"),
        (f"{LINEAGE}/{flow['db']}", {}, 404, "ATLAS-404-00-011"),
    ]
    for url, params, expected_status, code in cases:
        status, body = await send(client, "GET", url, params=params)
        assert (status, body["errorCode"]) == (expected_status, code), (url, params, body)


@pytest.mark.covers(f"{D}.get_lineage_graph_on_demand", f"{D}.lineage_service", rules=["LIN-06"])
async def test__lineage_on_demand_is_disabled_by_default(client: httpx.AsyncClient, flow: dict[str, str]) -> None:
    """``atlas.lineage.on.demand.enabled`` is false unless set."""
    status, body = await send(client, "POST", f"{LINEAGE}/{flow['dst']}", json={})
    assert (status, body) == (
        400,
        {
            "errorCode": "ATLAS-400-00-100",
            "errorMessage": "Lineage on demand config: atlas.lineage.on.demand.enabled is not enabled",
        },
    )


@pytest.mark.covers(f"{D}.get_lineage_graph_on_demand", f"{D}.lineage_service", rules=["LIN-06", "LIN-07"])
async def test__lineage_on_demand_when_enabled(app: FastAPI, client: httpx.AsyncClient, flow: dict[str, str]) -> None:
    """The body's constraints per GUID, defaults filled in, answered as the payload."""
    app.state.settings = app.state.settings.model_copy(update={"lineage_on_demand_enabled": True})
    status, found = await send(client, "POST", f"{LINEAGE}/{flow['dst']}", json={flow["dst"]: {"direction": "INPUT"}})
    assert (status, found["lineageDirection"], found["lineageDepth"]) == (200, "INPUT", 3)
    assert found["lineageOnDemandPayload"] == {
        flow["dst"]: {"direction": "INPUT", "inputRelationsLimit": 3, "outputRelationsLimit": 3, "depth": 3}
    }
    assert set(found["guidEntityMap"]) == {flow["src"], flow["dst"], flow["load"]}
