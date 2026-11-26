"""Aurelius Atlas MCP — the catalogue's MCP API surface.

The package exposes the app factory and its settings; everything else is internal to the
composition root (MCP-01, ADR 072).
"""

from aurelius_atlas_mcp.app import create_app
from aurelius_atlas_mcp.settings import McpSettings

__all__ = ["McpSettings", "create_app"]
