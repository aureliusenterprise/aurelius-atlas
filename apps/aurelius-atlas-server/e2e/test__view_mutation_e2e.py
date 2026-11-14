"""The mutation door against the container, on the dev store (AVW-04, AVW-05, AVW-07, AVW-10).

The editor's loop over one entity: read it as a view, edit the read answer, save it through the door,
and watch the stored state move (AVR-09's promise, kept). A second save of the first read is the stale
case: 409 with the stored view (AVW-04). The audit trail shows one update and each changed kind (AVW-10).
The entities are namespaced to the run and removed with the session's other writes (ECU-01).
"""

import uuid

import httpx2 as httpx
import pytest

DOOR = "/api/aurelius/v1/entity"
VIEW = f"{DOOR}/guid"
ENTITY = "/api/atlas/v2/entity"


async def make(client: httpx.AsyncClient, type_name: str, run: str, **attributes: str) -> str:
    """An entity of ``type_name`` named for ``run``, created as the writer; its GUID."""
    body = {"entity": {"typeName": type_name, "attributes": {"qualifiedName": f"{run}.{type_name}", **attributes}}}
    created = await client.post(ENTITY, json=body)
    assert created.status_code == 200, created.text
    return created.json()["mutatedEntities"]["CREATE"][0]["guid"]


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_server.routes.view_entity.write",
    "aurelius_atlas_core.view_mutation.ViewMutationDoor.apply",
    rules=["AVW-04", "AVW-05", "AVW-07", "AVW-10"],
)
async def test__an_editor_read_an_edit_and_a_save_move_the_stored_state(client: httpx.AsyncClient) -> None:
    """Read door -> edit -> save: the answer is the live view; a stale save answers 409 with the stored one."""
    run = uuid.uuid4().hex
    guid = await make(client, "Asset", run, name=f"before {run}")

    edited = (await client.get(f"{VIEW}/{guid}")).json()
    assert edited["name"] == f"before {run}"
    edited["name"] = None  # the door answers the derived field; the write rides the attributes
    edited["attributes"]["name"] = f"after {run}"
    edited["labels"] = ["edited"]
    edited["classifications"] = []
    edited["meanings"] = []

    saved = await client.post(DOOR, json=edited)
    assert saved.status_code == 200, saved.text
    answer = saved.json()
    assert answer["name"] == f"after {run}"
    assert answer["labels"] == ["edited"]
    assert answer["stale"] is False
    assert answer["updateTime"] > edited["updateTime"]

    read_back = (await client.get(f"{VIEW}/{guid}")).json()
    assert {field: answer[field] for field in ("guid", "name", "labels", "updateTime")} == {
        field: read_back[field] for field in ("guid", "name", "labels", "updateTime")
    }

    stale = await client.post(DOOR, json=edited)
    assert stale.status_code == 409
    body = stale.json()
    assert body["errorCode"] == "ENTITY_VERSION_CONFLICT"
    assert body["view"]["updateTime"] == answer["updateTime"]
    assert body["view"]["name"] == f"after {run}"
    assert body["view"]["stale"] is False

    audits = (await client.get(f"{ENTITY}/{guid}/audit")).json()
    update = [row for row in audits if row["action"] == "ENTITY_UPDATE"]
    assert len(update) == 1
    assert len([row for row in audits if row["action"] == "LABEL_ADD"]) == 1
