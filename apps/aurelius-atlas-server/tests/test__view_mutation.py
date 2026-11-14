"""The mutation door over HTTP (AVW-01 to AVW-10).

``POST /api/aurelius/v1/entity`` takes a view as one entity's desired state and answers its live view
(ADR 064). The seed goes through the Atlas routes so every step runs as the editor's will; the answer is
read back through the Atlas and read-door routes, never through the door itself. The door runs on the
fake store, which honours the version conflicts the real one does.
"""

import shutil
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.entity_samples import (
    CLASSIFICATION_TYPES,
    RELATIONSHIP_TYPES,
    SAMPLE_TYPES,
)
from fake_issuer import FakeIssuer

R = "aurelius_atlas_server.routes.view_entity"
D = "aurelius_atlas_core.view_mutation.ViewMutationDoor.apply"
ENTITY = "/api/atlas/v2/entity"
DOOR = "/api/aurelius/v1/entity"
VIEW = f"{DOOR}/guid"
GLOSSARY = "/api/atlas/v2/glossary"

TYPES = (SAMPLE_TYPES, CLASSIFICATION_TYPES, RELATIONSHIP_TYPES)
"""The sample types plus the tags, propagation edges and relationship attributes the door writes."""


MODELS = (Path("0000-Area0") / "0010-base_model.json", Path("0000-Area0") / "0011-glossary_model.json")
"""The base and glossary models: the tests' terms need ``AtlasGlossary`` and its term type."""


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base and glossary models alone (MDL-16)."""
    directory = tmp_path / "core-models"
    for model in MODELS:
        (directory / model.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy(BUILTIN_MODELS_DIR / model, directory / model)
    return directory


def as_roles(issuer: FakeIssuer, user: str, *roles: str) -> dict[str, str]:
    """The ``Authorization`` header of a token of the user holding these roles of the server's client."""
    return {"Authorization": f"Bearer {issuer.token(user, atlas_roles=roles)}"}


@pytest.fixture
async def typed(client: httpx.AsyncClient) -> httpx.AsyncClient:
    """The client of a server that knows every sample type."""
    for types in TYPES:
        created = await client.post("/api/atlas/v2/types/typedefs", json=types)
        assert created.status_code == 200, created.text
    return client


async def create(client: httpx.AsyncClient, type_name: str, **attributes: Any) -> str:  # noqa: ANN401 - attribute JSON
    """An entity created through the Atlas route; its GUID."""
    body = {"entity": {"typeName": type_name, "attributes": attributes}}
    created = await client.post(ENTITY, json=body)
    assert created.status_code == 200, created.text
    return created.json()["mutatedEntities"]["CREATE"][0]["guid"]


async def view_of(client: httpx.AsyncClient, guid: str) -> dict[str, Any]:
    """The entity's live view through the read door."""
    view = await client.get(f"{VIEW}/{guid}")
    assert view.status_code == 200, view.text
    return view.json()


async def save(client: httpx.AsyncClient, body: dict[str, Any]) -> httpx.Response:
    """One save through the mutation door."""
    return await client.post(DOOR, json=body)


async def relationship_end(client: httpx.AsyncClient, guid: str, attribute: str) -> str | None:
    """The GUID the entity's relationship attribute names through the Atlas read, or none."""
    found = await client.get(f"{ENTITY}/guid/{guid}")
    assert found.status_code == 200, found.text
    end = found.json()["entity"]["relationshipAttributes"].get(attribute)
    return None if end is None else end["guid"]


async def make_term(client: httpx.AsyncClient, name: str) -> str:
    """A term of a run's own glossary, created as the editor does; its GUID."""
    glossary = await client.post(GLOSSARY, json={"name": f"bank-{name}"})
    assert glossary.status_code == 200, glossary.text
    term = await client.post(
        f"{GLOSSARY}/term", json={"name": name, "anchor": {"glossaryGuid": glossary.json()["guid"]}}
    )
    assert term.status_code == 200, term.text
    return term.json()["guid"]


@pytest.mark.covers(D, rules=["AVW-02", "AVW-06", "AVW-07"])
async def test__a_view_created_through_the_door_answers_its_live_view(typed: httpx.AsyncClient) -> None:
    """A create gets the server's GUID; the answer is the read door's view; read-only fields pass ignored.

    The qualified name is the caller's, the GUID the server's (AVW-06); ``quality``, ``stale`` and the
    breadcrumb ride the body in and are ignored (AVW-02); the answer is derived fresh and equal to the
    read door's (AVW-07).
    """
    body = {
        "typeName": "s_database",
        "attributes": {"qualifiedName": "db@door", "title": "Orders DB"},
        "quality": [{"passed": 1, "failed": 2, "total": 3}],
        "stale": True,
        "breadcrumb": [{"guid": "x", "name": "X"}],
    }
    answer = await save(typed, body)
    assert answer.status_code == 200, answer.text
    view = answer.json()

    assert uuid.UUID(view["guid"])  # the server minted one; the body named none (AVW-06)
    assert view["typeName"] == "s_database"
    assert view["qualifiedName"] == "db@door"
    assert view["attributes"] == {"qualifiedName": "db@door", "title": "Orders DB"}
    assert view["stale"] is False  # the door's own write is the freshness (DD-594)
    assert view["updateTime"] >= view["createTime"]
    assert view["updatedBy"] == "admin"

    assert await view_of(typed, view["guid"]) == view

    held = await save(typed, {"typeName": "s_database", "attributes": {"qualifiedName": "db@door"}})
    assert (held.status_code, held.json()["errorCode"]) == (409, "ENTITY_NAME_TAKEN")
    assert held.json()["errorMessage"].count("db@door") == 1


@pytest.mark.covers(D, rules=["AVW-06"])
async def test__a_create_naming_a_held_qualified_name_names_its_holder(typed: httpx.AsyncClient) -> None:
    """The conflict names the held value and its holder, and stores nothing (AVW-06)."""
    holder = await create(typed, "s_database", qualifiedName="taken@door", title="Held")

    refused = await save(typed, {"typeName": "s_database", "attributes": {"qualifiedName": "taken@door"}})
    assert refused.status_code == 409
    assert refused.json()["errorCode"] == "ENTITY_NAME_TAKEN"
    assert "taken@door" in refused.json()["errorMessage"]
    assert holder in refused.json()["errorMessage"]

    again = await save(typed, {"typeName": "s_database", "attributes": {"qualifiedName": "other@door"}})
    assert again.status_code == 200
    assert again.json()["guid"] != holder


@pytest.mark.covers(f"{R}.write", f"{D}", rules=["AVW-04"])
async def test__a_stale_save_answers_the_conflict_beside_the_stored_view(typed: httpx.AsyncClient) -> None:
    """The door compares the view's ``updateTime`` and answers 409 with the stored view, applying nothing.

    The editor's save was built from a view read before another change (DD-591): the answer carries the
    stored view to merge from, and the door's own writes reached nowhere.
    """
    guid = await create(typed, "s_database", qualifiedName="db@clash", title="First")
    edited = await view_of(typed, guid)

    renamed = await typed.put(f"{ENTITY}/guid/{guid}", params={"name": "title"}, json="Second")
    assert renamed.status_code == 200, renamed.text

    stale = dict(edited, attributes={**edited["attributes"], "title": "Third"})
    conflict = await save(typed, stale)
    assert conflict.status_code == 409
    body = conflict.json()
    assert body["errorCode"] == "ENTITY_VERSION_CONFLICT"
    assert body["view"]["guid"] == guid
    assert body["view"]["attributes"]["title"] == "Second"
    assert body["view"]["stale"] is False

    assert (await view_of(typed, guid))["attributes"]["title"] == "Second"

    fresh = await view_of(typed, guid)
    saved = await save(typed, dict(fresh, attributes={**fresh["attributes"], "title": "Third"}))
    assert saved.status_code == 200
    assert saved.json()["attributes"]["title"] == "Third"


@pytest.mark.covers(D, rules=["AVW-05"])
async def test__a_save_replaces_each_named_set_and_leaves_the_rest(typed: httpx.AsyncClient) -> None:
    """Tags, labels, meanings and section edges, all replaced in one request (AVW-05, AVW-08, AVW-09).

    The meanings ride an ``Asset``: a term assigns to a ``Referenceable``, as 5.2c draws it (GTA-01).
    """
    node = await create(typed, "r_node", qualifiedName="node@sets", name="Node", labels=["a", "b"])
    asset = await create(typed, "Asset", qualifiedName="asset@sets", name="Ledger")
    first = await create(typed, "s_database", qualifiedName="db1@sets")
    second = await create(typed, "s_database", qualifiedName="db2@sets")
    loan = await make_term(typed, "loan")
    debt = await make_term(typed, "debt")
    assert (await typed.put(f"{ENTITY}/guid/{node}/labels", json=["a", "b"])).status_code == 204
    assert (await typed.post(f"{ENTITY}/guid/{node}/classifications", json=[{"typeName": "c_pii"}])).status_code == 204
    assert (
        await typed.post(f"{GLOSSARY}/terms/{loan}/assignedEntities", json=[{"guid": asset, "typeName": "Asset"}])
    ).status_code == 204
    opening = await view_of(typed, node)
    assert (
        await save(typed, dict(opening, sections=[{"attribute": "keeper", "entities": [first]}]))
    ).status_code == 200
    assert await relationship_end(typed, node, "keeper") == first

    start = await view_of(typed, node)
    saved = await save(
        typed,
        {
            "guid": node,
            "typeName": "r_node",
            "updateTime": start["updateTime"],
            "attributes": {"qualifiedName": "node@sets", "name": "Renamed"},
            "labels": ["b", "c"],
            "classifications": ["c_secret"],
            "sections": [{"attribute": "keeper", "entities": [second]}],
        },
    )
    assert saved.status_code == 200, saved.text
    answer = saved.json()
    assert answer["name"] == "Renamed"
    assert sorted(answer["labels"]) == ["b", "c"]
    assert answer["classificationNames"] == ["c_secret"]
    assert await relationship_end(typed, node, "keeper") == second

    emptied = await save(
        typed,
        {
            "guid": node,
            "typeName": "r_node",
            "updateTime": (await view_of(typed, node))["updateTime"],
            "attributes": {"qualifiedName": "node@sets"},
            "sections": [{"attribute": "keeper", "entities": []}],
        },
    )
    assert emptied.status_code == 200
    assert await relationship_end(typed, node, "keeper") is None

    asset_start = await view_of(typed, asset)
    remarked = await save(
        typed,
        {
            "guid": asset,
            "typeName": "Asset",
            "updateTime": asset_start["updateTime"],
            "attributes": {"qualifiedName": "asset@sets", "name": "Ledger"},
            "meanings": [debt],
        },
    )
    assert remarked.status_code == 200, remarked.text
    header = await typed.get(f"{ENTITY}/guid/{asset}/header")
    assert header.json()["meaningNames"] == ["debt"]


@pytest.mark.covers(D, rules=["AVW-09"])
async def test__a_delete_intent_removes_the_named_end(typed: httpx.AsyncClient) -> None:
    """A sections entry whose end is ``DELETED`` dissolves that edge (AVW-09)."""
    node = await create(typed, "r_node", qualifiedName="node@del")
    db = await create(typed, "s_database", qualifiedName="db@del")
    start = await view_of(typed, node)
    assert (await save(typed, dict(start, sections=[{"attribute": "keeper", "entities": [db]}]))).status_code == 200

    dropped = await view_of(typed, node)
    refused = await save(
        typed,
        dict(dropped, sections=[{"attribute": "keeper", "entities": [{"guid": db, "status": "DELETED"}]}]),
    )
    assert refused.status_code == 200, refused.text
    assert await relationship_end(typed, node, "keeper") is None


@pytest.mark.covers(D, rules=["AVW-08"])
async def test__a_propagated_tag_is_not_the_doors_to_write(typed: httpx.AsyncClient) -> None:
    """Naming a tag that only propagation brought is refused naming its source; omitting it leaves it.

    The desired state is the entity's own (DD-589): a propagated copy is the source's to remove.
    """
    data = await create(typed, "p_data", qualifiedName="data@prop")
    process = await create(typed, "p_process", qualifiedName="process@prop")
    assert (await typed.post(f"{ENTITY}/guid/{data}/classifications", json=[{"typeName": "c_pii"}])).status_code == 204
    start = await view_of(typed, process)
    assert (await save(typed, dict(start, sections=[{"attribute": "inputs", "entities": [data]}]))).status_code == 200

    refused = await save(
        typed,
        {
            "guid": process,
            "typeName": "p_process",
            "updateTime": (await view_of(typed, process))["updateTime"],
            "attributes": {"qualifiedName": "process@prop"},
            "classifications": ["c_pii"],
        },
    )
    assert refused.status_code == 400
    assert refused.json()["errorCode"] == "AURELIUS-400-00-001"
    assert f"entity {data}" in refused.json()["messages"][0]

    own_only = await save(
        typed,
        {
            "guid": process,
            "typeName": "p_process",
            "updateTime": (await view_of(typed, process))["updateTime"],
            "attributes": {"qualifiedName": "process@prop"},
            "classifications": [],
        },
    )
    assert own_only.status_code == 200
    header = await typed.get(f"{ENTITY}/guid/{process}/header")
    assert header.json()["classificationNames"] == ["c_pii"]  # the header shows the propagated copy, still in place
    assert (await view_of(typed, process))["classificationNames"] == []  # the view never counted it as its own (DD-326)


@pytest.mark.covers(D, rules=["AVW-05"])
async def test__a_failing_later_step_leaves_the_request_start_in_place(typed: httpx.AsyncClient) -> None:
    """The rollback of AVW-05 on the fake store: a failing section step leaves attributes, tags, labels.

    The attributes, labels and classifications of the request are written before the section step fails
    (the store gap ADR 047 names); the door rewinds them all and leaves no audit row either (DD-590).
    """
    node = await create(typed, "r_node", qualifiedName="node@undo", name="Keep")
    assert (await typed.put(f"{ENTITY}/guid/{node}/labels", json=["keep-me"])).status_code == 204
    assert (await typed.post(f"{ENTITY}/guid/{node}/classifications", json=[{"typeName": "c_pii"}])).status_code == 204
    before = await view_of(typed, node)
    audits = len((await typed.get(f"{ENTITY}/{node}/audit")).json())

    gone = str(uuid.uuid4())
    refused = await save(
        typed,
        {
            "guid": node,
            "typeName": "r_node",
            "updateTime": before["updateTime"],
            "attributes": {"qualifiedName": "node@undo", "name": "Renamed"},
            "labels": ["gone"],
            "classifications": [],
            "sections": [{"attribute": "keeper", "entities": [gone]}],
        },
    )
    assert refused.status_code == 400
    assert refused.json()["errorCode"] == "ATLAS-400-00-07D"

    after = await view_of(typed, node)
    assert after["name"] == "Keep"
    assert after["labels"] == ["keep-me"]
    assert after["classificationNames"] == ["c_pii"]
    assert after["updateTime"] == before["updateTime"]
    assert len((await typed.get(f"{ENTITY}/{node}/audit")).json()) == audits


@pytest.mark.covers(D, rules=["AVW-09"])
async def test__an_unknown_section_attribute_is_refused(typed: httpx.AsyncClient) -> None:
    """A sections entry the type has no attribute for is refused naming it (AVW-09)."""
    node = await create(typed, "r_node", qualifiedName="node@bogus")
    start = await view_of(typed, node)

    refused = await save(typed, dict(start, sections=[{"attribute": "no_such_attribute", "entities": [node]}]))
    assert refused.status_code == 400
    assert refused.json()["errorCode"] == "AURELIUS-400-00-001"
    assert "no_such_attribute" in refused.json()["messages"][0]


@pytest.mark.covers(D, rules=["AVW-02", "AVW-03"])
async def test__the_door_refuses_a_body_it_cannot_act_on(typed: httpx.AsyncClient) -> None:
    """One ``VIEW_REFUSED`` with one message per problem; EVL's refusals unchanged (AVW-02, AVW-03)."""
    refused = await save(typed, {})
    assert refused.status_code == 400
    assert refused.json()["errorCode"] == "AURELIUS-400-00-001"
    assert refused.json()["messages"] == [
        "A view through the door names its typeName",
        "A view through the door carries its attributes",
    ]

    no_time = await save(typed, {"guid": str(uuid.uuid4()), "typeName": "s_database", "attributes": {}})
    assert no_time.json()["messages"] == ["An update through the view door names the updateTime of the view it edited"]

    unknown = await save(typed, {"typeName": "no_such_type", "attributes": {}})
    assert unknown.json()["messages"] == ["Unknown entity type: no_such_type"]

    bad_set = await save(typed, {"typeName": "s_database", "attributes": {}, "classifications": "c_pii"})
    assert bad_set.json()["messages"] == ["The classifications must be a list of names"]

    mandatory = await save(typed, {"typeName": "r_pin", "attributes": {"qualifiedName": "pin@evl"}})
    assert mandatory.status_code == 404
    assert mandatory.json()["errorCode"] == "ATLAS-404-00-007"
    assert "mandatory attribute value missing in type r_pin" in mandatory.json()["errorMessage"]


@pytest.mark.covers(f"{R}.write", rules=["AVW-01"])
async def test__the_write_door_needs_the_write_role(typed: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """A reader 403 in the Aurelius shape and may not update either; the writer goes through (AVW-01)."""
    reader = as_roles(issuer, "reader", "atlas-read")
    writer = as_roles(issuer, "writer", "atlas-write")

    body = {"typeName": "s_database", "attributes": {"qualifiedName": "db@role"}}
    refused = await typed.post(DOOR, json=body, headers=reader)
    assert refused.status_code == 403
    assert refused.json() == {
        "errorCode": "AURELIUS-403-00-005",
        "errorMessage": "reader is not authorized to write the catalogue",
    }

    created = await typed.post(DOOR, json=body, headers=writer)
    assert created.status_code == 200, created.text

    stale = created.json()
    held = await typed.post(
        DOOR,
        json={**stale, "attributes": {**stale["attributes"], "title": "nope"}},
        headers=reader,
    )
    assert (held.status_code, held.json()["errorCode"]) == (403, "AURELIUS-403-00-005")


# impact=moderate, likelihood=medium (an audit trail that double-counts a save misleads every review)
@pytest.mark.covers(D, rules=["AVW-10"])
async def test__one_save_audits_one_update_per_changed_kind(typed: httpx.AsyncClient) -> None:
    """A save changing attributes, labels, tags and meanings records one update plus each kind's own event."""
    node = await create(typed, "Asset", qualifiedName="asset@audit", name="Auditee")
    term = await make_term(typed, "credit")
    start = await view_of(typed, node)
    audits = await typed.get(f"{ENTITY}/{node}/audit")
    assert audits.status_code == 200
    before = Counter(event["action"] for event in audits.json())

    saved = await save(
        typed,
        {
            "guid": node,
            "typeName": "Asset",
            "updateTime": start["updateTime"],
            "attributes": {"qualifiedName": "asset@audit", "name": "Audited"},
            "labels": ["reported"],
            "classifications": ["c_pii"],
            "meanings": [term],
        },
    )
    assert saved.status_code == 200, saved.text

    # one request's events may share a millisecond, so the tally is compared, not the order (LBL-05)
    now = Counter(event["action"] for event in (await typed.get(f"{ENTITY}/{node}/audit")).json())
    new = now - before
    assert new["ENTITY_UPDATE"] == 1
    assert set(new) >= {"ENTITY_UPDATE", "LABEL_ADD", "CLASSIFICATION_ADD", "TERM_ADD"}
