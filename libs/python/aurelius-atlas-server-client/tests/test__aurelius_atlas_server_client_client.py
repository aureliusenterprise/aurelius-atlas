"""The AtlasClient against the recording transport (CL-01..CL-05, CL-11; DD-115, DD-116).

Every call answers from the externally provided httpx client the test hands in —
its transport is a recorder, no socket opens (CL-02); each test names the methods
it exercises (ADR 049) and the rules it enforces.
"""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from aurelius_atlas_model.typedef import (
    AtlasBaseTypeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasRelationshipDef,
    AtlasStructDef,
    AtlasTypeDefHeader,
    AtlasTypesDef,
    TypeCategory,
)
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError
from server_recorder import Recorder

VERSION: dict[str, Any] = {"Version": "4.1.0", "Revision": "abc1234", "Name": "Aurelius Atlas", "Description": "d"}
TYPES_DEF: dict[str, Any] = {"enumDefs": [{"name": "e1", "category": "ENUM"}]}
LINEAGE: dict[str, Any] = {
    "guidEntityMap": {"e-1": {"guid": "e-1", "typeName": "hive_table", "displayText": "T"}},
    "relations": [],
}
ERROR_BODY: dict[str, Any] = {"errorCode": "ATLAS-400-00-00A", "errorMessage": "no such typedef"}


def _client(recorder: Recorder, token: str | Callable[[], str] = "tok") -> AtlasClient:  # noqa: S107 - a fixed fake credential, not a secret
    """The client under test: an externally built httpx client on the recorder (CL-02, CL-01)."""
    return AtlasClient(httpx.AsyncClient(base_url="https://atlas.test", transport=recorder.transport()), token)


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.AtlasClient.get_lineage",
    "aurelius_atlas_server_client.client.AtlasClient.with_token",
    rules=["CL-11", "CL-03", "CL-02"],
)
async def test__with_token_shares_the_pool_and_speaks_with_the_new_token(
    recorder: Recorder, tracked_client_http: httpx.AsyncClient
) -> None:
    """The wrapper sends the caller's token on the owner's connection pool (CL-03, LM-04)."""
    owner = AtlasClient(tracked_client_http, "service-token")
    recorder.answer(200, LINEAGE)

    info = await owner.with_token("browser-token").get_lineage("e-1")

    assert info.guid_entity_map["e-1"].type_name == "hive_table"
    assert recorder.sent().headers["authorization"] == "Bearer browser-token"
    await tracked_client_http.aclose()  # the pool's builder closes it — the client never does (CL-02)


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.AtlasClient.get_lineage",
    rules=["CL-11", "CL-03"],
)
async def test__an_empty_token_travels_unauthenticated(recorder: Recorder) -> None:
    """An empty token source is the unauthenticated call: no authorization header, no malformed bearer (CL-03)."""
    recorder.answer(200, LINEAGE)
    client = _client(recorder, "")

    await client.get_lineage("e-1")

    assert "authorization" not in recorder.sent().headers


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.AtlasClient.get_lineage",
    rules=["CL-11", "CL-12", "CL-03"],
)
async def test__get_lineage_reads_the_feed_with_depth_and_direction(recorder: Recorder) -> None:
    """``GET /v2/lineage/{guid}?depth&direction`` (the feed 5.1 serves; 8.2 is its first caller)."""
    recorder.answer(200, LINEAGE)

    await _client(recorder).get_lineage("e-1", depth=5, direction="INPUT")

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == "/v2/lineage/e-1"
    assert dict(sent.url.params) == {"depth": "5", "direction": "INPUT"}


@pytest.mark.covers("aurelius_atlas_server_client.client.AtlasClient.get_lineage", rules=["CL-01"])
async def test__the_base_url_passes_through_as_given(recorder: Recorder) -> None:
    """A base URL with a trailing slash — the ``str()`` of a pydantic ``HttpUrl`` — needs no trimming.

    The paths are relative, so httpx appends them and the request lands on the exact route (CL-01).
    """
    recorder.answer(200, LINEAGE)
    http = httpx.AsyncClient(base_url="https://atlas.test/", transport=recorder.transport())

    await AtlasClient(http, "tok").get_lineage("e-1")

    assert recorder.sent().url.path == "/v2/lineage/e-1"


@pytest.mark.covers("aurelius_atlas_server_client.client.AtlasClient.get_lineage", rules=["CL-04"])
async def test__get_lineage_raises_with_the_status_of_the_answer(recorder: Recorder) -> None:
    """A 404 is the feed's answer for a guid it has no lineage for (LM-05): raised, not swallowed — the app maps it."""
    recorder.answer(404, ERROR_BODY)

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).get_lineage("missing")

    assert raised.value.status_code == 404
    assert raised.value.info is not None
    assert raised.value.info.error_code == "ATLAS-400-00-00A"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.AdminApi.version",
    "aurelius_atlas_server_client.client.AdminApi.status",
    "aurelius_atlas_server_client.client.AdminApi.session",
    "aurelius_atlas_server_client.client.AdminApi.liveness",
    "aurelius_atlas_server_client.client.AdminApi.readiness",
    rules=["CL-11", "CL-10", "CL-03"],
)
async def test__the_admin_resource_answers_the_server_routes(recorder: Recorder) -> None:
    """The five admin calls, their paths mirroring ``routes/admin.py``, bearer on each (ADM-01..ADM-05)."""
    recorder.answer(200, VERSION)
    recorder.answer(200, {"Status": "ACTIVE"})
    recorder.answer(200, {"userName": "analyst", "groups": [], "timezones": ["UTC"], "_csrfToken": "t"})
    recorder.answer(200, text="OK")
    recorder.answer(200, text="READY")
    client = _client(recorder)

    version = await client.admin.version()
    status = await client.admin.status()
    session = await client.admin.session()
    liveness = await client.admin.liveness()
    readiness = await client.admin.readiness()

    assert (version.version, status.status, session.user_name) == ("4.1.0", "ACTIVE", "analyst")
    assert (liveness, readiness) == ("OK", "READY")
    assert [request.url.path for request in recorder.requests] == [
        "/api/atlas/admin/version",
        "/api/atlas/admin/status",
        "/api/atlas/admin/session",
        "/api/atlas/admin/liveness",
        "/api/atlas/admin/readiness",
    ]
    assert all(request.headers["authorization"] == "Bearer tok" for request in recorder.requests)


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.readiness", rules=["CL-11", "CL-04"])
async def test__readiness_raises_when_the_server_is_not_ready(recorder: Recorder) -> None:
    """A 503 readiness is an ``AtlasClientError`` — the container healthcheck's failure path (ADM-04)."""
    recorder.answer(503, text="es starting")

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).admin.readiness()

    assert raised.value.status_code == 503
    assert raised.value.info is None  # a plain-text answer is not the Atlas error body


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.TypesApi.typedef_by_name",
    "aurelius_atlas_server_client.client.TypesApi.typedef_by_guid",
    rules=["CL-11", "CL-03"],
)
async def test__a_typedef_of_any_kind_parses_by_its_category(recorder: Recorder) -> None:
    """``GET /typedef/name|guid``: the ``category`` picks the model (TYR-01, TYR-02)."""
    recorder.answer(200, {"category": "ENUM", "name": "e1"})
    recorder.answer(200, {"category": "STRUCT", "name": "s1"})
    client = _client(recorder)

    by_name = await client.types.typedef_by_name("e1")
    by_guid = await client.types.typedef_by_guid("g-1")

    assert isinstance(by_name, AtlasEnumDef)
    assert isinstance(by_guid, AtlasStructDef)
    assert [request.url.path for request in recorder.requests] == [
        "/api/atlas/v2/types/typedef/name/e1",
        "/api/atlas/v2/types/typedef/guid/g-1",
    ]


@pytest.mark.covers("aurelius_atlas_server_client.client.TypesApi.typedef_by_name", rules=["CL-11"])
async def test__a_typedef_of_an_unknown_category_stays_a_base_def(recorder: Recorder) -> None:
    """A category the model family has no class for is a ``AtlasBaseTypeDef``, not a crash."""
    recorder.answer(200, {"category": "PRIMITIVE", "name": "string"})

    typedef = await _client(recorder).types.typedef_by_name("string")

    assert type(typedef) is AtlasBaseTypeDef


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.TypesApi.typedefs",
    "aurelius_atlas_server_client.client.TypesApi.typedef_headers",
    rules=["CL-11"],
)
async def test__the_typedef_search_carries_the_filter(recorder: Recorder) -> None:
    """``GET /typedefs`` and ``GET /typedefs/headers`` with the search params (TYR-05..TYR-08)."""
    recorder.answer(200, TYPES_DEF)
    recorder.answer(200, [{"guid": "g", "name": "e1", "serviceType": "core", "category": "ENUM"}])
    client = _client(recorder)

    types_def = await client.types.typedefs({"type": "e1"})
    headers = await client.types.typedef_headers({"category": "e1"})

    enum_defs = types_def.enum_defs or []
    assert enum_defs[0].name == "e1"
    assert headers == [AtlasTypeDefHeader(guid="g", name="e1", service_type="core", category=TypeCategory.ENUM)]
    assert dict(recorder.sent(0).url.params) == {"type": "e1"}
    assert recorder.sent(1).url.path == "/api/atlas/v2/types/typedefs/headers"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.TypesApi.create_typedefs",
    "aurelius_atlas_server_client.client.TypesApi.update_typedefs",
    "aurelius_atlas_server_client.client.TypesApi.delete_typedefs",
    "aurelius_atlas_server_client.client.TypesApi.delete_typedef_by_name",
    rules=["CL-11"],
)
async def test__the_typedef_writes_post_put_and_delete(recorder: Recorder) -> None:
    """The writes mirror ``routes/types.py`` (TYR-09, TYR-10); the deletes answer 204."""
    recorder.answer(200, TYPES_DEF)
    recorder.answer(200, TYPES_DEF)
    recorder.answer(204)
    recorder.answer(204)
    client = _client(recorder)
    body = AtlasTypesDef.model_validate(TYPES_DEF)

    created = await client.types.create_typedefs(body)
    updated = await client.types.update_typedefs(body)
    await client.types.delete_typedefs(body)
    await client.types.delete_typedef_by_name("e1")

    assert created.enum_defs is not None
    assert created.enum_defs[0].name == "e1"
    assert updated.enum_defs is not None
    assert updated.enum_defs[0].name == "e1"
    assert [(request.method, request.url.path) for request in recorder.requests] == [
        ("POST", "/api/atlas/v2/types/typedefs"),
        ("PUT", "/api/atlas/v2/types/typedefs"),
        ("DELETE", "/api/atlas/v2/types/typedefs"),
        ("DELETE", "/api/atlas/v2/types/typedef/name/e1"),
    ]
    assert json.loads(recorder.sent(0).content) == body.to_json()


# The twelve kind lookups: (method, path segment, category) — the paths mirror routes/types.py (TYR-03).
KIND_LOOKUPS: list[tuple[str, str, str]] = [
    ("enumdef_by_name", "enumdef", "ENUM"),
    ("structdef_by_name", "structdef", "STRUCT"),
    ("classificationdef_by_name", "classificationdef", "CLASSIFICATION"),
    ("entitydef_by_name", "entitydef", "ENTITY"),
    ("relationshipdef_by_name", "relationshipdef", "RELATIONSHIP"),
    ("businessmetadatadef_by_name", "businessmetadatadef", "BUSINESS_METADATA"),
]
KIND_MODEL: dict[str, type[AtlasBaseTypeDef]] = {
    "ENUM": AtlasEnumDef,
    "STRUCT": AtlasStructDef,
    "CLASSIFICATION": AtlasClassificationDef,
    "ENTITY": AtlasEntityDef,
    "RELATIONSHIP": AtlasRelationshipDef,
    "BUSINESS_METADATA": AtlasBusinessMetadataDef,
}


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.TypesApi.enumdef_by_name",
    "aurelius_atlas_server_client.client.TypesApi.enumdef_by_guid",
    "aurelius_atlas_server_client.client.TypesApi.structdef_by_name",
    "aurelius_atlas_server_client.client.TypesApi.structdef_by_guid",
    "aurelius_atlas_server_client.client.TypesApi.classificationdef_by_name",
    "aurelius_atlas_server_client.client.TypesApi.classificationdef_by_guid",
    "aurelius_atlas_server_client.client.TypesApi.entitydef_by_name",
    "aurelius_atlas_server_client.client.TypesApi.entitydef_by_guid",
    "aurelius_atlas_server_client.client.TypesApi.relationshipdef_by_name",
    "aurelius_atlas_server_client.client.TypesApi.relationshipdef_by_guid",
    "aurelius_atlas_server_client.client.TypesApi.businessmetadatadef_by_name",
    "aurelius_atlas_server_client.client.TypesApi.businessmetadatadef_by_guid",
    rules=["CL-11"],
)
@pytest.mark.parametrize(("method", "path", "category"), KIND_LOOKUPS)
async def test__each_kind_lookup_reads_its_path_and_model(
    recorder: Recorder, method: str, path: str, category: str
) -> None:
    """``GET /{kind}def/name|guid``: one test per kind, both segments (TYR-03, CL-11)."""
    recorder.answer(200, {"name": "x", "category": category})
    recorder.answer(200, {"name": "x", "category": category})
    client = _client(recorder)
    call: Callable[..., Any] = getattr(client.types, method)

    by_name = await call("x")
    by_guid = await getattr(client.types, method.replace("_by_name", "_by_guid"))("g-1")

    assert type(by_name) is KIND_MODEL[category]
    assert type(by_guid) is KIND_MODEL[category]
    assert [request.url.path for request in recorder.requests] == [
        f"/api/atlas/v2/types/{path}/name/x",
        f"/api/atlas/v2/types/{path}/guid/g-1",
    ]


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.AtlasClient.get_lineage",
    "aurelius_atlas_server_client.client.AdminApi.status",
    rules=["CL-01", "CL-03"],
)
async def test__the_client_is_built_from_its_arguments_and_bears_its_token(recorder: Recorder) -> None:
    """The externally built httpx client and a callable token source called per request (CL-01, CL-03).

    Base URL, TLS and timeout live on the httpx client the app builds — no environment is read.
    """
    calls: list[str] = []

    def token_source() -> str:
        calls.append("called")
        return "fresh-token"

    http = httpx.AsyncClient(
        base_url="https://atlas.test",
        verify=False,  # noqa: S501 - a mock transport answers, no TLS to verify
        timeout=1.0,
        transport=recorder.transport(),
    )
    client = AtlasClient(http, token_source)
    recorder.answer(200, {"Status": "ACTIVE"})
    recorder.answer(200, LINEAGE)

    await client.admin.status()
    await client.get_lineage("e-1")

    assert recorder.sent(0).url.path == "/api/atlas/admin/status"
    assert calls == ["called", "called"]
    assert all(request.headers["authorization"] == "Bearer fresh-token" for request in recorder.requests)


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.session", rules=["CL-04"])
async def test__a_non_2xx_answer_raises_the_library_error(recorder: Recorder) -> None:
    """The status and the ``{errorCode, errorMessage}`` of the body, in the error (CL-04, SRV-04)."""
    recorder.answer(400, ERROR_BODY)

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).admin.session()

    assert raised.value.status_code == 400
    assert raised.value.info is not None
    assert raised.value.info.error_message == "no such typedef"
    assert "ATLAS-400-00-00A" in str(raised.value)


@pytest.mark.covers("aurelius_atlas_server_client.client.AdminApi.version", rules=["CL-05"])
async def test__an_unreachable_server_propagates_httpxs_own_error(recorder: Recorder) -> None:
    """The client maps nothing: a transport failure is ``httpx``'s, the app's job (CL-05, DV-22)."""
    recorder.handler = lambda _request: (_ for _ in ()).throw(httpx.ConnectError("refused"))

    with pytest.raises(httpx.ConnectError):
        await _client(recorder).admin.version()
