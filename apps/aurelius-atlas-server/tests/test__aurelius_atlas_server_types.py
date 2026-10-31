"""The HTTP side of the type endpoints of ``TypesREST`` (TYR-03 to TYR-12).

Read from ``TypesREST`` and ``Servlets.validateQueryParamLength`` of Apache Atlas 2.4.0, and its tests
``TypedefsJerseyResourceIT`` and ``TypeDefsRESTTest``.
"""

from typing import Any, cast

import httpx2 as httpx
import pytest
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore, types_def_of
from aurelius_atlas_model.typedef import AtlasEntityDef
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient
from aurelius_atlas_typesystem.registry import TypeRegistry
from elasticsearch import AsyncElasticsearch

TYPES = "/api/atlas/v2/types"
JSON = "application/json; charset=UTF-8"


async def create(client: httpx.AsyncClient, body: dict[str, Any]) -> dict[str, Any]:
    """Create the definitions of ``body``, which must succeed."""
    response = await client.post(f"{TYPES}/typedefs", json=body)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.covers(
    "aurelius_atlas_server.routes.types.kind_by_name",
    "aurelius_atlas_server.routes.types.kind_by_guid",
    rules=["TYR-03"],
)
@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("enumdef", {"enumDefs": [{"name": "t_kind", "elementDefs": [{"value": "A", "ordinal": 1}]}]}),
        ("structdef", {"structDefs": [{"name": "t_kind", "attributeDefs": [{"name": "a", "typeName": "string"}]}]}),
        ("classificationdef", {"classificationDefs": [{"name": "t_kind"}]}),
        ("entitydef", {"entityDefs": [{"name": "t_kind"}]}),
        ("businessmetadatadef", {"businessMetadataDefs": [{"name": "t_kind"}]}),
    ],
)
async def test__each_kind_has_its_own_lookups(client: httpx.AsyncClient, path: str, body: dict[str, Any]) -> None:
    """``get{Kind}DefByName`` and ``ByGuid`` find their kind; another kind's lookup does not."""
    created = await create(client, body)
    guid = next(typedefs[0]["guid"] for typedefs in created.values() if typedefs)
    other = "structdef" if path != "structdef" else "enumdef"

    by_name = await client.get(f"{TYPES}/{path}/name/t_kind")
    by_guid = await client.get(f"{TYPES}/{path}/guid/{guid}")
    wrong_name = await client.get(f"{TYPES}/{other}/name/t_kind")
    wrong_guid = await client.get(f"{TYPES}/{other}/guid/{guid}")

    assert (by_name.status_code, by_name.json()["guid"]) == (200, guid)
    assert (by_guid.status_code, by_guid.json()["name"]) == (200, "t_kind")
    assert (wrong_name.status_code, wrong_name.json()["errorCode"]) == (404, "ATLAS-404-00-001")
    assert (wrong_guid.status_code, wrong_guid.json()["errorCode"]) == (404, "ATLAS-404-00-002")


@pytest.mark.covers("aurelius_atlas_server.routes.types.validate_param_length", rules=["TYR-04"])
@pytest.mark.parametrize(
    ("path", "param"),
    [
        ("typedef/name", "name"),
        ("typedef/guid", "guid"),
        ("entitydef/name", "name"),
        ("relationshipdef/guid", "guid"),
    ],
)
async def test__a_lookup_value_over_4096_characters_is_refused(
    client: httpx.AsyncClient, path: str, param: str
) -> None:
    """``Servlets.validateQueryParamLength`` runs before the lookup; 4096 characters is still a lookup."""
    too_long = await client.get(f"{TYPES}/{path}/{'x' * 4097}")
    longest = await client.get(f"{TYPES}/{path}/{'x' * 4096}")

    assert too_long.status_code == 400
    assert too_long.json() == {
        "errorCode": "ATLAS-400-00-057",
        "errorMessage": f"Length of query param {param} exceeds the limit",
    }
    assert longest.status_code == 404


@pytest.mark.covers(
    "aurelius_atlas_server.routes.types.get_all_typedefs",
    "aurelius_atlas_server.routes.types.get_typedef_headers",
    rules=["TYR-05", "TYR-08"],
)
async def test__the_list_and_its_headers_use_the_query_as_filter(client: httpx.AsyncClient) -> None:
    """``getAllTypeDefs`` and ``getTypeDefHeaders`` read the filter from the query parameters."""
    await create(client, {"entityDefs": [{"name": "t_b", "serviceType": "t_svc"}, {"name": "t_a"}]})

    listed = await client.get(f"{TYPES}/typedefs", params={"type": "entity", "notname": "t_b"})
    headers = await client.get(f"{TYPES}/typedefs/headers", params={"servicetype": "t_svc"})

    assert [typedef["name"] for typedef in listed.json()["entityDefs"]] == ["t_a"]
    assert listed.json()["enumDefs"] == []
    assert [(h["name"], h["category"], h["serviceType"]) for h in headers.json()] == [("t_b", "ENTITY", "t_svc")]
    assert headers.headers["content-type"] == JSON


@pytest.mark.covers("aurelius_atlas_server.routes.types.update_typedefs", rules=["TYR-09"])
async def test__an_update_answers_the_definitions_as_stored(client: httpx.AsyncClient) -> None:
    """``updateAtlasTypeDefs``: the version goes up and the change is what later reads see (TDS-07)."""
    await create(client, {"entityDefs": [{"name": "t_up"}]})

    updated = await client.put(f"{TYPES}/typedefs", json={"entityDefs": [{"name": "t_up", "description": "new"}]})
    read = await client.get(f"{TYPES}/typedef/name/t_up")

    assert updated.status_code == 200
    assert (updated.json()["entityDefs"][0]["version"], updated.json()["entityDefs"][0]["description"]) == (2, "new")
    assert read.json()["description"] == "new"


@pytest.mark.covers(
    "aurelius_atlas_server.routes.types.create_typedefs",
    "aurelius_atlas_server.routes.types.update_typedefs",
    rules=["TYR-09"],
)
async def test__a_failing_write_answers_atlas_s_error(client: httpx.AsyncClient) -> None:
    """The store's checks surface as Atlas errors: a duplicate create, an update of an unknown type."""
    await create(client, {"entityDefs": [{"name": "t_dup"}]})

    duplicate = await client.post(f"{TYPES}/typedefs", json={"entityDefs": [{"name": "t_dup"}]})
    unknown = await client.put(f"{TYPES}/typedefs", json={"entityDefs": [{"name": "t_unknown"}]})

    assert (duplicate.status_code, duplicate.json()["errorCode"]) == (409, "ATLAS-409-00-001")
    assert unknown.status_code == 404


@pytest.mark.covers(
    "aurelius_atlas_server.routes.types.delete_typedefs",
    "aurelius_atlas_server.routes.types.delete_typedef_by_name",
    rules=["TYR-10"],
)
async def test__deletes_answer_204_without_a_body(client: httpx.AsyncClient) -> None:
    """``deleteAtlasTypeDefs`` and ``deleteAtlasTypeByName`` are ``void``: 204 and nothing else."""
    await create(client, {"entityDefs": [{"name": "t_one"}, {"name": "t_two"}]})

    by_body = await client.request("DELETE", f"{TYPES}/typedefs", json={"entityDefs": [{"name": "t_one"}]})
    by_name = await client.delete(f"{TYPES}/typedef/name/t_two")
    again = await client.delete(f"{TYPES}/typedef/name/t_two")
    blank = await client.delete(f"{TYPES}/typedef/name/%20")
    built_in = await client.delete(f"{TYPES}/typedef/name/string")

    assert (by_body.status_code, by_body.content) == (204, b"")
    assert (by_name.status_code, by_name.content) == (204, b"")
    assert (again.status_code, again.json()["errorCode"]) == (404, "ATLAS-404-00-001")
    assert (blank.status_code, blank.json()["errorCode"]) == (400, "ATLAS-400-00-014")
    assert (built_in.status_code, built_in.json()["errorCode"]) == (400, "ATLAS-400-00-024")


@pytest.mark.covers("aurelius_atlas_server.routes.types.types_def_body", rules=["TYR-11"])
@pytest.mark.parametrize(
    ("method", "content"),
    [
        ("POST", b"not json"),
        ("PUT", b'{"entityDefs": {"name": "t"}}'),
        ("DELETE", b"[]"),
        ("POST", b""),
    ],
    ids=["not-json", "wrong-shape", "not-an-object", "empty"],
)
async def test__a_body_that_is_not_a_types_def_is_a_bad_request(
    client: httpx.AsyncClient, method: str, content: bytes
) -> None:
    """A body Jersey could not read is ``BAD_REQUEST`` with Atlas's error body (DV-10)."""
    response = await client.request(method, f"{TYPES}/typedefs", content=content)

    assert response.status_code == 400
    assert response.json()["errorCode"] == "ATLAS-400-00-029"
    assert response.json()["errorMessage"].startswith("Invalid AtlasTypesDef: ")


@pytest.mark.covers("aurelius_atlas_server.routes.types.types_def_body", rules=["TYR-11"])
async def test__unknown_fields_of_a_body_are_ignored(client: httpx.AsyncClient) -> None:
    """Atlas's models ignore properties they do not know (``FAIL_ON_UNKNOWN_PROPERTIES`` off)."""
    created = await create(client, {"entityDefs": [{"name": "t_extra", "colour": "red"}], "unknownDefs": []})

    assert [typedef["name"] for typedef in created["entityDefs"]] == ["t_extra"]
    assert "colour" not in created["entityDefs"][0]


@pytest.mark.covers("aurelius_atlas_server.routes.types.typedef_store", rules=["TYR-12"])
async def test__reads_see_what_another_server_stored(
    settings: ServerSettings, fake_es: FakeClient, auth_headers: dict[str, str]
) -> None:
    """Each request refreshes the registry when due (TDS-13); errors and answers are Atlas JSON."""
    app = create_app(settings.model_copy(update={"typedef_refresh_seconds": 0.0}))
    other = TypedefStore(TypeRegistry(), ElasticsearchTypedefDocument(cast("AsyncElasticsearch", fake_es)))

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://aurelius-atlas", headers=auth_headers
        ) as client:
            missing = await client.get(f"{TYPES}/typedef/name/t_elsewhere")
            await other.load()
            await other.create_types_def(types_def_of([AtlasEntityDef(name="t_elsewhere")]))
            found = await client.get(f"{TYPES}/typedef/name/t_elsewhere")

    assert (missing.status_code, missing.headers["content-type"]) == (404, JSON)
    assert (found.status_code, found.headers["content-type"]) == (200, JSON)
    assert found.json()["name"] == "t_elsewhere"
