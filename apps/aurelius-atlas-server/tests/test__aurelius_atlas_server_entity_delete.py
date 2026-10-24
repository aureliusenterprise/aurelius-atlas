"""The HTTP side of deleting and purging entities (EDL-01 to EDL-08), on the fake Elasticsearch.

Read from ``EntityREST`` (``deleteByGuid``, ``deleteByGuids``, ``deleteByUniqueAttribute``), ``AdminResource``
(``purgeByIds``) and ``AuditFilter`` (``deleteType``) of Apache Atlas 2.4.0; the delete rules themselves are tested
on ``EntityWriter`` in ``aurelius-atlas-core``.
"""

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from aurelius_atlas_core.testing.entity_samples import SAMPLE_TYPES
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient

E = "aurelius_atlas_server.routes.entity"
ENTITY = "/api/atlas/v2/entity"
PURGE = "/api/atlas/admin/purge"


async def started(settings: ServerSettings) -> AsyncIterator[httpx.AsyncClient]:
    """A client of a started server with the sample types."""
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://aurelius-atlas") as client:
            created = await client.post("/api/atlas/v2/types/typedefs", json=SAMPLE_TYPES)
            assert created.status_code == 200, created.text
            yield client


@pytest.fixture
async def typed(settings: ServerSettings, fake_es: FakeClient) -> AsyncIterator[httpx.AsyncClient]:
    """A server with the default settings: soft deletes, no override."""
    _ = fake_es
    async for client in started(settings):
        yield client


@pytest.fixture
async def overridable(settings: ServerSettings, fake_es: FakeClient) -> AsyncIterator[httpx.AsyncClient]:
    """A server whose requests may choose the delete type."""
    _ = fake_es
    async for client in started(settings.model_copy(update={"delete_type_override": True})):
        yield client


async def send(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:  # noqa: ANN401
    """The status and JSON body of a request."""
    response = await client.request(method, url, **kwargs)
    return response.status_code, response.json()


async def create(client: httpx.AsyncClient, *entities: dict[str, Any]) -> dict[str, str]:
    """Create the entities; their GUIDs by request GUID."""
    _, created = await send(client, "POST", f"{ENTITY}/bulk", json={"entities": list(entities)})
    return created["guidAssignments"]


def database(guid: str, name: str) -> dict[str, Any]:
    """A database as Atlas JSON."""
    return {"typeName": "s_database", "guid": guid, "attributes": {"qualifiedName": name}}


@pytest.mark.covers(f"{E}.delete_by_guid", f"{E}.delete_by_guids", f"{E}.delete_by_unique_attribute", rules=["EDL-01"])
@pytest.mark.parametrize(
    ("method", "url", "param"),
    [
        ("DELETE", f"{ENTITY}/guid/{{}}", "guid"),
        ("DELETE", f"{ENTITY}/bulk?guid={{}}", "guid"),
        ("DELETE", f"{ENTITY}/uniqueAttribute/type/{{}}", "typeName"),
    ],
)
async def test__a_guid_or_type_name_over_4096_characters_is_refused(
    client: httpx.AsyncClient, method: str, url: str, param: str
) -> None:
    """``Servlets.validateQueryParamLength`` runs first."""
    assert await send(client, method, url.format("x" * 4097)) == (
        400,
        {"errorCode": "ATLAS-400-00-057", "errorMessage": f"Length of query param {param} exceeds the limit"},
    )


@pytest.mark.covers(
    f"{E}.delete_by_guid",
    f"{E}.delete_by_guids",
    f"{E}.writer",
    f"{E}.delete_type",
    "aurelius_atlas_server.routes.admin.purge_by_ids",
    rules=["EDL-02", "EDL-03", "EDL-04", "EDL-06", "EDL-08"],
)
async def test__entities_are_soft_deleted_then_purged(typed: httpx.AsyncClient) -> None:
    """Soft by default, ``deleteType`` ignored; a purge removes them; bad input fails."""
    guids = await create(typed, database("-1", "a@cl"), database("-2", "b@cl"))

    status, deleted = await send(typed, "DELETE", f"{ENTITY}/guid/{guids['-1']}", params={"deleteType": "hard"})
    _, read = await send(typed, "GET", f"{ENTITY}/guid/{guids['-1']}")
    _, bulk = await send(typed, "DELETE", f"{ENTITY}/bulk", params=[("guid", guids["-2"]), ("guid", "nope")])
    _, purged = await send(typed, "PUT", PURGE, json=[guids["-1"], guids["-2"]])
    gone, _ = await send(typed, "GET", f"{ENTITY}/guid/{guids['-1']}")

    assert (status, [h["guid"] for h in deleted["mutatedEntities"]["DELETE"]]) == (200, [guids["-1"]])
    assert read["entity"]["status"] == "DELETED"
    assert [h["guid"] for h in bulk["mutatedEntities"]["DELETE"]] == [guids["-2"]]
    assert [h["guid"] for h in purged["mutatedEntities"]["PURGE"]] == [guids["-1"], guids["-2"]]
    assert gone == 404
    not_specified = {"errorCode": "ATLAS-400-00-01A", "errorMessage": "invalid parameters: Guid(s) not specified"}
    assert await send(typed, "DELETE", f"{ENTITY}/bulk") == (400, not_specified)
    assert await send(typed, "PUT", PURGE, json=[]) == (400, not_specified)
    assert await send(typed, "PUT", PURGE, content=b"") == (400, not_specified)
    status, bad = await send(typed, "PUT", PURGE, json={"guid": "x"})
    assert (status, bad["errorCode"]) == (400, "ATLAS-400-00-029")
    assert await send(typed, "PUT", PURGE, json=["x" * 4097]) == (
        400,
        {"errorCode": "ATLAS-400-00-057", "errorMessage": "Length of query param guid exceeds the limit"},
    )


@pytest.mark.covers(f"{E}.delete_by_unique_attribute", f"{E}.delete_type", rules=["EDL-02", "EDL-04", "EDL-06"])
async def test__a_request_chooses_a_hard_delete_when_the_override_is_on(overridable: httpx.AsyncClient) -> None:
    """``deleteType=HARD`` removes the entity at once; no ``attr:`` values fail with Java's message."""
    guids = await create(overridable, database("-1", "a@cl"))
    path = f"{ENTITY}/uniqueAttribute/type/s_database"

    status, deleted = await send(
        overridable, "DELETE", path, params={"attr:qualifiedName": "a@cl", "deleteType": "HARD"}
    )
    gone, _ = await send(overridable, "GET", f"{ENTITY}/guid/{guids['-1']}")

    assert (status, deleted["mutatedEntities"]["DELETE"][0]["guid"], gone) == (200, guids["-1"], 404)
    assert await send(overridable, "DELETE", path) == (
        404,
        {"errorCode": "ATLAS-404-00-009", "errorMessage": "Instance {} with unique attribute {1} does not exist"},
    )
    assert (await send(overridable, "DELETE", f"{ENTITY}/uniqueAttribute/type/nope"))[0] == 400
