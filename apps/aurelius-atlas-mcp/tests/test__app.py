"""MCP-01, MCP-02 and MCP-15: the Streamable HTTP endpoint, the bearer gate, the open liveness.

The gate is tested at the HTTP boundary it stands on (DD-888): a raw POST to ``/mcp``
without a verified token is refused there, before any MCP message is read and before the
catalogue sees a request (MCP-02). The endpoint itself is proven by a real client session
over the in-process transport (the harness the conftest builds).
"""

from typing import Any

import httpx2 as httpx
import pytest


@pytest.mark.covers("aurelius_atlas_mcp.app.create_app", rules=["MCP-01", "MCP-04"])
async def test__mcp_answers_the_protocol(mcp_session: Any, token: Any) -> None:  # noqa: ANN401 - the session factory, the minter
    """``POST /mcp`` speaks MCP: a client initialises and the twelve tools are advertised (MCP-01, MCP-04)."""
    async with mcp_session(token()) as session:
        tools = await session.list_tools()
    names = {tool.name for tool in tools.tools}
    assert names == {
        "search_entities",
        "get_entity",
        "get_lineage",
        "search_glossary",
        "get_type",
        "list_types",
        "save_entity",
        "add_classifications",
        "remove_classification",
        "delete_entity",
        "validate_entity",
        "server_status",
    }


@pytest.mark.covers("aurelius_atlas_mcp.app.create_app", rules=["MCP-01"])
async def test__nothing_is_mounted_at_the_root(app: Any, token: Any) -> None:  # noqa: ANN401 - the gate app, the minter
    """The app is headless (DD-887): no OpenAPI, no UI — only ``/mcp`` and ``/liveness`` exist."""
    headers = {"authorization": f"Bearer {token()}"}  # behind the gate, so a 404 is a route answer
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mcp.test", headers=headers) as client:
        root = await client.get("/")
        docs = await client.get("/docs")
    assert root.status_code == 404
    assert docs.status_code == 404


@pytest.mark.covers("aurelius_atlas_mcp.auth.BearerGate.__call__", rules=["MCP-02"])
async def test__a_missing_bearer_is_refused_before_the_catalogue_sees_anything(
    app: Any,  # noqa: ANN401 - the gate app
    upstream: Any,  # noqa: ANN401 - the fake upstream
) -> None:
    """No token: 401 with the bearer challenge, and the upstream never called (MCP-02, MCP-03)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mcp.test") as client:
        answer = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert answer.status_code == 401
    assert answer.headers["www-authenticate"] == "Bearer"
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_mcp.auth.BearerGate.__call__", rules=["MCP-02"])
async def test__a_bad_bearer_is_refused(
    app: Any,  # noqa: ANN401 - the gate app
    upstream: Any,  # noqa: ANN401 - the fake upstream
) -> None:
    """A token that does not verify for the app's audience is refused the same way."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mcp.test") as client:
        answer = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"authorization": "Bearer not-a-token"},
        )
    assert answer.status_code == 401
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_mcp.auth.BearerGate.__call__", rules=["MCP-02"])
async def test__a_wrong_audience_is_refused(app: Any, token: Any) -> None:  # noqa: ANN401 - the gate app, the minter
    """A token signed by the right issuer for the wrong client does not open the gate (AUX-04)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mcp.test") as client:
        answer = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"authorization": f"Bearer {token(azp='someone-else', audience='someone-else')}"},
        )
    assert answer.status_code == 401


@pytest.mark.covers("aurelius_atlas_mcp.app.create_app", rules=["MCP-15"])
async def test__liveness_answers_204_without_a_token(app: Any) -> None:  # noqa: ANN401 - the gate app
    """The container healthcheck path answers 204 anonymously (MCP-15)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mcp.test") as client:
        answer = await client.get("/liveness")
    assert answer.status_code == 204


@pytest.mark.covers("aurelius_atlas_mcp.app.create_app", rules=["MCP-01"])
def test__create_app_builds_the_gate_over_the_mcp_app(app: Any) -> None:  # noqa: ANN401 - the gate app
    """The composition root: the gate wraps FastMCP's app, whose routes are /mcp and /liveness."""
    paths = {route.path for route in app.inner.routes}
    assert {"/mcp", "/liveness"} <= paths
