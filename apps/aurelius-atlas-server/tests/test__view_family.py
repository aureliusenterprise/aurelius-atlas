"""The view family's two doors over HTTP (AVR-01, AVR-02, AVR-08, AVR-10, AVR-13).

The search door of ``POST /api/aurelius/v1/search`` and the read door of ``GET /api/aurelius/v1/entity/guid/{guid}``,
on entities written through the store until 2.4 creates them over REST (DD-051). Both answer the same view
shape (ADR 064): the last test reads one entity through both doors and compares the card fields.
"""

from collections.abc import AsyncIterator

import httpx2 as httpx
import pytest
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.testing.entity_samples import SAMPLE_TYPES, sample_entity
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient
from fake_issuer import FakeIssuer
from fastapi import FastAPI

S = "aurelius_atlas_server.routes.view_search"
R = "aurelius_atlas_server.routes.view_entity"
SEARCH = "/api/aurelius/v1/search"
VIEW = "/api/aurelius/v1/entity/guid"

DB, TABLE = (
    "11111111-1111-4111-8111-111111111111",
    "44444444-4444-4444-8444-444444444444",
)
NIL = "00000000-0000-0000-0000-000000000000"
"""The GUIDs of the seeded database and table, and the nil UUID no entity holds (DV-161)."""


def as_roles(issuer: FakeIssuer, user: str, *roles: str) -> dict[str, str]:
    """The ``Authorization`` header of a token of the user holding these roles of the server's client."""
    return {"Authorization": f"Bearer {issuer.token(user, atlas_roles=roles)}"}


@pytest.fixture
async def seeded(client: httpx.AsyncClient, app: FastAPI) -> httpx.AsyncClient:
    """The client of a server holding a table, a database, and an entity of no name."""
    created = await client.post("/api/atlas/v2/types/typedefs", json=SAMPLE_TYPES)
    assert created.status_code == 200, created.text
    store: EntityStore = app.state.entity_store
    registry = store.registry
    await store.write(
        [
            EntityChange(sample_entity(registry, "s_database", DB, {"qualifiedName": "db@cl"})),
            EntityChange(
                sample_entity(
                    registry,
                    "s_table",
                    TABLE,
                    {"qualifiedName": "t@cl", "name": "orders"},
                    labels=["reporting"],
                )
            ),
        ]
    )
    return client


@pytest.fixture
async def anonymous(settings: ServerSettings, fake_es: FakeClient) -> AsyncIterator[httpx.AsyncClient]:
    """A client of the started application without credentials (AUT-04)."""
    _ = fake_es
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas") as client:
            yield client


@pytest.mark.covers(f"{S}.search", rules=["AVR-01"])
async def test__the_search_door_needs_the_read_role(
    seeded: httpx.AsyncClient, anonymous: httpx.AsyncClient, issuer: FakeIssuer
) -> None:
    """Anonymous 401; without the role 403 in the Aurelius shape; with it the cards (AVR-01, AUT-04)."""
    assert (await seeded.post(SEARCH, json={})).status_code == 200

    anonymous_answer = await anonymous.post(SEARCH, json={})
    assert anonymous_answer.status_code == 401

    watcher = as_roles(issuer, "watcher")
    refused = await seeded.post(SEARCH, json={}, headers=watcher)
    assert refused.status_code == 403
    assert refused.json() == {
        "errorCode": "AURELIUS-403-00-004",
        "errorMessage": "watcher is not authorized to read the catalogue",
    }


@pytest.mark.covers(f"{S}.search", rules=["AVR-08"])
async def test__the_search_door_answers_cards_facets_and_a_total(seeded: httpx.AsyncClient) -> None:
    """Both entities of an empty query, one of a word; the answer's shape and a facet over the types (AVR-08)."""
    answer = (await seeded.post(SEARCH, json={"query": "orders"})).json()
    assert answer["total"] == 1
    (card,) = answer["cards"]
    assert card["guid"] == TABLE
    assert card["name"] == card["displayText"] == "orders"
    assert card["typeName"] == "s_table"
    assert card["labels"] == ["reporting"]
    assert card["status"] == "ACTIVE"
    assert card["breadcrumb"] == []
    assert card["relations"] == []
    assert card["quality"] == []
    assert card["stale"] is False
    assert "governed" not in card

    everything = await seeded.post(SEARCH, json={"facets": ["typeName"]})
    assert everything.json()["total"] == 2
    assert everything.json()["facets"]["typeName"] == [
        {"value": "s_database", "count": 1},
        {"value": "s_table", "count": 1},
    ]


@pytest.mark.covers(f"{S}.search", rules=["AVR-02", "AVR-13"])
async def test__a_refused_search_answers_400_with_one_message_per_problem(seeded: httpx.AsyncClient) -> None:
    """The door's own shape: the Aurelius code, the joined message, and one message each (AVR-02, AVR-13)."""
    refused = await seeded.post(SEARCH, json={"bogus": 1, "limit": 0})
    assert refused.status_code == 400
    assert refused.json() == {
        "errorCode": "AURELIUS-400-00-001",
        "errorMessage": "The view door refuses the request: The request holds an unknown option: bogus; "
        "Limit must be between 1 and 100",
        "messages": ["The request holds an unknown option: bogus", "Limit must be between 1 and 100"],
    }

    bodyless = await seeded.post(SEARCH, json=[], headers={"Content-Type": "application/json"})
    assert (bodyless.status_code, bodyless.json()["errorCode"]) == (400, "AURELIUS-400-00-001")


@pytest.mark.covers(f"{R}.read", rules=["AVR-10"])
async def test__the_read_door_answers_the_view_with_the_read_role(
    seeded: httpx.AsyncClient, issuer: FakeIssuer
) -> None:
    """The read door answers the live view, with the role.

    Without it 403 before anything is read; with it the fields, empty derived, and no mark (AVR-10, AVS-02).
    """
    refused = await seeded.get(f"{VIEW}/{TABLE}", headers=as_roles(issuer, "watcher"))
    assert (refused.status_code, refused.json()["errorCode"]) == (403, "AURELIUS-403-00-004")

    view = (await seeded.get(f"{VIEW}/{TABLE}")).json()
    assert view["guid"] == TABLE
    assert view["typeName"] == "s_table"
    assert view["name"] == view["displayText"] == "orders"
    assert view["qualifiedName"] == "t@cl"
    assert view["status"] == "ACTIVE"
    assert view["labels"] == ["reporting"]
    assert view["attributes"] == {"qualifiedName": "t@cl", "name": "orders"}
    assert view["breadcrumb"] == []
    assert view["relations"] == []
    assert view["quality"] == []
    assert view["sections"] == []
    assert view["stale"] is False
    assert "governed" not in view


@pytest.mark.covers(f"{R}.read", rules=["AVR-10"])
async def test__a_guid_without_an_entity_is_the_atlas_404(seeded: httpx.AsyncClient) -> None:
    """A missing GUID answers the Atlas 404, not the door's refusal.

    Text that is no UUID is refused as an invalid object id (AVR-10, DV-161).
    """
    missing = await seeded.get(f"{VIEW}/{NIL}")
    assert (missing.status_code, missing.json()["errorCode"]) == (404, "ATLAS-404-00-005")
    assert missing.json()["errorMessage"] == f"Given instance guid {NIL} is invalid/not found"

    invalid = await seeded.get(f"{VIEW}/not-a-guid")
    assert (invalid.status_code, invalid.json()["errorCode"]) == (400, "ATLAS-400-00-021")


@pytest.mark.covers(f"{S}.search", f"{R}.read", rules=["AVR-08", "AVR-10"])
async def test__both_doors_answer_the_same_card_fields(seeded: httpx.AsyncClient) -> None:
    """The card from the search door and the view from the read door hold the same shared fields (AVR-08, AVR-10)."""
    answer = (await seeded.post(SEARCH, json={"query": "orders"})).json()
    (card,) = answer["cards"]
    view = (await seeded.get(f"{VIEW}/{TABLE}")).json()

    shared = ("guid", "typeName", "superTypeNames", "name", "qualifiedName", "displayText", "status", "labels")
    assert {field: card[field] for field in shared} == {field: view[field] for field in shared}
