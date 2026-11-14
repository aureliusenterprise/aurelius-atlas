"""The view family's doors against the container, on the dev store (AVR-01, AVR-08, AVR-10).

A results page's request (query, type filter, facets, a sort) through the search door, and the details
read of one of its cards through the read door: the same entity, answering the same fields (AVR-08,
ADR 064). The entities are namespaced to the run and removed with the session's other writes (ECU-01).
"""

import uuid
from collections.abc import Callable

import httpx2 as httpx
import pytest

SEARCH = "/api/aurelius/v1/search"
VIEW = "/api/aurelius/v1/entity/guid"
NIL = "00000000-0000-0000-0000-000000000000"

SHARED = ("guid", "typeName", "superTypeNames", "name", "qualifiedName", "displayText", "status", "labels")
"""The card's fields both doors answer (AVR-08)."""


async def make(client: httpx.AsyncClient, type_name: str, run: str, **attributes: str) -> str:
    """An entity of ``type_name`` named for ``run``, created as the writer; its GUID."""
    body = {"entity": {"typeName": type_name, "attributes": {"qualifiedName": f"{run}.{type_name}", **attributes}}}
    created = await client.post("/api/atlas/v2/entity", json=body)
    assert created.status_code == 200, created.text
    return created.json()["mutatedEntities"]["CREATE"][0]["guid"]


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.critical
@pytest.mark.covers("aurelius_atlas_server.routes.view_search.search", rules=["AVR-01", "AVR-08"])
async def test__a_results_request_answers_cards_facets_and_a_total(
    client: httpx.AsyncClient, anonymous: httpx.AsyncClient, reader_token: Callable[[], str]
) -> None:
    """The dev store's door: words of a run's name, typed out, faceted and sorted; a reader reads; an anonymous 401."""
    run = uuid.uuid4().hex
    domain = await make(client, "m4i_data_domain", run, name=f"view door {run}", definition="orders of the door")
    table = await make(client, "Asset", run, name=f"view asset {run}")

    asked = {
        "query": run,
        "filters": {"typeName": ["m4i_data_domain", "Asset"]},
        "facets": ["typeName"],
        "sort": {"createTime": "desc"},
    }
    answer = (await client.post(SEARCH, json=asked)).json()

    assert answer["total"] == 2
    assert {card["guid"] for card in answer["cards"]} == {domain, table}
    assert answer["cards"][0]["createTime"] >= answer["cards"][1]["createTime"]
    assert {entry["value"]: entry["count"] for entry in answer["facets"]["typeName"]} == {
        "m4i_data_domain": 1,
        "Asset": 1,
    }

    typed = await client.post(SEARCH, json={"filters": {"typeName": "m4i_data_domain"}, "query": run})
    assert [card["guid"] for card in typed.json()["cards"]] == [domain]

    reader = {"Authorization": f"Bearer {reader_token()}"}
    assert (await client.post(SEARCH, json={"limit": 1}, headers=reader)).status_code == 200
    assert (await anonymous.post(SEARCH, json={})).status_code == 401


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_server.routes.view_search.search",
    "aurelius_atlas_server.routes.view_entity.read",
    rules=["AVR-08", "AVR-10"],
)
async def test__the_details_read_of_a_card_agrees_with_the_search_door(
    client: httpx.AsyncClient, reader_token: Callable[[], str]
) -> None:
    """One entity read through both doors: the same shared fields; a GUID of none answers the Atlas 404 (AVR-10)."""
    run = uuid.uuid4().hex
    guid = await make(client, "m4i_data_entity", run, name=f"view read {run}", definition="read through one door")

    answer = (await client.post(SEARCH, json={"query": run})).json()
    (card,) = answer["cards"]
    assert card["guid"] == guid

    view = (await client.get(f"{VIEW}/{guid}")).json()
    assert {field: card[field] for field in SHARED} == {field: view[field] for field in SHARED}
    assert view["attributes"]["definition"] == "read through one door"

    reader = {"Authorization": f"Bearer {reader_token()}"}
    assert (await client.get(f"{VIEW}/{guid}", headers=reader)).status_code == 200

    missing = await client.get(f"{VIEW}/{NIL}")
    assert (missing.status_code, missing.json()["errorCode"]) == (404, "ATLAS-404-00-005")
