"""The view family's two doors over HTTP (AVR-01, AVR-02, AVR-08, AVR-10, AVR-13, VDR-13).

The search door of ``POST /api/aurelius/v1/search`` and the read door of ``GET /api/aurelius/v1/entity/guid/{guid}``,
on entities written through the store until 2.4 creates them over REST (DD-051). Both answer the same view
shape (ADR 064): the last test reads one entity through both doors and compares the card fields.
"""

from collections.abc import AsyncIterator

import httpx2 as httpx
import pytest
from aurelius_atlas_core.app_search_document import StoredVerdict
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.testing.entity_samples import CLASSIFICATION_TYPES, SAMPLE_TYPES, sample_entity
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelationship
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


@pytest.mark.covers(f"{S}.search", rules=["AVR-08", "MMS-09"])
async def test__the_search_door_answers_cards_facets_and_a_total(seeded: httpx.AsyncClient) -> None:
    """Both entities of an empty query, one of a word; the answer's shape and a facet over the types (AVR-08)."""
    answer = (await seeded.post(SEARCH, json={"query": "orders"})).json()
    assert answer["total"] == 1
    (card,) = answer["cards"]
    assert card["guid"] == TABLE
    assert card["name"] == card["displayText"] == "orders"
    assert card["typeName"] == "s_table"
    assert "typeAlias" not in card  # no attribute: the key is left out, as every null field (AVS-01, MMS-09)
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


@pytest.mark.covers(f"{R}.read", rules=["VDR-02"])
async def test__the_read_door_answers_the_ends_of_its_entity_own_relationships(
    seeded: httpx.AsyncClient, app: FastAPI
) -> None:
    """Each end answers under its relationship attribute, with its type and state; both ends see each other.

    The table's ``home`` answers the database and the database's ``tables`` the table (VDR-02, DD-604); the
    ends ride the entity's own edges, which the store lists, in one batched read.
    """
    store: EntityStore = app.state.entity_store
    created = await RelationshipStore(store, user="u").create(
        AtlasRelationship(
            type_name="s_table_home",
            end1=AtlasObjectId(guid=TABLE, type_name="s_table"),
            end2=AtlasObjectId(guid=DB, type_name="s_database"),
        )
    )
    assert created.guid is not None

    view = (await seeded.get(f"{VIEW}/{TABLE}")).json()
    assert view["sections"] == [
        {"attribute": "home", "entities": [{"guid": DB, "typeName": "s_database", "status": "ACTIVE"}]}
    ]
    other = (await seeded.get(f"{VIEW}/{DB}")).json()
    assert [(r["attribute"], [e["guid"] for e in r["entities"]]) for r in other["sections"]] == [("tables", [TABLE])]

    await RelationshipStore(store, user="u").delete_by_id(created.guid)
    after = (await seeded.get(f"{VIEW}/{TABLE}")).json()
    assert after["sections"] == []  # a deleted edge answers nothing (DD-604)


@pytest.mark.covers(f"{R}.read", rules=["VDR-05"])
async def test__the_read_door_answers_a_propagated_tag_with_the_entity_it_came_from(
    seeded: httpx.AsyncClient, app: FastAPI
) -> None:
    """The view names a tag propagated onto the entity, and the source it rode in from (VDR-05, DD-835).

    ``a`` carries ``c_pii``; the process reads it and writes ``b``, so the tag propagates downstream (PRO-01).
    ``b``'s view answers the name with ``a`` as its source, and never moves it into the entity's own names.
    """
    created = await seeded.post("/api/atlas/v2/types/typedefs", json=CLASSIFICATION_TYPES)
    assert created.status_code == 200, created.text
    store: EntityStore = app.state.entity_store
    registry = store.registry
    a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    p1 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    await store.write(
        [
            EntityChange(sample_entity(registry, "p_data", a, {"qualifiedName": "a", "name": "A"})),
            EntityChange(sample_entity(registry, "p_data", b, {"qualifiedName": "b", "name": "B"})),
            EntityChange(sample_entity(registry, "p_process", p1, {"qualifiedName": "p1", "name": "P1"})),
        ]
    )
    await RelationshipStore(store, user="u").create(
        AtlasRelationship(
            type_name="p_input",
            end1=AtlasObjectId(guid=a, type_name="p_data"),
            end2=AtlasObjectId(guid=p1, type_name="p_process"),
        )
    )
    await RelationshipStore(store, user="u").create(
        AtlasRelationship(
            type_name="p_output",
            end1=AtlasObjectId(guid=p1, type_name="p_process"),
            end2=AtlasObjectId(guid=b, type_name="p_data"),
        )
    )
    attached = await seeded.post(f"/api/atlas/v2/entity/guid/{a}/classifications", json=[{"typeName": "c_pii"}])
    assert attached.status_code == 204, attached.text

    view = (await seeded.get(f"{VIEW}/{b}")).json()
    assert view["classificationNames"] == []  # the tag is a's, not b's (AVS-01)
    assert view["propagatedClassifications"] == [
        {"typeName": "c_pii", "entities": [{"guid": a, "name": "A", "typeName": "p_data", "status": "ACTIVE"}]}
    ]

    own = (await seeded.get(f"{VIEW}/{a}")).json()
    assert own["classificationNames"] == ["c_pii"]  # attached here, so a's own (VDR-05)
    assert own["propagatedClassifications"] == []

    card = (await seeded.post(SEARCH, json={"query": "b"})).json()["cards"][0]
    # a result line names the propagated tag and its source too (VDR-12, DD-836)
    assert card["propagatedClassifications"] == [
        {"typeName": "c_pii", "entities": [{"guid": a, "name": "A", "typeName": "p_data", "status": "ACTIVE"}]}
    ]


@pytest.mark.covers(f"{S}.search", f"{R}.read", rules=["VDR-13", "AVS-11"])
async def test__both_doors_answer_the_joined_governance_verdicts(seeded: httpx.AsyncClient, app: FastAPI) -> None:
    """The refused verdicts ride both doors' answers, read from the verdicts index (VDR-13, AVS-11, DD-838).

    The worker's write of the verdict documents stands in for the round here: the doors join whatever the index
    holds, sorted by rule name with the compliant verdict left out. The webapp's mark (16.5h's card) reads it
    from the same field.
    """
    store: EntityStore = app.state.entity_store
    await store.documents.replace_verdicts(
        {
            TABLE: [
                StoredVerdict(
                    id=f"{TABLE}--r-z",
                    entity_guid=TABLE,
                    guid="r-z",
                    name="Zeta",
                    compliant="0",
                    noncompliant_message="the attribute holds no value to show",
                ),
                StoredVerdict(
                    id=f"{TABLE}--r-a",
                    entity_guid=TABLE,
                    guid="r-a",
                    name="Alpha",
                    compliant="0",
                    noncompliant_message="the record does not carry the attribute",
                ),
                StoredVerdict(id=f"{TABLE}--r-p", entity_guid=TABLE, guid="r-p", name="Passes", compliant="1"),
            ]
        }
    )
    rows = [
        {"rule": "r-a", "name": "Alpha", "message": "the record does not carry the attribute"},
        {"rule": "r-z", "name": "Zeta", "message": "the attribute holds no value to show"},
    ]

    view = (await seeded.get(f"{VIEW}/{TABLE}")).json()
    card = (await seeded.post(SEARCH, json={"query": "orders"})).json()["cards"][0]

    assert view["verdicts"] == rows
    assert card["verdicts"] == rows  # the same join on both doors (VDR-13)
    other = (await seeded.get(f"{VIEW}/{DB}")).json()
    assert other["verdicts"] == []  # an unjudged entity answers the field empty (AVS-05)


@pytest.mark.covers(f"{S}.search", f"{R}.read", rules=["AVR-08", "AVR-10", "MMS-09"])
async def test__both_doors_answer_the_same_card_fields(seeded: httpx.AsyncClient) -> None:
    """The card from the search door and the view from the read door hold the same shared fields (AVR-08, AVR-10)."""
    answer = (await seeded.post(SEARCH, json={"query": "orders"})).json()
    (card,) = answer["cards"]
    view = (await seeded.get(f"{VIEW}/{TABLE}")).json()

    shared = ("guid", "typeName", "superTypeNames", "name", "qualifiedName", "displayText", "status", "labels")
    assert {field: card[field] for field in shared} == {field: view[field] for field in shared}
