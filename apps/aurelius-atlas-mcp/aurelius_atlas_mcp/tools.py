"""The twelve catalogue tools of the MCP surface (MCP-04..MCP-14, DD-889).

Every tool is a thin relay: it calls one method the client library already answers and
projects the answer to a compact shape. No catalogue rule is decided here — the server
answers them (R4, ADR 072). Two shapes dominate:

- **Reads answer headers, not entities** (DD-889). A search of a populated catalogue over
  whole entities is megabytes a model cannot read; the caller gets the guid and asks for
  the record it wants (MCP-05, MCP-06).
- **A failure is a tool error that names it** (MCP-14). ``relay`` maps the upstream
  answer; no tool invents an empty result.

The tools are built by a factory because they close over the app's clients; the server
object and the settings are the only state they hold.
"""

import asyncio
from typing import Annotated, Any, cast

from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.instance.classification import AtlasClassification
from aurelius_atlas_model.instance.entity_with_ext_info import AtlasEntityWithExtInfo
from aurelius_atlas_server_client.client import AtlasClient
from aurelius_atlas_server_client.models import DeleteType
from aurelius_atlas_validate_entity_client.models import ValidationResponse
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from aurelius_atlas_mcp.auth import may_write
from aurelius_atlas_mcp.globals import LOGGER
from aurelius_atlas_mcp.relay import AtlasClients, bearer_token, caller_claims, relay

DEFAULT_LIMIT = 10
"""The page a read answers when the caller names none: small enough for a context window."""

MAX_LIMIT = 100
"""The largest page a tool accepts — the ceiling on one tool call's payload."""

MAX_DEPTH = 10
"""The deepest lineage walk a tool answers (the server bounds the graph, MCP-07)."""

LINEAGE_DIRECTIONS = ("BOTH", "INPUT", "OUTPUT")
"""The directions ``get_lineage`` accepts, as the server names them (MCP-07)."""

TYPE_KINDS = ("entity", "classification", "relationship", "struct", "enum", "business-metadata")
"""The kind words ``list_types`` accepts, mapped to the server's filter values."""

_SERVER_KINDS = {
    "entity": "ENTITY",
    "classification": "CLASSIFICATION",
    "relationship": "RELATIONSHIP",
    "struct": "STRUCT",
    "enum": "ENUM",
    "business-metadata": "BUSINESS_METADATA",
}


def register_tools(mcp: FastMCP[Any], clients: AtlasClients, role_client: str, write_role: str) -> None:  # noqa: C901, PLR0915 - the tool table: twelve thin relays read as one surface
    """Register every catalogue tool on the server (MCP-04).

    :param mcp: the FastMCP server to register on
    :param clients: the app's shared clients, relayed per call with the caller's token
    :param role_client: the client whose ``resource_access`` entry the write gate reads (MCP-28)
    :param write_role: the role a write tool requires (MCP-11)
    """

    def atlas_client() -> AtlasClient:
        """The shared Atlas client, bound to the calling agent's token (MCP-03, DD-890)."""
        return clients.atlas.with_token(bearer_token)

    def require_write(action: str) -> None:
        """Refuse a write the caller may not run, before any upstream call (MCP-11)."""
        if not may_write(caller_claims(), role_client, write_role):
            LOGGER.info("Refused the write tool %s: the caller lacks %r", action, write_role)
            msg = f"the write role {write_role!r} is required to {action}"
            raise ToolError(msg)

    # -- discovery and read -------------------------------------------------

    @mcp.tool
    async def search_entities(
        query: Annotated[str | None, Field(description="Free text the answer must match.")] = None,
        type_name: Annotated[str | None, Field(description="Keep only this entity type (and its sub types).")] = None,
        classification: Annotated[
            str | None,
            Field(description="Keep only entities carrying this classification."),
        ] = None,
        limit: Annotated[int, Field(ge=1, le=MAX_LIMIT, description="How many headers to answer.")] = DEFAULT_LIMIT,
        offset: Annotated[int, Field(ge=0, description="How many headers to skip.")] = 0,
    ) -> dict[str, Any]:
        """Search the catalogue and answer compact entity headers — never whole entities (MCP-05).

        Use the ``guid`` of the header you care about with ``get_entity`` for its full record.
        """
        parameters = SearchParameters(
            query=query, type_name=type_name, classification=classification, limit=limit, offset=offset
        )
        answer = await relay(atlas_client().search.search_with_parameters(parameters))
        return {
            "approximate_count": answer.approximate_count,
            "entities": [_header(h) for h in answer.entities or []],
        }

    @mcp.tool
    async def get_entity(
        guid: Annotated[str | None, Field(description="The entity's GUID.")] = None,
        type_name: Annotated[str | None, Field(description="The entity type, with unique_attributes.")] = None,
        unique_attributes: Annotated[
            dict[str, Any] | None, Field(description="The unique attribute values, with type_name.")
        ] = None,
    ) -> dict[str, Any]:
        """Read one entity in full, by GUID or by its unique attributes (MCP-06).

        Give exactly one locator: the ``guid``, or ``type_name`` with ``unique_attributes``.
        """
        client = atlas_client()
        both_locators = guid and (type_name or unique_attributes)
        neither_locator = not guid and not (type_name and unique_attributes)
        if both_locators or neither_locator:
            msg = "give a guid, or type_name with unique_attributes — not both, not neither"
            raise ToolError(msg)
        if guid:
            found = await relay(client.entity.by_guid(guid))
        else:
            found = await relay(client.entity.by_unique_attributes(type_name, unique_attributes))  # pyright: ignore[reportArgumentType] - checked by neither_locator
        return _entity(found)

    @mcp.tool
    async def get_lineage(
        guid: Annotated[str, Field(description="The entity to walk lineage from.")],
        depth: Annotated[int, Field(ge=1, le=MAX_DEPTH, description="How many hops to walk.")] = 3,
        direction: Annotated[str, Field(description="Which way to walk: BOTH, INPUT or OUTPUT.")] = "BOTH",
    ) -> dict[str, Any]:
        """Answer the lineage graph of an entity: its nodes as headers, its edges as relations (MCP-07)."""
        if direction not in LINEAGE_DIRECTIONS:
            msg = f"direction must be one of {', '.join(LINEAGE_DIRECTIONS)}"
            raise ToolError(msg)
        info = await relay(atlas_client().lineage.get(guid, depth, direction))  # type: ignore[arg-type] - checked above
        return {
            "base_entity_guid": guid,
            "depth": depth,
            "direction": direction,
            "nodes": [
                {"guid": str(node_guid), "type_name": header.type_name, "display_text": header.display_text}
                for node_guid, header in info.guid_entity_map.items()
            ],
            "relations": [
                {"from_entity_id": str(rel.from_entity_id), "to_entity_id": str(rel.to_entity_id)}
                for rel in info.relations
            ],
        }

    @mcp.tool
    async def server_status() -> dict[str, Any]:
        """Answer the catalogue's version and state, and what this caller's session may do (MCP-13)."""
        client = atlas_client()
        version, status, session = await relay(
            _gather(client.admin.version(), client.admin.status(), client.admin.session())
        )
        return {
            "version": version.version,
            "name": version.name,
            "status": status.status,
            "user_name": session.user_name,
            "entity_create_allowed": session.entity_create_allowed,
            "entity_update_allowed": session.entity_update_allowed,
        }

    # -- the type system ----------------------------------------------------

    @mcp.tool
    async def get_type(
        name: Annotated[str, Field(description="The type's name, e.g. ``m4i_dataset``.")],
    ) -> dict[str, Any]:
        """Answer one type definition: its attributes, its supers, and its kind (MCP-09)."""
        found = await relay(atlas_client().types.typedef_by_name(name))
        return found.to_json()

    @mcp.tool
    async def list_types(
        kind: Annotated[str, Field(description=f"One of: {', '.join(TYPE_KINDS)}.")],
    ) -> dict[str, Any]:
        """Answer the headers of every type of one kind (MCP-09)."""
        server_kind = _SERVER_KINDS.get(kind.lower())
        if server_kind is None:
            msg = f"kind must be one of {', '.join(TYPE_KINDS)}"
            raise ToolError(msg)
        headers = await relay(atlas_client().types.typedef_headers({"type": server_kind}))
        return {"kind": kind, "types": [{"name": h.name, "guid": h.guid, "category": str(h.category)} for h in headers]}

    # -- the glossary -------------------------------------------------------

    @mcp.tool
    async def search_glossary(
        glossary_guid: Annotated[str, Field(description="The glossary to read terms from.")],
        query: Annotated[str | None, Field(description="Keep terms whose name or description matches.")] = None,
        limit: Annotated[int, Field(ge=1, le=MAX_LIMIT, description="How many terms to answer.")] = DEFAULT_LIMIT,
        offset: Annotated[int, Field(ge=0, description="How many terms to skip.")] = 0,
    ) -> dict[str, Any]:
        """Answer the terms of a glossary as headers (MCP-08)."""
        terms = await relay(atlas_client().glossary.glossary_terms_headers(glossary_guid, limit=limit, offset=offset))
        chosen = [term for term in terms if _matches(term, query)]
        return {
            "glossary_guid": glossary_guid,
            "terms": [
                {"guid": term.term_guid, "display_text": term.display_text, "qualified_name": term.qualified_name}
                for term in chosen
            ],
        }

    # -- writes (gated) -----------------------------------------------------

    @mcp.tool
    async def save_entity(
        entity: Annotated[
            dict[str, Any],
            Field(description="The ``AtlasEntityWithExtInfo`` body: ``entity`` with ``typeName`` and ``attributes``."),
        ],
    ) -> dict[str, Any]:
        """Create or update an entity, as the caller (MCP-10). Needs the write role (MCP-11)."""
        require_write("save an entity")
        body = AtlasEntityWithExtInfo.model_validate(entity)
        answer = await relay(atlas_client().entity.create_or_update(body))
        return answer.to_json()

    @mcp.tool
    async def add_classifications(
        guid: Annotated[str, Field(description="The entity to classify.")],
        classifications: Annotated[
            list[dict[str, Any]], Field(description="The classification bodies, each with ``typeName``.")
        ],
    ) -> dict[str, Any]:
        """Add classifications to an entity (MCP-10). Needs the write role (MCP-11)."""
        require_write("add classifications")
        bodies = [AtlasClassification.model_validate(item) for item in classifications]
        await relay(atlas_client().entity.add_classifications(guid, bodies))
        return {"guid": guid, "added": [str(b.type_name) for b in bodies]}

    @mcp.tool
    async def remove_classification(
        guid: Annotated[str, Field(description="The entity to remove the classification from.")],
        name: Annotated[str, Field(description="The classification's type name.")],
    ) -> dict[str, Any]:
        """Remove one classification from an entity (MCP-10). Needs the write role (MCP-11)."""
        require_write("remove a classification")
        await relay(atlas_client().entity.delete_classification(guid, name))
        return {"guid": guid, "removed": name}

    @mcp.tool
    async def delete_entity(
        guid: Annotated[str, Field(description="The entity to delete.")],
        hard: Annotated[  # noqa: FBT002 - the MCP schema exposes this as a named parameter, not a positional flag
            bool, Field(description="Hard-delete (purge) instead of the server's default.")
        ] = False,
    ) -> dict[str, Any]:
        """Delete an entity and what it owns (MCP-10). Needs the write role (MCP-11)."""
        require_write("delete an entity")
        answer = await relay(atlas_client().entity.delete_by_guid(guid, delete_type=DeleteType.HARD if hard else None))
        return answer.to_json()

    @mcp.tool
    async def validate_entity(
        draft: Annotated[
            dict[str, Any], Field(description="The draft entity: its ``typeName`` and its ``attributes`` at least.")
        ],
    ) -> ValidationResponse:
        """Answer the live governance verdicts of the draft, from the verdicts API (MCP-12)."""
        answer = await relay(clients.validate_entity.with_token(bearer_token).validate(draft))
        verdicts = cast("ValidationResponse", answer)
        LOGGER.debug("Answered %d verdicts for a draft", len(verdicts.verdicts))
        return verdicts


def _header(header: Any) -> dict[str, Any]:  # noqa: ANN401 - AtlasEntityHeader
    """The compact projection of an entity header (MCP-05, DD-889): identity and summary only.

    The server's bulk-header noise — ``parameters``, ``contacts``, the full classification
    bodies — is a display concern of the webapp and stays out of a model's context.
    """
    return {
        "guid": header.guid,
        "type_name": header.type_name,
        "display_text": header.display_text,
        "status": str(header.status) if header.status else None,
        "classifications": header.classification_names or [],
        "qualified_name": (header.attributes or {}).get("qualifiedName"),
    }


def _entity(found: Any) -> dict[str, Any]:  # noqa: ANN401 - AtlasEntityWithExtInfo
    """The whole entity as the server answers it, plus its referred entities (MCP-06)."""
    return found.to_json()


def _matches(term: Any, query: str | None) -> bool:  # noqa: ANN401 - AtlasRelatedTermHeader
    """Whether a term header matches the glossary query: name or description, any case (MCP-08)."""
    if not query:
        return True
    needle = query.lower()
    haystack = " ".join(str(part or "") for part in (term.display_text, term.qualified_name, term.description))
    return needle in haystack.lower()


async def _gather(*awaitables: Any) -> list[Any]:  # noqa: ANN401 - the admin answers
    """Await several upstream calls together, so one status read is one round trip (MCP-13)."""
    return list(await asyncio.gather(*awaitables))
