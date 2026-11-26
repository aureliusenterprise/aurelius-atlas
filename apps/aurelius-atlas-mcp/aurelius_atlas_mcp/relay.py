"""The relay: the caller's token, the per-call clients, and the upstream failure wording (MCP-03, MCP-14, DD-890).

Every tool runs through this module. Two rules decide the shape:

- **The caller's token is the only credential that travels upstream** (MCP-03). The app
  holds one pool and one client each; a tool asks for a ``with_token`` wrapper whose
  bearer source reads the current request. A :class:`~contextvars.ContextVar` cannot be
  needed here — FastMCP already binds the live HTTP request per call (its own
  ``get_http_request``), and the verified bearer hangs off its ``state`` (DD-888), which
  is request-scoped across concurrent calls by construction.
- **A failed upstream is a tool error that names it** (MCP-14). An Atlas status and its
  ``{errorCode, errorMessage}`` are the client library's parsed facts (CL-04); an
  unreachable catalogue is a transport failure. Neither becomes an empty answer.
"""

from typing import Any

import httpx2 as httpx
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError
from aurelius_atlas_validate_entity_client.client import ValidateEntityClient, ValidateEntityClientError
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request

from aurelius_atlas_mcp.globals import BAD_GATEWAY, LOGGER

BEARER_STATE_KEY = "aurelius_atlas_mcp_bearer"
"""The ASGI scope's ``state`` key the gate stores the verified bearer under (DD-888)."""

CLAIMS_STATE_KEY = "aurelius_atlas_mcp_claims"
"""The ASGI scope's ``state`` key the gate stores the verified claims under (DD-891)."""

NO_TOKEN = "no caller token: this app forwards the caller's own credential and never calls the catalogue anonymously"  # noqa: S105 - the refusal text, not a credential
"""The answer of a tool that somehow runs with no verified caller (MCP-02, MCP-03, DD-890)."""


def current_request() -> Request:
    """The live HTTP request of the MCP call.

    :raises ToolError: when the tool runs outside an HTTP request (a stdio call, or a bug)
    """
    try:
        return get_http_request()
    except RuntimeError as error:  # FastMCP raises when no HTTP transport is bound
        raise ToolError(NO_TOKEN) from error


def bearer_token() -> str:
    """The caller's verified bearer token for this MCP call (MCP-03).

    :raises ToolError: MCP-02 — the gate always sets this, so its absence means the tool
        ran on a path the gate did not cover, which is a bug that must fail closed.
    """
    token = getattr(current_request().state, BEARER_STATE_KEY, None)
    if not token:
        raise ToolError(NO_TOKEN)
    return cast_str(token)


def caller_claims() -> dict[str, Any]:
    """The verified claims of the caller, for the write gate (MCP-11, DD-891)."""
    claims = getattr(current_request().state, CLAIMS_STATE_KEY, None)
    return claims if isinstance(claims, dict) else {}


def cast_str(value: object) -> str:
    """The token as a string, the one narrow cast the ASGI state's ``Any`` needs."""
    return str(value)


class AtlasClients:
    """The app's two shared clients, built over the shared pools (DD-205's ownership).

    The pools belong to the app's lifespan; these clients carry no credential.
    """

    def __init__(self, atlas: AtlasClient, validate_entity: ValidateEntityClient) -> None:
        self.atlas = atlas
        self.validate_entity = validate_entity


def upstream_tool_error(error: Exception) -> ToolError:
    """Map an upstream failure to the MCP tool error of MCP-14.

    The text names what the caller must act on: the upstream status and its
    ``{errorCode, errorMessage}`` for an Atlas refusal (CL-04), the transport failure for
    an unreachable catalogue. The raw body never travels, and an empty result is never
    invented in place of a failure.
    """
    if isinstance(error, AtlasClientError):
        info = error.info
        detail = (
            f"[{info.error_code}] {info.error_message}"
            if info and info.error_code
            else (info.error_message if info else "no detail")
        )
        message = f"the catalogue answered {error.status_code}: {detail}"
    elif isinstance(error, ValidateEntityClientError):
        detail = (
            f"[{error.error_code}] {error.error_message}" if error.error_code else (error.error_message or "no detail")
        )
        message = f"the verdicts API answered {error.status_code}: {detail}"
    elif isinstance(error, httpx.RequestError):
        message = f"{BAD_GATEWAY}: {error.__class__.__name__}: {error}"
    else:
        raise error
    LOGGER.info("Upstream failure surfaced as a tool error: %s", message)
    return ToolError(message)


async def relay(awaitable: Any) -> Any:  # noqa: ANN401 - the tool's parsed answer, any model
    """Await an upstream call, turning its failure into the tool error of MCP-14."""
    try:
        return await awaitable
    except (AtlasClientError, ValidateEntityClientError, httpx.RequestError) as error:
        raise upstream_tool_error(error) from error
