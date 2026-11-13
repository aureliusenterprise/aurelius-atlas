"""The HTTP side of the entity reads of ``EntityREST`` (ERD-01 to ERD-10), on entities written through the store.

Read from ``EntityREST``, ``AtlasEntityStoreV2`` and ``EntityGraphRetriever`` of Apache Atlas 2.4.0 and its tests
``EntityV2JerseyResourceIT`` and ``AtlasEntityStoreV2Test``. Entities are seeded through ``EntityStore`` until 2.4
creates them over REST (DD-051).
"""

from typing import Any, cast

import httpx2 as httpx
import pytest
from aurelius_atlas_core.entity_store import EntityChange, EntityStore
from aurelius_atlas_core.testing.entity_samples import SAMPLE_TYPES, sample_entity, sample_types
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient
from aurelius_atlas_typesystem.registry import TypeRegistry
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI

E = "aurelius_atlas_server.routes.entity"
ENTITY = "/api/atlas/v2/entity"
JSON = "application/json; charset=UTF-8"

DB, COL1, COL2, TABLE = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
    "33333333-3333-4333-8333-333333333333",
    "44444444-4444-4444-8444-444444444444",
)
"""The GUIDs of the seeded database, its two columns and the table (DV-161: every GUID is UUID text)."""


@pytest.fixture
async def seeded(client: httpx.AsyncClient, app: FastAPI) -> httpx.AsyncClient:
    """The client of a server holding the sample types, a database, two columns and a table."""
    created = await client.post("/api/atlas/v2/types/typedefs", json=SAMPLE_TYPES)
    assert created.status_code == 200, created.text
    store: EntityStore = app.state.entity_store
    registry = store.registry
    await store.write(
        [
            EntityChange(sample_entity(registry, "s_database", DB, {"qualifiedName": "db@cl", "title": "DB"})),
            EntityChange(sample_entity(registry, "s_column", COL1, {"qualifiedName": "c1@cl", "position": 1})),
            EntityChange(sample_entity(registry, "s_column", COL2, {"qualifiedName": "c2@cl"})),
            EntityChange(
                sample_entity(
                    registry,
                    "s_table",
                    TABLE,
                    {
                        "qualifiedName": "t@cl",
                        "name": "orders",
                        "db": DB,
                        "columns": [COL1, COL2],
                        "sizes": [1.5],
                    },
                )
            ),
        ]
    )
    return client


def error(code: str, message: str) -> dict[str, str]:
    """Atlas's error body."""
    return {"errorCode": code, "errorMessage": message}


async def get(client: httpx.AsyncClient, path: str, params: Any = None) -> tuple[int, Any]:  # noqa: ANN401 - JSON
    """The status and JSON body of a GET, which must be Atlas JSON."""
    response = await client.get(f"{ENTITY}{path}", params=params)
    assert response.headers["content-type"] == JSON
    return response.status_code, response.json()


@pytest.mark.covers(
    f"{E}.get_by_id",
    f"{E}.get_header_by_id",
    f"{E}.get_by_unique_attributes",
    f"{E}.get_entity_header_by_unique_attributes",
    f"{E}.get_entities_by_unique_attributes",
    f"{E}.get_by_guids",
    rules=["ERD-01"],
)
@pytest.mark.parametrize(
    ("path", "param"),
    [
        ("/guid/{}", "guid"),
        ("/guid/{}/header", "guid"),
        ("/uniqueAttribute/type/{}", "typeName"),
        ("/uniqueAttribute/type/{}/header", "typeName"),
        ("/bulk/uniqueAttribute/type/{}", "typeName"),
        ("/bulk?guid={}", "guid"),
    ],
)
async def test__a_guid_or_type_name_over_4096_characters_is_refused(
    client: httpx.AsyncClient, path: str, param: str
) -> None:
    """``Servlets.validateQueryParamLength`` runs before anything is read."""
    assert await get(client, path.format("x" * 4097)) == (
        400,
        error("ATLAS-400-00-057", f"Length of query param {param} exceeds the limit"),
    )


@pytest.mark.covers(f"{E}.get_by_id", f"{E}.retriever", f"{E}.flag", rules=["ERD-02", "ERD-03", "ERD-05", "ERD-06"])
async def test__an_entity_is_read_by_guid_with_the_entities_it_owns(seeded: httpx.AsyncClient) -> None:
    """``getById``: owned columns in ``referredEntities``, in full or minimal; ``ignoreRelationships`` drops them."""
    status, found = await get(seeded, f"/guid/{TABLE}")
    _, minimal = await get(seeded, f"/guid/{TABLE}", {"minExtInfo": "TRUE", "ignoreRelationships": "true"})
    _, not_flags = await get(seeded, f"/guid/{TABLE}", [("minExtInfo", "yes"), ("ignoreRelationships", "false")])

    assert status == 200
    assert found["entity"]["attributes"]["columns"] == [
        {"guid": COL1, "typeName": "s_column"},
        {"guid": COL2, "typeName": "s_column"},
    ]
    assert found["entity"]["attributes"]["db"] == {
        "guid": DB,
        "typeName": "s_database",
        "uniqueAttributes": {"qualifiedName": "db@cl"},
    }
    assert found["entity"]["attributes"]["sizes"] == [1.5]
    assert found["entity"]["relationshipAttributes"] == {"home": None}
    assert (found["entity"]["createTime"], found["entity"]["labels"], found["entity"]["proxy"]) == (1000, [], False)
    assert found["referredEntities"][COL2]["attributes"]["comment"] is None
    assert minimal["referredEntities"][COL2]["attributes"] == {"qualifiedName": "c2@cl"}
    assert "relationshipAttributes" not in minimal["entity"]
    assert not_flags == found


@pytest.mark.covers(f"{E}.get_by_id", f"{E}.get_header_by_id", rules=["ERD-02", "ERD-07"])
async def test__an_unknown_guid_is_not_found(client: httpx.AsyncClient) -> None:
    """``INSTANCE_GUID_NOT_FOUND`` for the entity and its header; text that is no GUID is refused first (DV-161)."""
    missing = error("ATLAS-404-00-005", f"Given instance guid {DB} is invalid/not found")

    assert await get(client, f"/guid/{DB}") == (404, missing)
    assert await get(client, f"/guid/{DB}/header") == (404, missing)
    for path in ("/guid/nope", "/guid/nope/header"):
        assert await get(client, path) == (400, error("ATLAS-400-00-021", "ObjectId is not valid nope"))


@pytest.mark.covers(f"{E}.get_by_guids", rules=["ERD-02", "ERD-06"])
async def test__entities_are_read_in_bulk_by_guid(seeded: httpx.AsyncClient) -> None:
    """``getByGuids``: in order, an entity asked for is not referred too; one unknown GUID or none fails."""
    status, found = await get(seeded, "/bulk", [("guid", COL1), ("guid", TABLE)])

    assert status == 200
    assert [entity["guid"] for entity in found["entities"]] == [COL1, TABLE]
    assert list(found["referredEntities"]) == [COL2]
    assert await get(seeded, "/bulk", [("guid", TABLE), ("guid", "nope")]) == (
        400,
        error("ATLAS-400-00-021", "ObjectId is not valid nope"),
    )
    absent = "55555555-5555-4555-8555-555555555555"
    assert await get(seeded, "/bulk", [("guid", TABLE), ("guid", absent)]) == (
        404,
        error("ATLAS-404-00-005", f"Given instance guid {absent} is invalid/not found"),
    )
    assert await get(seeded, "/bulk") == (404, error("ATLAS-404-00-005", "Given instance guid [] is invalid/not found"))


@pytest.mark.covers(f"{E}.get_header_by_id", f"{E}.get_entity_header_by_unique_attributes", rules=["ERD-07"])
async def test__headers_are_read_by_guid_and_by_unique_attributes(seeded: httpx.AsyncClient) -> None:
    """``getHeaderById`` has ``classifications``; the header by unique attributes does not."""
    _, by_guid = await get(seeded, f"/guid/{DB}/header")
    status, by_unique = await get(seeded, "/uniqueAttribute/type/s_database/header", {"attr:qualifiedName": "db@cl"})

    assert status == 200
    assert by_guid == {
        "typeName": "s_database",
        "attributes": {"qualifiedName": "db@cl", "name": ""},
        "guid": DB,
        "status": "ACTIVE",
        "displayText": "DB",
        "classificationNames": [],
        "classifications": [],
        "meaningNames": [],
        "meanings": [],
        "isIncomplete": False,
        "labels": [],
    }
    assert by_unique == {key: value for key, value in by_guid.items() if key != "classifications"}


@pytest.mark.covers(
    f"{E}.get_by_unique_attributes",
    f"{E}.unique_attributes",
    f"{E}.ensure_entity_type",
    f"{E}.validate_unique_attributes",
    rules=["ERD-08", "ERD-09"],
)
async def test__an_entity_is_read_by_its_unique_attributes(seeded: httpx.AsyncClient) -> None:
    """``attr:`` values with their first value; a sub type is found from its super type; misses and bad input fail."""
    path = "/uniqueAttribute/type/{}"

    status, found = await get(
        seeded, path.format("s_ref"), [("attr:qualifiedName", "t@cl"), ("attr:qualifiedName", "x")]
    )

    assert (status, found["entity"]["guid"], found["referredEntities"][COL1]["guid"]) == (200, TABLE, COL1)
    assert await get(seeded, path.format("s_table"), {"attr:qualifiedName": "nope"}) == (
        404,
        error("ATLAS-404-00-009", "Instance s_table with unique attribute {qualifiedName=nope} does not exist"),
    )
    assert await get(seeded, path.format("s_table"), {"attr:__guid": "t"}) == (
        404,
        error("ATLAS-404-00-009", "Instance s_table with unique attribute {__guid=t} does not exist"),
    )
    assert await get(seeded, path.format("s_place"), {"attr:qualifiedName": "t@cl"}) == (
        400,
        error("ATLAS-400-00-014", "Type ENTITY with name s_place does not exist"),
    )
    assert await get(seeded, path.format("s_table"), {"qualifiedName": "t@cl"}) == (
        400,
        error("ATLAS-400-00-013", "Type s_table with unique attribute  does not exist"),
    )
    assert await get(seeded, path.format("s_table"), {"attr:name": "orders"}) == (
        400,
        error("ATLAS-400-00-013", "Type s_table with unique attribute name does not exist"),
    )


@pytest.mark.covers(f"{E}.get_entities_by_unique_attributes", f"{E}.unique_attribute_sets", rules=["ERD-08", "ERD-09"])
async def test__entities_are_read_in_bulk_by_sets_of_unique_attributes(seeded: httpx.AsyncClient) -> None:
    """``attr_<n>:`` sets in the order they appear; sets that find nothing are left out; every set is checked."""
    path = "/bulk/uniqueAttribute/type/s_column"

    status, found = await get(
        seeded,
        path,
        [
            ("attr_2:qualifiedName", "c2@cl"),
            ("attr_x", "ignored"),
            ("attr_1:qualifiedName", "c1@cl"),
            ("attr_3:qualifiedName", "no"),
        ],
    )

    assert (status, [entity["guid"] for entity in found["entities"]]) == (200, [COL2, COL1])
    assert await get(seeded, path) == (200, {})
    assert await get(seeded, path, [("attr_1:qualifiedName", "c1@cl"), ("attr_2:position", "1")]) == (
        400,
        error("ATLAS-400-00-013", "Type s_column with unique attribute position does not exist"),
    )


@pytest.mark.covers(f"{E}.entity_store", rules=["ERD-10"])
async def test__reads_see_types_another_server_stored(
    settings: ServerSettings, fake_es: FakeClient, auth_headers: dict[str, str]
) -> None:
    """Each request refreshes the registry when due (TDS-13): a type created elsewhere is known at once."""
    app = create_app(settings.model_copy(update={"typedef_refresh_seconds": 0.0}))
    other = TypedefStore(TypeRegistry(), ElasticsearchTypedefDocument(cast("AsyncElasticsearch", fake_es)))
    path = f"{ENTITY}/uniqueAttribute/type/s_table"

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://aurelius-atlas", headers=auth_headers
        ) as client:
            unknown = await client.get(path, params={"attr:qualifiedName": "t@cl"})
            await other.load()
            await other.create_types_def(sample_types())
            known = await client.get(path, params={"attr:qualifiedName": "t@cl"})

    assert (unknown.status_code, unknown.json()["errorCode"]) == (400, "ATLAS-400-00-014")
    assert (known.status_code, known.json()["errorCode"]) == (404, "ATLAS-404-00-009")
