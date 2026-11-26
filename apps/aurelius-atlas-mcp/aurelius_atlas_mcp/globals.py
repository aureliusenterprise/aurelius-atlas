"""The app's name, logger and the tool-error posture of a failed upstream (MCP-14, MCP-15)."""

import logging

NAME = "aurelius-atlas-mcp"
"""The app's name: the MCP server name and the logger's name."""

LOGGER = logging.getLogger(NAME)

NO_CONTENT = 204
"""The healthcheck's answer while the process serves (MCP-15)."""

LIVENESS_PATH = "/liveness"
"""The one HTTP route beside the MCP endpoint, and the one path the gate lets through anonymously."""

MCP_PATH = "/mcp"
"""The path the MCP Streamable HTTP endpoint answers on (MCP-01)."""

SERVER_ERROR = 500
"""The status from which a catalogue answer is an outage for the relay's wording (MCP-14)."""

BAD_GATEWAY = "upstream unavailable"
"""How a transport failure — an unreachable catalogue — is named to the tool caller (MCP-14)."""
