"""MCP-10..MCP-12 and MCP-11's refusal: the write tools and the verdicts relay.

The gate here is the tool-level one (MCP-11): a token without the write role is refused
before any upstream request leaves the app — the test asserts the fake catalogue saw
nothing. The role lookup is pinned in both claim shapes Keycloak answers (DD-891), and
under the catalogue client rather than the app's audience, the shape a real realm
token carries (MCP-28, DD-898 — the e2e suite proves the same claim live).
"""

from typing import Any

import pytest
from aurelius_atlas_mcp.auth import may_write, token_roles
from fake_upstream import FakeUpstream, call_tool
from fastmcp.exceptions import ToolError

ENTITY = "/api/atlas/v2/entity"
CLASSIFICATIONS = "/classifications"
VALIDATE = ""

ENTITY_BODY = {
    "entity": {
        "typeName": "m4i_dataset",
        "displayText": "orders",
        "attributes": {"qualifiedName": "orders.snowflake"},
    }
}

MUTATION = {"mutatedEntities": {"CREATE": [{"typeName": "m4i_dataset", "guid": "guid-9"}]}}


@pytest.fixture
def writer(mcp_session: Any, token: Any) -> Any:  # noqa: ANN401 - the bound session factory
    """A session as a caller that holds the write role (MCP-11 satisfied)."""

    def _factory() -> Any:  # noqa: ANN401 - the async context manager
        return mcp_session(token(roles=["atlas-write"]))

    return _factory


@pytest.fixture
def reader(mcp_session: Any, token: Any) -> Any:  # noqa: ANN401 - the bound session factory
    """A session as a caller without the write role."""

    def _factory() -> Any:  # noqa: ANN401 - the async context manager
        return mcp_session(token(roles=["viewer"]))

    return _factory


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-10"])
async def test__save_entity_forwards_the_body(writer: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-10: the entity body travels to the catalogue, and its mutation answer comes back."""
    upstream.answers[ENTITY] = (200, MUTATION)
    async with writer() as session:
        answer = await call_tool(session, "save_entity", {"entity": ENTITY_BODY})
    assert answer["mutatedEntities"]["CREATE"][0]["guid"] == "guid-9"
    request = upstream.for_path(ENTITY)
    assert request is not None
    assert request.method == "POST"
    body = await request.aread()
    assert b"orders.snowflake" in body
    assert upstream.bearer_of(request)


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-10"])
async def test__add_classifications_posts_the_bodies(writer: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-10: the classification bodies travel; the 204 answers as the tool's confirmation."""
    upstream.answers[ENTITY + "/guid/guid-1" + CLASSIFICATIONS] = (204, None)
    async with writer() as session:
        answer = await call_tool(
            session, "add_classifications", {"guid": "guid-1", "classifications": [{"typeName": "PII"}]}
        )
    assert answer == {"guid": "guid-1", "added": ["PII"]}
    request = upstream.for_path(ENTITY + "/guid/guid-1" + CLASSIFICATIONS)
    assert request is not None
    body = await request.aread()
    assert b"PII" in body


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-10"])
async def test__remove_classification_deletes_it(writer: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-10: the delete asks the catalogue by classification name."""
    upstream.answers[ENTITY + "/guid/guid-1/classification/PII"] = (204, None)
    async with writer() as session:
        answer = await call_tool(session, "remove_classification", {"guid": "guid-1", "name": "PII"})
    assert answer == {"guid": "guid-1", "removed": "PII"}
    request = upstream.for_path(ENTITY + "/guid/guid-1/classification/PII")
    assert request is not None
    assert request.method == "DELETE"


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-10"])
async def test__delete_entity_sends_the_delete_type(writer: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-10: hard=True names the hard delete; without it the server's own setting stands (EDL-04)."""
    deleted = {"mutatedEntities": {"DELETE": [{"typeName": "m4i_dataset", "guid": "guid-1"}]}}
    upstream.answers[ENTITY + "/guid/guid-1"] = (200, deleted)
    async with writer() as session:
        soft = await call_tool(session, "delete_entity", {"guid": "guid-1"})
        upstream.requests.clear()
        hard = await call_tool(session, "delete_entity", {"guid": "guid-1", "hard": True})
    assert soft["mutatedEntities"]["DELETE"][0]["guid"] == "guid-1"
    assert hard is not None
    request = upstream.for_path(ENTITY + "/guid/guid-1")
    assert request is not None
    assert request.url.params.get("deleteType") == "HARD"


@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-12"])
async def test__validate_entity_relays_the_verdicts(writer: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-12: the draft travels to the verdicts API and the verdict document answers."""
    upstream.answers[VALIDATE] = (
        200,
        {
            "verdicts": [
                {
                    "ruleGuid": "r-1",
                    "ruleName": "datasets need owners",
                    "attribute": "owner",
                    "dimension": "COMPLETENESS",
                    "compliant": False,
                    "message": "owner is empty",
                }
            ],
            "unreadRules": [],
        },
    )
    async with writer() as session:
        answer = await call_tool(session, "validate_entity", {"draft": ENTITY_BODY["entity"]})
    assert answer["verdicts"][0]["message"] == "owner is empty"
    assert answer["unread_rules"] == []  # FastMCP's structured content speaks the model's field names
    verdicts_request = next(r for r in upstream.requests if str(r.url).startswith("http://verdicts.test"))
    assert upstream.bearer_of(verdicts_request)  # the verdicts leg forwards the caller too (DV-208)


@pytest.mark.covers("aurelius_atlas_mcp.auth.may_write", rules=["MCP-11"])
async def test__a_write_without_the_role_is_refused_with_no_upstream_call(reader: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-11: no write role means the tool errors and the catalogue sees nothing."""
    async with reader() as session:
        with pytest.raises(ToolError, match="atlas-write"):
            await call_tool(session, "save_entity", {"entity": ENTITY_BODY})
        with pytest.raises(ToolError, match="atlas-write"):
            await call_tool(session, "delete_entity", {"guid": "guid-1"})
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_mcp.auth.token_roles", rules=["MCP-11", "MCP-03"])
async def test__the_read_tools_need_no_write_role(reader: Any, upstream: FakeUpstream) -> None:  # noqa: ANN401 - the session factory
    """MCP-11 cuts one way only: a plain read caller still searches, with its own token."""
    upstream.answers["/api/atlas/v2/search/basic"] = (200, {"entities": [], "approximateCount": 0})
    async with reader() as session:
        answer = await call_tool(session, "search_entities", {"query": "orders"})
    assert answer["entities"] == []
    request = upstream.for_path("/api/atlas/v2/search/basic")
    assert request is not None
    assert upstream.bearer_of(request)


@pytest.mark.covers("aurelius_atlas_mcp.auth.token_roles", rules=["MCP-11", "MCP-28"])
def test__token_roles_reads_both_claim_shapes() -> None:
    """DD-891: the realm role and the catalogue client's resource role both count; another's does not."""
    realm = {"realm_access": {"roles": ["atlas-write"]}}
    resource = {"resource_access": {"aurelius-atlas-server": {"roles": ["atlas-write"]}}}
    other_client = {"resource_access": {"someone-else": {"roles": ["atlas-write"]}}}
    assert token_roles(realm, "aurelius-atlas-server") == {"atlas-write"}
    assert may_write(realm, "aurelius-atlas-server", "atlas-write")
    assert may_write(resource, "aurelius-atlas-server", "atlas-write")
    assert not may_write(other_client, "aurelius-atlas-server", "atlas-write")
    assert not may_write({}, "aurelius-atlas-server", "atlas-write")


@pytest.mark.covers("aurelius_atlas_mcp.auth.token_roles", rules=["MCP-28", "MCP-11"])
def test__the_role_of_the_app_audience_alone_does_not_write() -> None:
    """DD-898's regression: a browser token's `aurelius-write` is not the catalogue's role.

    The live realm answers a writer with `resource_access.aurelius.roles = [aurelius-write]`
    and `atlas-write` under the catalogue client. Reading the audience's entry — what this
    gate did before the chain ran it — refuses every writer (the e2e suite proves the live
    half of this claim).
    """
    browser_writer = {
        "azp": "aurelius",
        "resource_access": {
            "aurelius": {"roles": ["aurelius-write"]},
            "aurelius-atlas-server": {"roles": ["atlas-read", "atlas-write"]},
        },
    }
    audience_only = {"resource_access": {"aurelius": {"roles": ["aurelius-write"]}}}
    assert may_write(browser_writer, "aurelius-atlas-server", "atlas-write")
    assert not may_write(audience_only, "aurelius-atlas-server", "atlas-write")


@pytest.mark.covers("aurelius_atlas_mcp.auth.may_write", rules=["MCP-11"])
def test__an_empty_write_role_disables_the_gate() -> None:
    """The shared library's development posture carries over: an empty role asks nothing."""
    assert may_write({}, "aurelius-atlas-server", "")
