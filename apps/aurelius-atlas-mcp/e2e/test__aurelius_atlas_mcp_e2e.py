"""E2E: the MCP front door live over the chain (MCP-25..MCP-32).

The suite drives the deployed app on the stack of ``e2e/docker-compose.yaml``: the
twelve tools forward the caller's own bearer to a real Atlas server and the real
verdicts API (MCP-03 made visible), so every answer here came through the whole
chain. Tokens are the browser's own — the public ``aurelius`` client's password
grant (AUX-04) — exactly what an agent mints at the front door.

The increment's headline is the live write-gate proof (MCP-28, DD-898): a real
writer token carries the catalogue write role under the catalogue client, the
writer's ``save_entity`` lands, and a reader's write refuses before the server
ever sees it. Unit fakes had baked the claim location wrong; only this chain
could show it. Names are keyed by a ``zz<run>`` word and self-cleaned (DD-223).
"""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any
from uuid import uuid4

import httpx2 as httpx
import pytest
from aurelius_atlas_model.instance import AtlasEntity
from mcp import ClientSession

SessionMaker = Callable[[str], AbstractAsyncContextManager[ClientSession]]
"""The conftest's session factory: open one MCP session presenting the bearer given to it."""

Seeder = Callable[[list[AtlasEntity]], Awaitable[dict[str, str]]]
"""The conftest's seeder: entities in, ``{temp index: real guid}`` out (self-cleaned)."""

WRITE_ROLE = "atlas-write"
"""The catalogue write role the write gate requires (MCP-11, MCP-28)."""


class ToolRefusalError(RuntimeError):
    """A tool answered an MCP error — the live twin of the unit helper's raise (MCP-14)."""


async def _call(session: ClientSession, name: str, arguments: dict[str, Any] | None = None) -> Any:  # noqa: ANN401 - the tool's structured answer
    """Call a tool through the live session; answer its structured content or raise the refusal."""
    result = await session.call_tool(name, arguments or {})
    if result.is_error:
        texts = [text for content in result.content if isinstance(text := getattr(content, "text", None), str)]
        msg = texts[0] if texts else str(result)
        raise ToolRefusalError(msg)
    return result.structured_content


def _dataset(run: str, suffix: str = "orders") -> dict[str, Any]:
    """The ``save_entity`` arguments for one ``m4i_dataset`` named for this run (no mandatory attributes).

    The tool's ``entity`` argument is the whole ``AtlasEntityWithExtInfo`` body, so the
    record nests one level deeper (the unit suite's ``ENTITY_BODY`` shape).
    """
    return {
        "entity": {
            "entity": {
                "typeName": "m4i_dataset",
                "attributes": {"qualifiedName": f"zz{run}.{suffix}", "name": f"zz{run} {suffix}"},
            },
        },
    }


def _present_rule(run: str) -> dict[str, Any]:
    """An ACTIVE ATTRIBUTE_PRESENT rule for ``m4i_dataset`` over ``name`` (MCP-12).

    The shape the quality scanners seed (VEV-03): the qualifiedName names the type,
    and the governance type's ``id`` is mandatory, so the seed carries the editor's -1.
    """
    return {
        "name": f"zz{run}.name-present",
        "qualifiedName": f"m4i_dataset--zz{run}.name-present",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "name",
        "qualityDimension": "COMPLETENESS",
        "compliantMessage": f"zz{run} the draft carries a name",
        "nonCompliantMessage": f"zz{run} the draft carries no name",
    }


@pytest.fixture()
def run() -> str:
    """One word making this test's names unique in the shared store (DD-223)."""
    return uuid4().hex[:10]


# impact=critical, likelihood=high (the deployed gate; MCP-02's live twin)
@pytest.mark.high
@pytest.mark.covers(
    "aurelius_atlas_mcp.app.create_app", "aurelius_atlas_mcp.auth.BearerGate.__call__", rules=["MCP-32"]
)
async def test__the_wire_gate_and_liveness(anonymous_client: httpx.AsyncClient) -> None:
    """Over the image: no bearer is the 401 with the challenge; liveness is open (MCP-02, MCP-15)."""
    refused = await anonymous_client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    alive = await anonymous_client.get("/liveness")

    assert refused.status_code == 401
    assert refused.headers["www-authenticate"] == "Bearer"
    assert alive.status_code == 204


# impact=major, likelihood=high (the deployed pair's purpose; young, churn on its path)
@pytest.mark.high
@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-25", "MCP-04"])
async def test__the_image_advertises_the_twelve_tools(mcp_session: SessionMaker, token: str) -> None:
    """A real client session over the wire sees the twelve catalogue tools (MCP-04 over MCP-25's stack)."""
    async with mcp_session(token) as session:
        names = {tool.name for tool in (await session.list_tools()).tools}

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


# impact=critical, likelihood=high (the increment's headline: the caller's token, live)
@pytest.mark.high
@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-29", "MCP-13"])
async def test__server_status_names_the_caller(mcp_session: SessionMaker, token: str) -> None:
    """``server_status`` answers through the chain and names the caller: the token travelled (MCP-03)."""
    async with mcp_session(token) as session:
        answer = await _call(session, "server_status")

    assert answer["user_name"] == "aurelius-writer"
    assert answer["entity_create_allowed"] is True
    assert answer["status"] == "ACTIVE"


# impact=critical, likelihood=high (DD-898's live proof, writer side)
@pytest.mark.high
@pytest.mark.covers(
    "aurelius_atlas_mcp.tools.register_tools",
    "aurelius_atlas_mcp.auth.may_write",
    rules=["MCP-28", "MCP-29", "MCP-10"],
)
async def test__a_writers_save_lands_through_the_front_door(mcp_session: SessionMaker, token: str, run: str) -> None:
    """A browser writer token passes the gate and the server authorizes the write (MCP-28, MCP-29).

    The entity arrives over MCP, is read back over MCP, and is deleted over MCP — the
    whole write path rides the caller's own token, which carries ``atlas-write`` under
    the catalogue client (the claim DD-898 fixed).
    """
    async with mcp_session(token) as session:
        saved = await _call(session, "save_entity", _dataset(run))
        created = saved["mutatedEntities"]["CREATE"]
        guid = str(created[0]["guid"])
        assert guid
        found = await _call(session, "get_entity", {"guid": guid})
        deleted = await _call(session, "delete_entity", {"guid": guid, "hard": True})

    assert found["entity"]["attributes"]["qualifiedName"] == f"zz{run}.orders"
    assert deleted["mutatedEntities"]


# impact=critical, likelihood=high (DD-898's live proof, reader side — the bug)
@pytest.mark.high
@pytest.mark.covers(
    "aurelius_atlas_mcp.auth.may_write",
    "aurelius_atlas_mcp.tools.register_tools",
    rules=["MCP-30", "MCP-11"],
)
async def test__a_reader_write_refuses_before_the_server_sees_it(
    mcp_session: SessionMaker, reader_token: str, run: str
) -> None:
    """The reader holds atlas-read only: the tool refuses with the write role's name, and the store is clean.

    The refusal is an MCP tool error (MCP-14's live sibling), not an HTTP 403 — the gate
    answers where the tool stands, before the server sees a write (MCP-11). The old gate
    read the audience's roles and refused the *writer* too (DD-898); the writer test above
    and this one together pin both sides of the claim location.
    """
    async with mcp_session(reader_token) as session:
        with pytest.raises(ToolRefusalError, match=WRITE_ROLE):
            await _call(session, "save_entity", _dataset(run))
        # The store stayed clean: nothing answers the name the write would have used.
        headers = await _call(session, "search_entities", {"type_name": "m4i_dataset", "limit": 100})
    assert all(f"zz{run}" not in str(header["qualified_name"]) for header in headers["entities"])


# impact=major, likelihood=high (the gated classification pair, live)
@pytest.mark.high
@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-10"])
async def test__classifications_add_and_remove_on_a_seeded_entity(
    mcp_session: SessionMaker,
    token: str,
    run: str,
    seed_entities: Seeder,
) -> None:
    """PII lands on a catalogue entity over MCP and comes off again (MCP-10 live)."""
    guid = (
        await seed_entities(
            [
                AtlasEntity(
                    type_name="m4i_dataset",
                    guid="-0",
                    attributes={"qualifiedName": f"zz{run}.classified", "name": f"zz{run} classified"},
                )
            ]
        )
    )["0"]

    async with mcp_session(token) as session:
        await _call(session, "add_classifications", {"guid": guid, "classifications": [{"typeName": "PII"}]})
        with_pii = await _call(session, "get_entity", {"guid": guid})
        await _call(session, "remove_classification", {"guid": guid, "name": "PII"})
        without = await _call(session, "get_entity", {"guid": guid})

    assert "PII" in str(with_pii)
    assert "PII" not in str(without)


# impact=major, likelihood=high (the read path over live data)
@pytest.mark.high
@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-31", "MCP-05", "MCP-06", "MCP-09"])
async def test__the_read_tools_answer_live_data(
    mcp_session: SessionMaker,
    token: str,
    run: str,
    seed_entities: Seeder,
) -> None:
    """Search, get, list and get_type answer the seeded dataset and the m4i type system (MCP-31)."""
    guid = (
        await seed_entities(
            [
                AtlasEntity(
                    type_name="m4i_dataset",
                    guid="-0",
                    attributes={"qualifiedName": f"zz{run}.readable", "name": f"zz{run} readable"},
                )
            ]
        )
    )["0"]

    async with mcp_session(token) as session:
        search = await _call(session, "search_entities", {"type_name": "m4i_dataset", "limit": 100})
        entity = await _call(session, "get_entity", {"guid": guid})
        types = await _call(session, "list_types", {"kind": "entity"})
        typedef = await _call(session, "get_type", {"name": "m4i_dataset"})

    assert guid in {header["guid"] for header in search["entities"]}
    assert entity["entity"]["typeName"] == "m4i_dataset"
    assert "m4i_dataset" in {header["name"] for header in types["types"]}
    assert typedef["category"] == "ENTITY"


# impact=major, likelihood=high (MCP-12 over the real verdicts upstream)
@pytest.mark.high
@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-31", "MCP-12"])
async def test__validate_entity_answers_a_seeded_rule_live(
    mcp_session: SessionMaker,
    token: str,
    run: str,
    seed_entities: Seeder,
) -> None:
    """A rule seeded through the chain's catalogue answers the draft through the front door (MCP-12).

    The verdicts API reads its rules from the same server the tools relay to, with its
    own identity (VEV-04) and its cache off (the layer), so a fresh seed answers at once.
    """
    await seed_entities(
        [
            AtlasEntity(
                type_name="m4i_gov_data_quality",
                guid="-0",
                attributes={"id": -1, **_present_rule(run)},
            )
        ]
    )
    draft = {"typeName": "m4i_dataset", "attributes": {"qualifiedName": f"zz{run}.draft", "name": f"zz{run} draft"}}

    async with mcp_session(token) as session:
        answer = await _call(session, "validate_entity", {"draft": draft})

    verdicts = [verdict for verdict in answer["verdicts"] if run in str(verdict)]
    assert verdicts, f"the seeded rule answered nothing: {answer}"
    assert verdicts[0]["compliant"] is True


# impact=major, likelihood=low (the live 404 relay: an unknown guid is a tool error, not a crash)
@pytest.mark.high
@pytest.mark.covers("aurelius_atlas_mcp.tools.register_tools", rules=["MCP-14"])
async def test__an_unknown_guid_is_a_tool_error_naming_the_status(mcp_session: SessionMaker, token: str) -> None:
    """Upstream failures travel back as MCP tool errors that name the trouble (MCP-14 live)."""
    async with mcp_session(token) as session:
        with pytest.raises(ToolRefusalError):
            await _call(session, "get_entity", {"guid": "00000000-0000-0000-0000-000000000000"})
