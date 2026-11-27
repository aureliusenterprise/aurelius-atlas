"""Run the MCP app under uvicorn, the way every aux API runs (DD-887)."""

from typing import Any

import uvicorn

from aurelius_atlas_mcp.app import create_app
from aurelius_atlas_mcp.globals import LOGGER, NAME
from aurelius_atlas_mcp.settings import McpSettings


def uvicorn_options(settings: McpSettings) -> dict[str, Any]:
    """The uvicorn options the settings decide: host, port, TLS, log level.

    :param settings: the injected settings
    :return: the keyword arguments of :func:`uvicorn.run`
    """
    options: dict[str, Any] = {
        "host": settings.host,
        "port": settings.port,
        "log_level": settings.log_level.lower(),
    }
    if settings.tls is not None:
        options["ssl_certfile"], options["ssl_keyfile"] = settings.tls
    return options


def run() -> None:
    """Serve the app. This is the console entry point of the package."""
    settings = McpSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    LOGGER.info("Starting %s on port %d", NAME, settings.port)
    uvicorn.run(create_app(settings=settings), **uvicorn_options(settings))


if __name__ == "__main__":
    run()
