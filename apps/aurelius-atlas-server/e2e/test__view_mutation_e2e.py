"""The mutation door through the client library, against the container (AVW-04, AVW-05, AVW-07, AVW-10, CLV).

The editor's loop over one entity through the client's doors: read it as a view, edit the read answer, save
it through the door, and watch the stored state move (AVR-09's promise, kept). A second save of the first
read is the stale case: the client's conflict error beside the stored view (AVW-04, CLV-03). The audit trail
shows one update and each changed kind (AVW-10). A parent-side save reaching a child that holds another
parent is refused, and moves with the opt-in (RPS-01, RPS-03, RPS-05). The entities are namespaced to the
run and removed with the session's other writes (ECU-01).
"""

import uuid

import pytest
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo, EntityOperation
from aurelius_atlas_server_client import AtlasClient, AtlasClientError, ViewVersionConflictError


def _entity(
    type_name: str,
    attributes: dict[str, object],
    guid: str | None = None,
    relationship_attributes: dict[str, object] | None = None,
) -> AtlasEntityWithExtInfo:
    """The create-or-update body of one entity, held by ``guid`` when updating (AVW-05's seed)."""
    return AtlasEntityWithExtInfo(
        entity=AtlasEntity(
            type_name=type_name, attributes=attributes, guid=guid, relationship_attributes=relationship_attributes
        )
    )


async def make(api: AtlasClient, type_name: str, run: str, **attributes: str) -> str:
    """An entity of ``type_name`` named for ``run``, created as the writer; its GUID."""
    created = await api.entity.create_or_update(
        _entity(type_name, {"qualifiedName": f"{run}.{type_name}", **attributes})
    )
    header = created.get_first_entity_by_operation(EntityOperation.CREATE)
    assert header is not None
    assert header.guid is not None
    return header.guid


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_server_client.client.ViewApi.read",
    "aurelius_atlas_server_client.client.ViewApi.save",
    "aurelius_atlas_server_client.client.EntityApi.audit_events",
    "aurelius_atlas_server.routes.view_entity.write",
    "aurelius_atlas_core.view_mutation.ViewMutationDoor.apply",
    rules=["AVW-04", "AVW-05", "AVW-07", "AVW-10", "CLV-01", "CLV-02", "CLV-03"],
)
async def test__an_editor_read_an_edit_and_a_save_move_the_stored_state(api: AtlasClient) -> None:
    """Read door -> edit -> save: the answer is the live view; a stale save answers 409 with the stored one."""
    run = uuid.uuid4().hex
    guid = await make(api, "Asset", run, name=f"before {run}")

    edited = (await api.view.read(guid)).to_json()
    before = edited["updateTime"]
    assert edited["name"] == f"before {run}"
    del edited["name"]  # the door answers the derived field; the write rides the attributes
    edited["attributes"]["name"] = f"after {run}"
    edited["labels"] = ["edited"]

    answer = await api.view.save(edited)
    assert answer.name == f"after {run}"
    assert answer.labels == ["edited"]
    assert answer.stale is False
    assert answer.update_time is not None
    assert answer.update_time.timestamp() * 1000 > before

    read_back = await api.view.read(guid)
    assert (read_back.guid, read_back.name, read_back.labels, read_back.update_time) == (
        answer.guid,
        answer.name,
        answer.labels,
        answer.update_time,
    )

    with pytest.raises(ViewVersionConflictError) as stale:  # the same first read saved again: the lost update
        await api.view.save(edited)
    assert stale.value.status_code == 409
    assert stale.value.view.update_time == answer.update_time
    assert stale.value.view.name == f"after {run}"
    assert stale.value.view.stale is False

    audits = await api.entity.audit_events(guid)
    actions = [event.action for event in audits]
    assert actions.count(EntityAuditActionV2.ENTITY_UPDATE) == 1
    assert actions.count(EntityAuditActionV2.LABEL_ADD) == 1


async def held_parent(api: AtlasClient, guid: str) -> str | None:
    """The GUID the dataset holds as its ``parentDataset`` through the Atlas read, or none."""
    found = await api.entity.by_guid(guid)
    assert found.entity is not None
    end = found.entity.get_relationship_attribute("parentDataset")
    if end is None or end.get("relationshipStatus", "ACTIVE") != "ACTIVE":
        return None
    return str(end["guid"])


async def listed_children(api: AtlasClient, guid: str) -> list[str]:
    """The active ``childDataset`` GUIDs the dataset lists, through the Atlas read."""
    found = await api.entity.by_guid(guid)
    assert found.entity is not None
    listed = found.entity.get_relationship_attribute("childDataset") or []
    return [str(end["guid"]) for end in listed if end.get("relationshipStatus", "ACTIVE") == "ACTIVE"]


# impact=severe, likelihood=low (a child under two parents makes every hierarchy read lie),
# promoted to critical while 18.4 lands the parent-safe guard on this path
@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_server_client.client.ViewApi.save",
    "aurelius_atlas_server_client.client.EntityApi.by_guid",
    "aurelius_atlas_server.routes.view_entity.write",
    "aurelius_atlas_core.view_mutation.ViewMutationDoor.apply",
    rules=["RPS-01", "RPS-03", "RPS-05", "CLV-02"],
)
async def test__the_door_refuses_a_held_child_and_moves_it_with_the_opt_in(api: AtlasClient) -> None:
    """The m4i dataset hierarchy: a parent-side save reaching a held child refuses, and the flag moves it."""
    run = uuid.uuid4().hex
    old = await make(api, "m4i_dataset", run, qualifiedName=f"zz{run}.old", name=f"old parent {run}")
    new = await make(api, "m4i_dataset", run, qualifiedName=f"zz{run}.new", name=f"new parent {run}")
    child = await make(api, "m4i_dataset", run, qualifiedName=f"zz{run}.child", name=f"held child {run}")

    # the child holds its first parent through the wire door (RPS-01's held seed); the update body
    # carries the mandatory attributes, which a wire update revalidates
    await api.entity.create_or_update(
        _entity(
            "m4i_dataset",
            {"qualifiedName": f"zz{run}.child", "name": f"held child {run}"},
            guid=child,
            relationship_attributes={"parentDataset": {"guid": old, "typeName": "m4i_dataset"}},
        )
    )

    body = {
        "guid": new,
        "typeName": "m4i_dataset",
        "updateTime": (await api.view.read(new)).to_json()["updateTime"],
        "attributes": {"qualifiedName": f"zz{run}.new", "name": f"new parent {run}"},
        "sections": [{"attribute": "childDataset", "entities": [{"guid": child, "typeName": "m4i_dataset"}]}],
    }
    with pytest.raises(AtlasClientError) as refused:
        await api.view.save(body)
    assert refused.value.status_code == 404
    assert refused.value.info is not None
    assert refused.value.info.error_code == "ATLAS-404-00-007"
    assert f"m4i_dataset {child}: parentDataset holds parent m4i_dataset {old}" in refused.value.info.error_message
    assert "unsafeReparent" in refused.value.info.error_message
    assert await listed_children(api, new) == []  # the refusal wrote nothing (RPS-03)
    assert await held_parent(api, child) == old

    await api.view.save(body, unsafe_reparent=True)
    assert await held_parent(api, child) == new  # one parent, the new one (RPS-05)
    assert await listed_children(api, new) == [child]
    assert await listed_children(api, old) == []  # the old parent's list cleared with the edge
