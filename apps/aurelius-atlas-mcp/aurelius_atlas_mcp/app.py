"""The app factory of Aurelius Atlas MCP — the composition root of the MCP API (MCP-01).

Everything is passed in: the settings (constructor, never ``os.environ`` — DD-23), and for
tests the auth verifier and the relayed clients. The factory wires:

- the two shared upstream pools — the catalogue (the clients) and the verdicts API;
- :func:`aurelius_atlas_mcp.tools.register_tools` — the twelve tools;
- ``GET /liveness`` (204, open like every aux API's health path);
- :class:`aurelius_atlas_mcp.auth.BearerGate` wrapped around FastMCP's own streamable-HTTP
  app (DD-888), so the shared verifier answers 401 before any MCP message is read.

The pools close in FastMCP's lifespan — uvicorn drives the gate, the gate forwards the
lifespan scope to the app FastMCP built, and FastMCP drives the lifespan registered here.

This is a **headless** service (DD-887): FastMCP's own ``/mcp`` is the API, and the only
hand-written HTTP route is the liveness probe — no ``/api``, no OpenAPI, no Swagger UI.
"""

import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx2
from aurelius_atlas_auth.auth import AuthConfig, KeycloakAuth
from aurelius_atlas_server_client.client import AtlasClient
from aurelius_atlas_validate_entity_client.client import ValidateEntityClient
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import Response

from aurelius_atlas_mcp.auth import BearerGate
from aurelius_atlas_mcp.globals import LIVENESS_PATH, MCP_PATH, NAME
from aurelius_atlas_mcp.relay import AtlasClients
from aurelius_atlas_mcp.settings import McpSettings
from aurelius_atlas_mcp.tools import register_tools

__all__ = ["create_app"]


def create_app(
    *,
    settings: McpSettings,
    auth: KeycloakAuth | None = None,
    clients: AtlasClients | None = None,
) -> BearerGate:
    """Build the MCP app: FastMCP's streamable-HTTP app behind the bearer gate (MCP-01).

    :param settings: the injected settings — the only configuration source (DD-23)
    :param auth: the verifier, injectable so a unit test swaps the Keycloak issuer
    :param clients: the relayed clients, injectable so a unit test stubs the upstreams
    :return: the ASGI app uvicorn serves — the gate wrapped around the MCP app
    """
    verifier = auth if auth is not None else _issuer(settings)
    atlas_http, verdicts_http = _pools(settings)

    # The clients are built on the pools; every tool call rebinds their token to the
    # calling agent's own token, so the seed value here is never sent (DD-890).
    atlas = AtlasClient(atlas_http, token="")
    validate_entity = ValidateEntityClient(verdicts_http, token="")
    relayed = clients if clients is not None else AtlasClients(atlas=atlas, validate_entity=validate_entity)

    @asynccontextmanager
    async def _lifespan(server: FastMCP[Any]) -> AsyncIterator[dict[str, Any]]:
        """Hold the upstream pools open for the life of the app, and close them on shutdown."""
        del server  # the lifespan's argument is the FastMCP server
        try:
            yield {}
        finally:
            await atlas_http.aclose()
            await verdicts_http.aclose()

    mcp: FastMCP[Any] = FastMCP(NAME, lifespan=_lifespan)
    register_tools(mcp, relayed, audience=settings.auth_audience, write_role=settings.write_role)

    @mcp.custom_route(LIVENESS_PATH, methods=["GET"])
    async def _liveness(request: Request) -> Response:
        """Answer 204 when the process serves; open like every aux API's health path."""
        del request  # the route's signature, decided by Starlette
        return Response(status_code=204)

    # The lifespan uvicorn drives is FastMCP's own (the gate forwards it), which drives
    # _lifespan above; the gate adds auth in front of every MCP message (MCP-02).
    return BearerGate(mcp.http_app(path=MCP_PATH), verifier)


def _issuer(settings: McpSettings) -> KeycloakAuth:
    """Build the verifier the app asks Keycloak about (MCP-02, DD-888) — one config for auth."""
    config = AuthConfig(
        server_url=str(settings.auth_server_url),
        realm=settings.auth_realm,
        audience=settings.auth_audience,
        write_role=settings.write_role,
        ca_file=str(settings.auth_ca_file) if settings.auth_ca_file else None,
    )
    return KeycloakAuth(config)


def _pools(settings: McpSettings) -> tuple[httpx2.AsyncClient, httpx2.AsyncClient]:
    """Build the two upstream pools: the catalogue and the verdicts API (DD-890).

    The issuer's CA is the TLS material, as in every aux app (DD-205); the settings'
    timeout bounds each upstream call.
    """
    ca_file = settings.auth_ca_file
    verify: ssl.SSLContext = (
        ssl.create_default_context(cafile=str(ca_file)) if ca_file else ssl.create_default_context()
    )
    timeout = settings.upstream_timeout_seconds
    atlas = httpx2.AsyncClient(base_url=str(settings.server_base_url), verify=verify, timeout=timeout)
    verdicts = httpx2.AsyncClient(base_url=str(settings.validate_entity_base_url), verify=verify, timeout=timeout)
    return atlas, verdicts
