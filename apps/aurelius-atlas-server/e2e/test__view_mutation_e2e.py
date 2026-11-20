"""The mutation door against the container, on the dev store (AVW-04, AVW-05, AVW-07, AVW-10).

The editor's loop over one entity: read it as a view, edit the read answer, save it through the door,
and watch the stored state move (AVR-09's promise, kept). A second save of the first read is the stale
case: 409 with the stored view (AVW-04). The audit trail shows one update and each changed kind (AVW-10).
A parent-side save reaching a child that holds another parent is refused, and moves with the opt-in
(RPS-01, RPS-03, RPS-05). The entities are namespaced to the run and removed with the session's other
writes (ECU-01).
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


async def held_parent(client: httpx.AsyncClient, guid: str) -> str | None:
    """The GUID the dataset holds as its ``parentDataset`` through the Atlas read, or none."""
    found = await client.get(f"{ENTITY}/guid/{guid}")
    assert found.status_code == 200, found.text
    end = found.json()["entity"]["relationshipAttributes"].get("parentDataset")
    if end is None or end.get("relationshipStatus", "ACTIVE") != "ACTIVE":
        return None
    return end["guid"]


async def listed_children(client: httpx.AsyncClient, guid: str) -> list[str]:
    """The active ``childDataset`` GUIDs the dataset lists, through the Atlas read."""
    found = await client.get(f"{ENTITY}/guid/{guid}")
    assert found.status_code == 200, found.text
    listed = found.json()["entity"]["relationshipAttributes"].get("childDataset") or []
    return [end["guid"] for end in listed if end.get("relationshipStatus", "ACTIVE") == "ACTIVE"]


# impact=severe, likelihood=low (a child under two parents makes every hierarchy read lie),
# promoted to critical while 18.4 lands the parent-safe guard on this path
@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_server.routes.view_entity.write",
    "aurelius_atlas_core.view_mutation.ViewMutationDoor.apply",
    rules=["RPS-01", "RPS-03", "RPS-05"],
)
async def test__the_door_refuses_a_held_child_and_moves_it_with_the_opt_in(client: httpx.AsyncClient) -> None:
    """The m4i dataset hierarchy: a parent-side save reaching a held child refuses, and the flag moves it."""
    run = uuid.uuid4().hex
    old = await make(client, "m4i_dataset", run, qualifiedName=f"zz{run}.old", name=f"old parent {run}")
    new = await make(client, "m4i_dataset", run, qualifiedName=f"zz{run}.new", name=f"new parent {run}")
    child = await make(client, "m4i_dataset", run, qualifiedName=f"zz{run}.child", name=f"held child {run}")

    # the child holds its first parent through the wire door (RPS-01's held seed); the update body
    # carries the mandatory attributes, which a wire update revalidates
    attached = await client.post(
        ENTITY,
        json={
            "entity": {
                "typeName": "m4i_dataset",
                "guid": child,
                "attributes": {"qualifiedName": f"zz{run}.child", "name": f"held child {run}"},
                "relationshipAttributes": {"parentDataset": {"guid": old, "typeName": "m4i_dataset"}},
            }
        },
    )
    assert attached.status_code == 200, attached.text

    body = {
        "guid": new,
        "typeName": "m4i_dataset",
        "updateTime": (await client.get(f"{VIEW}/{new}")).json()["updateTime"],
        "attributes": {"qualifiedName": f"zz{run}.new", "name": f"new parent {run}"},
        "sections": [{"attribute": "childDataset", "entities": [{"guid": child, "typeName": "m4i_dataset"}]}],
    }
    refused = await client.post(DOOR, json=body)
    assert refused.status_code == 404, refused.text
    assert refused.json()["errorCode"] == "ATLAS-404-00-007"
    assert f"m4i_dataset {child}: parentDataset holds parent m4i_dataset {old}" in refused.json()["errorMessage"]
    assert "unsafeReparent" in refused.json()["errorMessage"]
    assert await listed_children(client, new) == []  # the refusal wrote nothing (RPS-03)
    assert await held_parent(client, child) == old

    moved = await client.post(f"{DOOR}?unsafeReparent=true", json=body)
    assert moved.status_code == 200, moved.text
    assert await held_parent(client, child) == new  # one parent, the new one (RPS-05)
    assert await listed_children(client, new) == [child]
    assert await listed_children(client, old) == []  # the old parent's list cleared with the edge
