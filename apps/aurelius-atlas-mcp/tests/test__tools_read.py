"""MCP-05..MCP-09, MCP-13 and MCP-14: the read tools against the fake catalogue.

Each test answers the one Atlas REST call the tool relays, calls the tool through a real
MCP session, and asserts on both directions: the compact answer the tool returns (DD-889)
and the request it forwarded — with the caller's own bearer (MCP-03).
"""

from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_mcp.relay import NO_TOKEN, bearer_token
from fake_upstream import FakeUpstream, call_tool
from fastmcp.exceptions import ToolError

SEARCH = "/api/atlas/v2/search/basic"
ENTITY = "/api/atlas/v2/entity/guid/"
LINEAGE = "/api/atlas/v2/lineage/"
GLOSSARY = "/api/atlas/v2/glossary/gloss-1/terms/headers"
TYPEDEFS = "/api/atlas/v2/types/typedef"
ADMIN_VERSION = "/api/atlas/admin/version"
ADMIN_STATUS = "/api/atlas/admin/status"
ADMIN_SESSION = "/api/atlas/admin/session"


@pytest.mark.covers("aurelius_atlas_mcp.relay.bearer_token", rules=["MCP-02", "MCP-03"])
def test__bearer_token_fails_closed_outside_a_request() -> None:
    """A tool that somehow runs with no verified caller fails closed — no anonymous upstream call."""
    with pytest.raises(ToolError, match=NO_TOKEN[:20]):
        bearer_token()


HEADER = {
    "typeName": "m4i_dataset",
    "guid": "guid-1",
    "displayText": "orders",
    "status": "ACTIVE",
    "classificationNames": ["PII"],
    "attributes": {"qualifiedName": "orders.snowflake", "owner": "someone"},
    "parameters": {"noise": "the server's bulk-header noise"},
}


@pytest.fixture
def session_factory(mcp_session: Any, token: Any) -> Any:  # noqa: ANN401 - the factory, bound to a read caller
    """A session as a plain read caller (no write role): what most of these tools are."""

    def _factory() -> Any:  # noqa: ANN401 - the async context manager
        return mcp_session(token())

    return _factory


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-05", "MCP-03"])
async def test__search_entities_answers_compact_headers_with_the_callers_token(
    session_factory: Any,  # noqa: ANN401 - the session factory
    upstream: FakeUpstream,
) -> None:
    """The search answers headers (guid, display, type, classifications, status, qualified name).

    Never whole entities (MCP-05), and the call carries the caller's own token (MCP-03).
    """
    upstream.answers[SEARCH] = (200, {"entities": [HEADER], "approximateCount": 1})
    async with session_factory() as session:
        answer = await call_tool(session, "search_entities", {"query": "orders", "limit": 5})
    assert answer == {
        "approximate_count": 1,
        "entities": [
            {
                "guid": "guid-1",
                "type_name": "m4i_dataset",
                "display_text": "orders",
                "status": "ACTIVE",
                "classifications": ["PII"],
                "qualified_name": "orders.snowflake",
            }
        ],
    }
    request = upstream.for_path(SEARCH)
    assert request is not None
    assert upstream.bearer_of(request)  # the caller's bearer travelled (MCP-03)
    body = await request.aread()
    assert b'"query":"orders"' in body.replace(b" ", b"")


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-06"])
async def test__get_entity_answers_the_whole_entity_by_guid(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-06: the entity travels in full — its attributes and its referred entities."""
    entity = {
        "entity": {
            "typeName": "m4i_dataset",
            "guid": "guid-1",
            "displayText": "orders",
            "attributes": {"qualifiedName": "orders.snowflake", "description": "one line"},
        }
    }
    upstream.answers[ENTITY + "guid-1"] = (200, entity)
    async with session_factory() as session:
        answer = await call_tool(session, "get_entity", {"guid": "guid-1"})
    assert answer["entity"]["attributes"]["description"] == "one line"


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-06"])
async def test__get_entity_reads_by_unique_attributes(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-06: the unique-attribute locator answers the same record."""
    upstream.answers["/api/atlas/v2/entity/uniqueAttribute/type/m4i_dataset"] = (
        200,
        {"entity": {"typeName": "m4i_dataset", "guid": "guid-1", "attributes": {"qualifiedName": "orders"}}},
    )
    async with session_factory() as session:
        answer = await call_tool(
            session, "get_entity", {"type_name": "m4i_dataset", "unique_attributes": {"qualifiedName": "orders"}}
        )
    assert answer["entity"]["guid"] == "guid-1"


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-06"])
async def test__get_entity_rejects_no_locator_and_both(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-06: neither locator, or both, is the MCP tool error — and no upstream call."""
    async with session_factory() as session:
        with pytest.raises(ToolError, match="guid"):
            await call_tool(session, "get_entity", {})
        with pytest.raises(ToolError, match="not both"):
            await call_tool(session, "get_entity", {"guid": "g", "type_name": "t", "unique_attributes": {"a": 1}})
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-07"])
async def test__get_lineage_answers_nodes_and_edges(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-07: the graph answers as compact nodes and directed edges, at the asked depth."""
    guid = "23b4e69e-9f6d-4f7d-9f3a-1d9f4f0a1b2c"
    other = "11111111-2222-3333-4444-555555555555"
    upstream.answers[LINEAGE + guid] = (
        200,
        {
            "guidEntityMap": {
                guid: {"guid": guid, "typeName": "m4i_dataset", "displayText": "orders"},
                other: {"guid": other, "typeName": "m4i_process", "displayText": "etl"},
            },
            "relations": [{"fromEntityId": guid, "toEntityId": other, "relationshipId": "r-1"}],
        },
    )
    async with session_factory() as session:
        answer = await call_tool(session, "get_lineage", {"guid": guid, "depth": 2, "direction": "OUTPUT"})
    assert answer["depth"] == 2
    assert answer["direction"] == "OUTPUT"
    assert {node["display_text"] for node in answer["nodes"]} == {"orders", "etl"}
    assert answer["relations"] == [{"from_entity_id": guid, "to_entity_id": other}]
    request = upstream.for_path(LINEAGE + guid)
    assert request is not None
    assert request.url.params["depth"] == "2"
    assert request.url.params["direction"] == "OUTPUT"


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-07"])
async def test__get_lineage_refuses_an_unknown_direction(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-07: a direction the server does not speak is the tool error, with no upstream call."""
    async with session_factory() as session:
        with pytest.raises(ToolError, match="direction"):
            await call_tool(session, "get_lineage", {"guid": "g", "direction": "SIDEWAYS"})
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-08"])
async def test__search_glossary_pages_and_filters_terms(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-08: the terms answer as headers; the query keeps the name or description matches."""
    upstream.answers[GLOSSARY] = (
        200,
        [
            {"termGuid": "t-1", "displayText": "Customer", "qualifiedName": "Customer", "description": "a person"},
            {"termGuid": "t-2", "displayText": "Order", "qualifiedName": "Order", "description": "a purchase"},
        ],
    )
    async with session_factory() as session:
        all_terms = await call_tool(session, "search_glossary", {"glossary_guid": "gloss-1"})
        one_term = await call_tool(session, "search_glossary", {"glossary_guid": "gloss-1", "query": "person"})
    assert [term["guid"] for term in all_terms["terms"]] == ["t-1", "t-2"]
    assert [term["guid"] for term in one_term["terms"]] == ["t-1"]


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-09"])
async def test__get_type_answers_the_typedef(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-09: one typedef travels as the server answers it."""
    upstream.answers[TYPEDEFS + "/name/m4i_dataset"] = (
        200,
        {
            "category": "ENTITY",
            "name": "m4i_dataset",
            "guid": "t-9",
            "serviceType": "ATLAS",
            "superTypes": ["DataSet"],
        },
    )
    async with session_factory() as session:
        answer = await call_tool(session, "get_type", {"name": "m4i_dataset"})
    assert answer["name"] == "m4i_dataset"
    assert answer["category"] == "ENTITY"


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-09"])
async def test__list_types_filters_by_kind(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-09: the kind word becomes the server's filter, and the headers answer compactly."""
    upstream.answers[TYPEDEFS + "s/headers"] = (
        200,
        [{"guid": "t-9", "name": "m4i_dataset", "category": "ENTITY"}],
    )
    async with session_factory() as session:
        answer = await call_tool(session, "list_types", {"kind": "entity"})
    assert answer["types"] == [{"name": "m4i_dataset", "guid": "t-9", "category": "ENTITY"}]
    request = upstream.for_path(TYPEDEFS + "s/headers")
    assert request is not None
    assert request.url.params["type"] == "ENTITY"


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-09"])
async def test__list_types_refuses_an_unknown_kind(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-09: a kind outside the six is the tool error, with no upstream call."""
    async with session_factory() as session:
        with pytest.raises(ToolError, match="kind"):
            await call_tool(session, "list_types", {"kind": "vocabulary"})
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-13"])
async def test__server_status_gathers_version_status_and_session(session_factory: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-13: the three admin answers travel as one tool answer."""
    upstream.answers[ADMIN_VERSION] = (
        200,
        {"Version": "4.0.0", "Revision": "abc", "Name": "Aurelius Atlas", "Description": "the catalogue"},
    )
    upstream.answers[ADMIN_STATUS] = (200, {"Status": "ACTIVE"})
    upstream.answers[ADMIN_SESSION] = (
        200,
        {"userName": "agent-1", "atlas.entity.create.allowed": True, "atlas.entity.update.allowed": False},
    )
    async with session_factory() as session:
        answer = await call_tool(session, "server_status")
    assert answer == {
        "version": "4.0.0",
        "name": "Aurelius Atlas",
        "status": "ACTIVE",
        "user_name": "agent-1",
        "entity_create_allowed": True,
        "entity_update_allowed": False,
    }
    assert upstream.for_path(ADMIN_VERSION) is not None


@pytest.mark.covers("aurelius_atlas_mcp.relay.upstream_tool_error", rules=["MCP-14"])
async def test__an_atlas_refusal_surfaces_as_a_tool_error_naming_it(
    session_factory: Any,  # noqa: ANN401 - the session factory
    upstream: FakeUpstream,
) -> None:
    """MCP-14: the upstream status and its {errorCode, errorMessage} name the tool error."""
    upstream.answers[ENTITY + "missing"] = (404, {"errorCode": "ATLAS404", "errorMessage": "no entity"})
    async with session_factory() as session:
        with pytest.raises(ToolError, match=r"the catalogue answered 404.*ATLAS404"):
            await call_tool(session, "get_entity", {"guid": "missing"})


@pytest.mark.covers("aurelius_atlas_mcp.relay.upstream_tool_error", rules=["MCP-14"])
async def test__an_unreachable_catalogue_names_the_transport_failure(
    session_factory: Any,  # noqa: ANN401 - the session factory
    upstream: FakeUpstream,
) -> None:
    """MCP-14: an unreachable upstream is a tool error naming the transport failure, never an empty answer."""
    upstream.fail = httpx.ConnectError("connection refused")
    async with session_factory() as session:
        with pytest.raises(ToolError, match="upstream unavailable"):
            await call_tool(session, "server_status")
